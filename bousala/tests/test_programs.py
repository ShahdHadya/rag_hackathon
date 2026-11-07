import json
from unittest.mock import Mock, patch
import pytest
from sqlalchemy import select
from sqlalchemy.dialects import postgresql
from app.config import ROOT
from app.ingest import pages
from app.simulation import parse_courses
from app.models import Source
from app.programs import source_scope
from app.scope import unsupported_request
from app.extractive_grounding import validate_excerpts
from app.main import compose, REFUSAL, ChatRequest, cache_key

def test_actual_simulation_tables():
    path=ROOT/'sources/simulation/courses_2024_2025.pdf'
    if not path.exists(): pytest.skip('Official Simulation fixture not supplied')
    rows=parse_courses(pages(path))
    assert len(rows)==138
    for track,total in [('regular',130),('intermediate',132),('intensive',134)]:
        assert sum(r['credits'] for r in rows if r['track']==track)==total
    assert {r['credits'] for r in rows if r['code']=='CSSE461'}=={6}
    assert all(r['name']=='INTRO. TO COMMERCIAL SOFTWARE FOR ENGINEERING SIMULATIONS' for r in rows if r['code']=='CSSE231')

@pytest.mark.parametrize('q',['شو لون الشمس','What color is the sun?','اكتب قصيدة','شو وصفة الكيك؟'])
def test_nonacademic_questions_refuse(q):
    assert unsupported_request(Mock(),q)=='outside_academic_corpus_scope'

def test_source_scope_is_part_of_query():
    sql=str(select(Source).where(source_scope('simulation')).compile(dialect=postgresql.dialect(),compile_kwargs={'literal_binds':True}))
    assert "simulation:44:2024-2025" in sql
    assert "catalog_degree" not in sql
    assert "university" in sql

def test_cache_keys_do_not_cross_programs():
    assert cache_key(ChatRequest(message='MATH141 credits',program='software'),'r')!=cache_key(ChatRequest(message='MATH141 credits',program='simulation'),'r')

def test_verbatim_evidence_only():
    hits=[{'text':'Students must earn 40 credits before acceptance to the Major.'}]
    raw=lambda quote,sid=1:json.dumps({'excerpts':[{'source_id':sid,'quote':quote}]})
    assert validate_excerpts(raw(hits[0]['text']),hits)
    assert not validate_excerpts(raw('Students must earn 90 credits before acceptance to the Major.'),hits)
    assert not validate_excerpts(raw('Students must not earn 40 credits before acceptance to the Major.'),hits)
    assert not validate_excerpts(raw(hits[0]['text'],2),hits)

def test_model_hallucination_with_valid_citation_is_rejected():
    with patch('app.main.llm') as model:
        model.return_value.stream.return_value=[Mock(content='الشمس تضيء بلون أخضر. [1]')]
        assert compose('شو لون الشمس',[{'title':'policy','page':10,'text':'القبول والتسجيل في الجامعة يخضع لشروط محددة.'}])==(REFUSAL,[],True)
