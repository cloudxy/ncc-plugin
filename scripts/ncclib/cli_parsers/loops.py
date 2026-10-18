"""CLI 参数注册：loops；不执行书项目读写。"""
from ..loops import cmd_feedback, cmd_finale, cmd_report, cmd_team, cmd_unit, cmd_volume


def register_unit(sub):
    p = sub.add_parser("unit"); us = p.add_subparsers(dest="action", required=True)
    q = us.add_parser("open"); q.add_argument("book_dir"); q.add_argument("--start", type=int, required=True); q.add_argument("--title")
    q = us.add_parser("close"); q.add_argument("book_dir"); q.add_argument("--end", type=int, required=True)
    q = us.add_parser("list"); q.add_argument("book_dir")
    p.set_defaults(fn=cmd_unit)


def register_volume(sub):
    p = sub.add_parser("volume"); vs = p.add_subparsers(dest="action", required=True)
    q = vs.add_parser("end"); q.add_argument("book_dir"); q.add_argument("--end", type=int, required=True)
    p.set_defaults(fn=cmd_volume)


def register_finale(sub):
    p = sub.add_parser("finale"); fns = p.add_subparsers(dest="action", required=True)
    q = fns.add_parser("begin"); q.add_argument("book_dir")
    p.set_defaults(fn=cmd_finale)


def register_report(sub):
    p = sub.add_parser("report"); p.add_argument("book_dir"); p.add_argument("kind", choices=["unit", "volume", "finale"])
    p.add_argument("--write", action="store_true")
    p.set_defaults(fn=cmd_report)


def register_feedback(sub):
    p = sub.add_parser("feedback"); fbs = p.add_subparsers(dest="action", required=True)
    q = fbs.add_parser("add"); q.add_argument("book_dir"); q.add_argument("--ch", type=int, required=True)
    q.add_argument("--source", required=True); q.add_argument("--kind", required=True); q.add_argument("--value", required=True)
    q.add_argument("--note"); q.add_argument("--persona")
    q = fbs.add_parser("list"); q.add_argument("book_dir"); q.add_argument("--ch", type=int)
    p.set_defaults(fn=cmd_feedback)


def register_team(sub):
    p = sub.add_parser("team"); ts = p.add_subparsers(dest="action", required=True)
    q = ts.add_parser("set"); q.add_argument("book_dir"); q.add_argument("position"); q.add_argument("name")
    q = ts.add_parser("list"); q.add_argument("book_dir")
    p.set_defaults(fn=cmd_team)

REGISTRARS = {
    'unit': register_unit,
    'volume': register_volume,
    'finale': register_finale,
    'report': register_report,
    'feedback': register_feedback,
    'team': register_team,
}
