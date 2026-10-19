"""Explicit private configuration. Importing the legacy CLI never imports this package."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_url: str
    public_origin: str = "http://127.0.0.1:8787"
    secure_cookie: bool = False
    session_hours: int = 8
    upload_limit: int = 20 * 1024 * 1024
    web_dist: Path = Path(__file__).resolve().parents[2] / "apps/management-web/dist"
    model_url: str = ""
    model_key: str = ""
    writer_model: str = ""
    judge_model: str = ""
    second_judge_model: str = ""
    model_timeout: int = 120

    @classmethod
    def from_env(cls):
        url = os.environ.get("NCC_DATABASE_URL", "")
        if not url:
            raise ValueError("请配置私有 NCC_DATABASE_URL；服务不会自动连接或创建数据库")
        origin = os.environ.get("NCC_PUBLIC_ORIGIN", "http://127.0.0.1:8787").rstrip("/")
        secure = origin.startswith("https://")
        if not secure and origin.split("://", 1)[-1].split(":")[0] not in {"localhost", "127.0.0.1", "[::1]"}:
            raise ValueError("非本机部署必须配置HTTPS的NCC_PUBLIC_ORIGIN")
        return cls(
            database_url=url,
            public_origin=origin,
            secure_cookie=secure,
            web_dist=Path(os.environ.get("NCC_WEB_DIST", str(cls.web_dist))),
            model_url=os.environ.get("NCC_MODEL_URL", "").rstrip("/"),
            model_key=os.environ.get("NCC_MODEL_KEY", ""),
            writer_model=os.environ.get("NCC_WRITER_MODEL", ""),
            judge_model=os.environ.get("NCC_JUDGE_MODEL", ""),
            second_judge_model=os.environ.get("NCC_SECOND_JUDGE_MODEL", ""),
        )
