"""Source-only parsing QA. Does not require or pretend to ingest a database."""
import csv
import json
from app.config import ROOT
from app.ingest import pages, course_rows, sha

def audit():
    manifest = []
    for path in sorted((ROOT/'sources').rglob('*.pdf')):
        texts = pages(path)
        manifest.append({'path': str(path.relative_to(ROOT)), 'pages': len(texts), 'sha256': sha(path.read_bytes()),
                         'textless_pages': [i+1 for i,t in enumerate(texts) if not t.strip()]})
    rows, issues = course_rows(pages(ROOT/'sources/catalog/program_of_study_2024_2025.pdf'))
    prereqs = list(csv.DictReader((ROOT/'data/official_site_prerequisites_team_transcription.csv').open(encoding='utf-8-sig')))
    totals = {}
    for track in ('regular','intermediate','intensive'):
        by_category = {}
        for r in rows:
            if r['track'] == track:
                by_category[r['category']] = by_category.get(r['category'], 0)+r['credits']
        totals[track] = by_category
    issues += [{'issue': 'SWER312/SWER342 same-semester paradigm vs sequential prerequisite conflict'},
               {'issue': 'Compiled policies may originate in 2020; current applicability not certified'},
               {'issue': 'Displayed GPA example 1.59 conflicts with 24/17 arithmetic'},
               {'issue': 'Held-out EVAL025 has no bundled GPA image; arithmetic inputs are in question'},
               {'issue': 'Held-out EVAL028 targets an excluded future What-If feature; not academic evidence'}]
    report = {'database_ingested': False, 'manifest': manifest, 'course_variant_rows': len(rows), 'unique_courses': len({r['code'] for r in rows}),
              'prerequisites': len(prereqs), 'track_row_sums': totals, 'issues': issues}
    (ROOT/'reports/data_quality_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    (ROOT/'reports/course_rows_review.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('manifest','issues')}))

if __name__ == '__main__':
    audit()
