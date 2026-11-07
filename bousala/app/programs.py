"""Explicit program/source boundaries, including the legacy Software corpus."""
from sqlalchemy import and_, or_
from app.models import Source

CURRICULA={'software':'software:44:2024-2025','simulation':'simulation:44:2024-2025'}
LEGACY_SOURCES=['catalog_description','catalog_outcomes','catalog_acceptance','catalog_degree','catalog_courses','catalog_paradigm','official_course_modal']
PROGRAM_NAMES={'software':'هندسة البرمجيات','simulation':'المحاكاة الحاسوبية في العلوم والهندسة'}

def source_scope(program):
    if program not in CURRICULA:
        raise ValueError('Unknown academic program')
    selected=Source.curriculum_id==CURRICULA[program]
    if program=='software':
        selected=or_(selected,Source.id.in_(LEGACY_SOURCES))
    return and_(Source.active,or_(selected,Source.scope=='university',Source.id=='academic_guidance'))

def suggested_questions(program):
    name=PROGRAM_NAMES[program]
    code='CSSE461' if program=='simulation' else 'SWER351'
    return [{'id':f'{program}-{i}','question':q,'seed':True,'frequency':None} for i,q in enumerate([
        f'كم ساعة مطلوبة لتخصص {name} لمسار Regular؟',
        f'كم ساعة مطلوبة لتخصص {name} لمسار Intermediate؟',
        f'كم ساعة مطلوبة لتخصص {name} لمسار Intensive؟',
        f'{code} كم ساعة؟',
        f'شو شروط القبول بتخصص {name}؟',
        'هل لازم آخذ كل المساقات الاختيارية؟',
        'كم ساعة الفصل الأول سنة أولى Regular؟',
        'شو مواد السنة الأولى Intermediate؟',
        'شو مواد الفصل الثاني سنة ثانية Intensive؟',
        'شو الفرق بالساعات بين Regular وIntermediate وIntensive؟',
        f'بأي فصل موجود {code} في الخطة Regular؟',
    ])]
