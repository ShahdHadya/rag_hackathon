"""Create only the requested native Bousala DB; never alter server authentication."""
import sys
import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url
from app.config import DATABASE_URL

def bootstrap():
    url=make_url(DATABASE_URL)
    if url.database!='bousala':
        raise ValueError('Bootstrap only creates the dedicated bousala database')
    params={'host':url.host or 'localhost','port':url.port or 5432,'user':url.username,'password':url.password,'connect_timeout':5}
    with psycopg.connect(dbname='postgres', **params, autocommit=True) as db:
        if not db.execute('SELECT 1 FROM pg_database WHERE datname=%s', ('bousala',)).fetchone():
            db.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier('bousala')))
    with psycopg.connect(dbname='bousala', **params, autocommit=True) as db:
        available=bool(db.execute("SELECT 1 FROM pg_available_extensions WHERE name='vector'").fetchone())
        print('native_database_connected=true; pgvector_available='+str(available).lower())
        if not available:
            return 2
    return 0

if __name__=='__main__':
    try:
        sys.exit(bootstrap())
    except Exception as exc:
        print('Native database bootstrap failed ('+type(exc).__name__+'). Credentials were not printed.')
        sys.exit(1)
