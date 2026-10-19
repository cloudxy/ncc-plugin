from ..quality import cmd_quality


def register_quality(sub):
    parser = sub.add_parser('quality', help='AI成果评分、证据与新鲜度；文件模式仅需标准库')
    parser.add_argument('action', choices=['plan', 'ingest', 'status', 'accept'])
    parser.add_argument('book_dir')
    parser.add_argument('seq', nargs='?', type=int)
    parser.add_argument('--file')
    parser.add_argument('--scheme', choices=['P1', 'P2', 'P3', 'P4', 'P5'], default='P1')
    parser.add_argument('--report')
    parser.add_argument('--note')
    parser.set_defaults(fn=cmd_quality)


REGISTRARS = {'quality': register_quality}
