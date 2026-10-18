"""CLI 参数注册：learning；不执行书项目读写。"""
from ..learning import cmd_craft, cmd_heat, cmd_pref, cmd_style
from ..materials import cmd_material
from ..memory import cmd_handoff, cmd_memory, cmd_recall
from ..settings import cmd_setting


def register_material(sub):
    p = sub.add_parser("material"); ms = p.add_subparsers(dest="action", required=True)
    q = ms.add_parser("add"); q.add_argument("book_dir"); q.add_argument("--content", required=True)
    q.add_argument("--source", required=True); q.add_argument("--use", required=True); q.add_argument("--trust")
    q.add_argument("--domain"); q.add_argument("--genre"); q.add_argument("--title"); q.add_argument("--shared", action="store_true")
    q = ms.add_parser("list"); q.add_argument("book_dir"); q.add_argument("--domain"); q.add_argument("--unused", action="store_true")
    q = ms.add_parser("check"); q.add_argument("book_dir")
    p.set_defaults(fn=cmd_material)


def register_style(sub):
    p = sub.add_parser("style"); p.add_argument("book_dir"); p.add_argument("--sample", nargs="+")
    p.add_argument("--from-chapters"); p.set_defaults(fn=cmd_style)


def register_heat(sub):
    p = sub.add_parser("heat"); p.add_argument("book_dir"); p.add_argument("--ch"); p.set_defaults(fn=cmd_heat)


def register_pref(sub):
    p = sub.add_parser("pref"); prs = p.add_subparsers(dest="action", required=True)
    q = prs.add_parser("show"); q.add_argument("path"); q.add_argument("--key")
    for act in ("like", "confirm", "reject"):
        q = prs.add_parser(act); q.add_argument("path"); q.add_argument("--key", required=True)
        q.add_argument("--value", required=True); q.add_argument("--note")
    q = prs.add_parser("dislike"); q.add_argument("path"); q.add_argument("--value", required=True); q.add_argument("--key")
    p.set_defaults(fn=cmd_pref)


def register_craft(sub):
    p = sub.add_parser("craft"); crs = p.add_subparsers(dest="action", required=True)
    q = crs.add_parser("init"); q.add_argument("book_dir")
    q = crs.add_parser("read"); q.add_argument("book_dir"); q.add_argument("--top", type=int, default=12)
    p.set_defaults(fn=cmd_craft)


def register_memory(sub):
    p = sub.add_parser("memory"); mms = p.add_subparsers(dest="action", required=True)
    q = mms.add_parser("add"); q.add_argument("book_dir"); q.add_argument("--role", required=True)
    q.add_argument("--kind", required=True); q.add_argument("--text", required=True)
    q.add_argument("--evidence", action="append"); q.add_argument("--ch", type=int)
    q = mms.add_parser("reinforce"); q.add_argument("book_dir"); q.add_argument("--role", required=True); q.add_argument("id")
    q.add_argument("--shared", action="store_true")
    q.add_argument("--evidence", action="append"); q.add_argument("--ch", type=int)
    q = mms.add_parser("merge"); q.add_argument("book_dir"); q.add_argument("--role", required=True)
    q.add_argument("--shared", action="store_true")
    q.add_argument("--into", required=True); q.add_argument("ids", nargs="+"); q.add_argument("--text")
    for act in ("archive", "restore"):
        q = mms.add_parser(act); q.add_argument("book_dir"); q.add_argument("--role", required=True); q.add_argument("id")
        q.add_argument("--note")
        q.add_argument("--shared", action="store_true")
    q = mms.add_parser("edit"); q.add_argument("book_dir"); q.add_argument("--role", required=True); q.add_argument("id")
    q.add_argument("--text", required=True); q.add_argument("--note"); q.add_argument("--shared", action="store_true")
    q = mms.add_parser("promote"); q.add_argument("book_dir"); q.add_argument("--role", required=True)
    q.add_argument("ids", nargs="*"); q.add_argument("--genre")
    q = mms.add_parser("list"); q.add_argument("book_dir"); q.add_argument("--role"); q.add_argument("--all", action="store_true")
    q.add_argument("--shared", action="store_true")
    q = mms.add_parser("consolidate"); q.add_argument("book_dir"); q.add_argument("--role"); q.add_argument("--apply", action="store_true")
    q.add_argument("--shared", action="store_true")
    p.set_defaults(fn=cmd_memory)


def register_handoff(sub):
    p = sub.add_parser("handoff"); hs = p.add_subparsers(dest="action", required=True)
    q = hs.add_parser("add"); q.add_argument("book_dir"); q.add_argument("--kind", required=True); q.add_argument("--text", required=True)
    q.add_argument("--layer"); q.add_argument("--ch")
    q = hs.add_parser("list"); q.add_argument("book_dir"); q.add_argument("--open", action="store_true"); q.add_argument("--role")
    q.add_argument("--ch", type=int)
    q = hs.add_parser("close"); q.add_argument("book_dir"); q.add_argument("id"); q.add_argument("--to", required=True); q.add_argument("--note")
    p.set_defaults(fn=cmd_handoff)


def register_recall(sub):
    p = sub.add_parser("recall"); p.add_argument("book_dir"); p.add_argument("words", nargs="+"); p.add_argument("--role")
    p.add_argument("--from", dest="from_ch", type=int); p.add_argument("--to", dest="to_ch", type=int)
    p.add_argument("--top", type=int, default=10); p.set_defaults(fn=cmd_recall)


def register_setting(sub):
    p = sub.add_parser("setting"); sts = p.add_subparsers(dest="action", required=True)
    for act in ("catalog", "list", "check"):
        q = sts.add_parser(act); q.add_argument("book_dir")
    q = sts.add_parser("use"); q.add_argument("book_dir"); q.add_argument("names", nargs="+"); q.add_argument("--why", required=True)
    q = sts.add_parser("new"); q.add_argument("book_dir"); q.add_argument("name"); q.add_argument("--required", required=True)
    q.add_argument("--optional"); q.add_argument("--alias"); q.add_argument("--why", required=True); q.add_argument("--gap", required=True)
    q = sts.add_parser("none"); q.add_argument("book_dir"); q.add_argument("--why", required=True)
    q = sts.add_parser("drop"); q.add_argument("book_dir"); q.add_argument("name")
    q = sts.add_parser("add"); q.add_argument("book_dir"); q.add_argument("cat"); q.add_argument("name")
    p.set_defaults(fn=cmd_setting)

REGISTRARS = {
    'material': register_material,
    'style': register_style,
    'heat': register_heat,
    'pref': register_pref,
    'craft': register_craft,
    'memory': register_memory,
    'handoff': register_handoff,
    'recall': register_recall,
    'setting': register_setting,
}
