#!/usr/bin/env python3
"""ncc_state.py — book.json 与 06-台账 的确定性读写工具（schema v2，v0.4 循环与收束）。

状态只从这里（和经理派单回收）写入；markdown 投影与正文永不回写状态。
只依赖标准库。

书与闸门
  init <book> --title T [--genre a,b] [--chapters N] [--level 新手|熟手|老手] [--mode 建筑师|园丁|混合]
  status <book>                          状态摘要（退出码恒 0）
  next <book>                            第一个非 done 章（无则退出 1）
  migrate <book>                         v0.1（schema 1）→ schema 2
  gate <book> soul|settings|outline|opening|volume|finale [--action check|pass|reject] [--quote Q] [--force]
  level <book> 新手|熟手|老手             引导档位
  mode <book> 建筑师|园丁|混合            写作模式（D15）
  soul <book> [--question Q] [--answer A] [--injustice I] [--ending E] [--status 暂定|确定] [--deadline D] [--arc 正向|负向|平弧]
  contract <book> [--main M] [--extra X]... [--poison a,b]
  sign <book> <签约点> --ch N             签约点：主角与欲望|世界的不公|主角的机会|第一次小兑现|长线钩子

循环与收束（M3）
  unit open <book> --start N [--title T]   开一个剧情单元（10–40 章）
  unit close <book> --end N               关单元：须先有 00-策划/复盘/单元-Uk.md
  unit list <book>
  volume end <book> --end N               本卷写完，进入卷复盘（stage → volume），之后过 gate volume
  finale begin <book>                     进入收束（stage → finale），之后过 gate finale
  report <book> unit|volume|finale        按台账生成复盘或收束清单的底稿（打印到标准输出）
  feedback add <book> --ch N --source 真实|模拟 --kind 追读|弃读|划线|评论 --value V [--note X]
  feedback list <book> [--ch N]
  team set <book> <位> <名字>              团队认领：主编|主笔|设定|考据|发展编辑|审稿|试读|拆书
  team list <book>

场景卡（先审故事，后写文字）
  scene check <book> <seq>               校验 02-大纲/场景卡/ch-NNNN.md 的格式
  scene review <book> <seq> --result pass|revise --by story-editor|author [--note N]

章节
  chapter add <book> <seq> --file F [--key]      第 1–3 章默认为关键章
  chapter key <book> <seq> [--off]
  chapter hook <book> <seq> --type T --intensity 1-5 [--line L]
  chapter mark <book> <seq> <status>     pending|drafting|drafted|checking|reviewing|revising|failed
                                         （标 drafting 前，场景卡必须已过故事审且之后未改动）
  chapter mood <book> <seq> 压|放|平 [--colors 爽,燃,虐,甜,怕,笑,悲,敬,叹]
  chapter pick <book> <seq> --version V [--note N]   关键章：作者从 2–3 版里选定
  chapter retry <book> <seq>             重写计数 +1，达上限转 failed
  chapter publish <book> --upto N        记录已发布到第 N 章（用于存稿线）
  complete <book> <seq> --words N --hard pass|fail [--decidable R] [--report P]
                                         章定稿闸：硬伤层通过 ∧ 场景卡已过故事审 ∧（关键章）作者已选定
  water <book> <seq>                     水章检测：本章未建立、推进或兑现任何读者向承诺 → 退出 1

三本账
  promise add <book> --type T --content C --ch N [--strength 1-5] [--window A-B] [--deadline D] [--desire K]
  promise touch|resolve <book> <id> --ch N [--note X]
  promise drop <book> <id> --ch N --compensation X
  promise reschedule <book> <id> --window A-B --note X   延期（须写强化手段）
  promise list <book> [--open] [--type T]
  know add <book> --fact F --ch N [--known-by a,b] [--unknown-to x,y]
  know learn <book> <id> --who X --ch N
  know list <book> [--who X]
  fact set <book> <key> <value> --ch N [--source S] [--category C] [--override]
  fact get <book> <key>
  fact list <book> [--category C]
  reader-now <book> <seq> [--top N]      生成上下文包的"读者此刻"块

其他
  sha <file>

环境变量 NCC_ACTOR：团队模式下写入操作日志（06-台账/操作日志.jsonl）的操作者名字。
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path

SCHEMA = 2
PLUGIN_ROOT = Path(__file__).resolve().parent.parent

DIRS = [
    "00-策划", "00-策划/复盘", "01-设定/人物卡", "02-大纲/卷纲", "02-大纲/章纲", "02-大纲/场景卡",
    "03-文风", "04-正文/_packs", "05-审稿", "06-台账", "07-导出", "memory",
]
LEDGER = "06-台账"
PROMISES = f"{LEDGER}/承诺台账.json"
KNOWLEDGE = f"{LEDGER}/知情台账.json"
FACTS = f"{LEDGER}/知识台账.json"
EVENTS = f"{LEDGER}/状态事件.json"
OLD_FORESHADOW = f"{LEDGER}/伏笔台账.json"
SCENE_DIR = "02-大纲/场景卡"
SEEDS = "00-策划/作者种子.md"
REVIEW_DIR = "00-策划/复盘"
FINALE_LIST = "00-策划/收束清单.md"
READER_DATA = f"{LEDGER}/读者数据.json"
OPLOG = f"{LEDGER}/操作日志.jsonl"
CRAFT_LIBRARY = "_craft-library"

LEVELS = ("新手", "熟手", "老手")
MODES = ("建筑师", "园丁", "混合")
ARCS = ("正向", "负向", "平弧")
PROMISE_TYPES = ("伏笔", "悬念", "爽点欠账", "人物弧", "感情线", "卷目标", "名场面", "母题", "期权", "暂定决策")
NON_READER_TYPES = ("期权", "暂定决策", "母题")   # 不计入水章判定、不进"读者在等什么"
OPEN_STATES = ("开放", "推进中")
CHAPTER_STATES = ("pending", "drafting", "drafted", "checking",
                  "reviewing", "revising", "failed")
TENSION = ("压", "放", "平")
LEGACY_MOOD = {"压抑": "压", "释放": "放"}
COLORS = ("爽", "燃", "虐", "甜", "怕", "笑", "悲", "敬", "叹")
SIGNING_POINTS = ("主角与欲望", "世界的不公", "主角的机会", "第一次小兑现", "长线钩子")
SCENE_REQUIRED = ("视角", "目标", "翻转", "两难", "情感")
SCENE_KEY_REQUIRED = ("盲区", "阻碍", "画面", "风险")
CHARACTER_REQUIRED = ("欲望", "需要", "恐惧", "声音")
UNIT_REVIEW_REQUIRED = ("暂定决策", "故事审", "下一单元")
VOLUME_REVIEW_REQUIRED = ("承诺盘点", "书魂检验", "数据归因", "变更提议")
FINALE_REQUIRED = ("承诺清算", "暗线收拢", "书魂回答")
TEAM_POSITIONS = ("主编", "主笔", "设定", "考据", "发展编辑", "审稿", "试读", "拆书")
FEEDBACK_SOURCES = ("真实", "模拟")
FEEDBACK_KINDS = ("追读", "弃读", "划线", "评论")

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


# ---------- 基础 ----------

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


def load_cfg(book_dir: Path) -> dict:
    cfg = {"words_min": 3000, "words_max": 5000, "max_retry": 3, "buffer_min": 5}
    for p in (book_dir.parent / "ncc.config.yaml", book_dir / "ncc.config.yaml"):
        if p.exists():
            text = p.read_text("utf-8")
            for k in cfg:
                m = re.search(rf"{k}:\s*(\d+)", text)
                if m:
                    cfg[k] = int(m.group(1))
            break
    return cfg


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


# ---------- 承诺账 ----------

def next_id(items, prefix):
    n = 0
    for it in items:
        m = re.fullmatch(rf"{prefix}-(\d+)", str(it.get("id", "")))
        if m:
            n = max(n, int(m.group(1)))
    return f"{prefix}-{n + 1:04d}"


def promise_overdue(p, cur: int) -> bool:
    if p.get("status") not in OPEN_STATES or p.get("type") in ("期权", "母题"):
        return False
    if p.get("type") == "暂定决策":
        dl = as_int(p.get("deadline"))
        return dl is not None and dl < cur
    w = p.get("window")
    return bool(w) and w[1] < cur


def promise_due_soon(p, cur: int, ahead: int = 3) -> bool:
    if p.get("type") != "暂定决策" or p.get("status") not in OPEN_STATES:
        return False
    dl = as_int(p.get("deadline"))
    return dl is not None and cur <= dl <= cur + ahead


def promise_summary(book_dir: Path, d: dict) -> dict:
    items = ledger(book_dir, PROMISES)["items"]
    cur = current_chapter(d)
    reader = [p for p in items if p.get("type") not in NON_READER_TYPES]
    live = lambda t: sum(1 for p in items if p.get("type") == t and p.get("status") in OPEN_STATES)
    return {
        "open": sum(1 for p in reader if p.get("status") in OPEN_STATES),
        "resolved": sum(1 for p in reader if p.get("status") == "已兑现"),
        "dropped": sum(1 for p in reader if p.get("status") == "作废"),
        "overdue": sum(1 for p in items if promise_overdue(p, cur)),
        "options": live("期权"),
        "motifs": live("母题"),
        "pending_decisions": live("暂定决策"),
    }


def refresh_summary(book_dir: Path):
    d = load(book_dir)
    d["promises"] = promise_summary(book_dir, d)
    save(book_dir, d)


def chapter_touches(items, seq: int):
    """本章建立、推进、兑现（或作废补偿）的读者向承诺。"""
    hits = []
    for p in items:
        if p.get("type") in NON_READER_TYPES:
            continue
        if p.get("created_ch") == seq:
            hits.append((p["id"], "建立"))
        if any(e.get("ch") == seq for e in p.get("progress", [])):
            hits.append((p["id"], "推进"))
        if p.get("resolved_ch") == seq:
            hits.append((p["id"], "兑现" if p.get("status") == "已兑现" else "作废补偿"))
    return hits


# ---------- 场景卡 ----------

def scene_path(book_dir: Path, seq: int) -> Path:
    return book_dir / SCENE_DIR / f"ch-{seq:04d}.md"


def scene_problems(book_dir: Path, seq: int, key: bool):
    p = scene_path(book_dir, seq)
    if not p.exists():
        return [f"缺场景卡: {SCENE_DIR}/ch-{seq:04d}.md（模板见 skills/ncc-write/references/scene-card.md）"], 0
    text = p.read_text("utf-8")
    blocks = re.split(r"^##\s*场景", text, flags=re.M)[1:]
    if not blocks:
        return ["场景卡里没有「## 场景」段"], 0
    problems = []
    if len(blocks) > 3:
        problems.append(f"一章 {len(blocks)} 场，超过 3 场（考虑拆章）")
    need = SCENE_REQUIRED + (SCENE_KEY_REQUIRED if key else ())
    for i, b in enumerate(blocks, 1):
        missing = [f for f in need if f not in b]
        if missing:
            problems.append(f"场景 {i} 缺: {'、'.join(missing)}" + ("（关键章用完整版）" if key else ""))
    return problems, len(blocks)


def scene_ready(book_dir: Path, c: dict):
    """返回 None 表示场景卡已过故事审且之后未改动，否则返回原因。"""
    sc = c.get("scenes") or {}
    if sc.get("review") != "passed":
        return "场景卡未过故事审（scene review --result pass）"
    if sc.get("sha") != sha16(scene_path(book_dir, c["seq"])):
        return "场景卡在故事审之后被改动，需要重审"
    return None


def cmd_scene(a):
    book_dir = Path(a.book_dir)
    d = load(book_dir)
    c = find_ch(d, a.seq)
    problems, n = scene_problems(book_dir, a.seq, c.get("key", False))
    if a.action == "check":
        if problems:
            print(f"SCENE ch{a.seq}: FAIL")
            for p in problems:
                print(f"  - {p}")
            sys.exit(1)
        print(f"SCENE ch{a.seq}: {n} 场，格式完整")
        return
    # review
    if a.by not in ("story-editor", "author"):
        die("--by 只能是 story-editor 或 author")
    if a.result == "pass":
        if problems:
            print(f"SCENE ch{a.seq}: 格式不完整，不能记为通过")
            for p in problems:
                print(f"  - {p}")
            sys.exit(1)
        if c.get("key") and a.by != "author":
            die(f"第 {a.seq} 章是关键章，场景卡须由作者过目（--by author）")
    c["scenes"] = {"count": n, "review": "passed" if a.result == "pass" else "revise", "by": a.by,
                   "at": now(), "note": a.note or "", "sha": sha16(scene_path(book_dir, a.seq))}
    save(book_dir, d)
    print(f"OK ch{a.seq} 场景卡故事审: {c['scenes']['review']}（{a.by}）")


# ---------- M3：单元、卷、读者数据、团队 ----------

def ensure_m3_fields(d: dict):
    """v0.3 及更早建的书补齐 M3 字段。"""
    d.setdefault("units", [])
    d.setdefault("volumes", [{"n": 1, "start": 1, "end": None, "status": "open"}])
    d.setdefault("published_upto", 0)
    d.setdefault("team", {})
    return d


def open_unit(d):
    return next((u for u in d.get("units", []) if u.get("status") == "open"), None)


def open_volume(d):
    return next((v for v in d.get("volumes", []) if v.get("status") in ("open", "reviewing")), None)


def has_sections(p: Path, needed) -> list:
    if not p.exists() or not p.read_text("utf-8").strip():
        return [f"缺文件或为空: {p.name}"]
    text = p.read_text("utf-8")
    return [f"{p.name} 缺「{x}」一节" for x in needed if x not in text]


def cmd_unit(a):
    book_dir = Path(a.book_dir)
    d = ensure_m3_fields(load(book_dir))
    units = d["units"]
    if a.action == "list":
        for u in units:
            print(f"{u['id']} 第{u['start']}–{u.get('end') or '…'}章 {u['status']}  {u.get('title', '')}")
        return
    if a.action == "open":
        if open_unit(d):
            die(f"单元 {open_unit(d)['id']} 还没关，先 unit close")
        uid = f"U{len(units) + 1}"
        units.append({"id": uid, "start": a.start, "end": None, "title": a.title or "", "status": "open",
                      "opened_at": now()})
        msg = f"OK 单元 {uid} 从第 {a.start} 章开始"
    else:  # close
        u = open_unit(d)
        if not u:
            die("没有进行中的单元")
        if a.end < u["start"]:
            die("--end 早于单元起点")
        problems = has_sections(book_dir / REVIEW_DIR / f"单元-{u['id']}.md", UNIT_REVIEW_REQUIRED)
        if problems:
            print(f"UNIT {u['id']}: 不能关闭——先做单元复盘（ncc_state.py report {book_dir} unit 生成底稿）")
            for p in problems:
                print(f"  - {p}")
            sys.exit(1)
        u.update({"end": a.end, "status": "closed", "closed_at": now()})
        msg = f"OK 单元 {u['id']} 关闭（第{u['start']}–{a.end}章）"
    save(book_dir, d)
    print(msg)


def cmd_volume(a):
    book_dir = Path(a.book_dir)
    d = ensure_m3_fields(load(book_dir))
    v = open_volume(d)
    if d.get("stage") != "serial" or not v or v.get("status") != "open":
        die(f"只能在连载阶段结束进行中的卷（当前 stage={d.get('stage')}）")
    v.update({"end": a.end, "status": "reviewing"})
    d["stage"] = "volume"
    save(book_dir, d)
    print(f"OK 第{v['n']}卷写到第 {a.end} 章，进入卷复盘；复盘写到 {REVIEW_DIR}/卷{v['n']}.md 后过 gate volume")


def cmd_finale(a):
    book_dir = Path(a.book_dir)
    d = ensure_m3_fields(load(book_dir))
    if d.get("stage") != "serial":
        die(f"只能从连载阶段进入收束（当前 stage={d.get('stage')}）")
    d["stage"] = "finale"
    save(book_dir, d)
    print(f"OK 进入收束；用 report {book_dir} finale 生成收束清单底稿，写到 {FINALE_LIST}")


def cmd_feedback(a):
    book_dir = Path(a.book_dir)
    load(book_dir)
    data = ledger(book_dir, READER_DATA)
    if a.action == "list":
        for f in data["items"]:
            if a.ch and f.get("ch") != a.ch:
                continue
            print(f"第{f['ch']}章 [{f['source']}] {f['kind']}={f['value']}  {f.get('note', '')}")
        return
    if a.source not in FEEDBACK_SOURCES:
        die(f"--source 只能是 {'/'.join(FEEDBACK_SOURCES)}")
    if a.kind not in FEEDBACK_KINDS:
        die(f"--kind 只能是 {'/'.join(FEEDBACK_KINDS)}")
    data["items"].append({"ch": a.ch, "source": a.source, "kind": a.kind, "value": a.value,
                          "note": a.note or "", "at": now()})
    write_json(book_dir / READER_DATA, data)
    print(f"OK 第{a.ch}章 {a.source}{a.kind}={a.value}")


def cmd_team(a):
    book_dir = Path(a.book_dir)
    d = ensure_m3_fields(load(book_dir))
    if a.action == "list":
        for pos in TEAM_POSITIONS:
            print(f"{pos}: {d['team'].get(pos) or '（未认领，个人模式下由作者兼任）'}")
        return
    if a.position not in TEAM_POSITIONS:
        die(f"位置只能是 {'/'.join(TEAM_POSITIONS)}")
    d["team"][a.position] = a.name
    save(book_dir, d)
    print(f"OK {a.position} 由 {a.name} 认领")


def sustain_lines(book_dir: Path, d: dict) -> list:
    """存稿线与倦怠信号（M3-7）。"""
    out = []
    done = [c for c in d.get("chapters", []) if c.get("status") == "done"]
    pub = d.get("published_upto", 0)
    if pub:
        buffer = sum(1 for c in done if c["seq"] > pub)
        cfg = load_cfg(book_dir)
        line = f"存稿: {buffer} 章（已发布到第 {pub} 章，存稿线 {cfg['buffer_min']}）"
        if buffer < cfg["buffer_min"]:
            line += "  ⚠ 低于存稿线，建议进入保更模式（见 sustain.md）"
        out.append(line)
    timed = [c for c in done if c.get("drafting_at") and c.get("done_at")]
    if len(timed) >= 6:
        def hours(c):
            t0 = datetime.datetime.fromisoformat(c["drafting_at"])
            t1 = datetime.datetime.fromisoformat(c["done_at"])
            return max((t1 - t0).total_seconds() / 3600, 0.0)
        recent, before = timed[-3:], timed[-6:-3]
        h_r, h_b = sum(map(hours, recent)) / 3, sum(map(hours, before)) / 3
        r_r = sum(c.get("retry", 0) for c in recent) / 3
        r_b = sum(c.get("retry", 0) for c in before) / 3
        if h_b > 0 and h_r > h_b * 1.5 and r_r >= r_b:
            out.append(f"⚠ 倦怠信号：近 3 章平均耗时 {h_r:.1f} 小时（此前 {h_b:.1f}），返工没有减少。建议调节奏（见 sustain.md）")
    return out


def range_chapters(d, lo, hi):
    return [c for c in d.get("chapters", []) if lo <= c["seq"] <= hi]


def cmd_report(a):
    book_dir = Path(a.book_dir)
    d = ensure_m3_fields(load(book_dir))
    items = ledger(book_dir, PROMISES)["items"]
    know = ledger(book_dir, KNOWLEDGE)["items"]
    events = read_json(book_dir / EVENTS, {"events": []}).get("events", [])
    fb = ledger(book_dir, READER_DATA)["items"]
    cur = current_chapter(d)
    if a.kind == "unit":
        u = open_unit(d)
        if not u:
            die("没有进行中的单元（unit open）")
        lo, hi, title = u["start"], cur, f"单元 {u['id']} 复盘（第{u['start']}–{cur}章）"
    elif a.kind == "volume":
        v = open_volume(d)
        if not v:
            die("没有进行中的卷")
        lo, hi, title = v["start"], v.get("end") or cur, f"第{v['n']}卷 卷复盘（第{v['start']}–{v.get('end') or cur}章）"
    else:
        lo, hi, title = 1, cur, "收束清单"
    chs = range_chapters(d, lo, hi)
    out = [f"# {title}", "", f"> 由 ncc_state.py report {a.kind} 生成的底稿：数据部分已填，带「（待填）」的由对应角色与作者补写。", ""]

    def plist(ps, empty="（无）"):
        return [f"- {p['id']} [{p['type']}] 强度{p.get('strength')} {p['status']}：{p['content']}" for p in ps] or [f"- {empty}"]

    open_reader = [p for p in items if p.get("type") not in ("期权", "暂定决策") and p.get("status") in OPEN_STATES]
    pending = [p for p in items if p.get("type") == "暂定决策" and p.get("status") in OPEN_STATES]
    overdue = [p for p in items if promise_overdue(p, cur)]

    if a.kind in ("unit", "volume"):
        out += ["## 本段章节", ""]
        for c in chs:
            sc = c.get("scenes") or {}
            m = mood_of(c) if c.get("mood") else None
            out.append(f"- 第{c['seq']}章 {c['status']}" + ("（关键章，作者选定 " + str((c.get("selection") or {}).get("version", "—")) + "）" if c.get("key") else "")
                       + f"｜故事审：{sc.get('review', '—')}（{sc.get('by', '—')}）"
                       + (f"｜{m['tension']}{'、'.join(m.get('colors', []))}" if m else "")
                       + (f"｜钩子 {c['hook']['type']}/{c['hook']['intensity']}" if c.get("hook") else ""))
        out += ["", "## 暂定决策（请作者逐条确认或推翻）", ""] + plist(pending)
        by_editor = [c["seq"] for c in chs if (c.get("scenes") or {}).get("by") == "story-editor"]
        out += ["", "## 故事审回顾", "", f"- 由发展编辑放行、待作者复看的章：{by_editor or '（无）'}",
                "- 发展编辑的单元问题（待填）：最打动人的是什么？主角的选择够不够难？哪个配角比主角更鲜活？哪条线该删？主角失去了什么？主题之问从哪个角度被考验？"]
        made = [p for p in items if lo <= (p.get("created_ch") or -1) <= hi]
        paid = [p for p in items if lo <= (p.get("resolved_ch") or -1) <= hi]
        water = [c["seq"] for c in chs if c.get("status") == "done" and not chapter_touches(items, c["seq"])]
        lost = [e for e in events if e.get("attribute") == "失去" and lo <= (e.get("chapter") or -1) <= hi]
        out += ["", "## 承诺", "", f"- 本段建立 {len(made)} 条，兑现或作废 {len(paid)} 条；水章：{water or '（无）'}", "- 逾期："] + plist(overdue)
        out += ["", "## 失去", ""] + ([f"- 第{e.get('chapter')}章 {e.get('entity')}：{e.get('old')} → {e.get('new')}" for e in lost] or ["- （本段主角没有失去任何东西——检查是否只有爽没有痛）"])
        seg_fb = [f for f in fb if lo <= f.get("ch", -1) <= hi]
        out += ["", "## 读者数据", ""] + ([f"- 第{f['ch']}章 [{f['source']}] {f['kind']}={f['value']} {f.get('note', '')}" for f in seg_fb] or ["- （无回流数据）"])
        sim = {f["ch"]: f["value"] for f in seg_fb if f["source"] == "模拟" and f["kind"] == "追读"}
        real = {f["ch"]: f["value"] for f in seg_fb if f["source"] == "真实" and f["kind"] == "追读"}
        both = sorted(set(sim) & set(real))
        if both:
            out += ["", "**模拟读者校准**（同一章的模拟追读 vs 真实追读）", ""]
            out += [f"- 第{ch}章：模拟 {sim[ch]}｜真实 {real[ch]}" for ch in both]
            out += ["- 偏差规律（待填）：模拟读者在哪类章节高估或低估？写进 reader 的校准备注"]
    if a.kind == "unit":
        out += ["", "## 下一单元", "", "- 候选走向 2–3 个（outliner 从承诺账、读者此刻、书魂推出；标推荐与理由，至少一个非主流）（待填）",
                "- 下一单元的关键章（系统先按规则推荐，作者确认）（待填）"]
    if a.kind == "volume":
        soul = d.get("soul", {})
        out += ["", "## 承诺盘点", "", "开放中的读者向承诺："] + plist(open_reader)
        out += ["", "## 书魂检验", "", f"- 书魂状态：{soul.get('status')}" + (f"（最晚 {soul.get('deadline')}）" if soul.get("status") == "暂定" else ""),
                "- 本卷从哪个角度考验了主题之问？主角的答案变了吗？（待填）"]
        out += ["", "## 数据归因", "", "- 追读与弃读的变化落在哪几章、对应哪类写法（scout 与 pulse 填）（待填）"]
        out += ["", "## 变更提议", "", "- 需要调整的骨架（L1）条目，按 architecture.md 的变更提议格式（待填）", "- 下一卷走向候选 2–3 个，标推荐（待填）"]
    if a.kind == "finale":
        gaps = [k for k in know if k.get("unknown_to")]
        scenes_left = [p for p in items if p.get("type") == "名场面" and p.get("status") in OPEN_STATES]
        motifs = [p for p in items if p.get("type") == "母题" and p.get("status") in OPEN_STATES]
        out += ["## 承诺清算", "", "终局前必须兑现或交代的读者向承诺（期权除外）："] + plist(open_reader)
        out += ["", "未定的暂定决策："] + plist(pending)
        out += ["", "## 暗线收拢", "", "知情账里仍有人不知道的事（哪些要在终局揭开）："]
        out += [f"- {k['id']} {k['fact']}——{'、'.join(k['unknown_to'])} 还不知道" for k in gaps] or ["- （无）"]
        out += ["", "未兑现的名场面："] + plist(scenes_left) + ["", "核心意象的最后一次变化："] + plist(motifs)
        out += ["", "## 书魂回答", "", f"- 主题之问：{d.get('soul', {}).get('question') or '（未填）'}",
                "- 终局给出的回答：主角答案的胜利、修正，还是胜利的代价？（待填）",
                "- 收束方案候选 2–3 个，标推荐（outliner 填）（待填）"]
    print("\n".join(out))


# ---------- 书与闸门 ----------

def new_book(title, genre, chapters, level, mode):
    return {
        "schema_version": SCHEMA,
        "title": title,
        "genre_tags": genre,
        "premise": "",
        "target": {"chapters": chapters, "words_per_chapter": [3000, 5000]},
        "stage": "founding",
        "mode": mode,
        "writing_mode": "serial",
        "experience_level": level,
        "soul": {"question": "", "answer": "", "injustice": "", "ending": "",
                 "status": "未填", "deadline": "", "arc": ""},
        "contract": {"main": "", "extras": [], "poison": [], "signing": {}},
        "gates": {k: {"status": "waiting"} for k in
                  ("soul", "settings_frozen", "outline_frozen", "opening_accepted")},
        "chapters": [],
        "units": [],
        "volumes": [{"n": 1, "start": 1, "end": None, "status": "open"}],
        "published_upto": 0,
        "team": {},
        "promises": {},
        "host_spawn": False,
        "updated_at": now(),
    }


def copy_template(name: str, dest: Path):
    tpl = PLUGIN_ROOT / "skills/ncc/templates" / name
    if not dest.exists() and tpl.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(tpl.read_text("utf-8"), "utf-8")


def init_ledgers(book_dir: Path):
    for rel, empty in ((PROMISES, {"items": []}), (KNOWLEDGE, {"items": []}),
                       (FACTS, {"facts": {}}), (EVENTS, {"events": []}), (READER_DATA, {"items": []})):
        p = book_dir / rel
        if not p.exists():
            write_json(p, empty)
    (book_dir / SCENE_DIR).mkdir(parents=True, exist_ok=True)
    (book_dir / REVIEW_DIR).mkdir(parents=True, exist_ok=True)
    copy_template("author-intent.md", book_dir / "author-intent.md")
    copy_template("author-seeds.md", book_dir / SEEDS)
    cf = book_dir / "current-focus.md"
    if not cf.exists():
        cf.write_text("# 当前焦点（近 1–3 章）\n\n", "utf-8")


def cmd_init(a):
    book_dir = Path(a.book_dir)
    if (book_dir / "book.json").exists():
        die(f"已存在: {book_dir / 'book.json'}（不覆盖）")
    if a.level not in LEVELS:
        die(f"--level 只能是 {'/'.join(LEVELS)}")
    if a.mode not in MODES:
        die(f"--mode 只能是 {'/'.join(MODES)}")
    for sub in DIRS:
        (book_dir / sub).mkdir(parents=True, exist_ok=True)
    genre = [g.strip() for g in (a.genre or "").split(",") if g.strip()]
    save(book_dir, new_book(a.title, genre, a.chapters, a.level, a.mode))
    init_ledgers(book_dir)
    refresh_summary(book_dir)
    print(f"OK init {book_dir} stage=founding level={a.level} mode={a.mode}")


def cmd_migrate(a):
    book_dir = Path(a.book_dir)
    p = book_dir / "book.json"
    if not p.exists():
        die(f"book.json 不存在: {p}")
    d = read_json(p, {})
    if d.get("schema_version", 1) >= SCHEMA:
        print(f"已是 schema {SCHEMA}，无需迁移")
        return
    stage_map = {"ideation": "founding", "golden": "opening"}
    d["stage"] = stage_map.get(d.get("stage"), d.get("stage"))
    gates = d.get("gates", {})
    if "golden_accepted" in gates:
        gates["opening_accepted"] = gates.pop("golden_accepted")
    gates.setdefault("opening_accepted", {"status": "waiting"})
    gates.setdefault("soul", {"status": "waiting", "note": "v0.1 迁移：开书时无书魂闸，需补填书魂与类型契约"})
    d["gates"] = gates
    d.pop("foreshadows", None)
    fresh = new_book("", [], 0, "熟手", "建筑师")
    d.setdefault("experience_level", "熟手")
    d.setdefault("mode", "建筑师")           # v0.1 的流程就是建筑师模式
    d.setdefault("soul", fresh["soul"])
    d.setdefault("contract", fresh["contract"])
    d["schema_version"] = SCHEMA
    ensure_m3_fields(d)
    save(book_dir, d)

    migrated = 0
    old = book_dir / OLD_FORESHADOW
    if old.exists() and not (book_dir / PROMISES).exists():
        raw = read_json(old, [])
        rows = raw if isinstance(raw, list) else raw.get("items", [])
        status_map = {"planned": "开放", "已回收": "已兑现", "超期未收": "开放"}
        items = []
        for r in rows:
            win = str(r.get("预计回收窗口", ""))
            items.append({
                "id": r.get("id") or next_id(items, "FS"),
                "type": "伏笔", "content": r.get("content", ""), "strength": 3,
                "created_ch": as_int(r.get("预计埋设章")),
                "window": parse_window(win) if re.search(r"\d+\s*[-~～至]\s*\d+", win) else None,
                "deadline": None, "status": status_map.get(r.get("status"), "开放"),
                "progress": [], "resolved_ch": None, "note": "v0.1 伏笔台账迁移",
            })
        write_json(book_dir / PROMISES, {"items": items})
        migrated = len(items)
    init_ledgers(book_dir)
    refresh_summary(book_dir)
    print(f"OK migrate → schema {SCHEMA}；stage={d['stage']}；mode={d['mode']}；伏笔迁入承诺台账 {migrated} 条"
          + ("（原伏笔台账.json 保留未删）" if migrated else ""))


def cmd_status(a):
    book_dir = Path(a.book_dir)
    d = load(book_dir)
    chs = d.get("chapters", [])
    done = [c for c in chs if c["status"] == "done"]
    soul, ct = d.get("soul", {}), d.get("contract", {})
    print(f"书: {d.get('title')}  标签: {','.join(d.get('genre_tags', []))}  "
          f"引导档位: {d.get('experience_level')}  写作模式: {d.get('mode')}")
    print(f"阶段: {d.get('stage')}  更新方式: {d.get('writing_mode')}")
    print(f"书魂: {soul.get('status')}" + (f"（最晚 {soul.get('deadline')} 定下）" if soul.get("status") == "暂定" else "")
          + f"  主角弧光: {soul.get('arc') or '未定'}  主契约: {ct.get('main') or '未填'}"
          + f"  签约点: {len(ct.get('signing', {}))}/{len(SIGNING_POINTS)}")
    for g, v in d.get("gates", {}).items():
        extra = f" @ {v.get('at')} 「{v.get('quote')}」" if v.get("status") not in ("waiting", None) else ""
        print(f"闸门 {g}: {v.get('status')}{extra}" + (f"  ({v['note']})" if v.get("note") else ""))
    print(f"章节: {len(done)}/{len(chs)} done")
    for c in chs:
        if c["status"] != "done":
            why = scene_ready(book_dir, c)
            print(f"  断点: ch{c['seq']} status={c['status']} retry={c.get('retry', 0)}"
                  + ("（关键章）" if c.get("key") else "") + (f"  场景卡: {why}" if why else "  场景卡: 已过故事审"))
            break
    s = promise_summary(book_dir, d)
    print(f"承诺: 开放{s['open']} 已兑现{s['resolved']} 作废{s['dropped']} 逾期{s['overdue']} "
          f"期权{s['options']} 母题{s['motifs']} 暂定决策{s['pending_decisions']}")
    items = ledger(book_dir, PROMISES)["items"]
    cur = current_chapter(d)
    for p in items:
        if promise_overdue(p, cur):
            print(f"  逾期: {p['id']} [{p['type']}] {p['content']}")
        elif promise_due_soon(p, cur):
            print(f"  将到期: {p['id']} 暂定决策「{p['content']}」最晚第 {p['deadline']} 章")
        elif p.get("type") == "暂定决策" and p.get("status") in OPEN_STATES and as_int(p.get("deadline")) is None:
            print(f"  暂定: {p['id']}「{p['content']}」最晚 {p['deadline']}")
    stale = [c["seq"] for c in done
             if (c.get("review") or {}).get("sha") and c.get("sha") and c["review"]["sha"] != c["sha"]]
    if stale:
        print(f"警告: 以下章正文已变更但未复评（评审作废）: {stale}")
    water = [c["seq"] for c in done if not chapter_touches(items, c["seq"])]
    if water:
        print(f"警告: 以下已完成章未建立、推进或兑现任何承诺（水章）: {water}")
    ensure_m3_fields(d)
    u, v = open_unit(d), open_volume(d)
    print(f"卷: 第{v['n']}卷（{v['status']}，自第{v['start']}章）" if v else "卷: 无进行中的卷",
          f"  单元: {u['id']}（自第{u['start']}章）" if u else "  单元: 无进行中的单元")
    for line in sustain_lines(book_dir, d):
        print(line)
    if d.get("team"):
        print("团队: " + "，".join(f"{k}={v}" for k, v in d["team"].items()))
    print(f"更新于: {d.get('updated_at')}")


def cmd_next(a):
    d = load(Path(a.book_dir))
    for c in d.get("chapters", []):
        if c["status"] != "done":
            print(c["seq"])
            return
    print("NONE")
    sys.exit(1)


def lexicon_count(book_dir: Path) -> int:
    p = book_dir / "01-设定" / "设定词典.md"
    if not p.exists():
        return 0
    rows = 0
    for line in p.read_text("utf-8").splitlines():
        s = line.strip()
        if s.startswith("|") and not set(s) <= {"|", "-", " ", ":"} and "首现章计划" not in s:
            rows += 1
    return rows


def nonempty(book_dir: Path, rel: str) -> bool:
    p = book_dir / rel
    return p.exists() and bool(p.read_text("utf-8").strip())


def hard_passed(c: dict) -> bool:
    rev = c.get("review") or {}
    if "hard" in rev:
        return rev["hard"] == "pass"
    return (rev.get("score") or 0) >= 70     # v0.1 旧评审兼容


def gate_check(book_dir: Path, name: str, d: dict) -> list:
    problems = []
    mode = d.get("mode", "混合")
    if name == "soul":
        soul, ct = d.get("soul", {}), d.get("contract", {})
        labels = {"question": "主题之问", "answer": "主角的答案", "injustice": "世界的不公", "ending": "终局的回答"}
        for k, label in labels.items():
            if not soul.get(k, "").strip():
                problems.append(f"书魂缺「{label}」（可写候选并标暂定，见 guidance.md）")
        if soul.get("status") not in ("暂定", "确定"):
            problems.append("书魂状态未标暂定或确定")
        elif soul.get("status") == "暂定" and not soul.get("deadline"):
            problems.append("书魂为暂定，但没写最晚决定点（D7：最晚第一卷卷复盘）")
        if not ct.get("main"):
            problems.append("类型契约缺主契约")
        if not ct.get("poison"):
            problems.append("类型契约缺毒点清单")
        if d.get("experience_level") not in LEVELS:
            problems.append("未设引导档位（新手/熟手/老手）")
        ai = book_dir / "author-intent.md"
        if not ai.exists() or "书魂" not in ai.read_text("utf-8"):
            problems.append("author-intent.md 缺书魂一节")
    elif name == "settings":
        for rel in ("01-设定/世界观圣经.md", "01-设定/力量体系.md", "01-设定/设定词典.md"):
            if not nonempty(book_dir, rel):
                problems.append(f"缺设定文件或为空: {rel}")
        n = lexicon_count(book_dir)
        if n < 30:
            problems.append(f"设定词典条目 {n} < 30")
        hb = book_dir / "01-设定" / "力量体系.md"
        if hb.exists() and "量纲" not in hb.read_text("utf-8"):
            problems.append("力量体系未含量纲定义")
        cards = [p for p in (book_dir / "01-设定" / "人物卡").glob("*.md")
                 if all(f in p.read_text("utf-8") for f in CHARACTER_REQUIRED)]
        if not cards:
            problems.append(f"没有一张完整的人物卡（须含 {'、'.join(CHARACTER_REQUIRED)}，见 character.md）")
        if d.get("soul", {}).get("arc") not in ARCS:
            problems.append("未选主角弧光类型（正向/负向/平弧，soul --arc）")
    elif name == "outline":
        if not nonempty(book_dir, "02-大纲/总纲.md"):
            problems.append("缺大纲文件或为空: 02-大纲/总纲.md")
        if mode in ("建筑师", "混合") and not nonempty(book_dir, "02-大纲/卷纲/卷1.md"):
            problems.append("缺大纲文件或为空: 02-大纲/卷纲/卷1.md"
                            + ("（混合模式只需写到当前单元）" if mode == "混合" else ""))
        if mode == "建筑师":
            zs = sorted((book_dir / "02-大纲" / "章纲").glob("ch-*.md"))
            if len(zs) < 3:
                problems.append(f"章纲 {len(zs)} 份 < 3（黄金三章细纲不齐）")
        items = ledger(book_dir, PROMISES)["items"]
        if mode != "园丁" and not [p for p in items if p.get("type") not in NON_READER_TYPES]:
            problems.append("承诺台账为空（大纲层的伏笔、悬念、卷目标应先登记）")
    elif name == "opening":
        chs = {c["seq"]: c for c in d.get("chapters", [])}
        for seq in (1, 2, 3):
            c = chs.get(seq)
            if not c or c.get("status") != "done":
                problems.append(f"第 {seq} 章未 done")
                continue
            if not hard_passed(c):
                problems.append(f"第 {seq} 章硬伤层未通过")
            rev = c.get("review") or {}
            if rev.get("sha") and c.get("sha") and rev["sha"] != c["sha"]:
                problems.append(f"第 {seq} 章正文变更后未复评")
            if c.get("key") and not c.get("selection"):
                problems.append(f"第 {seq} 章是关键章，缺作者的版本选定（chapter pick）")
        blinds = list((book_dir / "05-审稿").glob("blind-*"))
        if not blinds:
            problems.append("缺读者盲评报告（05-审稿/blind-*.md）")
        elif not any("记忆测试" in p.read_text("utf-8") for p in blinds):
            problems.append("盲评报告缺「记忆测试」一节")
        signing = d.get("contract", {}).get("signing", {})
        for pt in SIGNING_POINTS:
            ch = signing.get(pt)
            if ch is None:
                problems.append(f"签约点未落地: {pt}")
            elif ch > 3:
                problems.append(f"签约点「{pt}」落在第 {ch} 章，晚于黄金三章")
    elif name == "volume":
        v = open_volume(d)
        if d.get("stage") != "volume" or not v or v.get("status") != "reviewing":
            problems.append("当前不在卷复盘阶段（先 volume end）")
        else:
            problems += has_sections(book_dir / REVIEW_DIR / f"卷{v['n']}.md", VOLUME_REVIEW_REQUIRED)
            items = ledger(book_dir, PROMISES)["items"]
            late = [p["id"] for p in items if promise_overdue(p, v["end"])]
            if late:
                problems.append(f"逾期承诺未处置（兑现、带补偿作废，或带强化延期）：{late}")
            if open_unit(d):
                problems.append(f"单元 {open_unit(d)['id']} 还没关（先做单元复盘并 unit close）")
            soul = d.get("soul", {})
            if v["n"] == 1 and soul.get("status") == "暂定":
                problems.append("书魂仍是暂定——D7 要求最晚在第一卷卷复盘时定下（soul --status 确定）")
    elif name == "finale":
        if d.get("stage") != "finale":
            problems.append("当前不在收束阶段（先 finale begin）")
        items = ledger(book_dir, PROMISES)["items"]
        left = [p["id"] for p in items if p.get("type") not in ("期权", "母题") and p.get("status") in OPEN_STATES]
        if left:
            problems.append(f"还有未清算的承诺（含暂定决策）：{left}")
        if d.get("soul", {}).get("status") != "确定":
            problems.append("书魂还没定下")
        problems += has_sections(book_dir / FINALE_LIST, FINALE_REQUIRED)
        problems += [x.replace("缺文件或为空", "缺书复盘") for x in has_sections(book_dir / REVIEW_DIR / "全书.md", ())]
        lib = book_dir.parent / CRAFT_LIBRARY / f"{d.get('title')}.md"
        if not lib.exists():
            problems.append(f"技艺库还没有这本书的条目：{CRAFT_LIBRARY}/{d.get('title')}.md（见 loops.md 书循环）")
    return problems


def cmd_gate(a):
    book_dir = Path(a.book_dir)
    if a.name in PLANNED_GATES:
        print(f"GATE {a.name}: 尚未实现（计划于 {PLANNED_GATES[a.name]}）")
        sys.exit(3)
    key, next_stage = GATES[a.name]
    d = ensure_m3_fields(load(book_dir))
    if a.action == "check":
        problems = gate_check(book_dir, a.name, d)
        if problems:
            print(f"GATE {a.name}: FAIL")
            for p in problems:
                print(f"  - {p}")
            sys.exit(1)
        print(f"GATE {a.name}: 机械条件满足，等待作者确认")
        return
    forced = []
    if a.action == "pass":
        problems = gate_check(book_dir, a.name, d)
        if problems and not a.force:
            print(f"GATE {a.name}: 机械条件未满足，不能记录通过（作者坚持放行请加 --force 并附 --quote 原话）")
            for p in problems:
                print(f"  - {p}")
            sys.exit(1)
        if problems and not a.quote:
            die("--force 放行必须附 --quote（作者原话）")
        forced = problems
    d.setdefault("gates", {})[key] = {
        "status": "passed" if a.action == "pass" else "rejected", "at": now(), "quote": a.quote or ""}
    if forced:
        d["gates"][key]["forced_over"] = forced
    if a.action == "pass" and a.name == "volume":
        v = open_volume(d)
        v.update({"status": "closed", "closed_at": now()})
        d["volumes"].append({"n": v["n"] + 1, "start": (v.get("end") or 0) + 1, "end": None, "status": "open"})
    if a.action == "pass" and next_stage:
        d["stage"] = next_stage
    save(book_dir, d)
    print(f"GATE {a.name}: {a.action} 记录已写入，stage={d['stage']}")


def cmd_level(a):
    if a.level not in LEVELS:
        die(f"档位只能是 {'/'.join(LEVELS)}")
    book_dir = Path(a.book_dir)
    d = load(book_dir)
    d["experience_level"] = a.level
    save(book_dir, d)
    print(f"OK 引导档位={a.level}")


def cmd_mode(a):
    if a.mode not in MODES:
        die(f"写作模式只能是 {'/'.join(MODES)}")
    book_dir = Path(a.book_dir)
    d = load(book_dir)
    d["mode"] = a.mode
    save(book_dir, d)
    print(f"OK 写作模式={a.mode}")


def cmd_soul(a):
    book_dir = Path(a.book_dir)
    d = load(book_dir)
    soul = d.setdefault("soul", {})
    for k in ("question", "answer", "injustice", "ending", "deadline"):
        v = getattr(a, k)
        if v is not None:
            soul[k] = v
    if a.arc is not None:
        if a.arc not in ARCS:
            die(f"--arc 只能是 {'/'.join(ARCS)}")
        soul["arc"] = a.arc
    if a.status:
        if a.status not in ("暂定", "确定"):
            die("--status 只能是 暂定 或 确定")
        soul["status"] = a.status
        if a.status == "确定":
            soul["deadline"] = ""
    save(book_dir, d)
    print(f"OK 书魂 status={soul.get('status')}" + (f" deadline={soul.get('deadline')}" if soul.get("deadline") else "")
          + (f" arc={soul.get('arc')}" if soul.get("arc") else ""))


def cmd_contract(a):
    book_dir = Path(a.book_dir)
    d = load(book_dir)
    ct = d.setdefault("contract", {"main": "", "extras": [], "poison": [], "signing": {}})
    if a.main is not None:
        ct["main"] = a.main
    if a.extra:
        ct["extras"] = list(dict.fromkeys(ct.get("extras", []) + a.extra))
    if a.poison is not None:
        ct["poison"] = split_names(a.poison)
    save(book_dir, d)
    print(f"OK 主契约={ct['main'] or '未填'} 附加={len(ct['extras'])} 毒点={len(ct['poison'])}")


def cmd_sign(a):
    if a.point not in SIGNING_POINTS:
        die(f"签约点只能是: {'、'.join(SIGNING_POINTS)}")
    book_dir = Path(a.book_dir)
    d = load(book_dir)
    d.setdefault("contract", {}).setdefault("signing", {})[a.point] = a.ch
    save(book_dir, d)
    print(f"OK 签约点「{a.point}」落在第 {a.ch} 章")


# ---------- 章节 ----------

def cmd_chapter(a):
    book_dir = Path(a.book_dir)
    d = load(book_dir)
    if a.action == "publish":
        d["published_upto"] = max(d.get("published_upto", 0), a.upto)
        save(book_dir, d)
        print(f"OK 已发布到第 {d['published_upto']} 章")
        return
    if a.action == "add":
        if any(c["seq"] == a.seq for c in d.get("chapters", [])):
            die(f"第 {a.seq} 章已登记")
        key = a.key or a.seq <= 3
        d.setdefault("chapters", []).append({
            "seq": a.seq, "file": a.file, "status": "pending", "key": key, "word_count": 0,
            "hook": None, "mood": None, "retry": 0, "sha": "", "review": None,
            "scenes": {"count": 0, "review": "pending"}, "selection": None,
            "pack": f"04-正文/_packs/ch-{a.seq:04d}.json"})
        d["chapters"].sort(key=lambda c: c["seq"])
        msg = f"OK chapter add ch{a.seq} → {a.file}" + ("（关键章）" if key else "")
    else:
        c = find_ch(d, a.seq)
        if a.action == "key":
            c["key"] = not a.off
            msg = f"OK ch{a.seq} key={c['key']}"
        elif a.action == "hook":
            if not 1 <= a.intensity <= 5:
                die("--intensity 取 1–5（1 顺带 … 5 全书名场面）")
            c["hook"] = {"type": a.type, "intensity": a.intensity, "line": a.line or ""}
            msg = f"OK ch{a.seq} hook={a.type}/{a.intensity}"
        elif a.action == "mark":
            if a.status not in CHAPTER_STATES:
                die(f"status 只能是 {'/'.join(CHAPTER_STATES)}（done 只能经 complete）")
            if a.status == "drafting":
                why = scene_ready(book_dir, c)
                if why:
                    die(f"第 {a.seq} 章不能开写：{why}。先审故事，后写文字。")
            c["status"] = a.status
            if a.status == "drafting" and not c.get("drafting_at"):
                c["drafting_at"] = now()
            msg = f"OK ch{a.seq} status={a.status}"
        elif a.action == "mood":
            t = LEGACY_MOOD.get(a.tension, a.tension)
            if t not in TENSION:
                die(f"张弛只能是 {'/'.join(TENSION)}")
            colors = split_names(a.colors)
            bad = [x for x in colors if x not in COLORS]
            if bad:
                die(f"情绪色只能取 {'、'.join(COLORS)}，收到: {'、'.join(bad)}")
            c["mood"] = {"tension": t, "colors": colors}
            msg = f"OK ch{a.seq} mood={t}" + (f" {'、'.join(colors)}" if colors else "")
        elif a.action == "pick":
            if not c.get("key"):
                die(f"第 {a.seq} 章不是关键章；常规章不走比选")
            c["selection"] = {"version": a.version, "note": a.note or "", "by": "author", "at": now()}
            msg = f"OK ch{a.seq} 作者选定版本 {a.version}"
        elif a.action == "retry":
            c["retry"] = c.get("retry", 0) + 1
            if c["retry"] >= load_cfg(book_dir)["max_retry"]:
                c["status"] = "failed"
            msg = f"OK ch{a.seq} retry={c['retry']} status={c['status']}"
    save(book_dir, d)
    print(msg)


def cmd_complete(a):
    book_dir = Path(a.book_dir)
    d = load(book_dir)
    c = find_ch(d, a.seq)
    why = scene_ready(book_dir, c)
    if why:
        die(f"章定稿闸：{why}")
    if a.hard != "pass":
        die("章定稿闸：硬伤层未通过（先派 editor 修订并复审）")
    if c.get("key") and not c.get("selection"):
        die(f"章定稿闸：第 {a.seq} 章是关键章，须作者从 2–3 版中选定（chapter pick）")
    c["status"] = "done"
    c["done_at"] = now()
    c["word_count"] = a.words
    c["sha"] = sha16(book_dir / c.get("file", ""))
    c["review"] = {"hard": a.hard, "decidable": a.decidable,
                   "report": a.report or (c.get("review") or {}).get("report", ""), "sha": c["sha"]}
    d["promises"] = promise_summary(book_dir, d)
    save(book_dir, d)
    print(f"OK complete ch{a.seq} words={a.words} sha={c['sha']}")


def cmd_water(a):
    book_dir = Path(a.book_dir)
    items = ledger(book_dir, PROMISES)["items"]
    hits = chapter_touches(items, a.seq)
    if hits:
        print(f"ch{a.seq}: " + "，".join(f"{i} {k}" for i, k in hits))
        return
    print(f"ch{a.seq}: 水章——未建立、推进或兑现任何读者向承诺")
    sys.exit(1)


# ---------- 承诺账 ----------

PREFIX = {"伏笔": "FS", "暂定决策": "TD", "名场面": "SC", "母题": "MT"}


def cmd_promise(a):
    book_dir = Path(a.book_dir)
    load(book_dir)
    data = ledger(book_dir, PROMISES)
    items = data["items"]
    if a.action == "list":
        d = load(book_dir)
        cur = current_chapter(d)
        for p in items:
            if a.open and p.get("status") not in OPEN_STATES:
                continue
            if a.type and p.get("type") != a.type:
                continue
            flag = " 逾期" if promise_overdue(p, cur) else (" 将到期" if promise_due_soon(p, cur) else "")
            w = p.get("window")
            when = f" 窗口{w[0]}-{w[1]}" if w else (f" 最晚{p['deadline']}" if p.get("deadline") else "")
            print(f"{p['id']} [{p['type']}] 强度{p.get('strength')} {p['status']} 第{p.get('created_ch')}章起{when}{flag}  {p['content']}")
        return
    if a.action == "add":
        if a.type not in PROMISE_TYPES:
            die(f"--type 只能是 {'/'.join(PROMISE_TYPES)}")
        if a.type == "暂定决策" and not a.deadline:
            die("暂定决策必须给 --deadline（章号或节点，如 22 或 第一卷卷复盘）")
        if not 1 <= a.strength <= 5:
            die("--strength 取 1–5")
        pid = next_id(items, PREFIX.get(a.type, "P"))
        items.append({
            "id": pid, "type": a.type, "content": a.content, "strength": a.strength,
            "created_ch": a.ch, "window": parse_window(a.window), "deadline": a.deadline,
            "desire": a.desire, "status": "开放", "progress": [], "resolved_ch": None})
        msg = f"OK {pid} [{a.type}] 第{a.ch}章建立"
    else:
        p = next((x for x in items if x["id"] == a.id), None)
        if not p:
            die(f"承诺台账中没有 {a.id}")
        if p.get("status") not in OPEN_STATES:
            die(f"{a.id} 状态为 {p.get('status')}，不能再 {a.action}")
        if a.action == "touch":
            p.setdefault("progress", []).append({"ch": a.ch, "note": a.note or ""})
            p["status"] = "推进中"
            msg = f"OK {a.id} 第{a.ch}章推进"
        elif a.action == "resolve":
            p["status"] = "已兑现"
            p["resolved_ch"] = a.ch
            if a.note:
                p["resolve_note"] = a.note
            msg = f"OK {a.id} 第{a.ch}章兑现"
        elif a.action == "reschedule":
            if not (a.note or "").strip():
                die("延期必须写 --note（用什么强化让读者继续等，如\"第 30 章再露一角\"）")
            old = p.get("window")
            p["window"] = parse_window(a.window)
            p.setdefault("progress", []).append({"ch": None, "note": f"延期 {old}→{p['window']}：{a.note}"})
            msg = f"OK {a.id} 延期到第 {p['window'][0]}–{p['window'][1]} 章"
        elif a.action == "drop":
            if not (a.compensation or "").strip():
                die("承诺作废必须写 --compensation（给读者的交代或替代兑现）")
            p["status"] = "作废"
            p["resolved_ch"] = a.ch
            p["compensation"] = a.compensation
            msg = f"OK {a.id} 第{a.ch}章作废，补偿：{a.compensation}"
    write_json(book_dir / PROMISES, data)
    refresh_summary(book_dir)
    print(msg)


# ---------- 知情账 ----------

def cmd_know(a):
    book_dir = Path(a.book_dir)
    load(book_dir)
    data = ledger(book_dir, KNOWLEDGE)
    items = data["items"]
    if a.action == "list":
        for k in items:
            if a.who and a.who not in k.get("known_by", []) and a.who not in k.get("unknown_to", []):
                continue
            print(f"{k['id']} 第{k.get('since_ch')}章 知道:{','.join(k.get('known_by', [])) or '无'} "
                  f"不知道:{','.join(k.get('unknown_to', [])) or '无'}  {k['fact']}")
        return
    if a.action == "add":
        kid = next_id(items, "K")
        items.append({"id": kid, "fact": a.fact, "since_ch": a.ch,
                      "known_by": split_names(a.known_by), "unknown_to": split_names(a.unknown_to),
                      "log": []})
        msg = f"OK {kid} 第{a.ch}章登记"
    else:  # learn
        k = next((x for x in items if x["id"] == a.id), None)
        if not k:
            die(f"知情台账中没有 {a.id}")
        if a.who in k.get("unknown_to", []):
            k["unknown_to"].remove(a.who)
        if a.who not in k.setdefault("known_by", []):
            k["known_by"].append(a.who)
        k.setdefault("log", []).append({"ch": a.ch, "who": a.who})
        msg = f"OK {a.id} 第{a.ch}章 {a.who} 得知"
    write_json(book_dir / KNOWLEDGE, data)
    print(msg)


# ---------- 世界账：知识台账 ----------

def cmd_fact(a):
    book_dir = Path(a.book_dir)
    load(book_dir)
    data = read_json(book_dir / FACTS, {"facts": {}})
    facts = data.setdefault("facts", {})
    if a.action == "get":
        f = facts.get(a.key)
        if not f:
            die(f"知识台账中没有「{a.key}」", 1)
        print(f"{a.key} = {f['value']}（第{f.get('ch')}章，来源：{f.get('source') or '未注'}，类别：{f.get('category') or '未分'}）")
        return
    if a.action == "list":
        for k, f in facts.items():
            if a.category and f.get("category") != a.category:
                continue
            print(f"{k} = {f['value']}  [{f.get('category') or '未分'}] 第{f.get('ch')}章 来源：{f.get('source') or '未注'}")
        return
    old = facts.get(a.key)
    if old and old["value"] != a.value and not a.override:
        print(f"CONFLICT 「{a.key}」已记为 {old['value']}（第{old.get('ch')}章），本次为 {a.value}。"
              "若是剧情内的合理变化请加 --override 并在正文交代原因。", file=sys.stderr)
        sys.exit(1)
    entry = {"value": a.value, "ch": a.ch, "source": a.source or "", "category": a.category or ""}
    if old and old["value"] != a.value:
        entry["history"] = old.get("history", []) + [{k: old[k] for k in ("value", "ch", "source") if k in old}]
    facts[a.key] = entry
    write_json(book_dir / FACTS, data)
    print(f"OK {a.key} = {a.value}")


# ---------- 读者此刻 ----------

def mood_of(c):
    m = c.get("mood")
    if isinstance(m, str):                     # v0.2 旧格式
        return {"tension": LEGACY_MOOD.get(m, m), "colors": []}
    return m


def cmd_reader_now(a):
    book_dir = Path(a.book_dir)
    d = load(book_dir)
    seq, top = a.seq, a.top
    items = ledger(book_dir, PROMISES)["items"]
    know = ledger(book_dir, KNOWLEDGE)["items"]
    events = read_json(book_dir / EVENTS, {"events": []}).get("events", [])
    before = [c for c in d.get("chapters", []) if c["seq"] < seq]
    out = [f"## 读者此刻（写第 {seq} 章前）", ""]

    out.append("**知道什么（读者知道、角色还不知道）**")
    gaps = [k for k in know if "读者" in k.get("known_by", []) and k.get("unknown_to")
            and (k.get("since_ch") or 0) < seq]
    out += [f"- {k['id']} {k['fact']}——{'、'.join(k['unknown_to'])} 还不知道" for k in gaps[:top]] or ["- （无登记的信息差）"]

    out += ["", "**在等什么（强度最高的开放承诺）**"]
    waiting = [p for p in items if p.get("type") not in NON_READER_TYPES
               and p.get("status") in OPEN_STATES and (p.get("created_ch") or 0) < seq]
    waiting.sort(key=lambda p: (-(p.get("strength") or 0), p.get("created_ch") or 0))
    lines = []
    for p in waiting[:top]:
        age = seq - (p.get("created_ch") or seq)
        w = p.get("window")
        tail = f"，计划第{w[0]}–{w[1]}章兑现" if w else ""
        lines.append(f"- {p['id']} [{p['type']}] 强度{p.get('strength')}：{p['content']}（已等 {age} 章{tail}）")
    out += lines or ["- （没有开放承诺——本章至少要建立一条）"]

    out += ["", "**情绪在哪**"]
    moods = [(c["seq"], mood_of(c)) for c in before if c.get("mood")][-5:]
    if moods:
        out.append("- 近几章：" + " → ".join(
            f"{s}{m['tension']}" + (f"（{'、'.join(m['colors'])}）" if m.get("colors") else "") for s, m in moods))
        last_release = max((s for s, m in moods if m["tension"] == "放"), default=None)
        out.append(f"- 距上次释放：{seq - last_release} 章" if last_release else "- 近几章没有释放段")
    else:
        out.append("- （近几章未登记情绪，chapter mood 登记）")

    losses = [e for e in events if e.get("attribute") == "失去" and (e.get("chapter") or 0) < seq][-3:]
    if losses:
        out += ["", "**最近失去了什么**"]
        out += [f"- 第{e.get('chapter')}章 {e.get('entity')}：{e.get('old')} → {e.get('new')}" for e in losses]

    out += ["", "**可能腻了什么**"]
    hooks = [c["hook"]["type"] for c in before if c.get("hook")][-5:]
    tired = [f"章尾钩子「{t}」近 5 章用了 {hooks.count(t)} 次" for t in dict.fromkeys(hooks) if hooks.count(t) >= 3]
    colors = [x for _, m in moods for x in m.get("colors", [])]
    tired += [f"情绪「{x}」近 5 章出现 {colors.count(x)} 次" for x in dict.fromkeys(colors) if colors.count(x) >= 3]
    desires = [p.get("desire") for p in items if p.get("type") == "爽点欠账" and p.get("status") == "已兑现"
               and p.get("desire") and seq - 10 <= (p.get("resolved_ch") or -99) < seq]
    tired += [f"爽感谱系第 {x} 型近 10 章兑现了 {desires.count(x)} 次" for x in dict.fromkeys(desires) if desires.count(x) >= 3]
    out += [f"- {t}" for t in tired] or ["- （无明显重复）"]

    cur = current_chapter(d)
    alerts = [p for p in items if promise_overdue(p, cur) or promise_due_soon(p, cur)]
    if alerts:
        out += ["", "**到期提醒**"]
        out += [f"- {p['id']} [{p['type']}] {p['content']}" for p in alerts]
    print("\n".join(out))


def cmd_sha(a):
    print(sha16(Path(a.file)))


# ---------- CLI ----------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init"); p.add_argument("book_dir"); p.add_argument("--title", required=True)
    p.add_argument("--genre", default=""); p.add_argument("--chapters", type=int, default=300)
    p.add_argument("--level", default="新手"); p.add_argument("--mode", default="混合"); p.set_defaults(fn=cmd_init)
    for name, fn in (("status", cmd_status), ("next", cmd_next), ("migrate", cmd_migrate)):
        p = sub.add_parser(name); p.add_argument("book_dir"); p.set_defaults(fn=fn)

    p = sub.add_parser("gate"); p.add_argument("book_dir"); p.add_argument("name", choices=list(GATES))
    p.add_argument("--action", choices=["check", "pass", "reject"], default="check")
    p.add_argument("--quote", default=""); p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_gate)

    p = sub.add_parser("level"); p.add_argument("book_dir"); p.add_argument("level"); p.set_defaults(fn=cmd_level)
    p = sub.add_parser("mode"); p.add_argument("book_dir"); p.add_argument("mode"); p.set_defaults(fn=cmd_mode)
    p = sub.add_parser("soul"); p.add_argument("book_dir")
    for k in ("question", "answer", "injustice", "ending", "status", "deadline", "arc"):
        p.add_argument(f"--{k}")
    p.set_defaults(fn=cmd_soul)
    p = sub.add_parser("contract"); p.add_argument("book_dir"); p.add_argument("--main")
    p.add_argument("--extra", action="append"); p.add_argument("--poison"); p.set_defaults(fn=cmd_contract)
    p = sub.add_parser("sign"); p.add_argument("book_dir"); p.add_argument("point")
    p.add_argument("--ch", type=int, required=True); p.set_defaults(fn=cmd_sign)

    p = sub.add_parser("scene"); ss = p.add_subparsers(dest="action", required=True)
    q = ss.add_parser("check"); q.add_argument("book_dir"); q.add_argument("seq", type=int)
    q = ss.add_parser("review"); q.add_argument("book_dir"); q.add_argument("seq", type=int)
    q.add_argument("--result", choices=["pass", "revise"], required=True); q.add_argument("--by", required=True)
    q.add_argument("--note")
    p.set_defaults(fn=cmd_scene)

    p = sub.add_parser("chapter"); cs = p.add_subparsers(dest="action", required=True)
    q = cs.add_parser("add"); q.add_argument("book_dir"); q.add_argument("seq", type=int)
    q.add_argument("--file", required=True); q.add_argument("--key", action="store_true")
    q = cs.add_parser("key"); q.add_argument("book_dir"); q.add_argument("seq", type=int); q.add_argument("--off", action="store_true")
    q = cs.add_parser("hook"); q.add_argument("book_dir"); q.add_argument("seq", type=int)
    q.add_argument("--type", required=True); q.add_argument("--intensity", type=int, required=True); q.add_argument("--line")
    q = cs.add_parser("mark"); q.add_argument("book_dir"); q.add_argument("seq", type=int); q.add_argument("status")
    q = cs.add_parser("mood"); q.add_argument("book_dir"); q.add_argument("seq", type=int); q.add_argument("tension")
    q.add_argument("--colors")
    q = cs.add_parser("pick"); q.add_argument("book_dir"); q.add_argument("seq", type=int)
    q.add_argument("--version", required=True); q.add_argument("--note")
    q = cs.add_parser("retry"); q.add_argument("book_dir"); q.add_argument("seq", type=int)
    q = cs.add_parser("publish"); q.add_argument("book_dir"); q.add_argument("--upto", type=int, required=True)
    p.set_defaults(fn=cmd_chapter)

    p = sub.add_parser("unit"); us = p.add_subparsers(dest="action", required=True)
    q = us.add_parser("open"); q.add_argument("book_dir"); q.add_argument("--start", type=int, required=True); q.add_argument("--title")
    q = us.add_parser("close"); q.add_argument("book_dir"); q.add_argument("--end", type=int, required=True)
    q = us.add_parser("list"); q.add_argument("book_dir")
    p.set_defaults(fn=cmd_unit)
    p = sub.add_parser("volume"); vs = p.add_subparsers(dest="action", required=True)
    q = vs.add_parser("end"); q.add_argument("book_dir"); q.add_argument("--end", type=int, required=True)
    p.set_defaults(fn=cmd_volume)
    p = sub.add_parser("finale"); fns = p.add_subparsers(dest="action", required=True)
    q = fns.add_parser("begin"); q.add_argument("book_dir")
    p.set_defaults(fn=cmd_finale)
    p = sub.add_parser("report"); p.add_argument("book_dir"); p.add_argument("kind", choices=["unit", "volume", "finale"])
    p.set_defaults(fn=cmd_report)
    p = sub.add_parser("feedback"); fbs = p.add_subparsers(dest="action", required=True)
    q = fbs.add_parser("add"); q.add_argument("book_dir"); q.add_argument("--ch", type=int, required=True)
    q.add_argument("--source", required=True); q.add_argument("--kind", required=True); q.add_argument("--value", required=True)
    q.add_argument("--note")
    q = fbs.add_parser("list"); q.add_argument("book_dir"); q.add_argument("--ch", type=int)
    p.set_defaults(fn=cmd_feedback)
    p = sub.add_parser("team"); ts = p.add_subparsers(dest="action", required=True)
    q = ts.add_parser("set"); q.add_argument("book_dir"); q.add_argument("position"); q.add_argument("name")
    q = ts.add_parser("list"); q.add_argument("book_dir")
    p.set_defaults(fn=cmd_team)

    p = sub.add_parser("complete"); p.add_argument("book_dir"); p.add_argument("seq", type=int)
    p.add_argument("--words", type=int, required=True); p.add_argument("--hard", choices=["pass", "fail"], required=True)
    p.add_argument("--decidable", type=float); p.add_argument("--report", default=""); p.set_defaults(fn=cmd_complete)
    p = sub.add_parser("water"); p.add_argument("book_dir"); p.add_argument("seq", type=int); p.set_defaults(fn=cmd_water)

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

    p = sub.add_parser("know"); ks = p.add_subparsers(dest="action", required=True)
    q = ks.add_parser("add"); q.add_argument("book_dir"); q.add_argument("--fact", required=True)
    q.add_argument("--ch", type=int, required=True); q.add_argument("--known-by"); q.add_argument("--unknown-to")
    q = ks.add_parser("learn"); q.add_argument("book_dir"); q.add_argument("id")
    q.add_argument("--who", required=True); q.add_argument("--ch", type=int, required=True)
    q = ks.add_parser("list"); q.add_argument("book_dir"); q.add_argument("--who")
    p.set_defaults(fn=cmd_know)

    p = sub.add_parser("fact"); fs = p.add_subparsers(dest="action", required=True)
    q = fs.add_parser("set"); q.add_argument("book_dir"); q.add_argument("key"); q.add_argument("value")
    q.add_argument("--ch", type=int, required=True); q.add_argument("--source"); q.add_argument("--category")
    q.add_argument("--override", action="store_true")
    q = fs.add_parser("get"); q.add_argument("book_dir"); q.add_argument("key")
    q = fs.add_parser("list"); q.add_argument("book_dir"); q.add_argument("--category")
    p.set_defaults(fn=cmd_fact)

    p = sub.add_parser("reader-now"); p.add_argument("book_dir"); p.add_argument("seq", type=int)
    p.add_argument("--top", type=int, default=5); p.set_defaults(fn=cmd_reader_now)
    p = sub.add_parser("sha"); p.add_argument("file"); p.set_defaults(fn=cmd_sha)

    a = ap.parse_args()
    a.fn(a)
    log_op(a)


READ_ONLY = {("status", None), ("next", None), ("report", None), ("sha", None), ("water", None),
             ("reader-now", None), ("scene", "check"), ("promise", "list"), ("know", "list"),
             ("fact", "get"), ("fact", "list"), ("feedback", "list"), ("team", "list"), ("unit", "list")}


def log_op(a):
    """团队交接用：每个成功的写操作追加一行到 06-台账/操作日志.jsonl。"""
    key = (a.cmd, getattr(a, "action", None))
    if key in READ_ONLY or (a.cmd, None) in READ_ONLY or a.cmd == "gate" and getattr(a, "action", "") == "check":
        return
    book = getattr(a, "book_dir", None)
    if not book or not (Path(book) / "book.json").exists():
        return
    p = Path(book) / OPLOG
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps({"at": now(), "actor": os.environ.get("NCC_ACTOR", ""),
                            "argv": sys.argv[1:]}, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
