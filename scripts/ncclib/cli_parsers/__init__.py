"""按领域提供命令注册器；顺序由显式契约固定。"""
from . import book, loops, ledgers, scenes, learning, deconstruction, delivery, quality

COMMAND_ORDER = ('init', 'status', 'next', 'migrate', 'gate', 'level', 'mode', 'soul', 'contract', 'sign', 'scene', 'chapter', 'unit', 'volume', 'finale', 'report', 'feedback', 'team', 'complete', 'water', 'promise', 'know', 'fact', 'knowledge', 'era', 'study', 'material', 'style', 'heat', 'pref', 'craft', 'memory', 'handoff', 'recall', 'brief', 'setting', 'decon', 'technique', 'evolve', 'dashboard', 'export', 'pack', 'review', 'words', 'render', 'check', 'event', 'reader-now', 'sha')

COMMAND_ORDER = COMMAND_ORDER + ('quality',)
REGISTRARS = {}
for _domain in (book, loops, ledgers, scenes, learning, deconstruction, delivery, quality):
    for _name, _register in _domain.REGISTRARS.items():
        if _name in REGISTRARS:
            raise ValueError(f"重复 CLI 命令：{_name}")
        REGISTRARS[_name] = _register
if set(COMMAND_ORDER) != set(REGISTRARS):
    raise ValueError("CLI 顺序表与注册器不一致")
