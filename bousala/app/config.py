import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')
DATABASE_URL = os.getenv('DATABASE_URL') or 'postgresql+psycopg://postgres@localhost:5432/bousala'
MODEL = os.getenv('OLLAMA_MODEL', 'qwen3:1.7b')
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434')
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
DIM = int(os.getenv('EMBEDDING_DIM', '384'))
TOP_K = int(os.getenv('TOP_K', '5'))
CONFIG_REVISION = 'bousala-1'
