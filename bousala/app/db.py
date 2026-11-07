from functools import lru_cache
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.config import DATABASE_URL

@lru_cache(maxsize=1)
def engine():
    return create_engine(DATABASE_URL, pool_pre_ping=True, connect_args={'connect_timeout': 5})

def session():
    return Session(engine())
