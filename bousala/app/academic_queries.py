"""Source-derived academic queries; calculations never use generated numbers."""
import re
from functools import lru_cache
from pathlib import Path
from sqlalchemy import select
from app.config import ROOT
from app.models import Source, Setting, Prerequisite
from app.ingest import pages, course_rows, sha
from app.simulation import parse_courses, ROW
from app.text import normalize, codes

YEAR_NAMES={1:'الأولى',2:'الثانية',3:'الثالثة',4:'الرابعة'}
TERM_NAMES={'fall':'الفصل الأول','spring':'الفصل الثاني','summer':'الفصل الصيفي'}
YEAR_EN={'First':1,'Second':2,'Third':3,'Fourth':4}
PARADIGM_ROW=re.compile(r'^\s*([A-Z]{4}\d{3}|FINEART|POLSHUM|RELSPHI|CSSEGRO|SWERLIS|SWERGR1)\s+(.*?)\s+(\d{1,2})(?:\s+(University Requirement|Faculty Requirement|Major Requirement|Major Elective))?\s*$')
CATEGORIES={'University Requirement':'متطلبات الجامعة','Faculty Requirement':'متطلبات الكلية','Major Requirement':'متطلبات التخصص الإجبارية','Major Elective':'متطلبات التخصص الاختيارية'}

@lru_cache(maxsize=12)
def read_catalog(path,digest,kind):
    path=Path(path)
    if sha(path.read_bytes())!=digest:
        raise ValueError('Local catalog changed; re-ingest before answering from it')
    text_pages=pages(path)
    if kind=='text': return text_pages
    if kind=='courses_software':
        return course_rows(text_pages)[0]
    if kind=='courses_simulation':
        return parse_courses(text_pages)
    terms=[]
    track=year=term=None
    current=None
    for page,text in enumerate(text_pages,1):
        lines=text.splitlines()
        for i,line in enumerate(lines):
            line=line.strip()
            heading=re.fullmatch(r'(Regular|Intermediate|Intensive) English Students',line)
            if heading:
                track=heading[1].lower()
                year=term=None
                current=None
            year_match=re.fullmatch(r'(First|Second|Third|Fourth) Year',line)
            if year_match: year=YEAR_EN[year_match[1]]
            if line in ('Fall','Spring','Summer') and track and year:
                term=line.lower()
                current={'track':track,'year':year,'term':term,'rows':[],'pages':[],'printed':None}
                terms.append(current)
            match=PARADIGM_ROW.match(line)
            if match and current:
                code,name,credits,category=match.groups()
                if not name.strip():
                    before=next((v.strip() for v in reversed(lines[:i]) if v.strip()),'')
                    after=next((v.strip() for v in lines[i+1:] if v.strip()),'')
                    if not before or not after or ROW.match(before) or ROW.match(after):
                        raise ValueError('Ambiguous paradigm course title: '+code)
                    name=before+' '+after
                current['rows'].append(dict(code=code,name=name.strip(),credits=int(credits),category=category,page=page))
                current['pages'].append(page)
            total=re.fullmatch(r'CREDITS\s+(\d+)',line)
            if total and current:
                current['printed']=int(total[1])
                current['pages'].append(page)
    if not terms or {t['track'] for t in terms}!={'regular','intermediate','intensive'}:
        raise ValueError('Incomplete paradigm extraction')
    for t in terms:
        t['total']=sum(r['credits'] for r in t['rows'])
        t['verified']=bool(t['rows']) and t['printed'] is not None and t['total']==t['printed']
    return terms

def catalog_data(db,program,role):
    sid=('simulation_' if program=='simulation' else 'catalog_')+role
    source=db.get(Source,sid)
    if not source or not source.active: return None,None
    kind='courses_'+program if role=='courses' else 'paradigm'
    return source,read_catalog(str(ROOT/source.path),source.sha256,kind)

