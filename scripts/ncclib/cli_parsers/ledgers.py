"""CLI 参数注册：ledgers；不执行书项目读写。"""
from ..ledgers import cmd_event, cmd_fact, cmd_know, cmd_promise, cmd_reader_now, cmd_water


def register_water(sub):
    p = sub.add_parser("water"); p.add_argument("book_dir"); p.add_argument("seq", type=int); p.set_defaults(fn=cmd_water)


def register_promise(sub):
    p = sub.add_parser("promise"); ps = p.add_subparsers(dest="action", required=True)
    q = ps.add_parser("add"); q.add_argument("book_dir"); q.add_argument("--type", required=True)
    q.add_argument("--content", required=True); q.add_argument("--ch", type=int, required=True)
    q.add_argument("--strength", type=int, default=3); q.add_argument("--window"); q.add_argument("--deadline")
    q.add_argument("--desire")
    for act in ("touch", "resolve"):
        q = ps.add_parser(act); q.add_argument("book_dir"); q.add_argument("id")
        q.add_argument("--ch", type=int, required=True); q.add_argument("--note")
    q = ps.add_parser("reschedule"); q.add_argument("book_dir"); q.add_argument("id")
    q.add_argument("--window", required=True); q.add_argument("--note", required=True); q.add_argument("--ch", type=int)
    q = ps.add_parser("drop"); q.add_argument("book_dir"); q.add_argument("id")
    q.add_argument("--ch", type=int, required=True); q.add_argument("--compensation", required=True)
    q = ps.add_parser("list"); q.add_argument("book_dir"); q.add_argument("--open", action="store_true"); q.add_argument("--type")
    p.set_defaults(fn=cmd_promise)


def register_know(sub):
    p = sub.add_parser("know"); ks = p.add_subparsers(dest="action", required=True)
    q = ks.add_parser("add"); q.add_argument("book_dir"); q.add_argument("--fact", required=True)
    q.add_argument("--ch", type=int, required=True); q.add_argument("--known-by"); q.add_argument("--unknown-to")
    q = ks.add_parser("learn"); q.add_argument("book_dir"); q.add_argument("id")
    q.add_argument("--who", required=True); q.add_argument("--ch", type=int, required=True)
    q = ks.add_parser("list"); q.add_argument("book_dir"); q.add_argument("--who")
    p.set_defaults(fn=cmd_know)


def register_fact(sub):
    p = sub.add_parser("fact"); fs = p.add_subparsers(dest="action", required=True)
    q = fs.add_parser("set"); q.add_argument("book_dir"); q.add_argument("key"); q.add_argument("value")
    q.add_argument("--ch", type=int, required=True); q.add_argument("--source"); q.add_argument("--category")
    q.add_argument("--override", action="store_true")
    q = fs.add_parser("get"); q.add_argument("book_dir"); q.add_argument("key")
    q = fs.add_parser("list"); q.add_argument("book_dir"); q.add_argument("--category")
    p.set_defaults(fn=cmd_fact)


def register_event(sub):
    p = sub.add_parser("event"); evs = p.add_subparsers(dest="action", required=True)
    q = evs.add_parser("add"); q.add_argument("book_dir"); q.add_argument("--entity", required=True)
    q.add_argument("--ch", type=int, required=True); q.add_argument("--attr", required=True)
    q.add_argument("--old"); q.add_argument("--new"); q.add_argument("--reason"); q.add_argument("--evidence")
    q = evs.add_parser("list"); q.add_argument("book_dir"); q.add_argument("--entity")
    p.set_defaults(fn=cmd_event)


def register_reader_now(sub):
    p = sub.add_parser("reader-now"); p.add_argument("book_dir"); p.add_argument("seq", type=int)
    p.add_argument("--top", type=int, default=5); p.set_defaults(fn=cmd_reader_now)

REGISTRARS = {
    'water': register_water,
    'promise': register_promise,
    'know': register_know,
    'fact': register_fact,
    'event': register_event,
    'reader-now': register_reader_now,
}
