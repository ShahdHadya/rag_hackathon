import argparse
import hashlib
import json
import uuid
from app.config import ROOT
from app.db import session
from app.main import chat, ChatRequest
from app.models import Evaluation
from app.retrieval import retrieve

def evaluate(path, report_name='evaluation'):
    raw = path.read_bytes()
    cases = json.loads(raw).get('benchmark', [])
    results = []
    with session() as db, db.begin():
        for case in cases:
            if case['expected_source'] in ('app_help', 'user_supplied_gpa_diagram'):
                results.append({'id': case['id'], 'excluded': True, 'reason': 'Missing/excluded source; gold needs human review'})
                continue
            request = ChatRequest(message=case['question'])
            hits = retrieve(db, request.message)
            result = chat(db, request, use_cache=False)
            print(json.dumps({'case':case['id'],'kind':result.kind,'refusal':result.refusal,'latency_ms':result.latency_ms}),flush=True)
            expected = case['expected_source']
            page = case['expected_page']
            matching = lambda h: h['source_id'] == expected and (page is None or h['page'] == page)
            relevant = sum(matching(h) for h in hits)
            results.append({'id': case['id'], 'question': case['question'], 'answer': result.answer,
                            'recall_hit_at_k': bool(relevant), 'precision_at_k': relevant/len(hits) if hits else 0,
                            'citation_source_page_match': any(matching(c.model_dump()) for c in result.citations),
                            'refusal_correct': result.refusal if case['expected_kind'] == 'REFUSAL' else None,
                            'latency_ms': result.latency_ms, 'faithfulness': 'manual review required',
                            'gold_review': 'Draft supplied references, not certified gold'})
        measured = [r for r in results if not r.get('excluded')]
        supported = [r for r in measured if r['refusal_correct'] is None]
        negatives = [r for r in measured if r['refusal_correct'] is not None]
        report = {'dataset_sha256': hashlib.sha256(raw).hexdigest(), 'cache_disabled': True,
                  'recall_hits': sum(r['recall_hit_at_k'] for r in supported), 'recall_denominator': len(supported),
                  'negative_passes': sum(r['refusal_correct'] for r in negatives), 'negative_denominator': len(negatives), 'cases': results}
        db.add(Evaluation(id=str(uuid.uuid4()), dataset_hash=report['dataset_sha256'], results=report))
    (ROOT/'reports'/f'{report_name}.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    (ROOT/'reports'/f'{report_name}.md').write_text(f"# Actual evaluation\n\nRecall hits: {report['recall_hits']}/{report['recall_denominator']}. Negative refusals: {report['negative_passes']}/{report['negative_denominator']}.\n\nDraft gold needs human review; faithfulness is not automatically certified. See the JSON report for every answer and failure.\n", encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k != 'cases'}))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', type=lambda s: ROOT/s, default=ROOT/'quality/heldout_evaluation_seed.json')
    parser.add_argument('--report-name', choices=['evaluation','development_evaluation'], default='evaluation')
    args=parser.parse_args()
    evaluate(args.dataset,args.report_name)
