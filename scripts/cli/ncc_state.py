#!/usr/bin/env python3
"""ncc_state.py：书项目状态的命令入口。实现按领域分在 scripts/ncclib/ 各子包中。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ncclib.assets.evolve import *  # noqa: E402,F401,F403
from ncclib.assets.learning import *  # noqa: E402,F401,F403
from ncclib.assets.materials import *  # noqa: E402,F401,F403
from ncclib.assets.memory import *  # noqa: E402,F401,F403
from ncclib.assets.settings import *  # noqa: E402,F401,F403
from ncclib.cli.dispatch import READ_ONLY, main  # noqa: E402,F401
from ncclib.deconstruction.facade import *  # noqa: E402,F401,F403
from ncclib.deconstruction.techniques import *  # noqa: E402,F401,F403
from ncclib.foundation.core import *  # noqa: E402,F401,F403
from ncclib.narrative.book import *  # noqa: E402,F401,F403
from ncclib.narrative.delivery import *  # noqa: E402,F401,F403
from ncclib.narrative.ledgers import *  # noqa: E402,F401,F403
from ncclib.narrative.loops import *  # noqa: E402,F401,F403
from ncclib.narrative.scenes import *  # noqa: E402,F401,F403
from ncclib.narrative.views import *  # noqa: E402,F401,F403

if __name__ == "__main__":
    main()
