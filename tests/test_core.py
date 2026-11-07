import unittest
from rag.chunking import split_pages
from rag.ingestion import read_pdf, normalize_text
from rag.generation import answer, UNAVAILABLE, is_arabic


class CoreTests(unittest.TestCase):
    def test_empty_pdf_error(self):
        pages, error = read_pdf(b'bad', 'bad.pdf')
        self.assertEqual(pages, [])
        self.assertIn('bad.pdf', error)

    def test_chunk_metadata(self):
        chunks = split_pages([{'text': 'Alpha. ' * 100, 'source': 'a.pdf', 'page': 3}], 80, 10)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(c['page'] == 3 and c['source'] == 'a.pdf' for c in chunks))

    def test_no_context_abstains(self):
        self.assertEqual(answer('unknown', []), UNAVAILABLE)

    def test_arabic_normalization_and_detection(self):
        self.assertEqual(normalize_text('ﻋﻼﻣﺔ RAG'), 'علامة RAG')
        self.assertTrue(is_arabic('كم علامة مخصصة لجودة نظام RAG التقنية؟'))
        self.assertFalse(is_arabic('How many points?'))


if __name__ == '__main__':
    unittest.main()
