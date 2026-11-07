"""Run after replacing placeholders in questions_template.json with verified cases."""
import json
from pathlib import Path
from rag.retrieval import retrieve
from rag.generation import answer, UNAVAILABLE


def evaluate(path):
    cases = json.loads(Path(path).read_text(encoding='utf-8'))
    if len(cases) < 10 or any(not c.get('question') or c.get('reference_answer') is None or c.get('expected_sources') is None for c in cases):
        raise ValueError('Supply at least 10 verified questions, reference answers, and expected sources.')
    report = []
    for case in cases:
        sources = retrieve(case['question'])
        expected = {(s['source'], s['page']) for s in case['expected_sources']}
        hits = [(s['source'], s['page']) for s in sources]
        precision = sum(hit in expected for hit in hits) / len(hits) if hits else 0
        response = answer(case['question'], sources)
        unsupported_ok = (UNAVAILABLE == response) if case.get('out_of_scope') else None
        cited = all(f"[{i}]" in response for i in range(1, len(sources) + 1) if f"[{i}]" in response)
        report.append({'question': case['question'], 'precision_at_k': precision, 'answer': response, 'reference_answer': case['reference_answer'], 'expected_sources': case['expected_sources'], 'retrieved_sources': hits, 'out_of_scope_pass': unsupported_ok, 'citation_format_check': cited, 'faithfulness': 'manual review required', 'improvement': 'Inspect missed sources, chunk boundaries, threshold, and prompt if this case fails.'})
    return report


if __name__ == '__main__':
    import sys
    result = evaluate(sys.argv[1] if len(sys.argv) > 1 else 'evaluation/questions_template.json')
    Path('evaluation/report.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Wrote evaluation/report.json; manually review faithfulness against retrieved excerpts.')
