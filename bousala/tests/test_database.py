"""Real integration tests; explicit opt-in avoids touching arbitrary databases."""
import os
import pytest
from sqlalchemy import select, func
from app.db import session
from app.models import Chunk, Course, Prerequisite
from app.ingest import ingest

@pytest.mark.skipif(os.getenv('BOUSALA_TEST_DB')!='1', reason='Requires configured isolated Bousala database, migrations and pgvector')
def test_ingest_twice_without_duplicates():
    ingest()
    with session() as db:
        before=db.scalar(select(func.count()).select_from(Chunk))
    ingest()
    with session() as db:
        assert db.scalar(select(func.count()).select_from(Chunk))==before
        assert db.scalar(select(func.count()).select_from(Course))==57
        assert db.get(Prerequisite,'SWER381').required==['SWER142','SWER212']
