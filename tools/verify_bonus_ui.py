"""Live headless Streamlit check for bonus eligibility, with real streamed output."""
import json
from pathlib import Path
from streamlit.testing.v1 import AppTest
from rag.numeric_grounding import quantities

app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=180).run()
assert not app.exception, app.exception
app.chat_input[0].set_value('What are the conditions for earning bonus points?').run(timeout=180)
assert not app.exception, app.exception
message = app.session_state['messages'][-1]
assert message['status'] == 'validated', message['content']
assert any(kind == 'proportion' and value.numerator == 1 and value.denominator == 2 for kind, value, _, _ in quantities(message['content']))
assert message['sources'] and all(s['page'] == 6 for s in message['sources'])
assert message['metrics']['ui_chunks'] > 1
report = {'answer': message['content'], 'pages': [s['page'] for s in message['sources']], 'metrics': message['metrics'], 'passed': True}
Path('data/debug/bonus_ui.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report), flush=True)
