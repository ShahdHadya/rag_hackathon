"""Read every supplied Simulation PDF; no database writes."""
from pathlib import Path
import json
import pymupdf
from app.config import ROOT

def run():
    folder=ROOT/'reports/simulation_audit'
    folder.mkdir(parents=True,exist_ok=True)
    manifest=[]
    for path in sorted((Path.home()/'Downloads').glob('*majorCode=248*pdf')):
        with pymupdf.open(path) as doc:
            text='\n\n'.join(f'PDF PAGE {i+1}\n'+page.get_text(sort=True) for i,page in enumerate(doc))
            index=path.name.split('&page=')[1].split('&')[0]
            (folder/f'page_{index}.txt').write_text(text,encoding='utf-8')
            manifest.append({'file':str(path),'catalog_page':index,'pdf_pages':len(doc)})
            if index in ('0','1','2','3'):
                print(text,flush=True)
    (folder/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(manifest),flush=True)

if __name__=='__main__':
    run()
