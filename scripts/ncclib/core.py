"""核心：路径与常量、读写、通用工具。其余模块都只往下依赖到这里。"""

import datetime
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path


SCHEMA = 4


PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent


ENTRY = PLUGIN_ROOT / "scripts" / "ncc_state.py"   # 写进写手包与提示里的命令入口


REGISTRY = json.loads((PLUGIN_ROOT / "workflow" / "registry.json").read_text(encoding="utf-8"))   # 词表与布局的唯一源头（七律一）


LAYOUT = REGISTRY["layout"]


def L(key):
    """布局键 → 相对路径（书项目里相对书目录，scope 为 root 的相对书库根目录）。"""
    return LAYOUT[key]["path"]


V = {k: v["values"] for k, v in REGISTRY["vocab"].items()}


DIRS = sorted({e["path"] if e.get("dir") else str(Path(e["path"]).parent) for e in LAYOUT.values()
               if e.get("scope", "book") == "book" and not e.get("on_demand")} - {"."})   # init 建的目录


LEDGER = str(Path(L("promises")).parent)


PROMISES = L("promises")


KNOWLEDGE = L("knowledge")


FACTS = L("facts")


EVENTS = L("events")


OLD_FORESHADOW = REGISTRY["layout_legacy"]["foreshadow_v01"]


SCENE_DIR = L("scene_dir")


SEEDS = L("seeds")


REVIEW_DIR = L("review_dir")


FINALE_LIST = L("finale_list")


READER_DATA = L("reader_data")


WORK = L("work")


PACK_DIR = L("packs")


OPLOG = L("oplog")


AUTHOR_DIR = L("author_dir")


CRAFT_LIBRARY = L("craft_library")


INTENT_VIEW = L("intent_view")


FOCUS_VIEW = L("focus_view")


LEDGER_VIEWS = {L("promise_view"): "promise", L("know_view"): "know", L("fact_view"): "fact"}


def _legacy_target(ref):
    key, _, name = ref.partition(":")
    return f"{L(key)}/{name}" if name else L(key)


OLD_PACKS = REGISTRY["layout_legacy"]["book_moves"][0][0]   # v1.x 的写手包目录


OLD_BOOK_PATHS = tuple((old, _legacy_target(ref)) for old, ref in REGISTRY["layout_legacy"]["book_moves"])


LEVELS = tuple(V["levels"])


MODES = tuple(REGISTRY["writing_modes"])


ARCS = tuple(V["arcs"])


PROMISE_TYPES = tuple(V["promise_types"])


PROMISE_PREFIX = V["promise_id_prefix"]


NON_READER_TYPES = tuple(V["non_reader_types"])   # 不计入水章判定、不进"读者在等什么"


OPEN_STATES = tuple(V["open_states"])


CHAPTER_STATES = tuple(V["chapter_states"])


TENSION = tuple(V["tension"])


LEGACY_MOOD = V["legacy_mood"]


COLORS = tuple(V["colors"])


SIGNING_POINTS = tuple(V["signing_points"])


SCENE_REQUIRED = tuple(V["scene_required"])


SCENE_KEY_REQUIRED = tuple(V["scene_key_required"])


SCENE_BATCH = V["scene_batch"]


PACK_BUDGET = 12000


SNAPSHOT_DIR = L("snapshots")


KNOW_DIR = L("know_dir")


DOMAINS = tuple(V["domains"])


DOMAIN_ALIAS = V["domain_alias"]


ERAS = tuple(V["eras"])


REGIONS = {k: tuple(v) for k, v in V["regions"].items()}


MATERIAL_DIR = L("materials")


SHARED_MATERIALS = L("shared_materials")   # 书库根目录下，跨书共用，格式相同，编号前缀 MS


MATERIAL_REQUIRED = tuple(V["material_required"])


MATERIAL_FIELDS = MATERIAL_REQUIRED + ("可信级", "域", "题材")


MATERIAL_TRUST = tuple(V["material_trust"])


MATERIAL_HINT = {"转述": "（转述自真人：人名、地名和能认出本人的细节都要换掉）",
                 "传闻": "（传闻：只能当人物口中的说法，叙述不当事实写）",
                 "拆书": "（拆书样本：只借写法，不搬内容）"}


STYLE_FP = L("style_fp")          # 数字指纹：只给审稿与脚本看，不进写手包（铁律 9）


STYLE_ANCHOR = L("style_anchor")  # 语感、校准段、负面清单：进写手包


STYLE_MIN = 10000                 # 旧文样本至少 1 万汉字（约 3 章）


PREFS = L("prefs")


OLD_ROOT_PATHS = tuple((old, _legacy_target(ref)) for old, ref in REGISTRY["layout_legacy"]["root_moves"])


PREF_HALF_LIFE = 180


