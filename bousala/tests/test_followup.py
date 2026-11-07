from app.context import resolve_followup,track_from_text
from app.main import Turn
import pytest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from app.rules import lookup

def test_arabic_regular_is_explicit():
    assert track_from_text('كم ساعة مطلوب لتخصص هندسة البرمجيات للمستوى العادي؟')=='regular'

def test_single_placement_answer_keeps_original_question():
    history=[Turn(role='user',content='كم ساعة للدرجة؟'),Turn(role='assistant',content='ما مسار الإنجليزية؟')]
    question,track=resolve_followup('Intensive',history)
    assert track=='intensive' and 'كم ساعة' in question

def test_latest_choice_overrides_previous_regular():
    question,track=resolve_followup('Intensive',[Turn(role='user',content='كم ساعة للمستوى العادي؟')])
    assert track=='intensive' and track_from_text(question)=='intensive'

def test_placement_without_history_does_not_invent_question():
    assert resolve_followup('Intensive',[])==('Intensive','intensive')

@pytest.mark.parametrize('choice,total',[('Intermediate',132),('Intensive',134)])
def test_followup_reaches_degree_lookup_with_evidence(choice,total):
    question,track=resolve_followup(choice,[Turn(role='user',content='كم ساعة مطلوب لتخصص هندسة البرمجيات للمستوى العادي؟')])
    db=Mock()
    db.get.return_value=SimpleNamespace(value={'breakdown':{'University Requirement':31,'Faculty Requirement':18,'Major Requirement':66,'Major Elective':15},'additions':{'regular':0,'intermediate':2,'intensive':4}})
    with patch('app.rules.evidence',return_value={'source_id':'catalog_degree','page':1}):
        kind,answer,citations=lookup(db,question,track)
    assert kind=='lookup'
    assert f'{total} ساعة' in answer
    assert citations==[{'source_id':'catalog_degree','page':1}]
