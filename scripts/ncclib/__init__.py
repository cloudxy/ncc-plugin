"""ncc 状态脚本的实现，按领域分模块；入口是 scripts/ncc_state.py。"""
from pathlib import Path
import sys

_source = str(Path(__file__).resolve().parents[2] / "src")
if _source not in sys.path:
    sys.path.insert(0, _source)
