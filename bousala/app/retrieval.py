import re
from sqlalchemy import select
from app.config import TOP_K
from app.models import Setting, Chunk, Source
from app.text import embed, normalize, codes, embedding_spec

def check_index(db):
    setting = db.get(Setting, 'embedding')
    if setting is None:
        raise ValueError('Corpus not ingested. Run alembic upgrade head then python -m app.ingest --all.')
    if setting.value != embedding_spec():
        raise ValueError('Embedding configuration mismatch; vector search refused. Restore original config or migrate a fresh database and rebuild.')

def rrf(rankings, k=60):
    scores = {}
    for ranking in rankings:
        for rank, key in enumerate(ranking, 1):
            scores[key] = scores.get(key, 0)+1/(k+rank)
    return sorted(scores, key=lambda key: scores[key], reverse=True)

def retrieve(db, question: str, top_k=TOP_K):
    check_index(db)
    vector = embed([question])[0]
    distance = Chunk.embedding.cosine_distance(vector)
    nearest = list(db.execute(select(Chunk.id, distance.label('distance')).order_by(distance).limit(20)))
    # Arabic keyword search does not depend on English PostgreSQL text stemming.
    terms = re.findall(r'[A-Z]{4}\d{3}|[\u0621-\u064a]{3,}|[A-Z]{3,}', normalize(question))
    stop = {'WHAT', 'THE', 'ARE', 'HOW', 'FOR', 'CAN', 'شو', 'كيف', 'بقدر', 'المطلوب'}
    terms = [t for t in terms if t not in stop]
    aliases = {'GPA': 'معدل', 'DROP': 'حذف', 'WITHDRAW': 'انسحاب', 'LOAD': 'عبء', 'GRADE': 'علامات'}
    terms += [aliases[t] for t in terms if t in aliases]
    # Corpus is tiny: transparent normalized keyword scoring, fused with vector ranks.
    all_chunks = db.scalars(select(Chunk)).all()
    keyword = sorted(all_chunks, key=lambda c: sum(t in c.normalized for t in terms), reverse=True)
    keyword_ids = [c.id for c in keyword if any(t in c.normalized for t in terms)][:20]
    identifiers = codes(question)
    exact = [c.id for c in all_chunks if any(code in c.normalized for code in identifiers)]
    # Short physical heading lines are a fourth structural retrieval signal.
    # This prevents a contents list or a passing mention outranking the actual section.
    heading_scores = {}
    for chunk in all_chunks:
        heading = normalize(' '.join(line for line in chunk.text.splitlines()[:4] if 0 < len(line.strip()) <= 60))
        heading_scores[chunk.id] = sum(term in heading for term in terms)
    headings = sorted([c.id for c in all_chunks if heading_scores[c.id]], key=lambda key: heading_scores[key], reverse=True)[:20]
    vector_ids = [r.id for r in nearest if r.distance <= 0.65]
    ranking = rrf([exact, keyword_ids, vector_ids, headings])[:top_k]
    strongest = max((heading_scores[key] for key in ranking), default=0)
    if strongest >= 2 and not identifiers:
        focused = [key for key in ranking if heading_scores[key] == strongest]
        if focused:
            ranking = focused
    by_id = {c.id: c for c in all_chunks}
    sources = {s.id: s for s in db.scalars(select(Source).where(Source.active))}
    results = []
    for key in ranking:
        chunk = by_id[key]
        if chunk.source_id not in sources:
            continue
        source = sources[chunk.source_id]
        results.append({'chunk_id': chunk.id, 'source_id': source.id, 'title': source.title,
                        'page': chunk.page, 'url': chunk.details.get('url') or source.url,
                        'text': chunk.text, 'topic': chunk.topic, 'provenance': source.provenance,
                        'caution': chunk.details.get('caution'), 'csv_row': chunk.details.get('csv_row')})
    return results