def year_from_question(question):
    q=normalize(question).translate(str.maketrans('٠١٢٣٤٥٦٧٨٩','0123456789'))
    aliases={1:r'اولي|اول|الاولي|الاول|FIRST|1(?:ST)?',2:r'ثانيه|ثانية|ثاني|الثانيه|الثانية|الثاني|SECOND|2(?:ND)?',3:r'ثالثه|ثالثة|ثالث|الثالثه|الثالثة|الثالث|THIRD|3(?:RD)?',4:r'رابعه|رابعة|رابع|الرابعه|الرابعة|الرابع|FOURTH|4(?:TH)?'}
    for year,pattern in aliases.items():
        if re.search(r'(?:السنة|السنه|سنة|سنه|YEAR)\s*(?:'+pattern+r')(?!\w)|(?<!\w)(?:'+pattern+r')\s*(?:سنة|سنه|YEAR)(?!\w)',q):
            return year
    return None

def term_from_question(question):
    q=normalize(question).translate(str.maketrans('٠١٢٣٤٥٦٧٨٩','0123456789'))
    if re.search(r'صيف|\bSUMMER\b',q): return 'summer'
    if re.search(r'ربيع|\bSPRING\b|(?:الفصل|فصل|SEMESTER|TERM)\s*(?:الثاني|ثاني|2|SECOND)|(?:ثاني|SECOND)\s*(?:فصل|SEMESTER|TERM)',q): return 'spring'
    if re.search(r'خريف|\bFALL\b|(?:الفصل|فصل|SEMESTER|TERM)\s*(?:الاول|اول|1|FIRST)|(?:اول|FIRST)\s*(?:فصل|SEMESTER|TERM)',q): return 'fall'
    return None

