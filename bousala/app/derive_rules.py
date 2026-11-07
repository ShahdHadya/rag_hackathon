"""Source-parse the few explicit admission thresholds; do not certify individuals."""
import re
from app.config import ROOT
from app.ingest import pages

def admission_rules(text=None):
    if text is None:
        text = pages(ROOT/'sources/catalog/acceptance_to_major_2024_2025.pdf')[0]
    patterns = {'earned_credits':r'earned\s+(\d+)\s+credits',
                'overall_gpa':r'overall cumulative GPA of\s+([\d.]+)',
                'major_gpa':r'major cumulative GPA of\s+([\d.]+)',
                'major_courses':r'at least\s+(\d+)\s+courses',
                'major_credits':r'courses\s*\(\s*(\d+)\s+credits'}
    result={}
    for key,pattern in patterns.items():
        match=re.search(pattern,text,re.I)
        if not match:
            raise ValueError('Admission field could not be source-verified: '+key)
        result[key]=match[1]
    track_pattern=r'(Regular|Intermediate|Intensive) English students:\s*completion of\s*(.*?)(?=(?:Regular|Intermediate|Intensive) English students:|\n\s*4\.|\n\s*Note:)'
    tracks={m[1].lower():re.findall(r'ENG[L R]\d{3}'.replace(' ',''),m[2]) for m in re.finditer(track_pattern,text,re.I|re.S)}
    if len(tracks)!=3 or any(not codes for codes in tracks.values()):
        raise ValueError('English admission-track rows require manual review')
    result['english_courses']=tracks
    return result

if __name__=='__main__':
    from app.db import session
    from app.models import Setting
    with session() as db, db.begin():
        db.merge(Setting(key='admission', value=admission_rules()))
    print('Admission thresholds verified against catalog and stored.')
