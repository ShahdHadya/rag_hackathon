"""Live Ollama -> LangChain -> actual Streamlit write_stream enqueue timing.

No model content is logged. This proves server UI updates, not browser paint time.
"""
import json
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

from ollama import Client
from streamlit.delta_generator import DeltaGenerator
from streamlit.testing.v1 import AppTest
from rag.generation import AnswerStream, client

events, streams, requests = [], [], []
original_enqueue, original_chat = DeltaGenerator._enqueue, Client.chat

def stream_factory(*args, **kwargs):
    stream = AnswerStream(*args, **kwargs, observer=events.append)
    streams.append(stream)
    return stream

def enqueue(self, delta_type, element_proto, *args, **kwargs):
    result = original_enqueue(self, delta_type, element_proto, *args, **kwargs)
    if delta_type == 'markdown' and streams and streams[-1].ui_pending:
        events.append({'event': 'streamlit_markdown_enqueued', 'at': perf_counter()})
    return result

def chat(self, *args, **kwargs):
    requests.append({'stream': kwargs.get('stream'), 'think': kwargs.get('think')})
    return original_chat(self, *args, **kwargs)

reports = []
with patch('rag.generation.AnswerStream', side_effect=stream_factory), patch.object(DeltaGenerator, '_enqueue', enqueue), patch.object(Client, 'chat', chat):
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=180).run()
    assert not app.exception, app.exception
    for question in ['كم علامة مخصصة لجودة نظام RAG التقنية؟', 'How many points are allocated to technical RAG quality?']:
        events.clear()
        app.chat_input[0].set_value(question).run(timeout=180)
        assert not app.exception, app.exception
        stream = streams[-1]
        completed = next(e['at'] for e in events if e['event'] == 'model_finished')
        ui_events = [e for e in events if e['event'] == 'streamlit_markdown_enqueued' and e['at'] < completed]
        assert len(ui_events) >= 2, 'Streamlit did not enqueue multiple updates before model completion'
        message = app.session_state['messages'][-1]
        assert message['status'] == 'validated', stream.validation_reason
        assert '30' in message['content'] and message['sources'], 'Supported answer/source missing'
        report = {**message['metrics'], 'ui_updates_before_model_finished': len(ui_events),
                  'first_ui_enqueue_seconds': ui_events[0]['at'] - stream.started_at,
                  'last_ui_enqueue_before_finish_seconds': ui_events[-1]['at'] - stream.started_at,
                  'model_finished_seconds': completed - stream.started_at,
                  'source_pages': [s['page'] for s in message['sources']], 'passed': True}
        reports.append(report)
        print(json.dumps(report), flush=True)
        Path('data/debug').mkdir(parents=True, exist_ok=True)
        Path('data/debug/realtime_streaming.json').write_text(json.dumps({'cases': reports, 'requests': requests}, indent=2), encoding='utf-8')
assert requests and all(r['stream'] is True and r['think'] is False for r in requests)
assert client().reasoning is False
print('All captured Ollama requests: stream=true, think=false.', flush=True)
