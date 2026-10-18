"""CLI 参数注册：deconstruction；不执行书项目读写。"""
from ..decon import cmd_decon
from ..techniques import cmd_technique


def register_decon(sub):
    p = sub.add_parser("decon"); dcs = p.add_subparsers(dest="action", required=True)
    q = dcs.add_parser("index"); q.add_argument("lib"); q.add_argument("--source"); q.add_argument("--force", action="store_true")
    q.add_argument("--config"); q.add_argument("--accept-reindex", action="store_true")
    q = dcs.add_parser("mark"); q.add_argument("lib"); q.add_argument("--done"); q.add_argument("--skip", type=int); q.add_argument("--why")
    q.add_argument("--layer", choices=["L2", "screenplay"])
    q = dcs.add_parser("coverage"); q.add_argument("lib")
    q.add_argument("--layer", choices=["L0", "L1", "L2", "L3", "screenplay", "legacy"])
    q = dcs.add_parser("stats"); q.add_argument("lib"); q.add_argument("--range"); q.add_argument("--write", action="store_true")
    q.add_argument("--layer", choices=["L1", "L2"])
    q = dcs.add_parser("link"); q.add_argument("book_dir"); q.add_argument("name")
    q = dcs.add_parser("plan"); q.add_argument("lib")
    q.add_argument("--goal", choices=["structure", "technique", "full", "transfer"])
    q.add_argument("--select"); q.add_argument("--reason"); q.add_argument("--screenplay")
    q = dcs.add_parser("packet"); q.add_argument("lib"); q.add_argument("seq", type=int, nargs="?")
    q.add_argument("--layer", choices=["L2", "L3"], default="L2"); q.add_argument("--context")
    q.add_argument("--independent", action="store_true"); q.add_argument("--framework")
    q = dcs.add_parser("ingest"); q.add_argument("lib"); q.add_argument("file", nargs="?")
    q.add_argument("--layer", choices=["L2", "L3"], default="L2"); q.add_argument("--recover", action="store_true")
    p.set_defaults(fn=cmd_decon)


def register_technique(sub):
    p = sub.add_parser("technique"); tcs = p.add_subparsers(dest="action", required=True)
    q = tcs.add_parser("add"); q.add_argument("path"); q.add_argument("--kind", required=True); q.add_argument("--method", required=True)
    q.add_argument("--how", required=True); q.add_argument("--evidence", action="append", required=True)
    q.add_argument("--applies", required=True); q.add_argument("--cost", required=True); q.add_argument("--confidence", required=True)
    q.add_argument("--source", required=True); q.add_argument("--data"); q.add_argument("--title")
    q = tcs.add_parser("check"); q.add_argument("path")
    q = tcs.add_parser("list"); q.add_argument("path"); q.add_argument("--kind")
    q = tcs.add_parser("match"); q.add_argument("path"); q.add_argument("--role", required=True); q.add_argument("--seq", type=int, nargs="*")
    q = tcs.add_parser("result"); q.add_argument("path"); q.add_argument("id"); q.add_argument("--outcome", choices=["good", "bad"], required=True)
    q.add_argument("--note"); q.add_argument("--ch", type=int); q.add_argument("--book")
    for act in ("retire", "restore"):
        q = tcs.add_parser(act); q.add_argument("path"); q.add_argument("id"); q.add_argument("--note")
    p.set_defaults(fn=cmd_technique)

REGISTRARS = {
    'decon': register_decon,
    'technique': register_technique,
}
