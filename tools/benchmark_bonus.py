"""Live bonus-question trace; exact text stays in ignored data/debug."""
import json
import re
import sys
from pathlib import Path
from time import perf_counter
from rag.generation import AnswerStream, prompt_for
from rag.retrieval import retrieve
from rag.context_selection import focus_sources

question = 'What are the conditions for earning bonus points?'
started = perf_counter()
sources = retrieve(question)
if '--focused' in sys.argv:
    sources = focus_sources(question, sources)
retrieval_seconds = perf_counter()-started
stream = AnswerStream(question, sources)
raw = ''.join(stream.ui_chunks())
cited = set(re.findall(r'\[(\d+)\]', raw))
evidence = '\n'.join(sources[int(i)-1]['text'] for i in cited if 0 < int(i) <= len(sources))
numbers = lambda text: {str(int(n)) for n in re.findall(r'\d+', text)}
report = {'question': question, 'sources': sources, 'prompt': prompt_for(question, sources),
          'raw': raw, 'final': stream.final, 'reason': stream.validation_reason,
          'old_missing_numbers': sorted(numbers(re.sub(r'\[\d+\]', '', raw))-numbers(evidence)),
          'retrieval_seconds': retrieval_seconds, 'metrics': stream.metrics}
report['validation_details'] = stream.validation_details
folder = Path('data/debug')
folder.mkdir(parents=True, exist_ok=True)
name = sys.argv[1] if len(sys.argv)>1 else 'bonus_baseline'
(folder / f'{name}.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({k: report[k] for k in ('reason','old_missing_numbers','retrieval_seconds','metrics')}), flush=True)
