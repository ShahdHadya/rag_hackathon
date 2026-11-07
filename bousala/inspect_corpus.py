import csv
import json
from pathlib import Path
import pymupdf

root = Path(__file__).resolve().parent
out = root / 'reports'
out.mkdir(exist_ok=True)
manifest = []
for path in sorted((root / 'sources').rglob('*.pdf')):
    with pymupdf.open(path) as doc:
        pages = [p.get_text(sort=True) for p in doc]
        (out / (path.stem + '.txt')).write_text('\n\n'.join(f'PAGE {i+1}\n{t}' for i,t in enumerate(pages)), encoding='utf-8')
        manifest.append({'file': str(path.relative_to(root)), 'pages': len(doc), 'characters': [len(t) for t in pages]})
for path in (root/'data').glob('*.csv'):
    rows = list(csv.DictReader(path.open(encoding='utf-8-sig')))
    manifest.append({'file': str(path.relative_to(root)), 'rows': len(rows)})
for path in (root/'quality').glob('*.json'):
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    manifest.append({'file': str(path.relative_to(root)), 'keys': list(data)})
(out/'corpus_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print(json.dumps(manifest, indent=2))
