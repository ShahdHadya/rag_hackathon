"""Live checks for the bounded recovery path, using previously retrieved real context."""
import json
from pathlib import Path
from time import perf_counter
from rag.generation import repair_citation

reports = json.loads(Path('data/debug/final_checks.json').read_text(encoding='utf-8'))
sources = reports[1]['sources']
results = []
for question, expected_support in [(reports[1]['question'], True), ('What is the weather forecast in Tokyo tomorrow?', False)]:
    audit = {}
    start = perf_counter()
    result = repair_citation(question, sources, 'REFUSE', audit)
    passed = bool(result and '30' in result) if expected_support else result is None
    results.append({'question': question, 'answer': result, 'audit': audit, 'passed': passed, 'elapsed_seconds': perf_counter()-start})
    Path('data/debug/recovery_checks.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'expected_support': expected_support, 'passed': passed, 'seconds': results[-1]['elapsed_seconds']}), flush=True)
if not all(result['passed'] for result in results):
    raise SystemExit('Live recovery test failed; inspect ignored local trace.')
