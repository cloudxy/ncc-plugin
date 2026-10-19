"""Lazy runtime selection: plain file commands keep using the standard library."""

import os
import sys
from pathlib import Path

from .paths import project_root


def ensure_data_runtime(script, argv):
    environment = project_root() / ".venv"
    python = environment / "bin/python"
    if python.is_file() and Path(sys.prefix).resolve() != environment.resolve():
        os.execv(str(python), [str(python), str(Path(script).resolve()), *argv])
