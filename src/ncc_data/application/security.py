import hashlib
import hmac
import secrets
from datetime import timedelta

from sqlalchemy import select

from ncc_data.persistence.models import Membership, Scope, Session, User, utcnow
from ncc_shared.errors import DomainError, require
from ncc_shared.http import extract_hostname, is_loopback_host
from ncc_shared.serialization import digest

ALL_ACTIONS = frozenset({"read", "edit", "adopt", "assess", "export", "secret", "admin", "operate"})
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "123456"
LOOPBACK_REMINDER = "首次使用默认管理员账号（admin），请及时修改账号名和密码。"
ENFORCED_REMINDER = "当前通过真实地址访问且正在使用默认管理员账号（admin），第一次使用时必须先修改账号名和密码。"


def _scrypt_encode(password: str) -> str:
    salt = secrets.token_bytes(16)
    key = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)
    return "scrypt$" + salt.hex() + "$" + key.hex()


def password_hash(password):
    require(len(password) >= 12, "weak_password", "密码至少12个字符")
    return _scrypt_encode(password)


def default_bootstrap_password_hash() -> str:
    return _scrypt_encode(DEFAULT_ADMIN_PASSWORD)


async def ensure_default_admin(db) -> bool:
    if await db.scalar(select(User.id).limit(1)) is not None:
        return False
    db.add(
        User(
            username=DEFAULT_ADMIN_USERNAME,
            password_hash=default_bootstrap_password_hash(),
            admin=True,
            active=True,
            must_change_credentials=True,
        )
    )
    await db.flush()
    return True


def credential_change_policy(
    request,
    settings,
    user,
    bind_host: str | None = None,
) -> tuple[bool, bool, str]:
    must_change = bool(getattr(user, "must_change_credentials", False))
    if not must_change:
        return False, False, ""

    enforced = False
    if bind_host is not None and str(bind_host).strip():
        if not is_loopback_host(str(bind_host)):
            enforced = True

    origin_raw = getattr(settings, "public_origin", "") if settings is not None else ""
    origin_host = extract_hostname(origin_raw)
    if origin_host and origin_host != "testserver" and not is_loopback_host(origin_host):
        enforced = True

    if request is not None:
        headers = getattr(request, "headers", None)
        raw_req_host = headers.get("host", "") if headers is not None else ""
        if not raw_req_host:
            req_url = getattr(request, "url", None)
            raw_req_host = getattr(req_url, "hostname", "") or ""
        req_host = extract_hostname(raw_req_host)
        if req_host and req_host != "testserver" and not is_loopback_host(req_host):
            enforced = True

    uname = str(getattr(user, "username", "") or "").strip()
    if not uname or uname.lower() == DEFAULT_ADMIN_USERNAME:
        reminder = ENFORCED_REMINDER if enforced else LOOPBACK_REMINDER
    elif enforced:
        reminder = (
            f"当前监听或访问非回环地址，账号（{uname}）使用的是初始或已重置临时密码，请先修改密码后再继续使用。"
        )
    else:
        reminder = f"当前账号（{uname}）使用的是初始或已重置临时密码，请及时修改密码。"
    return True, enforced, reminder


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
