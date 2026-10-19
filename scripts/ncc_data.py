#!/usr/bin/env python3
"""Optional data service entry; the original CLI continues to use the standard library."""
import os
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
python = root / '.venv/bin/python'
if python.is_file() and Path(sys.executable).resolve() != python.resolve():
    os.execv(str(python), [str(python), '-m', 'ncc_data.cli', *sys.argv[1:]])
try:
    from ncc_data.cli.main import main
except ImportError:
    raise SystemExit('数据服务尚未安装。请在插件根目录运行 uv sync --python python3.12 --extra dev；文件模式无需安装。') from None
main()
