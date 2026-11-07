"""Import only the six supplied official Simulation catalog PDFs, additively."""
import argparse
import json
import re
import shutil
from pathlib import Path
from sqlalchemy import delete, update
from app.config import ROOT
from app.db import session
from app.models import Source, Chunk, Course, Setting, Cache
from app.platform_models import Program, Curriculum, RequirementGroup, CurriculumCourse
from app.programs import CURRICULA, LEGACY_SOURCES, PROGRAM_NAMES
from app.ingest import pages, sha, chunk_page
from app.text import embed, embedder, normalize
from app.retrieval import check_index
from app.derive_rules import admission_rules

ROLES=['description','outcomes','acceptance','degree','courses','paradigm']
ROW=re.compile(r'^\s*([A-Z]{4}\d{3}|FINEART|POLSHUM|RELSPHI|CSSEGRO|SWERLIS)\s+(.*?)\s*(\d{1,2})\s+(University Requirement|Faculty Requirement|Major Requirement|Major Elective)\s*$')

def parse_courses(text_pages):
    rows=[]
    track=None
    for page,text in enumerate(text_pages,1):
        lines=text.splitlines()
        for i,line in enumerate(lines):
            heading=re.fullmatch(r'\s*(Intensive|Intermediate|Regular) English Students\s*',line)
            if heading:
                track=heading[1].lower()
            match=ROW.match(line)
            if not match:
                continue
            code,name,credits,category=match.groups()
            if not name.strip():
                before=next((s.strip() for s in reversed(lines[:i]) if s.strip()),'')
                after=next((s.strip() for s in lines[i+1:] if s.strip()),'')
                if ROW.match(before) or ROW.match(after) or not before or not after:
                    raise ValueError('Ambiguous wrapped course title: '+code)
                name=before+' '+after
            if not track:
                raise ValueError('Course without an English track: '+code)
            rows.append(dict(code=code,name=name.strip(),credits=int(credits),category=category,track=track,page=page,
                             row=f'{code} {name.strip()} {credits} {category}'))
    if {r['track'] for r in rows}!={'regular','intermediate','intensive'}:
        raise ValueError('Missing course-track table')
    return rows

