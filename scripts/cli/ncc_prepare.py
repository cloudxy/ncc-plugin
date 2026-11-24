#!/usr/bin/env python3
"""ncc_prepare.py：创作前准备与素材库治理命令入口（实现位于 scripts/ncclib/preparation/）。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ncclib.preparation.workspace import *  # noqa: E402,F401,F403
from ncclib.preparation.workspace import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
