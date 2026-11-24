"""ncc 状态与工作流核心领域库，按职责拆分子包；命令行入口在 scripts/cli/。"""
import sys
from pathlib import Path

_source = str(Path(__file__).resolve().parents[2] / "src")
if _source not in sys.path:
    sys.path.insert(0, _source)
