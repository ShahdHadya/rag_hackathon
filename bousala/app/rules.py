import re
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import select
from app.models import Course, Prerequisite, Setting, Source, Chunk
from app.text import codes, normalize
from app.ingest import POLICY_CAUTION
from app.context import track_from_text

def weighted_gpa(pairs):
    if not pairs or any(Decimal(str(hours)) <= 0 for _, hours in pairs):
        raise ValueError('Positive graded credit hours required')
    grades = {'A': '4', 'B+': '3.5', 'B': '3', 'C+': '2.5', 'C': '2', 'D+': '1.5', 'D': '1', 'F': '0'}
    included = [(Decimal(grades[g]), Decimal(str(h))) for g,h in pairs if g not in ('P','W','I')]
    if not included:
        raise ValueError('No graded credits; GPA is undefined')
    value = sum(g*h for g,h in included)/sum(h for _,h in included)
    return str(value.quantize(Decimal('.01'), rounding=ROUND_HALF_UP))

def prerequisite_status(required, completed):
    return set(required) <= set(completed)

def evidence(db, sid, page=None):
    source = db.get(Source, sid)
    if source is None:
        raise ValueError('Referenced source is not ingested')
    return {'source_id': sid, 'title': source.title, 'page': page, 'url': source.url, 'provenance': source.provenance,
            'caution': POLICY_CAUTION if sid == 'academic_guidance' else None}

