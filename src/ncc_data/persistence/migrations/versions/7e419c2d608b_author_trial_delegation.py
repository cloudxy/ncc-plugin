"""Record bounded author trial separately from calibrated trust."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '7e419c2d608b'
down_revision = '6d30bb12e441'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('ncc_delegation', sa.Column('authorization', postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False))


def downgrade():
    op.drop_column('ncc_delegation', 'authorization')
