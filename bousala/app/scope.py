"""Corpus-aware scope boundaries, not pre-scripted academic answers."""
import re
from sqlalchemy import select
from app.models import Source
from app.text import codes, normalize

def unsupported_request(db, message):
    question=normalize(message)
    if re.search(r'PASSWORD|CREDENTIAL|API KEY|SECRET KEY|كلمة\s*(?:سر|مرور)|كلمات\s*المرور',question):
        return 'credentials_are_not_academic_evidence'
    exam=bool(re.search(r'EXAM|امتحان',question))
    date_request=bool(re.search(r'DATE|WHEN|NEXT|موعد|القادم|الجاي|متى',question))
    if exam and date_request and codes(question):
        schedule=db.scalar(select(Source.id).where(Source.active,Source.kind=='exam_schedule').limit(1))
        if schedule is None:
            return 'no_course_exam_schedule_in_corpus'
    return None
