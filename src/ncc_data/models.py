"""Stable infrastructure, not a table per fictional noun. Revisions and facts are append-only.

Only recorded-until markers, projections, leases and draft state are mutable. Scope row locks
serialize commits, providing a committed per-scope frontier instead of a wall-clock guess.
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def uid():
    return str(uuid4())


def utcnow():
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Row:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class User(Row, Base):
    __tablename__ = "ncc_user"
    username: Mapped[str] = mapped_column(String(128), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    admin: Mapped[bool] = mapped_column(Boolean, default=False)


class Session(Row, Base):
    __tablename__ = "ncc_session"
    user_id: Mapped[str] = mapped_column(ForeignKey("ncc_user.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    csrf_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    kind: Mapped[str] = mapped_column(String(16), default="browser")
    scope_id: Mapped[str | None] = mapped_column(ForeignKey("ncc_scope.id"))
    actions: Mapped[list | None] = mapped_column(JSONB)


class LoginAttempt(Base):
    __tablename__ = "ncc_login_attempt"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    failures: Mapped[int] = mapped_column(Integer, default=0)
    window_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Scope(Row, Base):
    __tablename__ = "ncc_scope"
    name: Mapped[str] = mapped_column(String(256))
    kind: Mapped[str] = mapped_column(String(32))
    owner_id: Mapped[str | None] = mapped_column(ForeignKey("ncc_user.id"))
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("ncc_scope.id"))
    base_id: Mapped[str | None] = mapped_column(ForeignKey("ncc_scope.id"))
    base_version: Mapped[int | None] = mapped_column(BigInteger)
    version: Mapped[int] = mapped_column(BigInteger, default=0)
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    __table_args__ = (CheckConstraint("version >= 0"),)


class Membership(Row, Base):
    __tablename__ = "ncc_membership"
    scope_id: Mapped[str] = mapped_column(ForeignKey("ncc_scope.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("ncc_user.id"), index=True)
    actions: Mapped[list] = mapped_column(JSONB)
    __table_args__ = (UniqueConstraint("scope_id", "user_id"),)


class Definition(Row, Base):
    __tablename__ = "ncc_definition"
    scope_id: Mapped[str] = mapped_column(ForeignKey("ncc_scope.id"), index=True)
    key: Mapped[str] = mapped_column(String(128))
    version: Mapped[int] = mapped_column(Integer)
    spec: Mapped[dict] = mapped_column(JSONB)
    __table_args__ = (UniqueConstraint("scope_id", "key", "version"),)


class Entity(Row, Base):
    __tablename__ = "ncc_entity"
    scope_id: Mapped[str] = mapped_column(ForeignKey("ncc_scope.id"), index=True)
    kind: Mapped[str] = mapped_column(String(128), index=True)
    current_version: Mapped[int] = mapped_column(BigInteger)
    name: Mapped[str] = mapped_column(String(512))
    data: Mapped[dict] = mapped_column(JSONB, default=dict)
    text: Mapped[str] = mapped_column(Text, default="")
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    secret: Mapped[bool] = mapped_column(Boolean, default=False)
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR)
    __table_args__ = (Index("ix_entity_search", "search_vector", postgresql_using="gin"),)


class Revision(Row, Base):
    __tablename__ = "ncc_revision"
    scope_id: Mapped[str] = mapped_column(ForeignKey("ncc_scope.id"), index=True)
    entity_id: Mapped[str] = mapped_column(ForeignKey("ncc_entity.id"), index=True)
    version: Mapped[int] = mapped_column(BigInteger)
    body: Mapped[dict] = mapped_column(JSONB)
    content_hash: Mapped[str] = mapped_column(String(64))
    change_id: Mapped[str] = mapped_column(String(36))
    __table_args__ = (UniqueConstraint("scope_id", "entity_id", "version"),)


class Fact(Row, Base):
    __tablename__ = "ncc_fact"
    scope_id: Mapped[str] = mapped_column(ForeignKey("ncc_scope.id"), index=True)
    subject_id: Mapped[str] = mapped_column(ForeignKey("ncc_entity.id"), index=True)
    predicate: Mapped[str] = mapped_column(String(128), index=True)
    category: Mapped[str] = mapped_column(String(32), default="fact")
    object_id: Mapped[str | None] = mapped_column(ForeignKey("ncc_entity.id"), index=True)
    value: Mapped[dict] = mapped_column(JSONB, default=dict)
    calendar: Mapped[str | None] = mapped_column(String(128))
    world_from: Mapped[Decimal | None] = mapped_column(Numeric(38, 12))
    world_to: Mapped[Decimal | None] = mapped_column(Numeric(38, 12))
    chapter_id: Mapped[str | None] = mapped_column(ForeignKey("ncc_entity.id"))
    recorded_from: Mapped[int] = mapped_column(BigInteger)
    recorded_to: Mapped[int | None] = mapped_column(BigInteger)
    supersedes: Mapped[str | None] = mapped_column(ForeignKey("ncc_fact.id"))
    secret: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[dict] = mapped_column(JSONB)
    change_id: Mapped[str] = mapped_column(String(36))
    __table_args__ = (
        CheckConstraint("world_to IS NULL OR world_from IS NULL OR world_to > world_from"),
        CheckConstraint("recorded_to IS NULL OR recorded_to > recorded_from"),
        Index("ix_fact_history", "scope_id", "recorded_from", "recorded_to"),
    )


class ChangeSet(Row, Base):
    __tablename__ = "ncc_change"
    scope_id: Mapped[str] = mapped_column(ForeignKey("ncc_scope.id"), index=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("ncc_user.id"))
    title: Mapped[str] = mapped_column(String(256))
    base_version: Mapped[int] = mapped_column(BigInteger)
    draft_version: Mapped[int] = mapped_column(Integer, default=1)
    operations: Mapped[list] = mapped_column(JSONB)
    state: Mapped[str] = mapped_column(String(32), default="draft")
    validation: Mapped[dict] = mapped_column(JSONB, default=dict)
    approved_hash: Mapped[str | None] = mapped_column(String(64))
    approver_id: Mapped[str | None] = mapped_column(ForeignKey("ncc_user.id"))
    applied_version: Mapped[int | None] = mapped_column(BigInteger)


class Receipt(Row, Base):
    __tablename__ = "ncc_receipt"
    scope_id: Mapped[str] = mapped_column(ForeignKey("ncc_scope.id"))
    actor_id: Mapped[str] = mapped_column(ForeignKey("ncc_user.id"))
    key: Mapped[str] = mapped_column(String(128))
    request_hash: Mapped[str] = mapped_column(String(64))
    result: Mapped[dict] = mapped_column(JSONB)
    __table_args__ = (UniqueConstraint("scope_id", "actor_id", "key"),)


class Audit(Row, Base):
    __tablename__ = "ncc_audit"
    scope_id: Mapped[str] = mapped_column(ForeignKey("ncc_scope.id"), index=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("ncc_user.id"))
    action: Mapped[str] = mapped_column(String(64))
    version: Mapped[int] = mapped_column(BigInteger)
    detail: Mapped[dict] = mapped_column(JSONB)


class Job(Row, Base):
    __tablename__ = "ncc_job"
    scope_id: Mapped[str] = mapped_column(ForeignKey("ncc_scope.id"), index=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("ncc_user.id"))
    kind: Mapped[str] = mapped_column(String(32))
    state: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    payload: Mapped[dict] = mapped_column(JSONB)
    result: Mapped[dict] = mapped_column(JSONB, default=dict)
    progress: Mapped[dict] = mapped_column(JSONB, default=dict)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    lease_token: Mapped[str | None] = mapped_column(String(36))
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Assessment(Row, Base):
    __tablename__ = "ncc_assessment"
    scope_id: Mapped[str] = mapped_column(ForeignKey("ncc_scope.id"), index=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("ncc_user.id"))
    entity_id: Mapped[str | None] = mapped_column(ForeignKey("ncc_entity.id"), index=True)
    content_hash: Mapped[str] = mapped_column(String(64))
    dependency_version: Mapped[int] = mapped_column(BigInteger)
    scheme: Mapped[str] = mapped_column(String(32))
    policy_hash: Mapped[str] = mapped_column(String(64))
    evaluator: Mapped[str] = mapped_column(String(128))
    report: Mapped[dict] = mapped_column(JSONB)
    score: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    verdict: Mapped[str] = mapped_column(String(32))


class Feedback(Row, Base):
    __tablename__ = "ncc_feedback"
    scope_id: Mapped[str] = mapped_column(ForeignKey("ncc_scope.id"), index=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("ncc_user.id"))
    assessment_id: Mapped[str] = mapped_column(ForeignKey("ncc_assessment.id"))
    choice: Mapped[str] = mapped_column(String(32))
    note: Mapped[str] = mapped_column(Text)


class Attachment(Row, Base):
    __tablename__ = "ncc_attachment"
    requires_secret: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    scope_id: Mapped[str] = mapped_column(ForeignKey("ncc_scope.id"), index=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("ncc_user.id"))
    name: Mapped[str] = mapped_column(String(256))
    media_type: Mapped[str] = mapped_column(String(128))
    digest: Mapped[str] = mapped_column(String(64))
    data: Mapped[bytes] = mapped_column(LargeBinary)
    purpose: Mapped[str] = mapped_column(String(32), default="source")


class ImportRun(Row, Base):
    __tablename__ = "ncc_import"
    scope_id: Mapped[str] = mapped_column(ForeignKey("ncc_scope.id"), index=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("ncc_user.id"))
    attachment_id: Mapped[str] = mapped_column(ForeignKey("ncc_attachment.id"))
    base_version: Mapped[int] = mapped_column(BigInteger)
    state: Mapped[str] = mapped_column(String(32), default="preview")
    mapping: Mapped[dict] = mapped_column(JSONB, default=dict)
    plan: Mapped[dict] = mapped_column(JSONB)


class Calibration(Row, Base):
    __tablename__ = "ncc_calibration"
    scope_id: Mapped[str] = mapped_column(ForeignKey("ncc_scope.id"), index=True)
    policy_hash: Mapped[str] = mapped_column(String(64))
    evaluator: Mapped[str] = mapped_column(String(128))
    scheme: Mapped[str] = mapped_column(String(32))
    report: Mapped[dict] = mapped_column(JSONB)
    active: Mapped[bool] = mapped_column(Boolean, default=False)


class Delegation(Row, Base):
    __tablename__ = "ncc_delegation"
    scope_id: Mapped[str] = mapped_column(ForeignKey("ncc_scope.id"), index=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("ncc_user.id"))
    target_ids: Mapped[list] = mapped_column(JSONB)
    schemes: Mapped[list] = mapped_column(JSONB)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    remaining: Mapped[int] = mapped_column(Integer)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    authorization: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
