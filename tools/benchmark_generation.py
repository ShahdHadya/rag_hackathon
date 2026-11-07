"""Synthetic context benchmark: python -m tools.benchmark_generation (no index changes)."""
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')
from time import perf_counter
from langchain_ollama import ChatOllama
from config import OLLAMA_MODEL
from rag.generation import AnswerStream, prompt_for, validate

sources = [{'source': 'benchmark.txt', 'page': 1, 'text': 'Technical RAG quality is worth 30 points.'}]
questions = ['كم علامة مخصصة لجودة نظام RAG التقنية؟', 'How many points is technical RAG quality worth?']
baseline = ChatOllama(model=OLLAMA_MODEL, temperature=0)
for question in questions:
    start = perf_counter()
    raw = baseline.invoke(prompt_for(question, sources)).content
    elapsed = perf_counter() - start
    print(json.dumps({'mode': 'baseline_invoke', 'question': question, 'first_visible_seconds': elapsed, 'total_seconds': elapsed, 'validated_answer': validate(raw, sources)}, ensure_ascii=False), flush=True)
    stream = AnswerStream(question, sources)
    draft = ''.join(stream)
    print(json.dumps({'mode': 'stream_no_thinking', 'question': question, **stream.metrics, 'draft': draft, 'validated_answer': stream.final}, ensure_ascii=False), flush=True)
