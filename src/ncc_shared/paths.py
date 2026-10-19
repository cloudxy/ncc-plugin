"""Project paths shared by stdlib commands, the service and packaged migrations."""

from pathlib import Path


def project_root():
    source = Path(__file__).resolve().parents[2]
    return source if (source / "plugin.json").is_file() else Path.cwd().resolve()


def config_path():
    return project_root() / ".env"
