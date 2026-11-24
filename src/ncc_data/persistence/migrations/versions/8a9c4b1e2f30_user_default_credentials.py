"""Add must_change_credentials flag for default bootstrap administrator."""
from alembic import op
import sqlalchemy as sa

revision = '8a9c4b1e2f30'
down_revision = '7e419c2d608b'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'ncc_user',
        sa.Column('must_change_credentials', sa.Boolean(), server_default=sa.false(), nullable=False),
    )


def downgrade():
    op.drop_column('ncc_user', 'must_change_credentials')
