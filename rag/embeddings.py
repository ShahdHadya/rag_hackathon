from functools import lru_cache
from sentence_transformers import SentenceTransformer
from config import EMBEDDING_MODEL


@lru_cache(maxsize=2)
def model(name=EMBEDDING_MODEL):
    return SentenceTransformer(name)


def encode(texts):
    return model().encode(texts, normalize_embeddings=True).tolist()
