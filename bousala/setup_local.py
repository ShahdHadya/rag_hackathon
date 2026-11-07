from pathlib import Path
path = Path(__file__).resolve().parent / '.env'
if not path.exists():
    path.write_text('DATABASE_URL=postgresql+psycopg://postgres@localhost:5432/bousala\n', encoding='utf-8')
print('Native PostgreSQL configuration ready. Edit .env locally if authentication requires a password; no credentials were printed.')
