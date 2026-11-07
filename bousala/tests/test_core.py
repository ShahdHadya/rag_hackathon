import csv
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from app.config import ROOT
from app.ingest import course_rows, pages, chunk_page
from app.rules import prerequisite_status, weighted_gpa
from app.retrieval import rrf
from app.text import normalize, codes
from app.main import app, ChatRequest, cacheable, compose, REFUSAL

@pytest.fixture(scope='module')
def rows():
    return course_rows(pages(ROOT/'sources/catalog/program_of_study_2024_2025.pdf'))[0]

def test_zero_and_small_credit_values_preserved(rows):
    assert next(r for r in rows if r['code']=='LIBR101')['credits'] == 0
    assert next(r for r in rows if r['code']=='SWER401')['credits'] == 1
    assert next(r for r in rows if r['code']=='SWER400')['credits'] == 2
    assert next(r for r in rows if r['code']=='MATH141')['credits'] == 4

@pytest.mark.parametrize('track,total', [('regular',130),('intermediate',132),('intensive',134)])
def test_totals_from_actual_course_rows(rows, track, total):
    required = sum(r['credits'] for r in rows if r['track']==track and r['category']!='Major Elective')
    assert required+15 == total

def test_all_tracks_and_no_optional_overcount(rows):
    assert len({r['code'] for r in rows}) == 57
    assert sum(r['credits'] for r in rows if r['track']=='regular' and r['category']=='Major Elective') > 15
    assert {'FINEART','POLSHUM','RELSPHI'} <= {r['code'] for r in rows}

def test_real_transcribed_prerequisites():
    data = {r['course_code']: r for r in csv.DictReader((ROOT/'data/official_site_prerequisites_team_transcription.csv').open(encoding='utf-8-sig'))}
    assert data['SWER312']['required_course_codes'] == 'SWER342'
    assert data['SWER381']['required_course_codes'] == 'SWER142;SWER212'
    assert data['SWER428']['required_course_codes'] == 'SWER313;SWER241'
    assert not prerequisite_status(['SWER142','SWER212'], ['SWER142'])
    assert prerequisite_status(['SWER142','SWER212'], ['SWER142','SWER212'])

def test_gpa_weighted_not_average_of_grades():
    assert weighted_gpa([('A',3),('B+',4),('B',3),('C+',2),('C',3)]) == '3.07'  # 46/15
    assert weighted_gpa([('A',3),('P',3),('W',2),('I',1)]) == '4.00'
    with pytest.raises(ValueError):
        weighted_gpa([('P',3)])

def test_rrf_preserves_exact_identifiers():
    assert rrf([['exact'],['general','exact'],['general','exact']])[0] == 'exact'
    assert codes('شو متطلب SWER312؟') == ['SWER312']
    assert codes('SWER 351 كم ساعة؟') == ['SWER351']
    assert codes('المتطلب لـMATH141؟') == ['MATH141']
    assert codes('موعد ENGL120؟') == ['ENGL120']
    assert normalize('إِرشاد') == normalize('ارشاد')

def test_chunks_do_not_split_rows():
    chunks = list(chunk_page('course row\n\n'+'x'*1400))
    assert chunks[0]=='course row'
    assert len(chunks[1])==1400

def test_personalized_never_cached():
    assert not cacheable(ChatRequest(message='شو معدلي؟'), 'lookup')
    assert not cacheable(ChatRequest(message='MY credits'), 'lookup')
    assert not cacheable(ChatRequest(message='generic', history=[{'role':'user','content':'previous'}]), 'lookup')
    assert not cacheable(ChatRequest(message='generic'), 'rag')
    assert cacheable(ChatRequest(message='SWER351 credits'), 'lookup')

def test_no_source_no_citation_and_invalid_citation_refuses():
    class Response:
        content = 'An invented answer [99]'
    with patch('app.main.llm') as model:
        model.return_value.stream.return_value = [Response()]
        assert compose('question', [{'text':'evidence','title':'doc','page':1}])[0] == REFUSAL

def test_api_invalid_contract_and_no_llm():
    client = TestClient(app)
    assert client.post('/api/chat', json={'message':''}).status_code==422
    assert client.post('/api/chat', json={'message':'x','english_track':'unknown'}).status_code==422
    with patch('app.main.session', side_effect=ConnectionError('offline')):
        result=client.post('/api/chat',json={'message':'question'})
        assert result.status_code==503
        assert 'answer' not in result.json()

def test_health_never_healthy_on_dependency_failure():
    with patch('app.main.session', side_effect=ConnectionError()), patch('app.main.embedder', return_value=True), patch('app.main.ollama_ready', side_effect=ConnectionError()):
        response=TestClient(app).get('/health')
        assert response.status_code==503
        assert response.json()['healthy'] is False

def test_no_quality_seed_in_academic_sources():
    assert not list((ROOT/'sources').rglob('*.json'))
    assert not list((ROOT/'sources').rglob('*Judging*'))

def test_degree_labels_do_not_depend_on_json_key_order():
    from types import SimpleNamespace
    from unittest.mock import Mock
    from app.rules import lookup
    db=Mock()
    db.get.return_value=SimpleNamespace(value={'breakdown': {'Major Elective':15,'Major Requirement':66,'Faculty Requirement':18,'University Requirement':31},'additions':{'regular':0,'intermediate':2,'intensive':4}})
    with patch('app.rules.evidence',return_value={'source_id':'catalog_degree','page':1}):
        _,answer,_=lookup(db,'Regular English total degree hours?')
    assert 'University requirements: 31' in answer
    assert 'Faculty requirements: 18' in answer
    assert 'Major requirements: 66' in answer
    assert 'Major electives: 15' in answer

def test_scope_does_not_invent_course_exam_schedule_or_credentials():
    from unittest.mock import Mock
    from app.scope import unsupported_request
    db=Mock()
    db.scalar.return_value=None
    assert unsupported_request(db,'اعطيني كلمة سر الجامعة')
    assert unsupported_request(db,'When is the next exam for SWER241?')
    assert unsupported_request(db,'شو موعد الامتحان القادم لـ SWER241؟')
    assert unsupported_request(db,'متى الامتحان القادم لـMATH141؟')
    assert unsupported_request(db,'ما سياسة الغياب عن الامتحان؟') is None
    assert unsupported_request(db,'SWER351 credits?') is None
