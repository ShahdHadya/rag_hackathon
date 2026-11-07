from unittest.mock import Mock,patch
import pytest
from app.config import ROOT
from app.ingest import sha
from app.academic_queries import read_catalog,academic_lookup,year_from_question,term_from_question

@pytest.mark.parametrize('question,year,term',[
 ('كم ساعة بخلص في الفصل الاول سنة اولى ؟',1,'fall'),
 ('شو مواد السنة الثانية الفصل الثاني؟',2,'spring'),
 ('السنة الثالثة صيفي',3,'summer'),
 ('First year fall credits',1,'fall'),
 ('YEAR 4 SPRING',4,'spring'),
 ('الفصل ٢ سنة ١',1,'spring'),
])
def test_period_language_variants(question,year,term):
    assert year_from_question(question)==year
    assert term_from_question(question)==term

@pytest.mark.parametrize('program,folder,count',[('software','catalog',30),('simulation','simulation',33)])
def test_all_actual_term_tables_match_printed_totals(program,folder,count):
    path=ROOT/f'sources/{folder}/paradigm_2024_2025.pdf'
    if not path.exists(): pytest.skip('Official paradigm fixture unavailable')
    terms=read_catalog(str(path),sha(path.read_bytes()),'paradigm')
    assert len(terms)==count
    assert all(t['verified'] for t in terms)
    for track,total in [('regular',130),('intermediate',132),('intensive',134)]:
        assert sum(t['total'] for t in terms if t['track']==track)==total
    first=next(t for t in terms if t['track']=='regular' and t['year']==1 and t['term']=='fall')
    assert first['total']==16
    assert any(r['code']=='LIBR101' and r['credits']==0 for r in first['rows'])
    if program=='software':
        assert sum(r['credits'] for t in terms if t['track']=='regular' for r in t['rows'] if r['code']=='SWERGR1')==15
    else:
        assert next(t for t in terms if t['track']=='intermediate' and t['year']==1 and t['term']=='fall')['total']==14

def test_missing_track_clarifies_before_reading_pdf():
    result=academic_lookup(Mock(),'كم ساعة الفصل الاول سنة اولى؟',None,'software')
    assert result[0]=='clarification' and result[2]==[]

def test_live_offerings_are_never_inferred_from_paradigm():
    assert academic_lookup(Mock(),'شو المواد المطروحة هالفصل Regular؟','regular','software')[0]=='refusal'

def test_mismatched_extraction_never_reports_total():
    terms=[{'track':'regular','year':1,'term':'fall','verified':False}]
    with patch('app.academic_queries.catalog_data',return_value=(Mock(),terms)):
        assert academic_lookup(Mock(),'كم ساعة الفصل الأول سنة أولى Regular؟','regular','software')[0]=='clarification'

def test_unknown_course_cannot_enter_sum():
    rows=[dict(code='MATH141',name='Calculus',credits=4,category='Faculty Requirement',track='regular',page=1)]
    with patch('app.academic_queries.catalog_data',return_value=(Mock(),rows)):
        assert academic_lookup(Mock(),'MATH141 + XXXX999 مجموع الساعات؟','regular','software')[0]=='refusal'

def test_modified_pdf_is_rejected(tmp_path):
    path=tmp_path/'changed.pdf'
    path.write_bytes(b'changed content')
    with pytest.raises(ValueError,match='changed'):
        read_catalog(str(path),'old-digest','paradigm')

@pytest.mark.parametrize('program,folder',[('software','catalog'),('simulation','simulation')])
def test_actual_graduation_gpa_wording(program,folder):
    name='degree_2024_2025.pdf' if program=='simulation' else 'degree_requirements_2024_2025.pdf'
    path=ROOT/f'sources/{folder}/{name}'
    if not path.exists(): pytest.skip('Official degree fixture unavailable')
    source=Mock(path=str(path.relative_to(ROOT)),sha256=sha(path.read_bytes()))
    db=Mock()
    db.get.return_value=source
    with patch('app.rules.evidence',return_value={'page':1}):
        result=academic_lookup(db,'كم معدل التخرج المطلوب؟',None,program)
    assert result[0]=='lookup' and result[1].count('2.00')==2