def import_simulation(folder):
    files={}
    for path in Path(folder).glob('*majorCode=248*pdf'):
        match=re.search(r'&page=([0-5])&catalogID=44',path.name)
        if match:
            index=int(match[1])
            if index in files:
                raise ValueError('Multiple files for catalog page '+str(index))
            files[index]=path
    if set(files)!=set(range(6)):
        raise ValueError('Need all six official majorCode=248 catalogID=44 PDFs')
    texts={i:pages(p) for i,p in files.items()}
    for i,text_pages in texts.items():
        if any(not p.strip() for p in text_pages):
            raise ValueError('Image-only page; OCR not implemented')
        if 'Computer Simulation in Science and' not in text_pages[0]:
            raise ValueError('Unexpected program header: '+str(i))
    rows=parse_courses(texts[4])
    breakdown={}
    for label in ['University Requirement','Faculty Requirement','Major Requirement','Major Elective']:
        match=re.search(re.escape(label)+r'\s+(\d+)',texts[3][0])
        if not match: raise ValueError('Missing degree component: '+label)
        breakdown[label]=int(match[1])
    additions={}
    for track in ['regular','intermediate','intensive']:
        selected=[r for r in rows if r['track']==track]
        additions[track]=sum(r['credits'] for r in selected if r['code'] in ['ENGR101','ENGR102'])
        if sum(r['credits'] for r in selected)!=sum(breakdown.values())+additions[track]:
            raise ValueError('Course/degree total mismatch: '+track)
    admission=admission_rules(texts[2][0])
    model=embedder()
    local=ROOT/'sources/simulation'
    local.mkdir(parents=True,exist_ok=True)
    cid=CURRICULA['simulation']
    with session() as db,db.begin():
        check_index(db)
        for program in ['software','simulation']:
            db.merge(Program(id=program,name_ar=PROGRAM_NAMES[program],name_en='Computer Simulation in Science and Engineering' if program=='simulation' else 'Software Engineering',official_code='248' if program=='simulation' else '237',verified=True))
        db.flush()
        for program in ['software','simulation']:
            if not db.get(Curriculum,CURRICULA[program]):
                db.add(Curriculum(id=CURRICULA[program],program_id=program,catalog_id='44',year='2024-2025',title=PROGRAM_NAMES[program],status='published'))
        db.flush()
        db.execute(update(Source).where(Source.id.in_(LEGACY_SOURCES)).values(curriculum_id=CURRICULA['software'],scope='program',review_status='published'))
        db.execute(update(Source).where(Source.id=='academic_guidance').values(scope='university',review_status='published'))
        for i,role in enumerate(ROLES):
            sid='simulation_'+role
            path=local/(role+'_2024_2025.pdf')
            shutil.copy2(files[i],path)
            db.merge(Source(id=sid,title=path.name,path=str(path.relative_to(ROOT)),url=f'https://reg.bethlehem.edu:100/CaDetails/ProgramDescription.aspx?majorCode=248&page={i}&catalogID=44&type=1',kind='catalog',provenance='OFFICIAL_CATALOG_PRINT',dates={'catalog_year':'2024-2025'},sha256=sha(path.read_bytes()),active=True,curriculum_id=cid,scope='program',review_status='published',document_role=role))
            db.flush()
            chunks=[]
            for page,text in enumerate(texts[i],1):
                values=[r['row'] for r in rows if r['page']==page] if i==4 else list(chunk_page(text,tokenizer=model.tokenizer))
                chunks.extend((page,value) for value in dict.fromkeys(values))
            vectors=embed([value for _,value in chunks])
            ids=[]
            for (page,value),vector in zip(chunks,vectors):
                key=sha(sid+str(page)+value)
                ids.append(key)
                db.merge(Chunk(id=key,source_id=sid,page=page,topic=sid,text=value,normalized=normalize(value),token_count=len(model.tokenizer.encode(value)),chunk_hash=sha(value),details={},embedding=vector))
            db.flush()
            db.execute(delete(Chunk).where(Chunk.source_id==sid,Chunk.id.not_in(ids)))
        for label,credits in breakdown.items():
            db.merge(RequirementGroup(id=cid+':'+label,curriculum_id=cid,name=label,category=label,kind='elective' if label=='Major Elective' else 'all',credits=credits,evidence=[{'source_id':'simulation_degree','page':1}]))
        db.flush()
        grouped={}
        for row in rows: grouped.setdefault(row['code'],[]).append(row)
        for code,variants in grouped.items():
            first=variants[0]
            if len({(v['credits'],v['category'],v['name']) for v in variants})!=1:
                raise ValueError('Conflicting course variants: '+code)
            courseid='44:'+code
            proof=[{'source_id':'simulation_courses','page':v['page'],'track':v['track']} for v in variants]
            placeholder=not bool(re.fullmatch(r'[A-Z]{4}\d{3}',code))
            if not db.get(Course,courseid):
                db.add(Course(id=courseid,code=code,name=first['name'],credits=first['credits'],category=first['category'],applicability={'tracks':sorted({v['track'] for v in variants})},evidence=proof,placeholder=placeholder))
                db.flush()
            db.merge(CurriculumCourse(id=cid+':'+code,curriculum_id=cid,course_id=courseid,group_id=cid+':'+first['category'],title=first['name'],credits=first['credits'],tracks=sorted({v['track'] for v in variants}),mandatory=first['category']!='Major Elective',options=re.findall(r'[A-Z]{4}\d{3}',first['name']) if placeholder else [],evidence=proof,verified=True))
        db.merge(Setting(key='simulation_degree',value={'breakdown':breakdown,'additions':additions,'source_id':'simulation_degree','page':1}))
        db.merge(Setting(key='simulation_admission',value=admission))
        db.merge(Setting(key='simulation_revision',value={'hash':sha(''.join(sha(files[i].read_bytes()) for i in range(6)))}))
        db.execute(delete(Cache))
    print(json.dumps({'documents':6,'pages':sum(len(p) for p in texts.values()),'course_variants':len(rows),'unique_course_or_group_codes':len(grouped),'breakdown':breakdown,'english_additions':additions,'prerequisites':'not supplied; not inferred'}))

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--folder',type=Path,default=Path.home()/'Downloads')
    import_simulation(parser.parse_args().folder)
