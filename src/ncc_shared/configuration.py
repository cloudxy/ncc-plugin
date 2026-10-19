"""One project .env reader. No process-environment mutation or shell execution."""

import ast
import json
import os
import re
from importlib.resources import files
from pathlib import Path

from .paths import config_path, project_root


def template():
    path = project_root() / ".env.example"
    if not path.is_file():
        path = files("ncc_shared").joinpath("resources/dotenv.example")
    return read_dotenv(path)


def read_dotenv(path):
    path = Path(path)
    if not path.exists():
        return {}
    values = {}
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.fullmatch(r"(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)", line)
        if not match:
            raise ValueError(f"{path.name}第{number}行不是 KEY=VALUE 配置")
        key, value = match.groups()
        if key in values:
            raise ValueError(f"{path.name}第{number}行重复定义{key}")
        if value.startswith(("'", '"')):
            try:
                value = ast.literal_eval(value)
                if not isinstance(value, str):
                    raise ValueError()
            except (SyntaxError, ValueError):
                raise ValueError(f"{path.name}第{number}行引号不完整；敏感值不会输出") from None
        else:
            value = re.split(r"\s+#", value, maxsplit=1)[0].rstrip()
        values[key] = value
    return values


def configuration(path=None, environ=None):
    # Existing automation stays compatible; the project's explicit file has priority.
    fallback = dict(os.environ if environ is None else environ)
    explicit = path or fallback.get("NCC_CONFIG_FILE")
    if explicit and not Path(explicit).is_file():
        raise ValueError("明确指定的配置文件不存在，拒绝回退其他连接")
    supplied = read_dotenv(explicit or config_path())
    if any(k == "NCC_DATABASE_URL" or k.startswith("NCC_DB_") for k in supplied):
        fallback = {
            k: v for k, v in fallback.items() if k != "NCC_DATABASE_URL" and not k.startswith("NCC_DB_")
        }
    return {**fallback, **supplied}


def initialize(path=None, source=None, values=None):
    path = Path(path or config_path())
    if path.exists():
        return False
    content = dict(values or {})
    if source:
        if not Path(source).is_file():
            raise ValueError("导入的既有配置文件不存在，未初始化")
        content.update({k: v for k, v in read_dotenv(source).items() if k.startswith("NCC_")})
    lines = ["# NCC 项目初始化配置；后续命令自动读取，不必export。\n"]
    for key, value in content.items():
        if not re.fullmatch(r"NCC_[A-Z0-9_]+", key):
            raise ValueError("配置键必须使用NCC_前缀")
        lines.append(key + "=" + json.dumps(str(value), ensure_ascii=False) + "\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write("".join(lines))
    return True
