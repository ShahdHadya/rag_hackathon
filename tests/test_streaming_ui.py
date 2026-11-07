"""Exercise invalid/interrupted draft handling through actual st.write_stream."""
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / 'app.py')
SOURCES = [{'source': 'fixture.pdf', 'page': 3, 'text': 'جودة RAG: 30 علامة', 'similarity': 0.7}]


class StreamingUIFailures(unittest.TestCase):
    def test_invalid_grounding_draft_not_saved_as_valid(self):
        with patch('rag.retrieval.retrieve', return_value=SOURCES), patch('rag.generation.client') as factory:
            factory.return_value.stream.return_value = iter([SimpleNamespace(content='9999 '), SimpleNamespace(content='[1]')])
            app = AppTest.from_file(APP, default_timeout=30).run()
            app.chat_input[0].set_value('How many points?').run()
            self.assertFalse(app.exception)
            message = app.session_state['messages'][-1]
            self.assertEqual(message['status'], 'unverified')
            self.assertNotIn('9999', message['content'])
            self.assertEqual(message['sources'], [])
            self.assertTrue(app.warning)
            factory.return_value.invoke.assert_not_called()
            factory.return_value.bind.assert_not_called()

    def test_interrupted_stream_not_saved(self):
        def interrupted():
            yield SimpleNamespace(content='provisional ')
            raise ConnectionError('test disconnect')
        with patch('rag.retrieval.retrieve', return_value=SOURCES), patch('rag.generation.client') as factory:
            factory.return_value.stream.return_value = interrupted()
            app = AppTest.from_file(APP, default_timeout=30).run()
            app.chat_input[0].set_value('How many points?').run()
            self.assertFalse(app.exception)
            self.assertTrue(app.error)
            self.assertFalse(any(m['role'] == 'assistant' for m in app.session_state['messages']))

    def test_no_context_refuses_without_llm_or_supporting_sources(self):
        from rag.generation import UNAVAILABLE
        with patch('rag.retrieval.retrieve', return_value=[]), patch('rag.generation.client') as factory:
            app = AppTest.from_file(APP, default_timeout=30).run()
            app.chat_input[0].set_value('Unrelated question').run()
            self.assertFalse(app.exception)
            message = app.session_state['messages'][-1]
            self.assertEqual(message['content'], UNAVAILABLE)
            self.assertEqual(message['status'], 'refusal')
            self.assertEqual(message['sources'], [])
            factory.assert_not_called()
