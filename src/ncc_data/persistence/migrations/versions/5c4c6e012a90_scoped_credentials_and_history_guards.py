"""Scoped credentials and immutable committed history.

Revision ID: 5c4c6e012a90
Revises: 070970fe2f0a
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "5c4c6e012a90"
down_revision = "070970fe2f0a"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("ncc_session", sa.Column("scope_id", sa.String(36), nullable=True))
    op.add_column("ncc_session", sa.Column("actions", postgresql.JSONB(), nullable=True))
    op.create_foreign_key("fk_session_scope", "ncc_session", "ncc_scope", ["scope_id"], ["id"])
    op.execute("""CREATE FUNCTION ncc_history_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF OLD.xmin::text::bigint <> (pg_current_xact_id()::text::bigint % 4294967296) THEN
        RAISE EXCEPTION 'committed NCC history is immutable' USING ERRCODE='23514';
      END IF;
      IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
      RETURN NEW;
    END $$""")
    for table in ("ncc_revision", "ncc_audit", "ncc_receipt", "ncc_assessment", "ncc_definition"):
        op.execute(f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION ncc_history_guard()")
    op.execute("""CREATE FUNCTION ncc_fact_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF OLD.xmin::text::bigint = (pg_current_xact_id()::text::bigint % 4294967296) THEN
        IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
        RETURN NEW;
      END IF;
      IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'committed NCC facts cannot be deleted' USING ERRCODE='23514';
      END IF;
      IF (to_jsonb(NEW)-'recorded_to') <> (to_jsonb(OLD)-'recorded_to')
        OR OLD.recorded_to IS NOT NULL OR NEW.recorded_to IS NULL OR NEW.recorded_to <= OLD.recorded_from THEN
        RAISE EXCEPTION 'NCC fact values are immutable; close once then append' USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$""")
    op.execute("CREATE TRIGGER ncc_fact_immutable BEFORE UPDATE OR DELETE ON ncc_fact FOR EACH ROW EXECUTE FUNCTION ncc_fact_guard()")


def downgrade():
    op.execute("DROP TRIGGER ncc_fact_immutable ON ncc_fact")
    op.execute("DROP FUNCTION ncc_fact_guard()")
    for table in ("ncc_revision", "ncc_audit", "ncc_receipt", "ncc_assessment", "ncc_definition"):
        op.execute(f"DROP TRIGGER {table}_immutable ON {table}")
    op.execute("DROP FUNCTION ncc_history_guard()")
    op.drop_constraint("fk_session_scope", "ncc_session", type_="foreignkey")
    op.drop_column("ncc_session", "actions")
    op.drop_column("ncc_session", "scope_id")
