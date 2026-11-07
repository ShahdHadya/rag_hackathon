import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
import pymupdf
from pypdf import PdfReader
from sqlalchemy import delete
from app.config import ROOT, EMBEDDING_MODEL
from app.db import session
from app.models import Source, Chunk, Course, Prerequisite, Setting, FAQ, Cache
from app.text import normalize, embed, embedder, embedding_spec
from app.pdf_reading import positioned_text

CATALOG = [('program_description', 'catalog_description', 0), ('program_learning_outcomes', 'catalog_outcomes', 1),
           ('acceptance_to_major', 'catalog_acceptance', 2), ('degree_requirements', 'catalog_degree', 3),
           ('program_of_study', 'catalog_courses', 4), ('paradigm', 'catalog_paradigm', 5)]
URL = 'https://reg.bethlehem.edu:100/CaDetails/ProgramDescription.aspx?majorCode=237&page={}&catalogID=44&type=1'
POLICY_CAUTION = 'تجميع المستخدم بتاريخ 2026-11-07 لصفحات قديمة (غالبًا 2020)؛ يلزم التأكد من التسجيل من سريان السياسة.'

def sha(text: str | bytes) -> str:
    return hashlib.sha256(text.encode() if isinstance(text, str) else text).hexdigest()

def pages(path: Path):
    if path.parent.name == 'policies':
        reader = PdfReader(path)
        return [positioned_text(p) for p in reader.pages]
    with pymupdf.open(path) as doc:
        return [p.get_text(sort=True) for p in doc]

def course_rows(text_pages):
    rows, issues, track = [], [], None
    pattern = re.compile(r'^\s*([A-Z]{4}\d{3}|FINEART|POLSHUM|RELSPHI|SWERGR1)\s+(.*?)\s*([0-4])\s+(University Requirement|Faculty Requirement|Major Requirement|Major Elective)\s*$')
    for page, text in enumerate(text_pages, 1):
        lines = text.splitlines()
        for i, line in enumerate(lines):
            heading = re.fullmatch(r'\s*(Intensive|Intermediate|Regular) English Students\s*', line)
            if heading:
                track = heading[1].lower()
            match = pattern.match(line)
            if not match:
                continue
            code, name, credits, category = match.groups()
            if code == 'SWER451' and not name.strip():
                before = next((s.strip() for s in reversed(lines[:i]) if s.strip()), '')
                after = next((s.strip() for s in lines[i+1:] if s.strip()), '')
                name = before + ' ' + after
                issues.append({'code': code, 'page': page, 'issue': 'Wrapped title joined; verify against PDF'})
            if not name.strip() or track is None:
                issues.append({'code': code, 'page': page, 'issue': 'Missing name or track; row not imported'})
                continue
            rows.append({'code': code, 'name': name.strip(), 'credits': int(credits), 'category': category,
                         'track': track, 'page': page, 'row': line.strip()})
    return rows, issues

def chunk_page(text: str, limit=1300, tokenizer=None):
    # Preserve complete rows/paragraphs; 1300 chars is approximately 250–500 tokens
    # for catalog English, but Arabic token counts vary and are recorded below.
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    expanded = []
    for paragraph in paragraphs:
        if len(paragraph) > limit and '\n' in paragraph:
            expanded.extend(line.strip() for line in paragraph.splitlines() if line.strip())
        else:
            expanded.append(paragraph)
    buffer = ''
    for paragraph in expanded:
        exceeds_tokens = tokenizer is not None and len(tokenizer.encode(buffer+'\n'+paragraph)) > 480
        if buffer and (len(buffer)+len(paragraph) > limit or exceeds_tokens):
            yield buffer
            buffer = ''
        buffer += ('\n\n' if buffer else '') + paragraph
    if buffer:
        yield buffer

