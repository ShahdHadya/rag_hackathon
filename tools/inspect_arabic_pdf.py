"""Inspect the specified public fixture; keep full extraction comparisons local."""
import importlib.util
import json
import sys
from pathlib import Path
from pypdf import PdfReader
from rag.ingestion import normalize_text, positioned_text
from rag.vector_store import collection

sys.stdout.reconfigure(encoding='utf-8')
path = Path(sys.argv[1])
reader = PdfReader(path)
page = reader.pages[2]
results = {'positioned_pypdf': positioned_text(page), 'pypdf': normalize_text(page.extract_text() or ''),
           'pypdf_layout': normalize_text(page.extract_text(extraction_mode='layout') or '')}
runs = []
def visit(text, cm, tm, font, size):
    if text.strip():
        runs.append({'text': normalize_text(text), 'x': tm[4]*cm[0]+tm[5]*cm[2]+cm[4], 'y': tm[4]*cm[1]+tm[5]*cm[3]+cm[5]})
page.extract_text(visitor_text=visit)
results['positioned_runs'] = runs
if importlib.util.find_spec('pymupdf'):
    import pymupdf as fitz
    with fitz.open(path) as doc:
        results['pymupdf'] = normalize_text(doc[2].get_text(sort=True))
        results['pymupdf_unsorted'] = normalize_text(doc[2].get_text())
        doc[2].get_pixmap(matrix=fitz.Matrix(1.3, 1.3)).save('data/debug/pdf_page3.png')
else:
    results['pymupdf'] = 'NOT INSTALLED'
stored = collection().get(where={'source': path.name}, include=['documents', 'metadatas'])
results['stored_page3'] = [text for text, meta in zip(stored['documents'], stored['metadatas']) if meta['page'] == 3]
Path('data/debug/extraction_comparison.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
for key, value in results.items():
    print(key, ':', str(value)[:1800], '\n', flush=True)
