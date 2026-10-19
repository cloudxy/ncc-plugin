"""Explicit private configuration. Importing the legacy CLI never imports this package."""

from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from ncc_shared.configuration import configuration
from ncc_shared.database import DatabasePair, configured_url
from ncc_shared.http import validate_origin
from ncc_shared.paths import project_root


@dataclass(frozen=True)
class Settings:
    database_url: str = field(repr=False)
    public_origin: str = "http://127.0.0.1:8787"
    secure_cookie: bool = False
    session_hours: int = 8
    upload_limit: int = 20 * 1024 * 1024
    web_dist: Path = project_root() / "apps/management-web/dist"
    model_url: str = ""
    model_key: str = field(default="", repr=False)
    api_token: str = field(default="", repr=False)
    mcp_token: str = field(default="", repr=False)
    writer_model: str = ""
    judge_model: str = ""
    second_judge_model: str = ""
    model_timeout: int = 120
    pg_bin: str = ""
    config_file: Path | None = None
    profile: str = "production"

    @classmethod
    def load(cls, path=None, profile="production", environ=None):
        values = configuration(path, environ)
        url = DatabasePair(configured_url(values)).select(profile)
        origin = validate_origin(
            values["NCC_TEST_PUBLIC_ORIGIN"] if profile == "test" else values["NCC_PUBLIC_ORIGIN"]
        )
        secure = urlsplit(origin).scheme == "https"
        return cls(
            database_url=url,
            public_origin=origin,
            secure_cookie=secure,
            session_hours=values["NCC_SESSION_HOURS"],
            upload_limit=values["NCC_UPLOAD_LIMIT"],
            model_timeout=values["NCC_MODEL_TIMEOUT"],
            web_dist=Path(values["NCC_WEB_DIST"])
            if Path(values["NCC_WEB_DIST"]).is_absolute()
            else project_root() / values["NCC_WEB_DIST"],
            model_url=values.get("NCC_MODEL_URL", "").rstrip("/"),
            model_key=values.get("NCC_MODEL_KEY", ""),
            api_token=values.get("NCC_API_TOKEN", ""),
            mcp_token=values.get("NCC_MCP_TOKEN", ""),
            writer_model=values.get("NCC_WRITER_MODEL", ""),
            judge_model=values.get("NCC_JUDGE_MODEL", ""),
            second_judge_model=values.get("NCC_SECOND_JUDGE_MODEL", ""),
            pg_bin=values.get("NCC_PG_BIN", ""),
            config_file=Path(path) if path else None,
            profile=profile,
        )

    @classmethod
    def from_env(cls):
        """Compatibility entry; project config/.env is the configuration source."""
        return cls.load()