def ingest(rebuild=False):
    issues, manifest = [], []
    model = embedder()
    with session() as db, db.begin():
        old = db.get(Setting, 'embedding')
        expected = embedding_spec()
        if old and old.value != expected:
            raise ValueError('Embedding model/dimension mismatch. Use a separate migrated database and rebuild.')
        db.merge(Setting(key='embedding', value=expected))
        definitions = [(ROOT/'sources/catalog'/f'{stem}_2024_2025.pdf', sid, URL.format(page), 'OFFICIAL_CATALOG_PRINT') for stem, sid, page in CATALOG]
        definitions.append((ROOT/'sources/policies/bethlehem_academic_guidance_compilation_ar.pdf', 'academic_guidance', None, 'USER_ASSEMBLED_OFFICIAL_PAGE_COMPILATION'))
        parsed_courses = []
        for path, sid, url, provenance in definitions:
            text_pages = pages(path)
            digest = sha(path.read_bytes())
            manifest.append({'id': sid, 'title': path.name, 'pages': len(text_pages), 'sha256': digest, 'provenance': provenance})
            if sid == 'catalog_courses':
                parsed_courses, warnings = course_rows(text_pages)
                issues.extend(warnings)
            db.merge(Source(id=sid, title=path.name, path=str(path.relative_to(ROOT)), url=url,
                            kind='policy' if sid == 'academic_guidance' else 'catalog', provenance=provenance,
                            dates={'catalog_year': '2024-2025', 'collected': '2026-11-07', 'policy_current': False if sid == 'academic_guidance' else None}, sha256=digest))
            db.flush()
            texts, meta = [], []
            for page, text in enumerate(text_pages, 1):
                if not text.strip():
                    issues.append({'source': sid, 'page': page, 'issue': 'No text; OCR not implemented'})
                # Course rows are independently retrievable, without splitting relationships.
                page_chunks = [r['row'] for r in parsed_courses if r['page'] == page] if sid == 'catalog_courses' else list(chunk_page(text, tokenizer=model.tokenizer))
                for chunk in page_chunks:
                    if len(model.tokenizer.encode(chunk)) > model.max_seq_length:
                        issues.append({'source': sid, 'page': page, 'issue': 'Atomic row exceeds embedding window; review extraction'})
                    texts.append(chunk)
                    meta.append((page, sha(sid+str(page)+chunk)))
            vectors = embed(texts)
            new_ids = []
            for text, vector, (page, cid) in zip(texts, vectors, meta):
                new_ids.append(cid)
                db.merge(Chunk(id=cid, source_id=sid, page=page, topic=sid,
                               text=text, normalized=normalize(text), token_count=len(model.tokenizer.encode(text)),
                               chunk_hash=sha(text), details={'caution': POLICY_CAUTION if sid == 'academic_guidance' else None}, embedding=vector))
            db.flush()
            db.execute(delete(Chunk).where(Chunk.source_id == sid, Chunk.id.not_in(new_ids)))
        # Reconcile course variants, never sum all optional electives.
        grouped = {}
        for row in parsed_courses:
            grouped.setdefault(row['code'], []).append(row)
        for code, variants in grouped.items():
            first = variants[0]
            if len({r['credits'] for r in variants}) != 1:
                issues.append({'code': code, 'issue': 'Conflicting credit values; not imported'})
                continue
            db.merge(Course(id='44:'+code, code=code, name=first['name'], credits=first['credits'], category=first['category'],
                          applicability={'tracks': sorted({r['track'] for r in variants})},
                          evidence=[{'source_id': 'catalog_courses', 'page': r['page'], 'track': r['track']} for r in variants],
                          placeholder=code in ('FINEART', 'POLSHUM', 'RELSPHI', 'SWERGR1')))
        db.execute(delete(Prerequisite))
        csv_path = ROOT/'data/official_site_prerequisites_team_transcription.csv'
        rows = list(csv.DictReader(csv_path.open(encoding='utf-8-sig')))
        db.merge(Source(id='official_course_modal', title=csv_path.name, path=str(csv_path.relative_to(ROOT)), url=URL.format(4), kind='transcription', provenance='USER_TRANSCRIBED_FROM_OFFICIAL_SITE', dates={'catalog_year': '2024-2025'}, sha256=sha(csv_path.read_bytes())))
        db.flush()
        for number, row in enumerate(rows, 2):
            required = re.findall(r'[A-Z]{4}\d{3}', row['required_course_codes'])
            code = row['course_code']
            evidence = {'source_id': 'official_course_modal', 'csv_row': number, 'url': row['source_url'], 'course_code': code, 'page': None,
                        'label': 'مستخرج من تفاصيل المساق على موقع الجامعة (تفريغ الفريق)'}
            caution = 'SWER312/SWER342 appear in the same paradigm semester; supplied sequential prerequisite conflicts with concurrent use.' if code == 'SWER312' else None
            db.add(Prerequisite(code=code, operator=row['rule_operator'], required=required, provenance=row['provenance'], evidence=evidence, caution=caution))
            if code not in grouped or any(r not in grouped for r in required):
                issues.append({'code': code, 'required': required, 'issue': 'Prerequisite code absent from parsed course table'})
            value = f'{code}: prerequisite AND ' + ', '.join(required)
            db.merge(Chunk(id=sha('prereq'+code), source_id='official_course_modal', page=None, topic='prerequisites', text=value, normalized=normalize(value), token_count=len(model.tokenizer.encode(value)), chunk_hash=sha(value), details=evidence, embedding=embed([value])[0]))
        degree_text = pages(ROOT/'sources/catalog/degree_requirements_2024_2025.pdf')[0]
        breakdown = {}
        for label in ['University Requirement', 'Faculty Requirement', 'Major Requirement', 'Major Elective']:
            match = re.search(re.escape(label)+r'\s+(\d+)', degree_text)
            if not match:
                raise ValueError(f'Could not verify degree component {label}')
            breakdown[label] = int(match[1])
        additions = {}
        for track in ('regular', 'intermediate', 'intensive'):
            additions[track] = sum(r['credits'] for r in parsed_courses if r['track'] == track and r['code'] in ('ENGR101', 'ENGR102'))
            required_total = sum(r['credits'] for r in parsed_courses if r['track'] == track and r['category'] != 'Major Elective')
            expected_total = sum(breakdown.values())+additions[track]
            if required_total+breakdown['Major Elective'] != expected_total:
                issues.append({'track': track, 'issue': 'Course total mismatch', 'course_total_plus_elective_group': required_total+breakdown['Major Elective'], 'catalog_total': expected_total})
        db.merge(Setting(key='degree', value={'breakdown': breakdown, 'additions': additions, 'source_id': 'catalog_degree', 'page': 1}))
        from app.derive_rules import admission_rules
        db.merge(Setting(key='admission', value=admission_rules()))
        seeds = json.loads((ROOT/'quality/reference_qa_seed.json').read_text(encoding='utf-8-sig'))
        for row in seeds['faq_questions']:
            db.merge(FAQ(id=row['key'], question=row['question_ar'], topic=row['category']))
        revision = sha(''.join(d['sha256'] for d in manifest)+sha(csv_path.read_bytes())+EMBEDDING_MODEL+'structure-v1')
        db.merge(Setting(key='revision', value={'hash': revision}))
        db.execute(delete(Cache))
    issues.extend([{'issue': 'Policy compilation recency/applicability uncertain; preserve visible caution'},
                   {'issue': 'SWER312→SWER342 conflicts with same-semester paradigm; do not grant registration authorization'},
                   {'issue': 'Guidance GPA example 24/17 differs from printed 1.59; use arithmetic, not example output'},
                   {'issue': 'ENGR103 in old policy is not equivalent to catalog ENGR101/ENGR102'},
                   {'issue': 'Table extraction is geometric; all wrapped/ambiguous rows require review'}])
    (ROOT/'reports/data_quality_report.json').write_text(json.dumps({'manifest': manifest, 'course_count': len(grouped), 'prerequisite_count': len(rows), 'issues': issues}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'documents': len(manifest), 'courses': len(grouped), 'prerequisites': len(rows), 'issues': len(issues)}))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--all', action='store_true')
    parser.add_argument('--rebuild', action='store_true', help='Transactionally reconcile all source chunks; never drops database')
    args = parser.parse_args()
    ingest(args.rebuild)
