#!/usr/bin/env python3
"""Optional data service entry; the original CLI continues to use the standard library."""
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "src"))
from ncc_shared.runtime import ensure_data_runtime  # noqa: E402

ensure_data_runtime(__file__, sys.argv[1:])
try:
    from ncc_data.cli.main import main
except ImportError:
    raise SystemExit('数据服务尚未安装。请在插件根目录运行 uv sync --python python3.12 --extra dev；文件模式无需安装。') from None
main()
