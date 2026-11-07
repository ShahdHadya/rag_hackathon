import hashlib
import chromadb
from config import DB_PATH
from rag.embeddings import encode


def collection():
    return chromadb.PersistentClient(path=DB_PATH).get_or_create_collection('documents', metadata={'hnsw:space': 'cosine'})


def index_chunks(chunks):
    if not chunks:
        return 0
    ids = [hashlib.sha256(f"{c['source']}:{c['page']}:{c['text']}".encode()).hexdigest() for c in chunks]
    unique = {key: chunk for key, chunk in zip(ids, chunks)}
    current = collection()
    existing = set(current.get(ids=list(unique), include=[])['ids'])
    pending = [(key, chunk) for key, chunk in unique.items() if key not in existing]
    if pending:
        current.add(ids=[key for key, _ in pending], documents=[c['text'] for _, c in pending], metadatas=[{'source': c['source'], 'page': c['page']} for _, c in pending], embeddings=encode([c['text'] for _, c in pending]))
    return len(pending)


def reset():
    client = chromadb.PersistentClient(path=DB_PATH)
    try:
        client.delete_collection('documents')
    except chromadb.errors.NotFoundError:
        pass