def academic_lookup(db,message,track,program):
    # Imported here to avoid coupling the existing rule engine to PDF parsing.
    from app.rules import evidence
    q=normalize(message)
    english=not re.search(r'[\u0600-\u06ff]',message)
    found=codes(message)
    def clarify(ar,en): return 'clarification',en if english else ar,[]
    def refuse(): return 'refusal',('The information is unavailable or unverified in the supplied sources.' if english else 'المعلومة غير متوفرة أو غير مؤكدة في المصادر الموجودة عندي'),[]
    def proof(source,page): return evidence(db,source.id,page)
    def sources_for(source,rows):
        selected=sorted({r['page'] for r in rows})
        return [proof(source,p) for p in selected],{p:i for i,p in enumerate(selected,1)}
    def row_text(row,refs):
        return f"• {row['code']} — {row['name']}: {row['credits']} {'credits' if english else 'ساعة'} [{refs[row['page']]}]"

    if re.search(r'معدل|GPA',q) and re.search(r'تخرج|GRADUAT',q):
        sid='simulation_degree' if program=='simulation' else 'catalog_degree'
        source=db.get(Source,sid)
        if not source: return refuse()
        text=' '.join(read_catalog(str(ROOT/source.path),source.sha256,'text')[0].split())
        major=re.search(r'(?:minimum Major Grade Point Average|Major requirements as listed below with a minimum Grade Point Average) \(GPA\) of (\d+(?:\.\d+)?)',text,re.I)
        overall=re.search(r'minimum cumulative GPA of (\d+(?:\.\d+)?)',text,re.I)
        if not major or not overall: return refuse()
        answer=(f'Minimum major GPA: {major[1]}; minimum cumulative GPA: {overall[1]}. This does not confirm your personal graduation eligibility. [1]' if english else f'الحد الأدنى لمعدل التخصص: {major[1]}؛ والحد الأدنى للمعدل التراكمي: {overall[1]}. هذا لا يؤكد استحقاق تخرجك الشخصي. [1]')
        return 'lookup',answer,[proof(source,1)]

    # Do not confuse a suggested catalog term with live registration/timetables.
    if re.search(r'مطروح|مطروحة|هالفصل|الساعه كم|ساعة المحاضرة|\b(?:OFFERED|TIMETABLE|ROOM|INSTRUCTOR)\b',q):
        return refuse()
    year=year_from_question(message)
    term=term_from_question(message)
    when=found and re.search(r'متي|اي فصل|باي فصل|اي سنة|وين.*الخطة|\bWHEN\b|WHICH (?:YEAR|SEMESTER|TERM)',q)
    semester_intent=year is not None or term is not None or when
    if semester_intent:
        if not track:
            return clarify('ما مسار الإنجليزية: Regular أم Intermediate أم Intensive؟','Which English track: Regular, Intermediate or Intensive?')
        source,terms=catalog_data(db,program,'paradigm')
        if terms is None: return refuse()
        selected=[t for t in terms if t['track']==track and (year is None or t['year']==year) and (term is None or t['term']==term)]
        if when:
            selected=[t for t in selected if any(r['code'] in found for r in t['rows'])]
        if not selected: return refuse()
        if any(not t['verified'] for t in selected):
            return clarify('وجدت تعارضًا بين مجموع صفوف الفصل والإجمالي المطبوع؛ لا أقدر أعطي مجموعًا مؤكدًا قبل مراجعة الجدول.','The extracted rows disagree with a printed term total; a verified answer requires table review.')
        if term and not year and not when:
            return clarify('أي سنة دراسية تقصد: الأولى، الثانية، الثالثة أم الرابعة؟','Which academic year: first, second, third or fourth?')
        row_list=[r for t in selected for r in t['rows']]
        proof_list,refs=sources_for(source,row_list)
        answer=[f"{'English track' if english else 'مسار الإنجليزية'}: {track.title()}"]
        for t in selected:
            label=f"Year {t['year']} / {t['term'].title()}" if english else f"السنة {YEAR_NAMES[t['year']]} — {TERM_NAMES[t['term']]}"
            citations=' '.join(f'[{refs[p]}]' for p in sorted(set(t['pages'])))
            answer.append(f"{label}: {t['total']} {'credits' if english else 'ساعة'} {citations}")
            if not when:
                answer.extend(row_text(r,refs) for r in t['rows'])
        if len(selected)>1 and not when:
            answer.append(f"{'Total of the listed terms' if english else 'مجموع الفصول المذكورة، شامل الصيفي المدرج'}: {sum(t['total'] for t in selected)} {'credits' if english else 'ساعة'}.")
        answer.append('Suggested catalog sequence, not confirmation of live offerings or registration eligibility.' if english else 'هذا ترتيب مقترح في الخطة؛ لا يؤكد طرح المواد حاليًا أو استحقاق تسجيلها. خانات الاختياري مجموعات خيارات وليست مواد إضافية ثابتة.')
        return 'calculation','\n'.join(answer),proof_list

    # Compare only explicit track differences supported by the degree table.
    if re.search(r'فرق|مقارن|\b(?:DIFFERENCE|COMPARE)\b',q) and re.search(r'انجليز|REGULAR|INTERMEDIATE|INTENSIVE',q):
        sid='simulation_degree' if program=='simulation' else 'catalog_degree'
        degree=db.get(Setting,sid if program=='simulation' else 'degree')
        if not degree: return refuse()
        value=degree.value
        answer=[]
        for name,extra in value['additions'].items():
            answer.append(f"{name.title()}: {sum(value['breakdown'].values())+extra} {'credits' if english else 'ساعة'} ({'additional English credits' if english else 'ساعات إنجليزي إضافية'}: {extra}) [1]")
        return 'calculation','\n'.join(answer),[evidence(db,sid,1)]

    # Verified reverse prerequisite links, never inferred from semester order.
    if found and re.search(r'بيفتح|بفتح|يفتح|بيعتمد|\b(?:UNLOCK|DEPENDENTS|REQUIRES THIS)\b',q):
        if program=='simulation': return clarify('قواعد المتطلبات السابقة للمحاكاة غير موثقة في الملفات المتاحة.','Simulation prerequisite rules were not supplied.')
        rules=[r for r in db.scalars(select(Prerequisite)) if found[0] in r.required]
        if not rules: return clarify('لا توجد علاقة موثقة ضمن قواعد المتطلبات المتاحة؛ هذا لا يثبت عدم وجود علاقات أخرى.','No relationship is documented in the supplied rules; missing rules remain unknown.')
        proof_list=[]
        lines=[]
        for r in rules:
            proof_list.append(evidence(db,'official_course_modal') | r.evidence)
            lines.append(f"• {r.code}: {' AND '.join(r.required)} [{len(proof_list)}]")
        lines.append('Previously completed prerequisites are required; this is not registration approval.' if english else 'ظهور المساق هنا لا يعني استحقاق تسجيله؛ يلزم إتمام جميع متطلباته سابقًا.')
        return 'lookup','\n'.join(lines),proof_list

    source,rows=catalog_data(db,program,'courses') if (found or re.search(r'مواد|مساقات|مساق|COURSES|متطلبات|REQUIREMENTS',q)) else (None,None)
    if rows is None: return None
    category=None
    for pattern,value in [(r'جامع|UNIVERSITY','University Requirement'),(r'كلي|FACULTY','Faculty Requirement'),(r'اختياري|ELECTIVE','Major Elective'),(r'اجباري|تخصص|MAJOR','Major Requirement')]:
        if re.search(pattern,q): category=value;break
    list_intent=re.search(r'شو.*(?:مواد|مساقات|متطلبات)|ما هي|اعطيني.*(?:مواد|مساقات)|قائمة|LIST|WHICH COURSES|WHAT COURSES',q)
    if re.search(r'قبول|ADMISSION|ACCEPTANCE|متطلب سابق|PREREQUISITE',q): return None
    if category and not found and re.search(r'كم|قديش|HOW MANY|TOTAL',q) and re.search(r'ساع|CREDIT|HOUR',q):
        sid='simulation_degree' if program=='simulation' else 'catalog_degree'
        degree=db.get(Setting,'simulation_degree' if program=='simulation' else 'degree')
        if not degree: return refuse()
        count=degree.value['breakdown'][category]
        label=category if english else CATEGORIES[category]
        answer=f"{label}: {count} {'credits' if english else 'ساعة'} [1]"
        if category=='University Requirement':
            answer+=('\nAdditional English-track credits are separate.' if english else '\nساعات الإنجليزي الإضافية حسب المسار منفصلة عن هذا الرقم.')
        return 'lookup',answer,[evidence(db,sid,1)]
    sum_intent=len(set(found))>1 and re.search(r'مجموع|كم ساعة|ساعاته|TOTAL|SUM|CREDITS|HOURS',q) and not re.search(r'متطلب|PREREQUISITE',q)
    if found and (sum_intent or re.search(r'ساعة|ساع|اسم|تصنيف|اجباري|اختياري|CREDIT|HOUR|TITLE|NAME|CATEGORY|ELECTIVE',q)):
        selected=[]
        for code in dict.fromkeys(found):
            variants=[r for r in rows if r['code']==code and (not track or r['track']==track)]
            if not variants: return refuse()
            if len({(r['credits'],r['category'],r['name']) for r in variants})!=1: return refuse()
            selected.append(variants[0])
        proof_list,refs=sources_for(source,selected)
        lines=[row_text(r,refs)+f" — {r['category'] if english else CATEGORIES[r['category']]}" for r in selected]
        if sum_intent:
            lines.append(f"{'Total (each distinct code once)' if english else 'المجموع (كل رمز مختلف مرة واحدة)'}: {sum(r['credits'] for r in selected)} {'credits' if english else 'ساعة'}.")
        if any(r['credits']==0 for r in selected): lines.append('Zero credits does not remove a listed requirement.' if english else 'صفر ساعات لا يعني إلغاء المتطلب المدرج.')
        return 'calculation' if sum_intent else 'lookup','\n'.join(lines),proof_list
    if list_intent:
        if not track:
            return clarify('حدّد مسار الإنجليزية: Regular أو Intermediate أو Intensive حتى أعرض القائمة المناسبة.','Specify Regular, Intermediate or Intensive to select the correct course table.')
        selected=[r for r in rows if r['track']==track and (category is None or r['category']==category)]
        if re.search(r'انجليز|ENGLISH',q):
            selected=[r for r in selected if r['code'].startswith(('ENGL','ENGR'))]
        # Repeated elective slots remain slots, not distinct completed courses.
        unique={r['code']:r for r in selected}
        if not unique: return refuse()
        proof_list,refs=sources_for(source,unique.values())
        lines=[f"{'English track' if english else 'مسار الإنجليزية'}: {track.title()}"]
        if category: lines.append(category if english else CATEGORIES[category])
        lines.extend(row_text(r,refs) for r in unique.values())
        lines.append('Elective/choice entries are groups; do not sum the whole list as mandatory degree credits.' if english else 'خانات الاختياري والخيارات مجموعات؛ لا تُجمع كل القائمة كساعات إجبارية للتخرج.')
        return 'lookup','\n'.join(lines),proof_list
    return None
