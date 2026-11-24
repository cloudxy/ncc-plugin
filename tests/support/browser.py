"""Make repository source and test support importable for direct script execution."""

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for entry in (ROOT / "src", ROOT / "tests"):
    sys.path.insert(0, str(entry))

browser_test = importlib.import_module("support.runtime").browser_test
