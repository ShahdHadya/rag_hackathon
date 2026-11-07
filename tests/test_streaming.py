import unittest
from unittest.mock import patch
from types import SimpleNamespace

from rag.generation import AnswerStream, UNAVAILABLE, answer, prompt_for, validate, VisibleContent


class StreamingTests(unittest.TestCase):
    sources = [{'source': 'arabic.pdf', 'page': 2, 'text': 'جودة RAG: 30 علامة'}]

    def run_stream(self, parts):
        with patch('rag.generation.client') as factory, patch('rag.generation.repair_citation', return_value=None):
            factory.return_value.stream.return_value = [SimpleNamespace(content=p) for p in parts]
            stream = AnswerStream('كم علامة؟', self.sources)
            self.assertIsNone(stream.final)
            draft = ''.join(stream)
        return stream, draft

    def test_progressive_chunks_and_valid_final(self):
        stream, draft = self.run_stream(['30 ', 'علامة [1]'])
        self.assertEqual(draft, '30 علامة [1]')
        self.assertEqual(stream.final, draft)
        self.assertIsNotNone(stream.metrics['ttft_seconds'])

    def test_invalid_citation_replaced(self):
        stream, _ = self.run_stream(['30 [9]'])
        self.assertEqual(stream.final, UNAVAILABLE)

    def test_uncited_draft_replaced(self):
        stream, _ = self.run_stream(['No evidence'])
        self.assertEqual(stream.final, UNAVAILABLE)

    def test_empty_context_skips_model(self):
        with patch('rag.generation.client') as factory:
            self.assertEqual(answer('unknown', []), UNAVAILABLE)
            factory.assert_not_called()

    def test_language_and_source_preserved(self):
        prompt = prompt_for('كم علامة؟', self.sources)
        self.assertIn('Arabic (العربية)', prompt)
        self.assertIn('arabic.pdf, page 2', prompt)
        self.assertIn('English', prompt_for('How many?', self.sources))

    def test_arabic_digit_citation(self):
        self.assertEqual(validate('30 علامة [١]', self.sources), '30 علامة [1]')

    def test_split_thinking_never_visible(self):
        parser = VisibleContent()
        result = ''.join(parser.feed(s) for s in ['<thi', 'nk>private', '</thi', 'nk>30 [1]'])
        self.assertEqual(result, '30 [1]')

    def test_refusal_has_explicit_reason(self):
        stream, _ = self.run_stream(['REFUSE'])
        self.assertEqual(stream.final, UNAVAILABLE)
        self.assertEqual(stream.validation_reason, 'model_refusal')

    def test_repair_requires_real_quote(self):
        import json
        from rag.generation import repair_citation
        with patch('rag.generation.client') as factory:
            factory.return_value.bind.return_value.invoke.return_value = SimpleNamespace(content=json.dumps({'supported': True, 'answer': '30 علامة', 'source_id': 1, 'quote': 'جودة RAG: 30 علامة'}))
            self.assertEqual(repair_citation('كم علامة؟', self.sources, '30'), '30 علامة [1]')
            factory.return_value.bind.return_value.invoke.return_value = SimpleNamespace(content=json.dumps({'supported': True, 'answer': '100 علامة', 'source_id': 1, 'quote': 'جودة RAG: 30 علامة'}))
            self.assertIsNone(repair_citation('كم علامة؟', self.sources, '100'))
            factory.return_value.bind.return_value.invoke.return_value = SimpleNamespace(content=json.dumps({'supported': True, 'answer': '30 علامة', 'source_id': 1, 'quote': 'invented evidence'}))
            self.assertIsNone(repair_citation('كم علامة؟', self.sources, '30'))

    def test_no_lookahead_or_completed_answer_buffer(self):
        reached_end = []
        def provider():
            yield SimpleNamespace(content='30 ')
            yield SimpleNamespace(content='علامة ')
            yield SimpleNamespace(content='[1]')
            reached_end.append(True)
        with patch('rag.generation.client') as factory:
            factory.return_value.stream.return_value = provider()
            stream = AnswerStream('كم علامة؟', self.sources)
            ui = stream.ui_chunks()
            self.assertEqual(next(ui), '30 ')
            self.assertIsNone(stream.final)
            self.assertFalse(reached_end)
            self.assertEqual(next(ui), 'علامة ')
            self.assertFalse(reached_end)
            self.assertEqual(''.join(ui), '[1]')
            self.assertTrue(reached_end)
            factory.return_value.invoke.assert_not_called()
            factory.return_value.bind.assert_not_called()

    def test_reasoning_is_timed_but_not_yielded(self):
        chunks = [SimpleNamespace(content='', additional_kwargs={'reasoning_content': 'private'}),
                  SimpleNamespace(content='30 [1]')]
        with patch('rag.generation.client') as factory:
            factory.return_value.stream.return_value = iter(chunks)
            stream = AnswerStream('كم علامة؟', self.sources)
            self.assertEqual(''.join(stream), '30 [1]')
            self.assertLessEqual(stream.metrics['first_raw_token_seconds'], stream.metrics['first_visible_token_seconds'])
            self.assertEqual(stream.metrics['raw_chunks'], 2)
            self.assertEqual(stream.metrics['visible_chunks'], 1)

    def test_provider_error_discards_partial_answer(self):
        def provider():
            yield SimpleNamespace(content='30 ')
            raise ConnectionError('disconnected')
        with patch('rag.generation.client') as factory:
            factory.return_value.stream.return_value = provider()
            stream = AnswerStream('كم علامة؟', self.sources)
            ui = stream.ui_chunks()
            self.assertEqual(next(ui), '30 ')
            with self.assertRaises(RuntimeError):
                next(ui)
            self.assertIsNone(stream.final)
            self.assertEqual(stream.validation_reason, 'generation_error')
            self.assertFalse(stream.finished)

    def test_cancellation_closes_provider(self):
        closed = []
        def provider():
            try:
                yield SimpleNamespace(content='30 ')
                yield SimpleNamespace(content='[1]')
            finally:
                closed.append(True)
        with patch('rag.generation.client') as factory:
            factory.return_value.stream.return_value = provider()
            stream = AnswerStream('كم علامة؟', self.sources)
            ui = stream.ui_chunks()
            next(ui)
            ui.close()
            self.assertTrue(closed)
            self.assertIsNone(stream.final)
            self.assertEqual(stream.validation_reason, 'interrupted_stream')

    def test_grounding_rejects_number_absent_from_cited_source(self):
        self.assertEqual(validate('100 علامة [1]', self.sources), UNAVAILABLE)
