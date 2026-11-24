#!/usr/bin/env python3
"""check_chapter.py：章节机械检查命令入口（实现位于 scripts/ncclib/quality/chapter_check.py）。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ncclib.quality.chapter_check import *  # noqa: E402,F401,F403
from ncclib.quality.chapter_check import main  # noqa: E402

if __name__ == "__main__":
    main()
