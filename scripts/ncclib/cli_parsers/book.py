"""CLI 参数注册：book；不执行书项目读写。"""
from ..book import cmd_chapter, cmd_complete, cmd_contract, cmd_gate, cmd_init, cmd_level, cmd_migrate, cmd_mode, cmd_next, cmd_sign, cmd_soul, cmd_status
from ..core import GATES


def register_init(sub):
    p = sub.add_parser("init"); p.add_argument("book_dir"); p.add_argument("--title", required=True)
    p.add_argument("--genre", default=""); p.add_argument("--chapters", type=int, default=300)
    p.add_argument("--level", default="新手"); p.add_argument("--mode", default="混合"); p.set_defaults(fn=cmd_init)


def register_status(sub):
    p = sub.add_parser("status")
    p.add_argument("book_dir")
    p.set_defaults(fn=cmd_status)


def register_next(sub):
    p = sub.add_parser("next")
    p.add_argument("book_dir")
    p.set_defaults(fn=cmd_next)


def register_migrate(sub):
    p = sub.add_parser("migrate")
    p.add_argument("book_dir")
    p.set_defaults(fn=cmd_migrate)


def register_gate(sub):
    p = sub.add_parser("gate"); p.add_argument("book_dir"); p.add_argument("name", choices=list(GATES))
    p.add_argument("--action", choices=["check", "pass", "reject"], default="check")
    p.add_argument("--quote", default=""); p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_gate)


def register_level(sub):
    p = sub.add_parser("level"); p.add_argument("book_dir"); p.add_argument("level"); p.set_defaults(fn=cmd_level)


def register_mode(sub):
    p = sub.add_parser("mode"); p.add_argument("book_dir"); p.add_argument("mode"); p.set_defaults(fn=cmd_mode)


def register_soul(sub):
    p = sub.add_parser("soul"); p.add_argument("book_dir")
    for k in ("question", "answer", "injustice", "ending", "status", "deadline", "arc"):
        p.add_argument(f"--{k}")
    p.set_defaults(fn=cmd_soul)


def register_contract(sub):
    p = sub.add_parser("contract"); p.add_argument("book_dir"); p.add_argument("--main")
    p.add_argument("--extra", action="append"); p.add_argument("--poison"); p.add_argument("--audience"); p.set_defaults(fn=cmd_contract)


def register_sign(sub):
    p = sub.add_parser("sign"); p.add_argument("book_dir"); p.add_argument("point")
    p.add_argument("--ch", type=int, required=True); p.set_defaults(fn=cmd_sign)


def register_chapter(sub):
    p = sub.add_parser("chapter"); cs = p.add_subparsers(dest="action", required=True)
    q = cs.add_parser("add"); q.add_argument("book_dir"); q.add_argument("seq", type=int)
    q.add_argument("--file", required=True); q.add_argument("--key", action="store_true")
    q.add_argument("--origin", choices=['ai', 'author', 'legacy'], default='legacy')
    q = cs.add_parser("key"); q.add_argument("book_dir"); q.add_argument("seq", type=int); q.add_argument("--off", action="store_true")
    q = cs.add_parser("hook"); q.add_argument("book_dir"); q.add_argument("seq", type=int)
    q.add_argument("--type", required=True); q.add_argument("--intensity", type=int, required=True); q.add_argument("--line")
    q = cs.add_parser("mark"); q.add_argument("book_dir"); q.add_argument("seq", type=int); q.add_argument("status")
    q = cs.add_parser("mood"); q.add_argument("book_dir"); q.add_argument("seq", type=int); q.add_argument("tension")
    q.add_argument("--colors")
    q = cs.add_parser("pick"); q.add_argument("book_dir"); q.add_argument("seq", type=int)
    q.add_argument("--version", required=True); q.add_argument("--note")
    q = cs.add_parser("end"); q.add_argument("book_dir"); q.add_argument("seq", type=int)
    q.add_argument("--time"); q.add_argument("--place"); q.add_argument("--next")
    q = cs.add_parser("length"); q.add_argument("book_dir"); q.add_argument("seq", type=int)
    q.add_argument("--accept", action="store_true"); q.add_argument("--compressed", action="store_true")
    q.add_argument("--force", action="store_true"); q.add_argument("--note"); q.add_argument("--tentative", action="store_true")
    q = cs.add_parser("retry"); q.add_argument("book_dir"); q.add_argument("seq", type=int)
    q = cs.add_parser("publish"); q.add_argument("book_dir"); q.add_argument("--upto", type=int, required=True)
    p.set_defaults(fn=cmd_chapter)


def register_complete(sub):
    p = sub.add_parser("complete"); p.add_argument("book_dir"); p.add_argument("seq", type=int)
    p.add_argument("--words", type=int, required=True); p.add_argument("--hard", choices=["pass", "fail"], required=True)
    p.add_argument("--decidable", type=float); p.add_argument("--report", default=""); p.set_defaults(fn=cmd_complete)

REGISTRARS = {
    'init': register_init,
    'status': register_status,
    'next': register_next,
    'migrate': register_migrate,
    'gate': register_gate,
    'level': register_level,
    'mode': register_mode,
    'soul': register_soul,
    'contract': register_contract,
    'sign': register_sign,
    'chapter': register_chapter,
    'complete': register_complete,
}
