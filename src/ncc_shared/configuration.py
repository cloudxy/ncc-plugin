"""Single Dynaconf configuration service shared by all database-facing entries."""

import json
import os
import re
from importlib.resources import files
from pathlib import Path

from .paths import config_directory, config_path, legacy_config_path, project_root


def template():
    path = config_directory(project_root()) / ".env.example"
    if not path.is_file():
        path = files("ncc_shared").joinpath("resources/dotenv.example")
    return read_dotenv(path)


def read_dotenv(path):
    """Strict parsing through python-dotenv; no interpolation or shell execution."""
    import ast

    from dotenv.parser import parse_stream

    path = Path(path)
    if not path.exists():
        return {}
    result = {}
    with path.open(encoding="utf-8-sig") as stream:
        for binding in parse_stream(stream):
            if binding.error or binding.key is not None and binding.value is None:
                raise ValueError(f"{path.name}第{binding.original.line}行配置语法无效；敏感值不会输出")
            if binding.key is None:
                continue
            if binding.key in result:
                raise ValueError(f"{path.name}第{binding.original.line}行重复定义{binding.key}")
            value = binding.value
            # Earlier releases accepted Python/JSON-quoted values. Preserve their
            # Unicode/control escapes while python-dotenv owns the file grammar.
            original_value = binding.original.string.split("=", 1)[1].strip()
            if original_value.startswith(('"', "'")):
                try:
                    decoded = ast.literal_eval(original_value)
                    if isinstance(decoded, str):
                        value = decoded
                except (ValueError, SyntaxError):
                    pass
            result[binding.key] = value
    return result


def load_settings(path=None, environ=None):
    """Dynaconf owns defaults, environment overlays, merges and validation.

    Explicit dotenv parsing avoids mutating process globals in API/test workers.
    Its data is merged by Dynaconf last, preserving the author's file precedence.
    """
    from dynaconf import Dynaconf, ValidationError, Validator

    fallback = dict(os.environ if environ is None else environ)
    explicit = path or fallback.get("NCC_CONFIG_FILE")
    selected = Path(explicit or config_path())
    if selected.resolve() == config_path().resolve() and (
        legacy_config_path().exists() or legacy_config_path().is_symlink()
    ):
        if selected.exists() or selected.is_symlink():
            raise ValueError("config/.env与旧根.env同时存在，请核对并仅保留config/.env；不会自动合并")
        raise ValueError("配置已统一到config/.env，请执行ncc-data init迁移旧根.env；原值不会改变")
    if explicit and not selected.is_file():
        raise ValueError("明确指定的配置文件不存在，拒绝回退其他连接")
    supplied = read_dotenv(selected)
    environment = supplied.get("NCC_ENV", fallback.get("NCC_ENV", "local"))
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,32}", environment):
        raise ValueError("NCC_ENV只能是环境名，不能包含路径")
    defaults = config_directory(project_root()) / "default/settings.toml"
    if not defaults.is_file():
        defaults = files("ncc_shared").joinpath("resources/settings.toml")

    def new_manager(settings_files):
        return Dynaconf(
            envvar_prefix="NCC",
            root_path=str(project_root()),
            settings_files=[str(value) for value in settings_files],
            environments=False,
            load_dotenv=False,
            loaders=[],
            merge_enabled=True,
            auto_cast=False,
        )

    manager = new_manager([defaults])

    def overlay(values, source):
        values = {k[4:]: v for k, v in values.items() if k.startswith("NCC_") and k != "NCC_CONFIG_FILE"}
        # A layer chooses either a URL or fields; stale lower-layer credentials cannot mix.
        if any(k == "DATABASE_URL" or k.startswith("DB_") for k in values):
            for key in ("DATABASE_URL", "DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"):
                manager.set(key, "", loader_identifier=source)
        manager.update(values, loader_identifier=source, tomlfy=False)

    overlay(fallback, "legacy_process_fallback")
    environment_file = config_directory(project_root()) / environment / "settings.toml"
    if environment_file.is_file():
        layer = new_manager([environment_file])
        overlay({"NCC_" + key: value for key, value in layer.as_dict().items()}, "environment_file")
    overlay(supplied, "project_dotenv")
    manager.validators.register(
        Validator("PUBLIC_ORIGIN", "TEST_PUBLIC_ORIGIN", is_type_of=str),
        Validator("SESSION_HOURS", cast=int, gte=1, lte=168),
        Validator("UPLOAD_LIMIT", cast=int, gte=1024, lte=100 * 1024 * 1024),
        Validator("MODEL_TIMEOUT", cast=int, gte=1, lte=3600),
        Validator("API_PROFILE", is_in=["production", "test"]),
    )
    try:
        manager.validators.validate()
    except (ValidationError, ValueError, TypeError):
        raise ValueError("项目配置类型或范围无效，请检查config目录；敏感值不会输出") from None
    return manager


def configuration(path=None, environ=None):
    return {"NCC_" + key: value for key, value in load_settings(path, environ).as_dict().items()}


def _move_no_replace(source, target):
    """One filesystem operation; never fall back to a clobbering rename or unlink."""
    import ctypes
    import sys

    library = ctypes.CDLL(None, use_errno=True)
    try:
        if sys.platform == "darwin":
            operation = library.renamex_np
            operation.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
            arguments = [os.fsencode(source), os.fsencode(target), 0x00000004]  # RENAME_EXCL
        elif sys.platform.startswith("linux"):
            operation = library.renameat2
            operation.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
            arguments = [-100, os.fsencode(source), -100, os.fsencode(target), 1]  # RENAME_NOREPLACE
        else:
            raise ValueError("当前平台不支持安全自动迁移，请手动将唯一私有配置移入config目录")
    except AttributeError:
        raise ValueError("当前系统不支持排他原子迁移，配置未移动，请手动迁移") from None
    operation.restype = ctypes.c_int
    if operation(*arguments) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), str(source))


def _migrate_legacy(path):
    old = legacy_config_path()
    if not old.exists() and not old.is_symlink():
        return False
    if path.exists() or path.is_symlink():
        raise ValueError("config/.env与旧根.env同时存在，请核对并仅保留config/.env；不会覆盖或合并")
    if old.is_symlink() or not old.is_file() or path.parent.is_symlink():
        raise ValueError("旧配置迁移需要普通文件和config目录，原文件保留")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(old, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        original = os.fstat(descriptor)
        _move_no_replace(old, path)
        current = path.lstat()
        if (
            (current.st_dev, current.st_ino) != (original.st_dev, original.st_ino)
            or old.exists()
            or old.is_symlink()
        ):
            raise ValueError("迁移期间配置发生变化；当前文件已保留，请核对新旧位置，不会删除并发修改")
        os.fchmod(descriptor, 0o600)
    finally:
        os.close(descriptor)
    return True


def initialize(path=None, source=None, values=None):
    path = Path(path or config_path())
    if path.resolve() == config_path().resolve() and _migrate_legacy(path):
        return True
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
