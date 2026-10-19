"""Bind attachment confidentiality to every read, including old generated exports."""
from alembic import op
import sqlalchemy as sa
revision = '6d30bb12e441'
down_revision = '5c4c6e012a90'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('ncc_attachment', sa.Column('requires_secret', sa.Boolean(), server_default=sa.true(), nullable=False))


def downgrade():
    op.drop_column('ncc_attachment', 'requires_secret')
