"""Stable production connection ``ncc-pro`` and its sole local/test sibling ``ncc-dev``."""

from dataclasses import dataclass, field
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit


class DatabaseNotConfigured(ValueError):
    """The initial project configuration does not contain a production connection yet."""


PRODUCTION_DATABASE = "ncc-pro"
TEST_DATABASE = "ncc-dev"


def postgres_url(value):
    value = (
        value.replace("postgresql://", "postgresql+psycopg://", 1)
        if value.startswith("postgresql://")
        else value
    )
    if not value.startswith("postgresql+psycopg://"):
        raise ValueError("数据库只支持PostgreSQL/Psycopg连接；请检查config/.env")
    parsed = urlsplit(value)
    if any(
        key.lower() in {"dbname", "database"} for key, _ in parse_qsl(parsed.query, keep_blank_values=True)
    ):
        raise ValueError("连接串查询参数不得再次指定数据库名，避免覆盖ncc-dev")
    if parsed.fragment or not parsed.path.strip("/"):
        raise ValueError("PostgreSQL连接须包含数据库名且不得带片段")
    try:
        _ = parsed.port
    except ValueError:
        raise ValueError("PostgreSQL端口格式无效") from None
    return value


def configured_url(values):
    raw = values.get("NCC_DATABASE_URL", "").strip()
    fields = {k: values.get("NCC_DB_" + k, "") for k in ("HOST", "PORT", "NAME", "USER", "PASSWORD")}
    if raw:
        if any(fields.values()):
            raise ValueError("连接串与分项数据库配置只能选择一套，避免两个事实源")
        postgres_url(raw)
        return raw
    if not all(fields[k] for k in ("HOST", "NAME", "USER")):
        raise DatabaseNotConfigured("请在config/.env填写既定PostgreSQL连接；不会猜测、修改或创建正式库")
    credentials = quote(fields["USER"], safe="") + ":" + quote(fields["PASSWORD"], safe="") + "@"
    port = fields["PORT"] or "5432"
    if fields["HOST"].startswith("/"):
        netloc, query = credentials, urlencode({"host": fields["HOST"], "port": port})
    else:
        host = fields["HOST"]
        host = "[" + host + "]" if ":" in host and not host.startswith("[") else host
        netloc, query = credentials + host + ":" + port, ""
    return postgres_url(
        urlunsplit(("postgresql+psycopg", netloc, "/" + quote(fields["NAME"], safe=""), query, ""))
    )


@dataclass(frozen=True)
class DatabasePair:
    production_url: str = field(repr=False)

    def __post_init__(self):
        postgres_url(self.production_url)
        if self.production_name != PRODUCTION_DATABASE:
            raise ValueError("线上数据库名必须是ncc-pro；本地与测试数据只进入ncc-dev")
        if len(self.test_name.encode("utf-8")) > 63:
            raise ValueError("测试库名超过PostgreSQL标识符长度；原配置保持原状")

    @property
    def production_name(self):
        from urllib.parse import unquote

        return unquote(urlsplit(self.production_url).path[1:])

    @property
    def test_name(self):
        return TEST_DATABASE

    @property
    def test_url(self):
        parsed = urlsplit(self.production_url)
        return urlunsplit(parsed._replace(path="/" + quote(self.test_name, safe="")))

    def select(self, profile="local"):
        if profile not in {"local", "production", "test"}:
            raise ValueError("数据库profile只支持local、production或test")
        return self.production_url if profile == "production" else self.test_url

    def require_test(self, url):
        if postgres_url(url) != postgres_url(self.test_url):
            raise ValueError("测试只允许同连接的ncc-dev；ncc-pro及其他连接均拒绝重置")
        return url
