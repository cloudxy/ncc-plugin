"""Project paths shared by stdlib commands, the service and packaged migrations."""

from pathlib import Path


def project_root():
    source = Path(__file__).resolve().parents[2]
    return source if (source / "plugin.json").is_file() else Path.cwd().resolve()


def config_directory(root=None):
    return Path(root or project_root()) / "config"


def config_path(root=None):
    return config_directory(root) / ".env"


def legacy_config_path(root=None):
    return Path(root or project_root()) / ".env"
