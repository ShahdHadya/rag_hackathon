"""Allow official six-credit Simulation graduation projects."""
from alembic import op
from sqlalchemy import inspect
revision='003'
down_revision='002'

def upgrade():
    checks=inspect(op.get_bind()).get_check_constraints('courses')
    for check in checks:
        if 'credits' in check['sqltext'] and check['name']!='courses_credit_range':
            op.drop_constraint(check['name'],'courses',type_='check')
    if not any(c['name']=='courses_credit_range' for c in checks):
        op.create_check_constraint('courses_credit_range','courses','credits BETWEEN 0 AND 30')

def downgrade():
    raise RuntimeError('Cannot safely narrow credits while six-credit official courses exist.')
