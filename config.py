import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
ROOT = Path(__file__).resolve().parent
DB_PATH = os.getenv('RAG_DB_PATH') or str(ROOT / 'data' / 'chroma')
EMBEDDING_MODEL = os.getenv('RAG_EMBEDDING_MODEL', 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
OLLAMA_MODEL = os.getenv('RAG_OLLAMA_MODEL', 'qwen3:1.7b')
CHUNK_SIZE = int(os.getenv('RAG_CHUNK_SIZE', '800'))
CHUNK_OVERLAP = int(os.getenv('RAG_CHUNK_OVERLAP', '120'))
TOP_K = int(os.getenv('RAG_TOP_K', '4'))
MAX_DISTANCE = float(os.getenv('RAG_MAX_DISTANCE', '0.8'))
