"""Balanced full/focused prompt benchmark; exact public fixture traces stay local."""
import json
import uuid
from pathlib import Path
from time import perf_counter
from rag.context_selection import focus_sources
from rag.generation import AnswerStream, prompt_for
from rag.retrieval import retrieve

question = 'What are the conditions for earning bonus points?'
start = perf_counter()
candidates = retrieve(question)
retrieval_seconds = perf_counter()-start
focused = focus_sources(question, candidates)
reports = []
# Alternate order; unique early identifiers reduce shared-prefix prompt-cache bias.
for mode in ['full', 'focused', 'focused', 'full']:
    sources = candidates if mode == 'full' else focused
    prompt = f'Request identifier {uuid.uuid4().hex}; ignore this identifier.\n' + prompt_for(question, sources)
    stream = AnswerStream(question, sources, prepared_prompt=prompt)
    raw = ''.join(stream.ui_chunks())
    report = {'mode': mode, 'sources': sources, 'raw': raw, 'final': stream.final,
              'reason': stream.validation_reason, 'failures': stream.validation_details,
              'metrics': stream.metrics, 'retrieval_seconds': retrieval_seconds}
    reports.append(report)
    Path('data/debug/bonus_context_comparison.json').write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'mode': mode, 'pages': [s['page'] for s in sources], 'reason': stream.validation_reason, 'metrics': stream.metrics}), flush=True)
