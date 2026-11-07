import os
from pathlib import Path
import unittest
from pypdf import PdfReader
from rag.ingestion import positioned_text, read_pdf

FIXTURE = Path(os.getenv('RAG_ARABIC_PDF', str(Path.home() / 'Downloads' / 'IEEE_RAG_Hackathon_Judging_Guide_AR.pdf')))


@unittest.skipUnless(FIXTURE.is_file(), 'Actual Arabic PDF fixture unavailable')
class ArabicPdfRegression(unittest.TestCase):
    def test_page_three_logical_words_and_score(self):
        text = positioned_text(PdfReader(FIXTURE).pages[2])
        self.assertIn('جودة حل RAG التقني', text)
        self.assertIn('30 علامة', text)
        self.assertNotIn('ﻋ', text)

    def test_filename_and_page_preserved(self):
        pages, error = read_pdf(FIXTURE.read_bytes(), FIXTURE.name)
        self.assertIsNone(error)
        third = next(p for p in pages if p['page'] == 3)
        self.assertEqual(third['source'], FIXTURE.name)
        self.assertIn('جودة حل RAG التقني', third['text'])
