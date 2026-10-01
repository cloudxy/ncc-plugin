#!/usr/bin/env python3
"""ncc_state.py：书项目状态的命令入口。实现按领域分在 ncclib/ 里，命令说明见 --help（ncclib/cli.py）。

其他脚本（check_chapter.py、ncc_eval.py、自测）从这里 import 的名字保持不变。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ncclib.core import *  # noqa: E402,F401,F403
from ncclib.ledgers import *  # noqa: E402,F401,F403
from ncclib.materials import *  # noqa: E402,F401,F403
from ncclib.scenes import *  # noqa: E402,F401,F403
from ncclib.learning import *  # noqa: E402,F401,F403
from ncclib.views import *  # noqa: E402,F401,F403
from ncclib.loops import *  # noqa: E402,F401,F403
from ncclib.delivery import *  # noqa: E402,F401,F403
from ncclib.book import *  # noqa: E402,F401,F403
from ncclib.cli import main, READ_ONLY  # noqa: E402,F401

if __name__ == "__main__":
    main()
