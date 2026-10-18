"""CLI 参数注册：delivery；不执行书项目读写。"""
from ..core import cmd_sha
from ..delivery import cmd_dashboard, cmd_export
from ..evolve import cmd_evolve
from ..views import cmd_check, cmd_render


def register_evolve(sub):
    p = sub.add_parser("evolve"); evs_ = p.add_subparsers(dest="action", required=True)
    q = evs_.add_parser("propose"); q.add_argument("path"); q.add_argument("--key", required=True); q.add_argument("--value", required=True)
    q.add_argument("--parent", help="新技法类别继承的内置父类（默认剧情规划）")
    q.add_argument("--why", required=True); q.add_argument("--evidence", action="append")
    for act in ("eval", "apply", "reject", "revert"):
        q = evs_.add_parser(act); q.add_argument("path"); q.add_argument("id"); q.add_argument("--quote"); q.add_argument("--note")
    q = evs_.add_parser("list"); q.add_argument("path"); q.add_argument("--open", action="store_true")
    q = evs_.add_parser("rules"); q.add_argument("path")
    q = evs_.add_parser("scan"); q.add_argument("path"); q.add_argument("--propose", action="store_true")
    p.set_defaults(fn=cmd_evolve)


def register_dashboard(sub):
    p = sub.add_parser("dashboard"); p.add_argument("book_root"); p.add_argument("--bucket", type=int, default=10)
    p.add_argument("--html"); p.set_defaults(fn=cmd_dashboard)


def register_export(sub):
    p = sub.add_parser("export"); p.add_argument("book_dir"); p.add_argument("--format", choices=["md", "txt", "epub"], default="md")
    p.add_argument("--from", dest="from_ch", type=int); p.add_argument("--to", dest="to_ch", type=int); p.add_argument("--author")
    p.set_defaults(fn=cmd_export)


def register_render(sub):
    p = sub.add_parser("render"); p.add_argument("book_dir"); p.set_defaults(fn=cmd_render)


def register_check(sub):
    p = sub.add_parser("check"); p.add_argument("book_dir"); p.set_defaults(fn=cmd_check)


def register_sha(sub):
    p = sub.add_parser("sha"); p.add_argument("file"); p.set_defaults(fn=cmd_sha)

REGISTRARS = {
    'evolve': register_evolve,
    'dashboard': register_dashboard,
    'export': register_export,
    'render': register_render,
    'check': register_check,
    'sha': register_sha,
}