PREF_V1 = {"favoriteGenres": "题材", "preferredProtagonist": "主角", "preferredPerspective": "视角",
           "preferredTone": "基调", "styleReferences": "风格参考"}


CRAFT_EXCERPT = L("craft_excerpt")


HAN = re.compile(r"[一-鿿]")


WRITER_SEEDS = tuple(V["writer_seeds"])   # 画面、亲历、生活经验；#2"最在乎的问题"离主题太近，不进写手包


CHARACTER_REQUIRED = tuple(V["character_required"])


UNIT_REVIEW_REQUIRED = tuple(V["unit_review_required"])


VOLUME_REVIEW_REQUIRED = tuple(V["volume_review_required"])


FINALE_REQUIRED = tuple(V["finale_required"])


TEAM_POSITIONS = tuple(V["team_positions"])


FEEDBACK_SOURCES = tuple(V["feedback_sources"])


FEEDBACK_KINDS = tuple(V["feedback_kinds"])


ROLES = tuple(REGISTRY["roles"])


MEMORY_ROLES = ("manager",) + ROLES


MEMORY_DIR = L("memory")


SHARED_MEMORY = L("shared_memory")


MEMORY_LOG = L("memory_log")


HANDOFF = L("handoff")


BRIEF_DIR = L("briefs")


CATEGORY_DIR = L("categories")


DECON_LIB = L("decon_lib")


TECHNIQUE_LIB = L("technique_library")


TECHNIQUE_USAGE = L("technique_usage")


OVERLAY = L("evolution_overlay")


EVOLUTION_LOG = L("evolution_log")


MEMORY_KINDS = tuple(V["memory_kinds"])


HANDOFF_KINDS = tuple(V["handoff_kinds"])


HANDOFF_LAYERS = tuple(V["handoff_layers"])


TECHNIQUE_STATES = tuple(V["technique_states"])


TECHNIQUE_STAGES = tuple(V["technique_stages"])


CONFIDENCE = tuple(V["confidence"])


MEMORY_CFG = REGISTRY["memory"]


HANDOFF_CFG = REGISTRY["handoff"]


TECH_CFG = REGISTRY["techniques"]


DECON_CFG = REGISTRY["decon"]


EVOLUTION = REGISTRY["evolution"]


REVIEW_WORDS = tuple(REGISTRY["review_words"]["values"])


WRITER_GUARD = REVIEW_WORDS + tuple(REGISTRY["review_words"]["memory_extra"])


# 阶段（D10）：founding → settings → outline → opening → serial ⇄ volume → finale → finished
GATES = {
    "soul": ("soul", "settings"),
    "settings": ("settings_frozen", "outline"),
    "outline": ("outline_frozen", "opening"),
    "opening": ("opening_accepted", "serial"),
    "volume": ("volume", "serial"),
    "finale": ("finale", "finished"),
}


PLANNED_GATES = {}


def now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def die(msg, code=1):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    os.replace(tmp, path)


def read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text("utf-8"))
    except json.JSONDecodeError as e:
        die(f"{path} 损坏: {e}")


def load(book_dir: Path) -> dict:
    p = book_dir / "book.json"
    if not p.exists():
        die(f"book.json 不存在: {p}（先 init，或按 references/book-state.md 重建）")
    d = read_json(p, {})
    if d.get("schema_version", 1) < SCHEMA:
        die(f"book.json 是 schema {d.get('schema_version', 1)}，先运行: ncc_state.py migrate {book_dir}")
    return d


def save(book_dir: Path, data: dict):
    data["updated_at"] = now()
    write_json(book_dir / "book.json", data)


def config_numbers(path: Path, keys) -> dict:
    """读取约定的整数配置项，兼容平铺与分节；忽略注释与相似键名。"""
    if not path.is_file():
        return {}
    text = path.read_text("utf-8")
    out = {}
    for key in keys:
        matches = re.findall(rf"^\s*{re.escape(key)}:[ \t]*(\d+)[ \t]*(?:#.*)?$", text, re.M)
        if matches:
            out[key] = int(matches[-1])
    return out


def resolved_config(where: Path):
    """默认 < 书库配置 < 作者覆盖 < 本书配置；同时返回每项的实际来源。"""
    where = Path(where)
    root = book_root(where)
    cfg = {"words_min": 3000, "words_max": 5000, "max_retry": 3, "buffer_min": 5,
           "half_life_days": PREF_HALF_LIFE}
    cfg.update({key[6:]: spec["default"] for key, spec in EVOLUTION["keys"].items()
                if key.startswith("check.") and spec["type"] == "int"})
    sources = dict.fromkeys(cfg, "插件默认")

    def apply(values, source):
        cfg.update(values)
        sources.update(dict.fromkeys(values, source))

    apply(config_numbers(root / "ncc.config.yaml", cfg), "书库配置")
    over = overlay_values(where)
    apply({key[6:]: int(value) for key, value in over.items()
           if key.startswith("check.") and key[6:] in cfg and EVOLUTION["keys"].get(key, {}).get("type") == "int"}, "作者覆盖")
    if root != where:
        apply(config_numbers(where / "ncc.config.yaml", cfg), "本书配置")
    return cfg, sources


