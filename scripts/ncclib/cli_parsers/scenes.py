"""CLI 参数注册：scenes；不执行书项目读写。"""
from ..scenes import cmd_brief, cmd_era, cmd_knowledge, cmd_pack, cmd_review, cmd_scene, cmd_study, cmd_words


def register_scene(sub):
    p = sub.add_parser("scene"); ss = p.add_subparsers(dest="action", required=True)
    q = ss.add_parser("next"); q.add_argument("book_dir")
    q = ss.add_parser("check"); q.add_argument("book_dir"); q.add_argument("seq", type=int, nargs="+")
    q = ss.add_parser("review"); q.add_argument("book_dir"); q.add_argument("seq", type=int, nargs="+")
    q.add_argument("--result", choices=["pass", "revise"], required=True); q.add_argument("--by", required=True)
    q.add_argument("--note")
    p.set_defaults(fn=cmd_scene)


def register_knowledge(sub):
    p = sub.add_parser("knowledge"); kns = p.add_subparsers(dest="action", required=True)
    q = kns.add_parser("plan"); q.add_argument("book_dir"); q.add_argument("seq", type=int, nargs="+")
    q = kns.add_parser("check"); q.add_argument("book_dir"); q.add_argument("seq", type=int, nargs="+")
    p.set_defaults(fn=cmd_knowledge)


def register_era(sub):
    p = sub.add_parser("era"); p.add_argument("book_dir"); p.add_argument("era"); p.set_defaults(fn=cmd_era)


def register_study(sub):
    p = sub.add_parser("study"); p.add_argument("book_dir"); p.add_argument("--add"); p.set_defaults(fn=cmd_study)


def register_brief(sub):
    p = sub.add_parser("brief"); p.add_argument("book_dir"); p.add_argument("--role", required=True)
    p.add_argument("--seq", type=int, nargs="*"); p.add_argument("--task"); p.add_argument("--persona"); p.add_argument("--note")
    p.set_defaults(fn=cmd_brief)


def register_pack(sub):
    p = sub.add_parser("pack"); p.add_argument("book_dir"); p.add_argument("seq", type=int); p.add_argument("--note")
    p.set_defaults(fn=cmd_pack)


def register_review(sub):
    p = sub.add_parser("review"); rs = p.add_subparsers(dest="action", required=True)
    q = rs.add_parser("plan"); q.add_argument("book_dir"); q.add_argument("seq", type=int)
    q = rs.add_parser("delta"); q.add_argument("book_dir"); q.add_argument("seq", type=int)
    p.set_defaults(fn=cmd_review)


def register_words(sub):
    p = sub.add_parser("words"); p.add_argument("book_dir"); p.add_argument("seq", type=int); p.add_argument("--file")
    p.set_defaults(fn=cmd_words)

REGISTRARS = {
    'scene': register_scene,
    'knowledge': register_knowledge,
    'era': register_era,
    'study': register_study,
    'brief': register_brief,
    'pack': register_pack,
    'review': register_review,
    'words': register_words,
}
