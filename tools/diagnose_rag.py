"""Local-only reproduction. Exact context/output go to ignored data/debug, never console."""
import json
import sys
from pathlib import Path
from time import perf_counter
from rag.retrieval import retrieve
from rag.generation import AnswerStream, prompt_for

sys.stdout.reconfigure(encoding='utf-8')
questions = ['كم علامة مخصصة لجودة نظام RAG التقنية؟',
             'How many points are allocated to technical RAG quality?',
             'What is the weather forecast in Tokyo tomorrow?']
reports = []
output = sys.argv[1] if len(sys.argv) > 1 else 'reproduction'
for question in questions:
    start = perf_counter()
    sources = retrieve(question)
    retrieval_time = perf_counter() - start
    stream = AnswerStream(question, sources)
    raw = ''.join(stream)
    report = {'question': question, 'retrieval_seconds': retrieval_time,
              'sources': sources, 'prompt': prompt_for(question, sources),
              'raw_content': raw, 'final': stream.final, 'metrics': stream.metrics,
              'validation_reason': stream.validation_reason, 'repair': stream.repair_details}
    reports.append(report)
    path = Path(f'data/debug/{output}.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'case': len(reports), 'retrieval_seconds': retrieval_time,
                      'pages': [s['page'] for s in sources], 'metrics': stream.metrics,
                      'raw_has_citation': '[' in raw, 'final_equals_raw': raw.strip() == stream.final}, ensure_ascii=True), flush=True)
