"""Pytest source and support discovery; no configuration or database is loaded here."""

import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
for entry in (root / "src", root / "tests"):
    sys.path.insert(0, str(entry))
