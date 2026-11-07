from config import TOP_K, MAX_DISTANCE
from rag.embeddings import encode
from rag.vector_store import collection
from rag.ingestion import normalize_text


def retrieve(question, top_k=TOP_K, max_distance=MAX_DISTANCE):
    current = collection()
    if current.count() == 0:
        return []
    result = current.query(query_embeddings=encode([question]), n_results=min(top_k, current.count()), include=['documents', 'metadatas', 'distances'])
    sources, seen = [], set()
    for text, meta, distance in zip(result['documents'][0], result['metadatas'][0], result['distances'][0]):
        normalized = normalize_text(text)
        key = (meta['source'], meta['page'], ' '.join(normalized.split()))
        if distance <= max_distance and key not in seen:
            seen.add(key)
            sources.append({'text': normalized, **meta, 'distance': distance, 'similarity': 1 - distance})
    return sources
