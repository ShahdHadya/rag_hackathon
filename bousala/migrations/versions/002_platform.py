"""Add multi-curriculum platform without deleting or resetting existing rows."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from app.models import Base

revision='002'
down_revision='001'

def upgrade():
    bind=op.get_bind()
    Base.metadata.create_all(bind,checkfirst=True)
    existing={c['name'] for c in inspect(bind).get_columns('source_documents')}
    for name,kind in [('curriculum_id',sa.String()),('scope',sa.String()),('review_status',sa.String()),('document_role',sa.String())]:
        if name not in existing:
            op.add_column('source_documents',sa.Column(name,kind,nullable=True))
    op.execute("UPDATE source_documents SET scope=CASE WHEN kind='policy' THEN 'university' ELSE 'program' END WHERE scope IS NULL")
    op.execute("UPDATE source_documents SET review_status=CASE WHEN active THEN 'published' ELSE 'draft' END WHERE review_status IS NULL")
    # Curriculum FK is added after the legacy backfill can create a real program row.
    if not any(i['name']=='ix_source_documents_curriculum_id' for i in inspect(bind).get_indexes('source_documents')):
        op.create_index('ix_source_documents_curriculum_id','source_documents',['curriculum_id'])

def downgrade():
    raise RuntimeError('Destructive platform downgrade is intentionally disabled; restore the pre-upgrade backup if required.')
