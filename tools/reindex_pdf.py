"""Preview or replace only one PDF's chunks; back up its records/vectors first."""
import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from config import CHUNK_SIZE, CHUNK_OVERLAP
from rag.ingestion import read_pdf
from rag.chunking import split_pages
from rag.vector_store import collection, index_chunks

sys.stdout.reconfigure(encoding='utf-8')
parser = argparse.ArgumentParser()
parser.add_argument('pdf', type=Path)
parser.add_argument('--apply', action='store_true')
args = parser.parse_args()
pages, error = read_pdf(args.pdf.read_bytes(), args.pdf.name)
if error:
    raise SystemExit(error)
chunks = split_pages(pages, CHUNK_SIZE, CHUNK_OVERLAP)
current = collection()
old = current.get(where={'source': args.pdf.name}, include=['documents', 'metadatas', 'embeddings'])
print(json.dumps({'old_chunks': len(old['ids']), 'replacement_chunks': len(chunks), 'apply': args.apply}))
print(next((p['text'] for p in pages if p['page'] == 3), '')[:1800])
if args.apply:
    backup = Path('data/debug') / f'index_backup_{datetime.now():%Y%m%d_%H%M%S}.json'
    backup.parent.mkdir(parents=True, exist_ok=True)
    old['embeddings'] = old['embeddings'].tolist() if old['embeddings'] is not None else []
    backup.write_text(json.dumps({k: old[k] for k in ('ids', 'documents', 'metadatas', 'embeddings')}, ensure_ascii=False), encoding='utf-8')
    new_ids = {hashlib.sha256(f"{c['source']}:{c['page']}:{c['text']}".encode()).hexdigest() for c in chunks}
    index_chunks(chunks)  # Complete new embeddings and inserts before removing old records.
    stored = current.get(ids=list(new_ids), include=[])['ids']
    if set(stored) != new_ids:
        raise RuntimeError('Replacement incomplete; old records preserved.')
    stale = [key for key in old['ids'] if key not in new_ids]
    if stale:
        current.delete(ids=stale)
    print(json.dumps({'removed_stale': len(stale), 'backup': str(backup), 'indexed_chunks': len(new_ids)}))
