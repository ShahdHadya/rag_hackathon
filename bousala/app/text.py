import re
import unicodedata
from functools import lru_cache
from sentence_transformers import SentenceTransformer
from app.config import EMBEDDING_MODEL, DIM

def normalize(text: str) -> str:
    text = unicodedata.normalize('NFKC', text).upper()
    text = re.sub(r'[\u064b-\u065f\u0640]', '', text)
    text = text.translate(str.maketrans('أإآى', 'اااي'))
    return ' '.join(text.split())

def codes(text: str) -> list[str]:
    value = re.sub(r'([A-Z]{4})\s+(\d{3})', r'\1\2', normalize(text))
    # Arabic clitics may touch a Latin code; Unicode \b incorrectly rejects that.
    return re.findall(r'(?<![A-Z0-9])(?:[A-Z]{4}\d{3}|SWERGR1)(?![A-Z0-9])', value)

@lru_cache(maxsize=1)
def embedder():
    model = SentenceTransformer(EMBEDDING_MODEL, device='cpu')
    if model.get_sentence_embedding_dimension() != DIM:
        raise ValueError('EMBEDDING_DIM differs from model dimension. Use a new database/migration and rebuild.')
    maximum = getattr(model[0].auto_model.config, 'max_position_embeddings', 512)
    model.max_seq_length = min(512, maximum)
    return model

def embedding_spec():
    return {'model': EMBEDDING_MODEL, 'dimension': DIM, 'max_seq_length': embedder().max_seq_length, 'normalization': 'L2'}

def embed(texts: list[str]) -> list[list[float]]:
    return embedder().encode(texts, normalize_embeddings=True).tolist()
