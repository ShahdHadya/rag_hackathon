"""Headless Streamlit + live local RAG checks; not a browser visual test."""
import json
from streamlit.testing.v1 import AppTest
from rag.generation import UNAVAILABLE
from pathlib import Path

app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=180).run()
assert not app.exception, app.exception
for question, supported in [('كم علامة مخصصة لجودة نظام RAG التقنية؟', True),
                            ('How many points are allocated to technical RAG quality?', True),
                            ('What is the weather forecast in Tokyo tomorrow?', False)]:
    app.chat_input[0].set_value(question).run(timeout=180)
    assert not app.exception, app.exception
    message = app.session_state['messages'][-1]
    if supported:
        assert '30' in message['content'], 'Expected supported score absent'
        assert message['sources'], 'Missing supporting citation'
        assert all(s['page'] in (2, 3) for s in message['sources']), 'Wrong cited page'
        assert all(s['source'] == 'IEEE_RAG_Hackathon_Judging_Guide_AR.pdf' for s in message['sources'])
    else:
        assert message['content'] == UNAVAILABLE, 'Unsupported question was not refused'
        assert not message['sources'], 'Refusal displayed supporting evidence'
    print(json.dumps({'supported_case': supported, 'passed': True, 'source_pages': [s['page'] for s in message['sources']]}), flush=True)
assert any('dir="rtl"' in markdown.value for markdown in app.markdown)
assert any('dir="ltr"' in markdown.value for markdown in app.markdown)
print('RTL/LTR HTML attributes present; headless check only.', flush=True)