def lookup(db, message, track=None, program="software"):
    from app.academic_queries import academic_lookup
    track=track_from_text(message) or track
    expanded=academic_lookup(db,message,track,program)
    if expanded is not None:
        return expanded
    simulation=program=="simulation"
    def proof_for(sid,page=None):
        return evidence(db,sid.replace("catalog_","simulation_") if simulation and sid.startswith("catalog_") else sid,page)
    q = normalize(message)
    track=track_from_text(message) or track
    english = not re.search(r'[\u0600-\u06ff]', message)
    found = codes(message)
    if any(t in q for t in ('قبول', 'ACCEPTANCE', 'ATM')):
        setting=db.get(Setting,'simulation_admission' if simulation else 'admission')
        if setting:
            a=setting.value
            tracks=[track] if track else list(a['english_courses'])
            requirements='; '.join(t.title()+': '+', '.join(a['english_courses'][t]) for t in tracks)
            if english:
                answer=f"Admission criteria: {a['earned_credits']} earned credits; overall GPA ≥ {a['overall_gpa']}; major GPA ≥ {a['major_gpa']}; at least {a['major_courses']} major courses / {a['major_credits']} major credits. English completions: {requirements}. Summer/transfer/warning exceptions need context. These are criteria, not confirmation of your eligibility. [1]"
            else:
                answer=f"شروط القبول للتخصص: {a['earned_credits']} ساعة منجزة؛ معدل عام لا يقل عن {a['overall_gpa']}؛ معدل تخصص لا يقل عن {a['major_gpa']}؛ إتمام {a['major_courses']} مساقات تخصص على الأقل، مجموعها {a['major_credits']} ساعات.\nالإنجليزية: {requirements}.\nتوجد استثناءات للصيف والتحويل والإنذارات تحتاج سياقًا. لا يمكن تأكيد استحقاقك شخصيًا دون جميع المدخلات. [1]"
            return 'conditional',answer,[proof_for('catalog_acceptance',1)]
    if 'SWERGR1' in found and not simulation:
        chunk = db.scalar(select(Chunk).where(Chunk.source_id == 'catalog_paradigm', Chunk.normalized.contains('SWERGR1')).order_by(Chunk.page))
        if chunk:
            return 'lookup', 'SWERGR1 خانة لمجموعة اختياري، وليست مساقًا مستقلًا يُحسب كمساق منجز. [1]', [proof_for('catalog_paradigm', chunk.page)]
    # Bare numbers are ambiguous identifiers and are never expanded to a guessed department.
    if not found and re.search(r'\b\d{3}\b', q) and any(t in q for t in ('مادة','متطلب','قبل','مساق')):
        return 'clarification', 'يرجى كتابة رمز المساق كاملاً، مثل SWER312؛ الرقم وحده قد يكون ملتبسًا.', []
    prerequisite_query = any(t in q for t in ('متطلب', 'PREREQUISITE', 'قبل', 'بقدر', 'خلصت', 'رسبت', 'قيد الدراسة'))
    if found and prerequisite_query:
        if simulation:
            return "conditional", ("Verified prerequisite rules for this program have not been supplied." if english else "المتطلبات السابقة لهذا التخصص غير موثقة في الملفات المتاحة؛ لا يمكن استنتاجها من ترتيب الخطة."), []
        code = found[0]
        for candidate in found:
            candidate_rule = db.get(Prerequisite, candidate)
            if candidate_rule and set(candidate_rule.required).intersection(found):
                code = candidate
                break
        rule = db.get(Prerequisite, code)
        if not rule:
            return 'conditional', ('No prerequisite was mentioned in the available data.' if english else 'لم يُذكر متطلب سابق في البيانات المتاحة'), []
        proof = proof_for('official_course_modal') | rule.evidence
        proof['caution'] = rule.caution
        proofs = [proof]
        requirements = ' AND '.join(rule.required)
        answer = f'{code}: {requirements} [1]. '
        answer += ('Prerequisites must be previously completed; this is advisory, not registration authorization.' if english else 'المتطلبات المذكورة يجب إتمامها سابقًا؛ هذا إرشاد وليس تصريح تسجيل.')
        if rule.caution:
            answer += (' The paradigm places these in the same term, which conflicts with the sequential prerequisite.' if english else ' تنبيه: تضع الخطة المساقين في الفصل نفسه، وهذا يتعارض مع المتطلب التسلسلي المقدم.')
            paradigm = db.scalar(select(Chunk).where(Chunk.source_id=='catalog_paradigm', Chunk.normalized.contains(code)).order_by(Chunk.page))
            if paradigm:
                proofs.append(proof_for('catalog_paradigm',paradigm.page))
                answer += ' [2]'
        return 'lookup', answer, proofs
    if found and any(t in q for t in ('ساعة', 'ساع', 'CREDIT', 'HOUR', 'LIBR101', 'TITLE', 'اسم')) and not any(t in q for t in ('REGULAR', 'INTERMEDIATE', 'INTENSIVE', 'تخرج', 'TOTAL')):
        course = db.scalar(select(Course).where(Course.code == found[0], Course.evidence.contains([{'source_id':'catalog_courses'}]))) if not simulation else None
        if simulation:
            from app.platform_models import CurriculumCourse
            from app.programs import CURRICULA
            row=db.get(CurriculumCourse,CURRICULA[program]+':'+found[0])
            if row:
                from types import SimpleNamespace
                course=SimpleNamespace(code=found[0],name=row.title,credits=row.credits,evidence=row.evidence,placeholder=not bool(re.fullmatch(r'[A-Z]{4}\d{3}',found[0])))
        if course:
            proof = proof_for('catalog_courses', course.evidence[0]['page'])
            answer = f'{course.code} — {course.name}: {course.credits} '+('credits' if english else 'ساعة معتمدة')
            if course.credits == 0:
                answer += ('; zero credits does not remove a listed requirement' if english else '؛ صفر ساعات لا يعني إلغاء المتطلب المدرج')
            if course.placeholder:
                answer += ('; choice group, not an ordinary completed course' if english else '؛ مجموعة خيارات وليست مساقًا عاديًا منجزًا')
            return 'lookup', answer+' [1]', [proof]
    degree_query = any(t in q for t in ('ساعة', 'ساع', 'CREDIT', 'HOUR', 'المطلوب', 'بتزيد', 'توزع')) and any(t in q for t in ('تخرج', 'خطت', 'تخصص', 'برمجيات', 'محاكاة', 'SIMULATION', 'REGULAR', 'INTENSIVE', 'INTERMEDIATE', 'DEGREE', 'GRADUAT', 'ENGLISH'))
    if degree_query:
        degree = db.get(Setting, 'simulation_degree' if simulation else 'degree')
        if degree:
            value = degree.value
            if track is None:
                return 'clarification', 'ما مسار الإنجليزية: Regular أم Intermediate أم Intensive؟', []
            total = sum(value['breakdown'].values())+value['additions'][track]
            parts = value['breakdown']
            names = [('University Requirement', 'University requirements', 'متطلبات الجامعة'),
                     ('Faculty Requirement', 'Faculty requirements', 'متطلبات الكلية'),
                     ('Major Requirement', 'Major requirements', 'متطلبات التخصص الإجبارية'),
                     ('Major Elective', 'Major electives', 'متطلبات التخصص الاختيارية')]
            components = '\n'.join(f'• {en if english else ar}: {parts[key]}' for key,en,ar in names)
            extra = value['additions'][track]
            if english:
                answer = f'English track: {track.title()}\nTotal degree requirement: {total} credits.\n{components}\nAdditional English-track credits: {extra}.'
            else:
                answer = f'مسار الإنجليزية: {track.title()}\nإجمالي متطلبات الدرجة: {total} ساعة معتمدة.\n{components}\nساعات مسار الإنجليزية الإضافية: {extra}.'
            return 'lookup', answer+' [1]', [proof_for('catalog_degree', 1)]
    if any(t in q for t in ('اختياري', 'ELECTIVE')) and any(t in q for t in ('كل', 'جميع', 'ALL', '15', 'مجموعة')):
        degree = db.get(Setting, 'simulation_degree' if simulation else 'degree')
        if degree:
            count = degree.value['breakdown']['Major Elective']
            return 'lookup', f'المطلوب إتمام مجموعة الاختياري ({count} ساعة)، وليس كل المساقات الاختيارية المدرجة. [1]', [proof_for('catalog_degree', 1)]
    arithmetic = re.search(r'(\d+(?:\.\d+)?)\s*(?:/|على|POINTS OVER)\s*(\d+(?:\.\d+)?)', q)
    grade_pairs = re.findall(r'\b(A|B\+|B|C\+|C|D\+|D|F|P|W|I)\s*[:=]\s*(\d+(?:\.\d+)?)\b', q)
    if grade_pairs and any(t in q for t in ('GPA', 'معدل')):
        return 'calculation', weighted_gpa(grade_pairs)+' [1] [2]', [proof_for('academic_guidance', 19), proof_for('academic_guidance', 17)]
    if arithmetic and any(t in q for t in ('GPA', 'معدل', 'نقطة', 'نقاط')):
        numerator, denominator = map(Decimal, arithmetic.groups())
        if denominator <= 0:
            return 'clarification', 'يلزم عدد ساعات موجب للحساب.', []
        result = (numerator/denominator).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
        return 'calculation', f'{numerator}/{denominator} = {result}. هذا حساب المدخلات فقط؛ لا يثبت معدلك التراكمي، خصوصًا مع إعادة المساقات. [1]', [proof_for('academic_guidance', 19)]
    if any(t in q for t in ('معدلي', 'MY GPA', 'انا مؤهل', 'AM I ELIGIBLE', 'قبلوني')):
        return 'clarification', 'لا أملك سجلًا شخصيًا لك. اذكر المدخلات اللازمة؛ لا يمكن تأكيد القبول أو المعدل دونها.', []
    return None
