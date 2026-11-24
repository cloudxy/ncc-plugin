#!/usr/bin/env python3
"""ncc_eval.py：审稿判据回归评测与模型横评命令入口（实现位于 scripts/ncclib/evaluation/benchmark.py）。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ncclib.evaluation.benchmark import *  # noqa: E402,F401,F403
from ncclib.evaluation.benchmark import main  # noqa: E402

if __name__ == "__main__":
    main()
