"""One authenticated stdlib HTTP client for all command-line consumers."""

import json
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .configuration import configuration


def validate_origin(origin):
    origin = origin.rstrip("/")
    parsed = urlsplit(origin)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("API地址必须是完整HTTP(S)源地址，不得携带凭据或路径")
    if parsed.scheme != "https" and parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("远端API必须使用HTTPS")
    return origin


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class APIClient:
    def __init__(self, values=None, timeout=120, profile=None):
        values = configuration() if values is None else values
        self.origin = validate_origin(
            values.get("NCC_API_URL") or values.get("NCC_PUBLIC_ORIGIN") or "http://127.0.0.1:8787"
        )
        self.token = values.get("NCC_API_TOKEN", "")
        if not self.token:
            raise ValueError("请将本范围凭据填入项目.env的NCC_API_TOKEN")
        if any(not 33 <= ord(character) <= 126 for character in self.token):
            raise ValueError("范围凭据格式无效，请重新复制；凭据内容不会输出")
        self.timeout = timeout
        self.opener = build_opener(NoRedirect)
        self.profile = profile or values.get("NCC_API_PROFILE", "production")
        if self.profile not in {"production", "test"}:
            raise ValueError("API profile必须是production或test")
        self._profile_checked = False

    def check_profile(self):
        if self._profile_checked:
            return
        # No token is sent to a wrong/old service before its profile is identified.
        request = Request(self.origin + "/health/live")
        with self.opener.open(request, timeout=self.timeout) as response:
            status = json.load(response)
        if status.get("profile") != self.profile:
            raise ValueError("API服务的正式/测试模式与所选配置不一致，未发送操作或范围凭据")
        self._profile_checked = True

    def request(self, method, path, body=None):
        if not path.startswith("/") or path.startswith("//") or ".." in path.split("/"):
            raise ValueError("API路径无效")
        self.check_profile()
        data = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
        request = Request(
            self.origin + "/api/v1" + path,
            data=data,
            method=method,
            headers={
                "Authorization": "Bearer " + self.token,
                "Content-Type": "application/json",
                "X-NCC-Profile": self.profile,
            },
        )
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                return json.load(response)
        except HTTPError as exc:
            try:
                detail = json.load(exc).get("detail", "API请求失败")
            except (ValueError, AttributeError):
                detail = "API请求失败"
            raise ValueError(str(detail)) from None


def http_request(method, path, body=None):
    return APIClient().request(method, path, body)