def load_cfg(book_dir: Path) -> dict:
    return resolved_config(book_dir)[0]


def ledger(book_dir: Path, rel: str, key: str = "items"):
    return read_json(book_dir / rel, {key: [] if key != "facts" else {}})


def sha16(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16] if p.is_file() else ""


def current_chapter(d: dict) -> int:
    done = [c["seq"] for c in d.get("chapters", []) if c.get("status") == "done"]
    return max(done) if done else 0


def find_ch(d: dict, seq: int) -> dict:
    for c in d.get("chapters", []):
        if c["seq"] == seq:
            return c
    die(f"book.json 中没有第 {seq} 章（先 chapter add）")


def parse_window(s):
    if not s:
        return None
    m = re.fullmatch(r"\s*(\d+)\s*[-~～至]\s*(\d+)\s*", str(s))
    if not m:
        die(f"--window 格式应为 A-B（章号），收到: {s}")
    a, b = int(m.group(1)), int(m.group(2))
    return [min(a, b), max(a, b)]


def as_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def split_names(s):
    return [x.strip() for x in re.split(r"[,，、]", s or "") if x.strip()]


def next_id(items, prefix):
    n = 0
    for it in items:
        m = re.fullmatch(rf"{prefix}-(\d+)", str(it.get("id", "")))
        if m:
            n = max(n, int(m.group(1)))
    return f"{prefix}-{n + 1:04d}"


def scene_path(book_dir: Path, seq: int) -> Path:
    return book_dir / SCENE_DIR / f"ch-{seq:04d}.md"


def section(text: str, title: str) -> str:
    m = re.search(rf"^##\s*{re.escape(title)}[^\n]*\n(.*?)(?=^##\s|\Z)", text, flags=re.M | re.S)
    return m.group(1).strip() if m else ""


def plain(text: str) -> str:
    return re.sub(r"^[#>*\-|`\s]+", "", text, flags=re.M)


REV_LINE = re.compile(r"^\s*rev\s*\d+\s*[:：].*$", re.M)   # editor 的修订注记，不算正文


def han_words(text: str) -> int:
    """正文字数口径（check_chapter、words、chapter length 共用）：只数汉字，剔除 Markdown 标记与修订注记。"""
    return len(HAN.findall(plain(REV_LINE.sub("", text))))


def length_band(book_dir: Path, seq: int):
    """本章字数区间：场景卡里写了「字数范围：A-B」就用它，否则用 ncc.config.yaml 的 words_min/words_max。"""
    card = scene_path(book_dir, seq)
    if card.exists():
        m = re.search(r"字数范围[：:]\s*(\d+)\s*[-~～至]\s*(\d+)", card.read_text("utf-8"))
        if m:
            lo, hi = sorted((int(m.group(1)), int(m.group(2))))
            return lo, hi, "场景卡"
    cfg = load_cfg(book_dir)
    return cfg["words_min"], cfg["words_max"], "配置"


def knowledge_path(book_dir: Path, seq: int) -> Path:
    return book_dir / KNOW_DIR / f"ch-{seq:04d}.md"


def normalize_domain(x: str):
    x = x.strip()
    return x if x in DOMAINS else DOMAIN_ALIAS.get(x)


def chapter_file(book_dir: Path, c: dict) -> Path:
    p = book_dir / c.get("file", "")
    if not p.is_file():
        die(f"找不到第 {c['seq']} 章正文：{c.get('file')}")
    return p


def ensure_m3_fields(d: dict):
    """v0.3 及更早建的书补齐 M3 字段。"""
    d.setdefault("units", [])
    d.setdefault("volumes", [{"n": 1, "start": 1, "end": None, "status": "open"}])
    d.setdefault("published_upto", 0)
    d.setdefault("team", {})
    d.setdefault("era", "")
    d.setdefault("study", [])
    d.setdefault("setting_categories", {"used": {}, "none": ""})
    d.setdefault("benchmarks", [])
    return d


def open_unit(d):
    return next((u for u in d.get("units", []) if u.get("status") == "open"), None)


def open_volume(d):
    return next((v for v in d.get("volumes", []) if v.get("status") in ("open", "reviewing")), None)


def range_chapters(d, lo, hi):
    return [c for c in d.get("chapters", []) if lo <= c["seq"] <= hi]


