"""Corpus-aware scope boundaries, not pre-scripted academic answers."""
import re
from sqlalchemy import select
from app.models import Source
from app.text import codes, normalize

def unsupported_request(db, message):
    question=normalize(message)
    # The corpus is an academic catalog/policy collection. A nearby vector and
    # an existing citation ID do not make a general-knowledge answer supported.
    academic=r'تخصص|مساق|مواد|مادة|متطلب|جامعة|جامع|كلية|اكاديم|معدل|ساع|تخرج|تسجيل|قبول|انذار|سحب|انسحاب|اضافة|حذف|فصل|امتحان|رسوب|اعادة|علام|تدريب|مشروع|برمجيات|محاكاة|خطة|خطت|اختياري|انجليز|حضور|غياب|تحويل|معادلة|منحة|رسوم|منح|REGULAR|INTERMEDIATE|INTENSIVE|\b(?:COURSE|CREDITS?|HOURS?|DEGREE|GPA|PREREQUISITES?|ADMISSION|MAJOR|MINOR|ELECTIVES?|ENGLISH|UNIVERSITY|FACULTY|GRADUATION|ACADEMIC|SEMESTER|TUITION|SCHOLARSHIP|WITHDRAW\w*|REGISTRATION|EXAM\w*|POLIC\w*|PROGRAM|CURRICULUM|INTERNSHIP|GRADE\w*|SIMULATION|SOFTWARE|PROBATION|TRANSFER)\b'
    if not codes(question) and not re.search(academic,question) and not re.search(r'سنة|سنه|\b(?:YEAR|TERM|FALL|SPRING|SUMMER)\b',question):
        return 'outside_academic_corpus_scope'
    if re.search(r'PASSWORD|CREDENTIAL|API KEY|SECRET KEY|كلمة\s*(?:سر|مرور)|كلمات\s*المرور',question):
        return 'credentials_are_not_academic_evidence'
    exam=bool(re.search(r'EXAM|امتحان',question))
    date_request=bool(re.search(r'DATE|WHEN|NEXT|موعد|القادم|الجاي|متى',question))
    if exam and date_request and codes(question):
        schedule=db.scalar(select(Source.id).where(Source.active,Source.kind=='exam_schedule').limit(1))
        if schedule is None:
            return 'no_course_exam_schedule_in_corpus'
    return None
