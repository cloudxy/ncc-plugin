import hashlib
import hmac
import secrets
from datetime import timedelta

from sqlalchemy import select

from .errors import DomainError, require
from .models import Membership, Scope, Session, User, utcnow
from .utils import digest

ALL_ACTIONS = frozenset({"read", "edit", "adopt", "assess", "export", "secret", "admin", "operate"})


def password_hash(password):
    require(len(password) >= 12, "weak_password", "密码至少12个字符")
    salt = secrets.token_bytes(16)
    key = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)
    return "scrypt$" + salt.hex() + "$" + key.hex()


def password_matches(password, encoded):
    try:
        algorithm, salt, expected = encoded.split("$")
        if algorithm != "scrypt":
            return False
        actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1, dklen=32)
        return hmac.compare_digest(actual.hex(), expected)
    except (ValueError, TypeError):
        return False


async def create_session(db, user, hours=8, kind="browser", scope_id=None, actions=None):
    token, csrf = secrets.token_urlsafe(40), secrets.token_urlsafe(32)
    row = Session(
        user_id=user.id,
        token_hash=digest(token),
        csrf_hash=digest(csrf),
        expires_at=utcnow() + timedelta(hours=hours),
        kind=kind,
        scope_id=scope_id,
        actions=actions,
    )
    db.add(row)
    await db.flush()
    return token, csrf


async def authenticate(db, token):
    require(bool(token), "authentication_required", "请登录", 401)
    row = await db.scalar(
        select(Session).where(Session.token_hash == digest(token), Session.revoked.is_(False))
    )
    require(row is not None and row.expires_at > utcnow(), "session_expired", "会话已失效，请重新登录", 401)
    user = await db.get(User, row.user_id)
    require(user is not None and user.active, "session_expired", "账号不可用", 401)
    if row.kind == "cli":
        user._access_scope, user._access_actions, user._credential_id = (
            row.scope_id,
            set(row.actions or []),
            row.id,
        )
    return user, row


async def permissions(db, user, scope_id):
    scope = await db.get(Scope, scope_id)
    if scope is None:
        raise DomainError("not_found", "范围不存在或不可访问", 404)
    row = (
        None
        if scope.owner_id == user.id
        else await db.scalar(
            select(Membership).where(Membership.scope_id == scope_id, Membership.user_id == user.id)
        )
    )
    actions = ALL_ACTIONS if scope.owner_id == user.id else frozenset(row.actions) if row else frozenset()
    if hasattr(user, "_access_scope"):
        actions = actions & user._access_actions if user._access_scope == scope_id else frozenset()
    if "read" not in actions:
        raise DomainError("not_found", "范围不存在或不可访问", 404)
    return scope, actions


async def authorize(db, user, scope_id, action="read", lock=False):
    scope, actions = await permissions(db, user, scope_id)
    require(action in actions, "forbidden", "当前范围未授予此操作", 403)
    if lock:
        scope = await db.scalar(
            select(Scope)
            .where(Scope.id == scope_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        # Recheck after waiting: another transaction may have revoked membership meanwhile.
        _, actions = await permissions(db, user, scope_id)
        require(action in actions, "forbidden", "权限已变化", 403)
    return scope, actions