def next_seq(d: dict) -> int:
    pending = [c["seq"] for c in d.get("chapters", []) if c.get("status") != "done"]
    return min(pending) if pending else current_chapter(d) + 1


def copy_template(name: str, dest: Path):
    tpl = PLUGIN_ROOT / "skills/ncc/templates" / name
    if not dest.exists() and tpl.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(tpl.read_text("utf-8"), "utf-8")


def view_head(sources: str, how: str) -> str:
    return f"> 本文件由 `ncc_state.py render` 从 {sources} 生成，勿手改；要改就改源头：{how}。"


def book_root(p: Path) -> Path:
    """书目录 → 书库根目录；本身就是书库根目录（或拆书库里的一本书）时按原样或向上找。"""
    p = Path(p)
    if (p / "book.json").exists():
        return p.parent
    if p.parent.name == DECON_LIB:
        return p.parent.parent
    return p


def overlay_values(where: Path = None) -> dict:
    """作者覆盖层（evolve apply 写入）：插件默认 < 作者覆盖 < 本书设置。NCC_OVERLAY 指向别的文件时用它（评测对比用）。"""
    env = os.environ.get("NCC_OVERLAY")
    if env:
        return read_json(Path(env), {}).get("values", {})
    if where is None:
        return {}
    return read_json(book_root(where) / OVERLAY, {}).get("values", {})


def with_words(base, change) -> list:
    """词表增删：change 里 "+词" 加、"-词" 删（不带符号当作加）。"""
    out = list(base)
    for w in change or []:
        if w.startswith("-"):
            out = [x for x in out if x != w[1:]]
        elif w.lstrip("+") not in out:
            out.append(w.lstrip("+"))
    return out


def technique_catalog(where: Path = None) -> dict:
    """类别 → 内置父类；新增类别继承父类的可见范围，不扩大审稿权限。"""
    catalog = {kind: kind for kind in V["technique_kinds"]}
    for change in overlay_values(where).get("technique.kinds", []):
        if change.startswith("-"):
            catalog.pop(change[1:], None)
            continue
        name, _, parent = change.lstrip("+").partition(":")
        # v3.0 已批准但未指定父类的类别兼容为剧情规划。
        if name in V["technique_kinds"]:
            catalog[name] = name
        else:
            parent = parent or TECH_CFG["default_parent"]
            if parent not in V["technique_kinds"]:
                die(f"技法类别「{name}」的父类「{parent}」不存在")
            catalog[name] = parent
    return catalog


def technique_kinds(where: Path = None) -> tuple:
    return tuple(technique_catalog(where))


def category_catalog(where: Path = None) -> dict:
    """设定类目表：注册表的首批类目＋作者覆盖层增补的类目。"""
    cat = dict(REGISTRY["setting_categories"]["catalog"])
    for name, spec in (overlay_values(where).get("setting.categories") or {}).items():
        cat.setdefault(name, {"alias": [], "genres": [], "optional": [], "numbers": [], **spec})
    return cat


def append_jsonl(path: Path, rec: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list:
    if not path.exists():
        return []
    out = []
    for i, line in enumerate(path.read_text("utf-8").splitlines(), 1):
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError as e:
                die(f"{path} 第 {i} 行损坏: {e}")
    return out


def bigrams(s: str) -> set:
    t = re.sub(r"[^\w]", "", s or "")
    return {t[i:i + 2] for i in range(len(t) - 1)}


def similarity(a: str, b: str) -> float:
    x, y = bigrams(a), bigrams(b)
    return len(x & y) / len(x | y) if x and y else 0.0


def soul_leaks(d: dict, text: str) -> list:
    soul = d.get("soul", {})
    return [v for v in (soul.get("question"), soul.get("answer"), soul.get("injustice"), soul.get("ending"))
            if v and len(v) >= 6 and v in text]


def chars(lines) -> int:
    return sum(len(HAN.findall(x)) for x in lines)


def capped(lines: list, cap: int):
    """整条筛选至汉字预算；超长条目跳过，继续容纳后面的短条，不截断语义。"""
    out, used, omitted = [], 0, 0
    for line in lines:
        size = chars([line])
        if used + size > cap:
            omitted += 1
            continue
        out.append(line)
        used += size
    return out, omitted


def writer_input_problems(d: dict, text: str) -> list:
    bad = [w for w in WRITER_GUARD if w in text]
    return ([f"审稿判据词：{'、'.join(bad)}"] if bad else []) + [f"书魂原文：{x}" for x in soul_leaks(d, text)]


def mood_of(c):
    m = c.get("mood")
    if isinstance(m, str):                     # v0.2 旧格式
        return {"tension": LEGACY_MOOD.get(m, m), "colors": []}
    return m


def cmd_sha(a):
    print(sha16(Path(a.file)))
