"""Initial Bousala schema."""
from alembic import op
from app.models import Base
revision = '001'
down_revision = None

def upgrade():
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')
    Base.metadata.create_all(op.get_bind())
    op.execute('CREATE INDEX chunk_text_trgm ON document_chunks USING gin (normalized gin_trgm_ops)')

def downgrade():
    Base.metadata.drop_all(op.get_bind())
