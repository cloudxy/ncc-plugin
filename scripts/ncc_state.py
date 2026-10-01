#!/usr/bin/env python3
"""ncc_state.py — 书项目状态的确定性读写工具（书项目 schema 3；信息架构见 workflow/principles.md）。

状态只从这里（和经理派单回收）写入；视图（author-intent.md、current-focus.md、台账的 .md）由 render 生成，
脚本从不读视图当输入；正文永不回写状态。每次写操作后自动重新生成视图。
只依赖标准库。

书与闸门
  init <book> --title T [--genre a,b] [--chapters N] [--level 新手|熟手|老手] [--mode 建筑师|园丁|混合]
  status <book>                          状态摘要（退出码恒 0）
  next <book>                            第一个非 done 章（无则退出 1）
  migrate <book>                         旧书（schema 1、2）→ schema 3：按七律归位（.ncc/、_作者/、05-审稿/读者数据）
  render <book>                          重新生成全部视图
  check <book>                           七律自查：视图与源头逐字一致、状态事件只追加、旧布局残留、圣经里的数据
  gate <book> soul|settings|outline|opening|volume|finale [--action check|pass|reject] [--quote Q] [--force]
  level <book> 新手|熟手|老手             引导档位
  mode <book> 建筑师|园丁|混合            写作模式（D15）
  soul <book> [--question Q] [--answer A] [--injustice I] [--ending E] [--status 暂定|确定] [--deadline D] [--arc 正向|负向|平弧]
  contract <book> [--main M] [--extra X]... [--poison a,b] [--audience 目标读者]
  sign <book> <签约点> --ch N             签约点：主角与欲望|世界的不公|主角的机会|第一次小兑现|长线钩子

循环与收束（M3）
  unit open <book> --start N [--title T]   开一个剧情单元（10–40 章）
  unit close <book> --end N               关单元：须先有 00-策划/复盘/单元-Uk.md
  unit list <book>
  volume end <book> --end N               本卷写完，进入卷复盘（stage → volume），之后过 gate volume
  finale begin <book>                     进入收束（stage → finale），之后过 gate finale
  report <book> unit|volume|finale [--write]
                                         按台账生成复盘或收束清单的底稿；--write 写进对应文件的生成区块（判断写在区块外）
  feedback add <book> --ch N --source 真实|模拟 --kind 追读|弃读|略读|划线|评论|出戏 --value V [--note X] [--persona 画像]
  feedback list <book> [--ch N]
  team set <book> <位> <名字>              团队认领：主编|主笔|设定|考据|发展编辑|审稿|试读|拆书
  team list <book>

场景卡（先审故事，后写文字；小批量，D16）
  scene next <book>                      按写作模式给出下一批要做场景卡的章（混合 3、建筑师 5、园丁 2）
  scene check <book> <seq>               校验 02-大纲/场景卡/ch-NNNN.md 的格式
  scene review <book> <seq>... --result pass|revise --by story-editor|author [--note N]
                                         可一次审一批；关键章须 --by author；有一张不合格则整批不写入

底蕴（M4，D3：场景触发、有据可依）
  knowledge plan <book> <seq>...         列出场景卡"知识"一栏，判断这一批要不要派 scholar
  knowledge check <book> <seq>...        校验 02-大纲/知识点/ch-NNNN.md（学科、来源、状态）
  era <book> 古代|架空古代|近代|现代|架空现代|未来     时代背景（机械检查的时代错置词据此启用）
  study <book> [--add 学科]               一书一深学

素材（M5：艺术源于生活；场景卡写"素材：M-0003"，写手包自动带上）
  material add <book> --content C --source S --use U [--trust 亲历|转述|文献|传闻|拆书] [--domain 学科]
                      [--genre G] [--title T] [--shared]
                                         记一张素材卡到 素材/<八域>/M-NNNN-短名.md（--shared 记到书库根目录 _素材/，跨书共用）
  material list <book> [--domain 学科] [--unused]   素材索引（outliner 写场景卡时读这份，不读全部卡）
  material check <book>                  校验素材卡（来源、内容、可用处三项必填）

学习与嗓音（M6）
  style <book> --sample 文件或目录... | --from-chapters 1
                                         文风指纹 03-文风/文风指纹.json（数字只给审稿看）＋文风基准.md 模板＋校准段候选
  heat <book> [--ch A-B]                 读者画像热力：各画像追读、弃读与略读热点、划线、出戏
  pref show|like|confirm|reject|dislike <书目录或书库根目录> [--key K] [--value V] [--note N]
                                         偏好演化：权重按半衰期衰减；作者否决过的降权、不首推；雷点是硬约束
  craft init <book>                      完本后生成技艺库条目模板 _作者/技艺库/<书名>.md
  craft read <book> [--top N]            开书时读别的书的技艺库，挑出相关条目写进 00-策划/技艺库摘录.md

写手包与审稿（D17、D18）
  pack <book> <seq> [--note 本章特别提醒]   脚本组装写手包 .ncc/写手包/ch-NNNN.md（审稿文件与书魂原文一律不进）
  review plan <book> <seq>               本章该派谁审（continuity 必派；pulse 仅兑现章、关键章、开篇），并存一份正文快照
  review delta <book> <seq>              列出快照之后改动过的段落（复审只看这些），然后更新快照

章节
  chapter add <book> <seq> --file F [--key]      第 1–3 章默认为关键章
  chapter key <book> <seq> [--off]
  chapter hook <book> <seq> --type T --intensity 1-5 [--line L]
  chapter mark <book> <seq> <status>     pending|drafting|drafted|checking|reviewing|revising|failed
                                         （标 drafting 前，场景卡必须已过故事审且之后未改动）
  chapter mood <book> <seq> 压|放|平 [--colors 爽,燃,虐,甜,怕,笑,悲,敬,叹]
  chapter end <book> <seq> [--time T] [--place P] [--next 下一章要接的事]   续写状态卡的源头
  chapter pick <book> <seq> --version V [--note N]   关键章：作者从 2–3 版里选定
  chapter length <book> <seq> --accept [--force] [--tentative] [--note 作者原话]
                                         收下当前长度（字数不在区间时）。--tentative：写章循环里按推荐先收、单元复盘时作者确认；
                                         不到下限一半不能先收，要当场问作者（作者坚持收下用 --force）
  chapter length <book> <seq> --compressed   超长时 editor 已做过一次只删不加的压缩
  words <book> <seq> [--file F]          量字数：写完前半段量一次，告诉写手后半段还剩多少
  chapter retry <book> <seq>             重写计数 +1，达上限转 failed（只用于质量问题；字数不够不重写，交作者定）
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
  event add <book> --entity E --ch N --attr A [--old O] [--new N] [--reason R] [--evidence 定位词]
                                         状态事件（只追加；主角失去的东西 --attr 失去）
  event list <book> [--entity E]
  reader-now <book> <seq> [--top N]      生成上下文包的"读者此刻"块

书库与导出（M7）
  dashboard <书库根目录> [--bucket 10] [--html 文件]
                                         多书仪表盘：每本书的阶段、进度、存稿、承诺健康度，以及承诺热力图（每格 N 章里建立、推进、兑现的次数）
  export <book> [--format md|txt|epub] [--from N] [--to M] [--author A]
                                         合稿与导出到 07-导出/：只收已定稿的章；去掉修订注记；epub 为 EPUB 3（附 NCX 目录）

其他
  sha <file>

评测与模型横评见 scripts/ncc_eval.py。
环境变量 NCC_ACTOR：团队模式下写入操作日志（.ncc/操作日志.jsonl）的操作者名字。
"""
import argparse
import datetime
import hashlib
import html
import json
import os
import re
import statistics
import sys
import uuid
import zipfile
import tempfile
from pathlib import Path

SCHEMA = 3
PLUGIN_ROOT = Path(__file__).resolve().parent.parent

DIRS = [
    "00-策划", "00-策划/复盘", "01-设定/人物卡", "02-大纲/卷纲", "02-大纲/章纲", "02-大纲/场景卡",
    "02-大纲/知识点", "03-文风", "05-审稿", "06-台账", "07-导出", "memory", "素材", ".ncc/写手包",
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
READER_DATA = "05-审稿/读者数据.json"     # 读者的反馈是评价的一部分，不是世界状态
WORK = ".ncc"                             # 机器工作件：写手包、快照、横评、操作日志、迁移备份
PACK_DIR = f"{WORK}/写手包"
OPLOG = f"{WORK}/操作日志.jsonl"
AUTHOR_DIR = "_作者"                     # 书库根目录下：关于作者本人的跨书资产
CRAFT_LIBRARY = f"{AUTHOR_DIR}/技艺库"
INTENT_VIEW = "author-intent.md"          # 生成的视图（七律二）
FOCUS_VIEW = "current-focus.md"
LEDGER_VIEWS = {f"{LEDGER}/承诺台账.md": "promise", f"{LEDGER}/知情台账.md": "know", f"{LEDGER}/知识台账.md": "fact"}
OLD_BOOK_PATHS = (("04-正文/_packs", PACK_DIR), ("05-审稿/_snapshots", f"{WORK}/快照"), ("05-审稿/_bench", f"{WORK}/横评"),
                  ("06-台账/操作日志.jsonl", OPLOG), ("06-台账/读者数据.json", READER_DATA),
                  ("author-intent.md", f"{WORK}/迁移备份/author-intent.旧.md"),
                  ("current-focus.md", f"{WORK}/迁移备份/current-focus.旧.md"))

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
SCENE_KEY_REQUIRED = ("盲区", "阻碍", "画面", "风险", "默认写法")
SCENE_BATCH = {"建筑师": 5, "混合": 3, "园丁": 2}
PACK_BUDGET = 12000
SNAPSHOT_DIR = f"{WORK}/快照"
KNOW_DIR = "02-大纲/知识点"
DOMAINS = ("爽文", "人情冷暖", "社会", "心理", "历史与朝代更替", "政治", "经济", "军事", "天文", "地理", "生物", "自然",
           "物理", "化学", "数学", "工程", "建造", "工艺", "语言", "文学", "艺术", "视频", "想象力", "宗教神话民俗")
DOMAIN_ALIAS = {"人情": "人情冷暖", "历史": "历史与朝代更替", "朝代": "历史与朝代更替", "宗教": "宗教神话民俗",
                "神话": "宗教神话民俗", "民俗": "宗教神话民俗", "影视": "视频", "建筑": "建造", "医学": "生物", "医药": "生物",
                "气象": "自然", "历法": "天文", "称谓": "语言", "礼仪": "语言", "诗词": "文学", "音乐": "艺术", "书画": "艺术"}
ERAS = ("古代", "架空古代", "近代", "现代", "架空现代", "未来")
REGIONS = {"甲-爽感": ("爽文",), "乙-人间": ("人情冷暖", "社会", "心理"),
           "丙-天下": ("历史与朝代更替", "政治", "经济", "军事"), "丁-天地": ("天文", "地理", "生物", "自然"),
           "戊-物数": ("物理", "化学", "数学"), "己-造物": ("工程", "建造", "工艺"),
           "庚-表达": ("语言", "文学", "艺术", "视频"), "辛-想象": ("想象力", "宗教神话民俗")}
MATERIAL_DIR = "素材"
SHARED_MATERIALS = f"{AUTHOR_DIR}/素材"   # 书库根目录下，跨书共用，格式相同，编号前缀 MS
MATERIAL_REQUIRED = ("来源", "内容", "可用处")
MATERIAL_FIELDS = MATERIAL_REQUIRED + ("可信级", "域", "题材")
MATERIAL_TRUST = ("亲历", "转述", "文献", "传闻", "拆书")
MATERIAL_HINT = {"转述": "（转述自真人：人名、地名和能认出本人的细节都要换掉）",
                 "传闻": "（传闻：只能当人物口中的说法，叙述不当事实写）",
                 "拆书": "（拆书样本：只借写法，不搬内容）"}
STYLE_FP = "03-文风/文风指纹.json"      # 数字指纹：只给审稿与脚本看，不进写手包（铁律 9）
STYLE_ANCHOR = "03-文风/文风基准.md"    # 语感、校准段、负面清单：进写手包
STYLE_MIN = 10000                       # 旧文样本至少 1 万汉字（约 3 章）
PREFS = f"{AUTHOR_DIR}/偏好.json"
OLD_ROOT_PATHS = (("_preferences.json", PREFS), ("_素材", SHARED_MATERIALS), ("_craft-library", CRAFT_LIBRARY))
PREF_HALF_LIFE = 180
PREF_V1 = {"favoriteGenres": "题材", "preferredProtagonist": "主角", "preferredPerspective": "视角",
           "preferredTone": "基调", "styleReferences": "风格参考"}
CRAFT_EXCERPT = "00-策划/技艺库摘录.md"
HAN = re.compile(r"[一-鿿]")
WRITER_SEEDS = ("1", "3", "6")   # 画面、亲历、生活经验；#2"最在乎的问题"离主题太近，不进写手包
CHARACTER_REQUIRED = ("欲望", "需要", "恐惧", "声音")
UNIT_REVIEW_REQUIRED = ("暂定决策", "故事审", "下一单元")
VOLUME_REVIEW_REQUIRED = ("承诺盘点", "书魂检验", "数据归因", "变更提议")
FINALE_REQUIRED = ("承诺清算", "暗线收拢", "书魂回答")
TEAM_POSITIONS = ("主编", "主笔", "设定", "考据", "发展编辑", "审稿", "试读", "拆书")
FEEDBACK_SOURCES = ("真实", "模拟")
FEEDBACK_KINDS = ("追读", "弃读", "略读", "划线", "评论", "出戏")

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
    refs = material_refs(text)
    if refs:
        lost = [r for r in refs if r not in material_cards(book_dir)]
        if lost:
            problems.append(f"引用的素材卡不存在: {'、'.join(lost)}（material list 查编号）")
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
    if a.action == "next":
        size = SCENE_BATCH.get(d.get("mode", "混合"), 3)
        chs = d.get("chapters", [])
        pending = [c["seq"] for c in chs if c.get("status") != "done" and (c.get("scenes") or {}).get("review") != "passed"]
        start = pending[0] if pending else max([c["seq"] for c in chs] or [0]) + 1
        batch = list(range(start, start + size))
        print(f"下一批场景卡：第 {batch[0]}–{batch[-1]} 章（{d.get('mode', '混合')}模式一批 {size} 章）")
        missing = [n for n in batch if n not in {c["seq"] for c in chs}]
        if missing:
            print(f"  先登记：{missing}（chapter add）")
        keys = [c["seq"] for c in chs if c["seq"] in batch and c.get("key")]
        if keys:
            print(f"  其中关键章 {keys}：场景卡须写完整版，由作者过目")
        return
    seqs = a.seq if isinstance(a.seq, list) else [a.seq]
    if a.action == "check":
        bad = False
        for seq in seqs:
            c = find_ch(d, seq)
            problems, n = scene_problems(book_dir, seq, c.get("key", False))
            if problems:
                bad = True
                print(f"SCENE ch{seq}: FAIL")
                for p in problems:
                    print(f"  - {p}")
            else:
                print(f"SCENE ch{seq}: {n} 场，格式完整")
        sys.exit(1 if bad else 0)
    # review（整批校验通过才写入）
    if a.by not in ("story-editor", "author"):
        die("--by 只能是 story-editor 或 author")
    results, errors = [], []
    for seq in seqs:
        c = find_ch(d, seq)
        problems, n = scene_problems(book_dir, seq, c.get("key", False))
        if a.result == "pass":
            if problems:
                errors += [f"ch{seq}: {p}" for p in problems]
            if c.get("key") and a.by != "author":
                errors.append(f"ch{seq} 是关键章，场景卡须由作者过目（--by author）")
        results.append((c, n))
    if errors:
        print("SCENE: 整批未写入")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    for c, n in results:
        c["scenes"] = {"count": n, "review": "passed" if a.result == "pass" else "revise", "by": a.by,
                       "at": now(), "note": a.note or "", "sha": sha16(scene_path(book_dir, c["seq"]))}
    save(book_dir, d)
    done_list = "、".join("ch" + str(c[0]["seq"]) for c in results)
    print(f"OK 场景卡故事审: {done_list} → "
          f"{'passed' if a.result == 'pass' else 'revise'}（{a.by}）")


# ---------- 写手包与审稿计划（D17、D18） ----------

def section(text: str, title: str) -> str:
    m = re.search(rf"^##\s*{re.escape(title)}[^\n]*\n(.*?)(?=^##\s|\Z)", text, flags=re.M | re.S)
    return m.group(1).strip() if m else ""


def plain(text: str) -> str:
    return re.sub(r"^[#>*\-|`\s]+", "", text, flags=re.M)


def reader_now_lines(book_dir: Path, d: dict, seq: int, top: int = 5):
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
            f"{s_}{m['tension']}" + (f"（{'、'.join(m['colors'])}）" if m.get("colors") else "") for s_, m in moods))
        last_release = max((s_ for s_, m in moods if m["tension"] == "放"), default=None)
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
    return out


BRIEF_TAIL = ("两难里的两个选项都不完全对。把人物的选择演出来，不要替他解释，也不要让任何人（包括叙述者）说出这场的意义。"
              "从视角人物能感知到的写起；他不知道的事，叙述也不知道。"
              "情绪落在选择、台词、物件和后果上；身体反应只写有后果的（手一抖摔了杯子、信封被攥皱），"
              "不用指尖、指节、喉结、呼吸、心跳这类小动作去标注情绪。写完删掉解释情绪、复述前情、结尾点题的句子。")
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


def knowledge_points(card: str):
    pts = []
    for m in re.finditer(r"知识[：:]\s*([^\n]+)", card):
        pts += [x.strip() for x in re.split(r"[；;、,，]", m.group(1)) if x.strip() and x.strip() not in ("无", "——", "-")]
    return pts


def knowledge_path(book_dir: Path, seq: int) -> Path:
    return book_dir / KNOW_DIR / f"ch-{seq:04d}.md"


def normalize_domain(x: str):
    x = x.strip()
    return x if x in DOMAINS else DOMAIN_ALIAS.get(x)


def knowledge_rows(book_dir: Path, seq: int):
    p = knowledge_path(book_dir, seq)
    if not p.exists():
        return None
    rows = []
    for line in p.read_text("utf-8").splitlines():
        t = line.strip()
        if not t.startswith("|") or set(t) <= {"|", "-", " ", ":"}:
            continue
        cells = [c.strip() for c in t.strip("|").split("|")]
        if cells and cells[0] == "知识点":
            continue
        rows.append(cells)
    return rows


def knowledge_problems(book_dir: Path, seq: int):
    rows = knowledge_rows(book_dir, seq)
    if rows is None:
        return [f"缺知识点清单: {KNOW_DIR}/ch-{seq:04d}.md（格式见 skills/ncc/references/domains/README.md 第三节）"]
    if not rows:
        return ["知识点清单是空表"]
    problems = []
    for i, r in enumerate(rows, 1):
        if len(r) < 5:
            problems.append(f"第 {i} 行不足五栏（知识点｜学科｜写成什么｜来源｜状态）")
            continue
        point, dom, how, src, state = r[:5]
        if not normalize_domain(dom):
            problems.append(f"第 {i} 行「{point}」的学科「{dom}」不是 24 张卡之一")
        if state not in ("已核", "待核"):
            problems.append(f"第 {i} 行「{point}」的状态应为 已核 或 待核")
        elif state == "已核" and src in ("", "——", "-", "—"):
            problems.append(f"第 {i} 行「{point}」标了已核却没有来源")
        if not how:
            problems.append(f"第 {i} 行「{point}」缺\"写成什么\"")
        elif state == "待核" and re.search(r"\d|[一二两三四五六七八九十百千万半]+\s*(?:里|斤|两|年|月|天|日|夜|丈|尺|寸|度|公里|米|钱|文|贯|石|刻|时辰|人|兵|骑)", how):
            problems.append(f"第 {i} 行「{point}」是待核，写法里却有具体数字（宁缺律：改成可感的现象，如\"走到脚底起泡\"）")
    return problems


def knowledge_ready(book_dir: Path, seq: int):
    """场景卡标了知识点时，返回清单的问题；没标则返回空。"""
    card = scene_path(book_dir, seq)
    if not card.exists() or not knowledge_points(card.read_text("utf-8")):
        return []
    return knowledge_problems(book_dir, seq)


def cmd_knowledge(a):
    book_dir = Path(a.book_dir)
    d = load(book_dir)
    if a.action == "plan":
        need = []
        for seq in a.seq:
            find_ch(d, seq)
            card = scene_path(book_dir, seq)
            pts = knowledge_points(card.read_text("utf-8")) if card.exists() else []
            if pts:
                need.append(seq)
                print(f"第 {seq} 章：{'；'.join(pts)}")
            else:
                print(f"第 {seq} 章：场景卡没有标知识点")
        print(f"→ 派 scholar（一次）做第 {'、'.join(map(str, need))} 章的知识点清单" if need else "→ 这一批不派 scholar")
        return
    bad = False
    for seq in a.seq:
        problems = knowledge_problems(book_dir, seq)
        if problems:
            bad = True
            print(f"KNOWLEDGE ch{seq}: FAIL")
            for p in problems:
                print(f"  - {p}")
        else:
            rows = knowledge_rows(book_dir, seq)
            print(f"KNOWLEDGE ch{seq}: {len(rows)} 条，待核 {sum(1 for r in rows if r[4] == '待核')} 条")
    sys.exit(1 if bad else 0)


def cmd_era(a):
    if a.era not in ERAS:
        die(f"时代背景只能是 {'/'.join(ERAS)}")
    book_dir = Path(a.book_dir)
    d = ensure_m3_fields(load(book_dir))
    d["era"] = a.era
    save(book_dir, d)
    print(f"OK 时代背景={a.era}")


def cmd_study(a):
    book_dir = Path(a.book_dir)
    d = ensure_m3_fields(load(book_dir))
    if a.add:
        dom = normalize_domain(a.add)
        if not dom:
            die(f"「{a.add}」不是 24 张卡之一（见 skills/ncc/references/domains/README.md）")
        if dom not in d["study"]:
            d["study"].append(dom)
        save(book_dir, d)
    print("一书一深学：" + ("、".join(d["study"]) or "（未选）"))


# ---------- 素材（M5） ----------

def region_of(dom: str) -> str:
    return next((r for r, doms in REGIONS.items() if dom in doms), "未分")


def material_dirs(book_dir: Path):
    return [(book_dir / MATERIAL_DIR, "M"), (book_dir.parent / SHARED_MATERIALS, "MS")]


def material_cards(book_dir: Path) -> dict:
    """本书 素材/ 与书库根目录 _素材/ 里的全部素材卡：{编号: {path, title, 各字段}}。"""
    cards = {}
    for base, prefix in material_dirs(book_dir):
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*.md")):
            m = re.match(rf"({prefix}-\d{{4}})", p.stem)
            if not m:
                continue
            text = p.read_text("utf-8")
            head = re.search(r"^#\s*\S+\s*(.*)$", text, flags=re.M)
            card = {"path": p, "title": head.group(1).strip() if head else ""}
            for f in MATERIAL_FIELDS:
                mm = re.search(rf"^[-*]\s*{f}[：:][ \t]*(.*)$", text, flags=re.M)
                card[f] = mm.group(1).strip() if mm else ""
            cards[m.group(1)] = card
    return cards


def material_problems(card: dict) -> list:
    problems = [f"缺「{f}」" for f in MATERIAL_REQUIRED if card.get(f, "") in ("", "——", "-", "—")]
    if card.get("可信级") and card["可信级"] not in MATERIAL_TRUST:
        problems.append(f"可信级「{card['可信级']}」应为 {'/'.join(MATERIAL_TRUST)}")
    if card.get("域") and not normalize_domain(card["域"]):
        problems.append(f"域「{card['域']}」不是 24 张底蕴卡之一")
    return problems


def material_refs(text: str) -> list:
    refs = []
    for m in re.finditer(r"素材[：:]\s*([^\n]+)", text):
        refs += re.findall(r"MS?-\d{4}", m.group(1))
    return list(dict.fromkeys(refs))


def material_usage(book_dir: Path) -> dict:
    used = {}
    for p in sorted((book_dir / SCENE_DIR).glob("ch-*.md")):
        seq = int(re.search(r"(\d+)", p.stem).group(1))
        for r in material_refs(p.read_text("utf-8")):
            used.setdefault(r, []).append(seq)
    return used


def cmd_material(a):
    book_dir = Path(a.book_dir)
    load(book_dir)
    cards = material_cards(book_dir)
    if a.action == "add":
        dom = ""
        if a.domain:
            dom = normalize_domain(a.domain)
            if not dom:
                die(f"「{a.domain}」不是 24 张底蕴卡之一（见 skills/ncc/references/domains/README.md）")
        if a.trust and a.trust not in MATERIAL_TRUST:
            die(f"--trust 只能是 {'/'.join(MATERIAL_TRUST)}")
        base, prefix = material_dirs(book_dir)[1 if a.shared else 0]
        mid = next_id([{"id": k} for k in cards], prefix)
        first = a.title or re.split(r"[，。、！？；：,.!?;:\s]", a.content.strip())[0]
        title = re.sub(r"[\\/:*?\"<>|\s，。、！？；：]+", "", first)[:16] or "素材"
        dest = base / region_of(dom) / f"{mid}-{title}.md"
        lines = [f"# {mid} {title}", "", f"- 来源：{a.source}", f"- 内容：{a.content}", f"- 可用处：{a.use}"]
        lines += [f"- {k}：{v}" for k, v in (("可信级", a.trust), ("域", dom), ("题材", a.genre)) if v]
        lines.append(f"- 记录于：{now()[:10]}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("\n".join(lines) + "\n", "utf-8")
        print(f"OK {mid} → {dest.relative_to(base.parent)}")
        return
    used = material_usage(book_dir)
    if a.action == "list":
        for mid, c in cards.items():
            if a.domain and normalize_domain(c.get("域", "")) != normalize_domain(a.domain):
                continue
            if a.unused and mid in used:
                continue
            where = f"  已用：第{'、'.join(map(str, used[mid]))}章" if mid in used else ""
            print(f"{mid} [{c.get('域') or '未分'}] 可用处：{c.get('可用处')}｜{c.get('内容', '')[:30]}"
                  + (f"（{c['可信级']}）" if c.get("可信级") else "") + where)
        if not cards:
            print("（还没有素材卡：material add，或从作者种子 #3、#6 起头）")
        elif a.unused and all(k in used for k in cards):
            print("（素材卡都用过了）")
        return
    bad = 0
    for mid, c in cards.items():
        problems = material_problems(c)
        if problems:
            bad += 1
            print(f"MATERIAL {mid}: FAIL（{c['path'].name}）")
            for p in problems:
                print(f"  - {p}")
    ok = len(cards) - bad
    print(f"素材卡 {len(cards)} 张，合格 {ok} 张，场景卡已引用 {len([k for k in cards if k in used])} 张"
          + ("；开写前建议至少 10 张（作者种子 #3、#6 和生活里的观察都可以记）" if ok < 10 else ""))
    sys.exit(1 if bad else 0)


def cmd_pack(a):
    book_dir = Path(a.book_dir)
    d = load(book_dir)
    c = find_ch(d, a.seq)
    why = scene_ready(book_dir, c)
    if why:
        die(f"不能组装写手包：{why}")
    card = scene_path(book_dir, a.seq).read_text("utf-8")
    blocks = re.split(r"^##\s*场景", card, flags=re.M)[1:]
    out = [f"# 第 {a.seq} 章 写手包", "", "> 由 ncc_state.py pack 组装。阅读顺序：写作简报 → 读者此刻 → 人物声音 → 可用材料 → 前情 → 前一章结尾 → 文风基准。", ""]

    out += ["## 写作简报", ""]
    for i, b in enumerate(blocks, 1):
        body = b.split("\n", 1)[1] if "\n" in b else ""
        out += [f"### 场景 {i}", body.strip()]
        if "默认写法" in body:
            out.append("- 上面\"默认写法\"列的是这场最容易想到的走法：不要这样写。")
        if c.get("key") and "关键节拍" in body:
            out.append("- 关键节拍写 2–3 个版本，彼此走法不同，存到 04-正文/_versions/，不要自己挑。")
        out += [f"- {BRIEF_TAIL}", ""]
    lo, hi, _ = length_band(book_dir, a.seq)
    out += ["### 篇幅", f"- 本章 {lo}–{hi} 字。分两段写：先把前半段（写到一个自然转场处）写进正文文件，"
            f"跑一次 `python3 {Path(__file__).resolve()} words {book_dir.resolve()} {a.seq}`，它会告诉你后半段大约还要多少字；"
            "再接着写后半段。只量这一次，不回头改前半段去追字数。",
            "- 简报里的事写完就停：不为凑字数加情节、加人物、加设定。写短了照实交回，由作者决定收不收。", ""]
    if a.note:
        out += ["### 经理的特别提醒（只写意图与材料）", a.note, ""]

    out += reader_now_lines(book_dir, d, a.seq) + [""]

    rows = knowledge_rows(book_dir, a.seq)
    if rows:
        out += ["## 本章知识点（scholar 已查；写成什么就照这个方向写）", ""]
        for r in rows:
            if len(r) >= 5:
                tail = "（待核：不写具体数字和术语，写可感的现象）" if r[4] == "待核" else ""
                out.append(f"- {r[0]}：{r[2]}{tail}")
        out.append("")

    out += ["## 人物声音", ""]
    names = []
    for p in sorted((book_dir / "01-设定" / "人物卡").glob("*.md")):
        if p.stem.endswith("-采访") or p.stem not in card:
            continue
        names.append(p.stem)
        t = p.read_text("utf-8")
        out.append(f"### {p.stem}")
        for sec in ("欲望", "恐惧", "声音"):
            v = section(t, sec)
            if v:
                out.append(f"- {sec}：{v}")
        out.append("")
    if not names:
        out += ["（场景卡里没有出现已建卡的人物名）", ""]

    out += ["## 可用材料", ""]
    seeds = book_dir / SEEDS
    if seeds.exists():
        for line in seeds.read_text("utf-8").splitlines():
            m = re.match(r"^\|\s*(\d+)\s*\|[^|]*\|\s*([^|]+?)\s*\|", line)
            if m and m.group(1) in WRITER_SEEDS and m.group(2).strip():
                out.append(f"- 作者种子 #{m.group(1)}：{m.group(2).strip()}")
    mats = material_cards(book_dir)
    for r in material_refs(card):
        if r in mats:
            m = mats[r]
            out.append(f"- 素材 {r}：{m['内容']}（可用在：{m['可用处']}）{MATERIAL_HINT.get(m.get('可信级'), '')}")
    facts = read_json(book_dir / FACTS, {"facts": {}}).get("facts", {})
    for k, f in facts.items():
        if k in card:
            out.append(f"- {k} = {f['value']}（知识台账）")
    lex = book_dir / "01-设定" / "设定词典.md"
    if lex.exists():
        rows = [[x.strip() for x in line.strip().strip("|").split("|")] for line in lex.read_text("utf-8").splitlines()
                if line.strip().startswith("|") and not set(line.strip()) <= {"|", "-", " ", ":"}]
        head = rows[0] if rows else []
        col = head.index("读者已知") if "读者已知" in head else None
        for r in rows[1:]:
            if r and r[0] and r[0] in card:
                known = r[col] if col is not None and col < len(r) else ""
                out.append(f"- {r[0]}：读者目前知道「{known or '（未登记）'}」（设定词典；完整真相不进写手包）")
    out.append("")

    out += ["## 前情", ""] + focus_core(book_dir, d, a.seq) + [""]
    prev = next((x for x in d.get("chapters", []) if x["seq"] == a.seq - 1), None)
    if prev and (book_dir / prev.get("file", "")).is_file():
        tail = plain((book_dir / prev["file"]).read_text("utf-8")).strip()[-800:]
        out += ["## 前一章结尾（原文）", "", tail, ""]
    style = book_dir / "03-文风" / "文风基准.md"
    if style.exists() and style.read_text("utf-8").strip():
        out += ["## 文风基准（最后读）", "", style.read_text("utf-8").strip(), ""]

    text = "\n".join(out)
    soul = d.get("soul", {})
    leaks = [v for v in (soul.get("question"), soul.get("answer"), soul.get("injustice"), soul.get("ending"))
             if v and len(v) >= 6 and v in text]
    if leaks:
        die("写手包里出现了书魂原文（多半写进了场景卡）：" + "；".join(leaks) + "。书魂不进写手提示，请改场景卡后重审。")
    size = len(re.findall(r"[\u4e00-\u9fff]", text))
    dest = book_dir / PACK_DIR / f"ch-{a.seq:04d}.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text + "\n", "utf-8")
    c["pack"] = str(dest.relative_to(book_dir))
    save(book_dir, d)
    print(f"OK 写手包 {c['pack']}（{size} 字" + (f"，超过预算 {PACK_BUDGET}，请删减材料" if size > PACK_BUDGET else "") + "）")


def chapter_file(book_dir: Path, c: dict) -> Path:
    p = book_dir / c.get("file", "")
    if not p.is_file():
        die(f"找不到第 {c['seq']} 章正文：{c.get('file')}")
    return p


def cmd_words(a):
    """量字数。写前半段后量一次，给出后半段还剩多少（只量这一次，不据此回改前半段）。"""
    book_dir = Path(a.book_dir)
    d = load(book_dir)
    c = find_ch(d, a.seq)
    p = Path(a.file) if a.file else chapter_file(book_dir, c)
    if not p.is_file():
        die(f"找不到文件：{p}")
    n = han_words(p.read_text("utf-8"))
    lo, hi, src = length_band(book_dir, a.seq)
    print(f"第 {a.seq} 章现在 {n} 字；本章区间 {lo}–{hi} 字（来自{src}）")
    if n < lo:
        print(f"后半段大约还要 {lo - n}–{hi - n} 字。照简报写完就停，不为凑字数加内容。")
    elif n <= hi:
        print(f"已在区间内；后半段最多还能写 {hi - n} 字，简报里的事写完就停。")
    else:
        print(f"已超出上限 {n - hi} 字：后半段只收尾，不再展开。")


def paragraphs(text: str):
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def cmd_review(a):
    book_dir = Path(a.book_dir)
    d = load(book_dir)
    c = find_ch(d, a.seq)
    body = book_dir / c.get("file", "")
    if not body.is_file():
        die(f"找不到第 {a.seq} 章正文：{c.get('file')}")
    snap = book_dir / SNAPSHOT_DIR / f"ch-{a.seq:04d}.md"
    if a.action == "plan":
        items = ledger(book_dir, PROMISES)["items"]
        payoff = [p["id"] for p in items if p.get("resolved_ch") == a.seq and p.get("type") in ("爽点欠账", "名场面")]
        reasons = []
        if c.get("key"):
            reasons.append("关键章（另做成对比较）")
        if a.seq <= 3:
            reasons.append("开篇（查签约点）")
        if payoff:
            reasons.append(f"本章兑现 {payoff}（查欠·挣·超·证）")
        print(f"第 {a.seq} 章审稿计划：continuity 必派（硬伤层，含契约与毒点）")
        print("  pulse：" + ("派——" + "；".join(reasons) if reasons else "不派（常规章、无兑现）"))
        snap.parent.mkdir(parents=True, exist_ok=True)
        snap.write_text(body.read_text("utf-8"), "utf-8")
        print(f"  已存正文快照：{snap.relative_to(book_dir)}（修订后用 review delta 只看改动）")
        return
    # delta
    if not snap.exists():
        die("没有快照：先 review plan")
    old, new = paragraphs(snap.read_text("utf-8")), paragraphs(body.read_text("utf-8"))
    old_set = set(old)
    changed = [(i, p) for i, p in enumerate(new, 1) if p not in old_set]
    removed = len([p for p in old if p not in set(new)])
    if not changed and not removed:
        print(f"第 {a.seq} 章：快照之后没有改动")
    else:
        print(f"第 {a.seq} 章改动：{len(changed)} 段新增或修改，{removed} 段删除。复审只看这些段落与上次不通过的项：")
        for i, p in changed:
            print(f"\n[第 {i} 段]\n{p}")
    snap.write_text(body.read_text("utf-8"), "utf-8")


# ---------- M3：单元、卷、读者数据、团队 ----------

def ensure_m3_fields(d: dict):
    """v0.3 及更早建的书补齐 M3 字段。"""
    d.setdefault("units", [])
    d.setdefault("volumes", [{"n": 1, "start": 1, "end": None, "status": "open"}])
    d.setdefault("published_upto", 0)
    d.setdefault("team", {})
    d.setdefault("era", "")
    d.setdefault("study", [])
    return d


def open_unit(d):
    return next((u for u in d.get("units", []) if u.get("status") == "open"), None)


def open_volume(d):
    return next((v for v in d.get("volumes", []) if v.get("status") in ("open", "reviewing")), None)


def has_sections(p: Path, needed) -> list:
    """复盘与收束文件：只看生成区块之外（作者与角色写的判断），区块里的数据不算回答。"""
    if not p.exists() or not p.read_text("utf-8").strip():
        return [f"缺文件或为空: {p.name}"]
    text = outside_block(p.read_text("utf-8"))
    problems = [f"{p.name} 缺「{x}」一节" for x in needed if x not in text]
    if "（待填）" in text:
        problems.append(f"{p.name} 还有「（待填）」没写")
    return problems


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
            print(f"第{f['ch']}章 [{f['source']}{'·' + f['persona'] if f.get('persona') else ''}] "
                  f"{f['kind']}={f['value']}  {f.get('note', '')}")
        return
    if a.source not in FEEDBACK_SOURCES:
        die(f"--source 只能是 {'/'.join(FEEDBACK_SOURCES)}")
    if a.kind not in FEEDBACK_KINDS:
        die(f"--kind 只能是 {'/'.join(FEEDBACK_KINDS)}")
    item = {"ch": a.ch, "source": a.source, "kind": a.kind, "value": a.value, "note": a.note or "", "at": now()}
    if a.persona:
        item["persona"] = a.persona
    data["items"].append(item)
    write_json(book_dir / READER_DATA, data)
    print(f"OK 第{a.ch}章 {a.source}{'·' + a.persona if a.persona else ''} {a.kind}={a.value}")


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
        target = f"{REVIEW_DIR}/单元-{u['id']}.md"
        human = ("暂定决策", "故事审", "下一单元")
    elif a.kind == "volume":
        v = open_volume(d)
        if not v:
            die("没有进行中的卷")
        lo, hi, title = v["start"], v.get("end") or cur, f"第{v['n']}卷 卷复盘（第{v['start']}–{v.get('end') or cur}章）"
        target = f"{REVIEW_DIR}/卷{v['n']}.md"
        human = VOLUME_REVIEW_REQUIRED
    else:
        lo, hi, title = 1, cur, "收束清单"
        target, human = FINALE_LIST, FINALE_REQUIRED
    chs = range_chapters(d, lo, hi)
    out = [f"# {title}", "", f"> 由 `ncc_state.py report {a.kind}` 从台账生成的数据与要回答的问题；"
           "回答与决定写在本区块外对应的小节里（区块会随数据刷新）。", ""]

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
        sim = {}
        for f in seg_fb:
            if f["source"] == "模拟" and f["kind"] == "追读":
                v = f"{f['value']}（{f['persona']}）" if f.get("persona") else str(f["value"])
                sim[f["ch"]] = f"{sim[f['ch']]}／{v}" if f["ch"] in sim else v
        real = {f["ch"]: f["value"] for f in seg_fb if f["source"] == "真实" and f["kind"] == "追读"}
        both = sorted(set(sim) & set(real))
        if both:
            out += ["", "**模拟读者校准**（同一章的模拟追读 vs 真实追读）", ""]
            out += [f"- 第{ch}章：模拟 {sim[ch]}｜真实 {real[ch]}" for ch in both]
            out += ["- 偏差规律（待填）：模拟读者在哪类章节高估或低估？写进 reader 的校准备注"]
    if a.kind in ("unit", "volume"):
        pend_rows = [(c["seq"], r) for c in chs for r in (knowledge_rows(book_dir, c["seq"]) or []) if len(r) >= 5 and r[4] == "待核"]
        out += ["", "## 待核知识点（请作者核实，或维持宁缺写法）", ""]
        out += [f"- 第{seq}章 {r[0]}（{r[1]}）：{r[2]}" for seq, r in pend_rows] or ["- （无）"]
        odd = [c for c in chs if (c.get("length") or {}).get("accepted") is not None]
        out += ["", "## 篇幅（字数不在区间、已收下的章；按推荐先收的请作者确认）", ""]
        out += [f"- 第{c['seq']}章 {c['length']['accepted']} 字（区间 {c['length']['band'][0]}–{c['length']['band'][1]}）"
                + ("，按推荐先收，待你确认" if c["length"].get("by") == "recommendation" else "，你已收下")
                + (f"：{c['length']['note']}" if c["length"].get("note") else "") for c in odd] or ["- （无）"]
        mats, used = material_cards(book_dir), material_usage(book_dir)
        seg = {r: [s for s in seqs if lo <= s <= hi] for r, seqs in used.items()}
        seg = {r: s for r, s in seg.items() if s}
        idle = [r for r in mats if r not in used]
        out += ["", "## 素材", ""]
        out.append("- 本段用到：" + "；".join(f"{r}（第{'、'.join(map(str, s))}章）" for r, s in seg.items())
                   if seg else "- 本段场景卡没有引用素材")
        out.append(f"- 素材库共 {len(mats)} 张，从未用过 {len(idle)} 张" + (f"：{'、'.join(idle[:10])}" if idle else "")
                   + "（outliner 排下一单元时可以挑；作者这段时间新看到、新想到的，随时 material add）")
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
        by_dom, pend = {}, {}
        for c in chs:
            for r in knowledge_rows(book_dir, c["seq"]) or []:
                if len(r) >= 5:
                    dom = normalize_domain(r[1]) or r[1]
                    by_dom[dom] = by_dom.get(dom, 0) + 1
                    if r[4] == "待核":
                        pend[dom] = pend.get(dom, 0) + 1
        slips = {}
        for f in fb:
            if f.get("kind") == "出戏" and lo <= f.get("ch", -1) <= hi:
                slips.setdefault(normalize_domain(str(f["value"])) or str(f["value"]), []).append(f"第{f['ch']}章 {f.get('note', '')}".strip())
        out += ["", "## 底蕴", "", f"- 一书一深学：{'、'.join(d.get('study', [])) or '（未选）'}"]
        out += [f"- {k}：知识点 {v} 条，待核 {pend.get(k, 0)} 条" + (f"；出戏 {len(slips[k])} 处" if k in slips else "")
                for k, v in sorted(by_dom.items(), key=lambda x: -x[1])] or ["- （本卷没有知识点清单）"]
        out += [f"- {k}（无知识点清单）：出戏 {len(v)} 处——{'；'.join(v)}" for k, v in slips.items() if k not in by_dom]
        out += ["- 补学清单（待填）：按 domains/reading-list.md 第二节，挑知识点最多或出戏最多的学科"]
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
    if a.write:
        skeleton = "\n\n".join(f"## {h}\n\n（待填）" for h in human) + "\n"
        write_block(book_dir / target, "\n".join(out), skeleton)
        print(f"OK 底稿已写进 {target} 的生成区块；回答与决定写在区块外的「{'」「'.join(human)}」各节")
        return
    print("\n".join(out))


# ---------- M6：文风指纹 ----------

def style_metrics(text: str) -> dict:
    """可复算的文风指纹：句长、段长、对话占比、人称、标点习惯。只给审稿与脚本用。"""
    body = re.sub(r"^[#>*\-|`\s]+", "", text, flags=re.M)
    han = len(HAN.findall(body))
    lens = [len(HAN.findall(s)) for s in re.split(r"[。！？!?…\n]+", body) if HAN.search(s)]
    plens = [len(HAN.findall(p)) for p in body.splitlines() if HAN.search(p)]
    quoted = "".join(re.findall(r"[“「『\"]([^”」』\"]*)[”」』\"]", body))
    narr = re.sub(r"[“「『\"][^”」』\"]*[”」』\"]", "", body)
    mean = statistics.mean(lens) if lens else 0
    k = max(han / 1000, 1)
    return {
        "han": han,
        "sentence_mean": round(mean, 1),
        "sentence_cv": round(statistics.pstdev(lens) / mean, 2) if mean else 0,
        "short_share": round(sum(1 for n in lens if n <= 8) / len(lens), 2) if lens else 0,
        "long_share": round(sum(1 for n in lens if n >= 40) / len(lens), 2) if lens else 0,
        "paragraph_mean": round(statistics.mean(plens), 1) if plens else 0,
        "dialogue_share": round(len(HAN.findall(quoted)) / han, 2) if han else 0,
        "person": "第一人称" if narr.count("我") > narr.count("他") + narr.count("她") else "第三人称",
        "per_1000": {p: round(body.count(p) / k, 1) for p in ("——", "……", "！", "？")},
    }


def style_drift_lines(book_dir: Path, text: str) -> list:
    """本章与文风指纹的偏离（只作参考，交审稿判断是否"文风明显漂移"）。"""
    fp = read_json(book_dir / STYLE_FP, None)
    if not fp:
        return []
    m = style_metrics(text)
    tag = "" if fp.get("enough") else "（指纹样本不足 1 万字，只作参考）"
    out = []
    if fp.get("sentence_mean") and abs(m["sentence_mean"] - fp["sentence_mean"]) > fp["sentence_mean"] * 0.35:
        out.append(f"文风：平均句长 {m['sentence_mean']} 字，指纹 {fp['sentence_mean']} 字{tag}")
    if fp.get("paragraph_mean") and abs(m["paragraph_mean"] - fp["paragraph_mean"]) > fp["paragraph_mean"] * 0.6:
        out.append(f"文风：平均段长 {m['paragraph_mean']} 字，指纹 {fp['paragraph_mean']} 字{tag}")
    if abs(m["dialogue_share"] - fp.get("dialogue_share", 0)) > 0.2:
        out.append(f"文风：对话占比 {m['dialogue_share']}，指纹 {fp.get('dialogue_share')}{tag}")
    if fp.get("person") and m["person"] != fp["person"]:
        out.append(f"文风：人称像是{m['person']}，指纹是{fp['person']}{tag}")
    return out


def sample_files(paths) -> list:
    files = []
    for s in paths:
        p = Path(os.path.expanduser(s))
        if p.is_dir():
            files += sorted(x for x in p.rglob("*") if x.suffix in (".md", ".txt"))
        elif p.is_file():
            files.append(p)
        else:
            die(f"找不到样本：{s}")
    return files


def cmd_style(a):
    book_dir = Path(a.book_dir)
    d = ensure_m3_fields(load(book_dir))
    if a.from_chapters:
        lo, hi = parse_window(a.from_chapters) if re.search(r"[-~～至]", a.from_chapters) else (int(a.from_chapters),) * 2
        files = [book_dir / c["file"] for c in range_chapters(d, lo, hi) if c.get("status") == "done"]
        if not files:
            die(f"第 {lo}–{hi} 章还没有定稿的正文，不能反推")
        source = f"本书第{lo}–{hi}章" if lo != hi else f"本书第{lo}章"
    elif a.sample:
        files, source = sample_files(a.sample), "旧文样本"
    else:
        die("给 --sample <作者旧文的文件或目录>，或 --from-chapters 1（没有旧文时，第 1 章定稿后反推）")
    texts = [(f, f.read_text("utf-8", errors="ignore")) for f in files]
    m = style_metrics("\n".join(t for _, t in texts))
    enough = m["han"] >= STYLE_MIN or source != "旧文样本"
    fp = {"source": source, "files": [f.name for f in files], "enough": enough, "at": now(), **m}
    write_json(book_dir / STYLE_FP, fp)
    anchor = book_dir / STYLE_ANCHOR
    copy_template("style-anchor.md", anchor)
    d["style"] = {"source": source, "han": m["han"], "at": fp["at"]}
    save(book_dir, d)
    print(f"OK 文风指纹 {STYLE_FP}（{source}，{m['han']} 字"
          + ("" if enough else f"，不足 {STYLE_MIN} 字：指纹只作参考，第 1 章定稿后可再用 --from-chapters 1 补") + "）")
    print(f"  句长 {m['sentence_mean']} 字（起伏 {m['sentence_cv']}），段长 {m['paragraph_mean']} 字，"
          f"对话占比 {m['dialogue_share']}，{m['person']}")
    cands = []
    for f, t in texts:
        for i, para in enumerate((x.strip() for x in t.splitlines() if HAN.search(x)), 1):
            n = len(HAN.findall(para))
            if 150 <= n <= 400 and para[0] not in "“「『\"":
                sm = style_metrics(para)["sentence_mean"]
                cands.append((abs(sm - m["sentence_mean"]), f.name, i, para))
    cands.sort(key=lambda x: x[0])
    if cands:
        print("  校准段候选（句长最接近整体的叙述段，worldbuilder 从中挑 2–3 段、作者确认后写进 文风基准.md）：")
        for _, name, i, para in cands[:5]:
            print(f"  - {name} 第{i}段：{para[:30]}……")


# ---------- M6：读者画像热力 ----------

def cmd_heat(a):
    book_dir = Path(a.book_dir)
    d = load(book_dir)
    lo, hi = parse_window(a.ch) if a.ch else (1, max([c["seq"] for c in d.get("chapters", [])] or [1]))
    fb = [f for f in ledger(book_dir, READER_DATA)["items"] if lo <= f.get("ch", -1) <= hi]
    who = lambda f: f.get("persona") or ("真实读者" if f.get("source") == "真实" else "模拟（未标画像）")
    people = list(dict.fromkeys(who(f) for f in fb))
    out = [f"# 读者热力（第{lo}–{hi}章）", ""]
    follow = [f for f in fb if f["kind"] == "追读"]
    if follow:
        out += ["## 追读", "", "| 章 | " + " | ".join(people) + " |", "|---|" + "---|" * len(people)]
        for ch in sorted({f["ch"] for f in follow}):
            row = {who(f): str(f["value"]) for f in follow if f["ch"] == ch}
            out.append(f"| 第{ch}章 | " + " | ".join(row.get(p, "—") for p in people) + " |")
        out.append("")
    for kinds, title in ((("弃读", "略读"), "弃读与略读热点（越多画像在同一段失去耐心，越要先改）"), (("划线",), "划线")):
        spots = {}
        for f in fb:
            if f["kind"] in kinds:
                m = re.search(r"\d+", str(f["value"]))
                spots.setdefault((f["ch"], int(m.group()) if m else 0), []).append(f"{f['kind']}·{who(f)}")
        out += [f"## {title}", ""]
        for (ch, para), hits in sorted(spots.items(), key=lambda x: (-len(x[1]), x[0])):
            out.append(f"- 第{ch}章 " + (f"第{para}段" if para else "（未标段落）") + f"：{'█' * len(hits)} {len(hits)}（{'、'.join(hits)}）")
        if not spots:
            out.append("- （无）")
        out.append("")
    slips = [f for f in fb if f["kind"] == "出戏"]
    if slips:
        out += ["## 出戏（懂行读者）", ""] + [f"- 第{f['ch']}章 {f['value']}：{f.get('note', '')}（{who(f)}）" for f in slips]
    print("\n".join(out))


# ---------- M6：偏好演化 ----------

def pref_file(p: Path) -> Path:
    return (p.parent if (p / "book.json").exists() else p) / PREFS


def pref_load(path: Path) -> dict:
    raw = read_json(path, {})
    if raw.get("version") == 2:
        return raw
    data = {"version": 2, "items": [], "dislikes": list(raw.get("dislikes", [])), "rejected": [],
            "settings": {}, "creationHistory": raw.get("creationHistory", [])}
    for k, v in raw.items():
        if k in ("dislikes", "creationHistory", "version"):
            continue
        if k not in PREF_V1:
            data["settings"][k] = v
            continue
        for x in v if isinstance(v, list) else [v]:
            name, w = (x.get("name"), x.get("weight", 1)) if isinstance(x, dict) else (x, 1)
            data["items"].append({"key": PREF_V1[k], "value": name, "weight": w, "last": now()})
    return data


def pref_half_life(path: Path) -> int:
    for cfg in (path.parent.parent / "ncc.config.yaml", path.parent.parent.parent / "ncc.config.yaml"):
        if cfg.exists():
            m = re.search(r"half_life_days:\s*(\d+)", cfg.read_text("utf-8"))
            if m:
                return int(m.group(1))
    return PREF_HALF_LIFE


def pref_effective(item: dict, half_life: int) -> float:
    age = (datetime.datetime.now() - datetime.datetime.fromisoformat(item.get("last") or now())).days
    return item["weight"] * 0.5 ** (max(age, 0) / half_life)


def cmd_pref(a):
    path = pref_file(Path(a.path))
    data = pref_load(path)
    hl = pref_half_life(path)
    if a.action == "show":
        rejected = {(r["key"], r["value"]): r for r in data["rejected"]}
        keys = [a.key] if a.key else list(dict.fromkeys(i["key"] for i in data["items"]))
        for key in keys:
            items = sorted((i for i in data["items"] if i["key"] == key), key=lambda i: -pref_effective(i, hl))
            line = []
            for i in items:
                eff = pref_effective(i, hl)
                flag = "（作者否决过，不首推）" if (key, i["value"]) in rejected else ("⭐" if eff >= 2 else "")
                line.append(f"{i['value']} {eff:.1f}{flag}")
            print(f"{key}：" + "；".join(line))
        if data["dislikes"]:
            print("雷点（硬约束，不衰减）：" + "、".join(data["dislikes"]))
        for r in data["rejected"]:
            if not a.key or r["key"] == a.key:
                print(f"否决记录：{r['key']}「{r['value']}」{r['at'][:10]} {r.get('note', '')}")
        print(f"（权重按半衰期 {hl} 天衰减；作者确认过的会重新计时）")
        return
    if a.action == "dislike":
        if a.value not in data["dislikes"]:
            data["dislikes"].append(a.value)
        write_json(path, data)
        print(f"OK 雷点「{a.value}」")
        return
    if not a.key:
        die("--key 必填（如 题材、主契约、主角、视角、基调、风格参考、写作模式、金手指、力量体系）")
    item = next((i for i in data["items"] if i["key"] == a.key and i["value"] == a.value), None)
    if not item:
        item = {"key": a.key, "value": a.value, "weight": 0, "last": now()}
        data["items"].append(item)
    if a.action == "reject":
        if not (a.note or "").strip():
            die("否决要写 --note（为什么不要，下次推荐时避开的就是这一点）")
        item["weight"] -= 2
        data["rejected"].append({"key": a.key, "value": a.value, "at": now(), "note": a.note})
    else:
        item["weight"] += 2 if a.action == "confirm" else 1
        if a.action == "confirm":
            item["confirmed"] = now()
        before = len(data["rejected"])
        data["rejected"] = [r for r in data["rejected"] if (r["key"], r["value"]) != (a.key, a.value)]
        if len(data["rejected"]) < before:
            print(f"  （作者改了主意：撤销对「{a.value}」的否决记录）")
    item["last"] = now()
    write_json(path, data)
    print(f"OK {a.action} {a.key}「{a.value}」权重 {item['weight']}")


def pref_note_book(book_dir: Path, title: str, genre: list):
    path = pref_file(book_dir)
    data = pref_load(path)
    data["creationHistory"] = (data["creationHistory"] + [{"title": title, "genre": "、".join(genre), "at": now()}])[-50:]
    write_json(path, data)


# ---------- M6：技艺库回灌 ----------

def craft_entries(p: Path):
    rows = []
    for line in p.read_text("utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.strip().startswith("|") else []
        if len(cells) >= 5 and re.fullmatch(r"\d+", cells[0]) and cells[1]:
            rows.append({"n": cells[0], "entry": cells[1], "evidence": cells[2], "when": cells[3], "tags": cells[4]})
    return rows


def book_terms(d: dict) -> list:
    ct = d.get("contract", {})
    raw = list(d.get("genre_tags", [])) + re.split(r"[＋+、,，/\s]", ct.get("main", "")) + list(ct.get("extras", []))
    raw += [d.get("soul", {}).get("arc", ""), d.get("mode", "")]
    return [t for t in dict.fromkeys(x.strip() for x in raw) if len(t) >= 2]


def cmd_craft(a):
    book_dir = Path(a.book_dir)
    d = load(book_dir)
    lib = book_dir.parent / CRAFT_LIBRARY
    if a.action == "init":
        dest = lib / f"{d.get('title')}.md"
        if dest.exists():
            die(f"已存在：{dest}")
        tpl = (PLUGIN_ROOT / "skills/ncc/templates/craft-entry.md").read_text("utf-8")
        ct, soul = d.get("contract", {}), d.get("soul", {})
        tpl = (tpl.replace("{书名}", d.get("title", "")).replace("{题材}", "、".join(d.get("genre_tags", [])))
               .replace("{主契约}", ct.get("main", "")).replace("{弧光}", soul.get("arc", "")).replace("{写作模式}", d.get("mode", "")))
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(tpl, "utf-8")
        print(f"OK 技艺库条目模板 {CRAFT_LIBRARY}/{dest.name}（全书复盘后填，每条一句话＋证据＋适用条件＋标签）")
        return
    terms = book_terms(d)
    hits, others = [], {}
    for p in sorted(lib.glob("*.md")) if lib.is_dir() else []:
        if p.stem == d.get("title"):
            continue
        for r in craft_entries(p):
            generic = r["when"] in ("", "通用", "—", "——", "-")
            why = ["通用"] if generic else [t for t in terms if t in f"{r['when']} {r['tags']}"]
            if why:
                hits.append((len(why), p.stem, r, why))
            else:
                others[p.stem] = others.get(p.stem, 0) + 1
    if not hits and not others:
        print("技艺库里还没有别的书的条目（第一本书不需要这一步）")
        return
    hits.sort(key=lambda x: -x[0])
    out = ["# 技艺库摘录（开书时读，M6-4）", "",
           f"> 由 ncc_state.py craft read 生成。本书：{'、'.join(terms) or '（题材与契约未定）'}。"
           "推荐理由引用时写\"源自技艺库《书名》#n\"；排在作者种子之后、题材常规之前。", "",
           "## 相关条目", "", "| 来源 | # | 条目 | 证据 | 适用条件 | 为什么相关 |", "|---|---|---|---|---|---|"]
    out += [f"| 《{b}》 | {r['n']} | {r['entry']} | {r['evidence']} | {r['when']} | "
            + ("通用经验" if w == ["通用"] else f"本书也有 {'、'.join(w)}") + " |" for _, b, r, w in hits[:a.top]]
    if not hits:
        out.append("| —— | | （没有和本书题材、契约、弧光、写作模式相关的条目） | | | |")
    if others:
        out += ["", "## 其他条目（不一定适用）", ""] + [f"- 《{b}》{n} 条" for b, n in others.items()]
    dest = book_dir / CRAFT_EXCERPT
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(out) + "\n", "utf-8")
    print("\n".join(out))


def craft_pending(book_dir: Path, d: dict) -> int:
    """别的书在技艺库里的条目数（本书开书时要读）。"""
    lib = book_dir.parent / CRAFT_LIBRARY
    return sum(len(craft_entries(p)) for p in lib.glob("*.md") if p.stem != d.get("title")) if lib.is_dir() else 0


# ---------- M7：多书仪表盘 ----------

SHADES = "·░▒▓█"


def shade(n: int) -> str:
    return SHADES[0 if n <= 0 else 1 if n == 1 else 2 if n == 2 else 3 if n <= 4 else 4]


def promise_events(items) -> list:
    """读者向承诺的事件：(章, 类型, 动作)。期权、暂定决策不算。"""
    ev = []
    for p in items:
        if p.get("type") in ("期权", "暂定决策"):
            continue
        if p.get("created_ch") is not None:
            ev.append((p["created_ch"], p["type"], "建立"))
        ev += [(e["ch"], p["type"], "推进") for e in p.get("progress", []) if e.get("ch") is not None]
        if p.get("resolved_ch") is not None:
            ev.append((p["resolved_ch"], p["type"], "兑现" if p.get("status") == "已兑现" else "作废"))
    return ev


def book_overview(b: Path, bucket: int) -> dict:
    d = ensure_m3_fields(read_json(b / "book.json", {}))
    if d.get("schema_version", 1) < SCHEMA:
        return {"title": d.get("title") or b.name, "legacy": True}
    chs = d.get("chapters", [])
    done = [c for c in chs if c.get("status") == "done"]
    items = ledger(b, PROMISES)["items"]
    cur = current_chapter(d)
    pub = d.get("published_upto", 0)
    ev = promise_events(items)
    last = max([c["seq"] for c in chs] + [e[0] for e in ev] + [1])
    nb = -(-last // bucket)
    grid = {}
    for ch, t, _ in ev:
        grid.setdefault(t, [0] * nb)[min(max(ch - 1, 0) // bucket, nb - 1)] += 1
    return {"title": d.get("title") or b.name, "stage": d.get("stage"), "done": len(done), "total": len(chs),
            "words": sum(c.get("word_count") or 0 for c in done), "buffer": sum(1 for c in done if c["seq"] > pub) if pub else None,
            "promises": promise_summary(b, d), "soul": d.get("soul", {}).get("status"), "updated": (d.get("updated_at") or "")[:10],
            "unit": (open_unit(d) or {}).get("id"), "nb": nb, "grid": {t: grid[t] for t in PROMISE_TYPES if t in grid},
            "overdue": [f"{p['id']}（{p['type']}）{p['content']}" for p in items if promise_overdue(p, cur)]}


def cmd_dashboard(a):
    root = Path(a.book_root)
    books = [p.parent for p in sorted(root.glob("*/book.json")) if not p.parent.name.startswith("_")]
    if not books:
        die(f"{root} 下没有书（每本书一个目录，含 book.json）")
    views = [book_overview(b, a.bucket) for b in books]
    out = [f"# 书库仪表盘（{len(views)} 本）", "",
           "| 书 | 阶段 | 章（定稿／登记） | 字数 | 存稿 | 承诺 开放／逾期 | 暂定决策 | 书魂 | 更新 |", "|---|---|---|---|---|---|---|---|---|"]
    for v in views:
        if v.get("legacy"):
            out.append(f"| {v['title']} | v0.1 旧书，先 migrate | | | | | | | |")
            continue
        s = v["promises"]
        out.append(f"| {v['title']} | {v['stage']}{'·' + v['unit'] if v['unit'] else ''} | {v['done']}／{v['total']} | {v['words']} | "
                   f"{'—' if v['buffer'] is None else v['buffer']} | {s['open']}／{s['overdue']}{' ⚠' if s['overdue'] else ''} | "
                   f"{s['pending_decisions']} | {v['soul']} | {v['updated']} |")
    for v in views:
        if v.get("legacy") or not v["grid"]:
            continue
        out += ["", f"## 承诺热力：《{v['title']}》（每格 {a.bucket} 章；{SHADES[1]}1 {SHADES[2]}2 {SHADES[3]}3–4 {SHADES[4]}5+ 次建立、推进或兑现）", ""]
        width = max([len(t) for t in v["grid"]] + [3])
        out.append(f"第几格{'　' * (width - 3)}：" + " ".join(str(i % 10) for i in range(1, v["nb"] + 1)) + f"（第 1 格＝第 1–{a.bucket} 章）")
        out += [f"{t}{'　' * (width - len(t))}：" + " ".join(shade(n) for n in cells) for t, cells in v["grid"].items()]
        if v["overdue"]:
            out.append("逾期：" + "；".join(v["overdue"]))
    print("\n".join(out))
    if a.html:
        dest = Path(a.html)
        dest.write_text(dashboard_html(views, a.bucket), "utf-8")
        print(f"\nOK 网页版：{dest}")


def dashboard_html(views, bucket) -> str:
    e = html.escape
    rows = []
    for v in views:
        if v.get("legacy"):
            rows.append(f"<tr><td>{e(v['title'])}</td><td colspan='8'>v0.1 旧书，先 migrate</td></tr>")
            continue
        s = v["promises"]
        rows.append("<tr>" + "".join(f"<td>{e(str(x))}</td>" for x in (
            v["title"], v["stage"], f"{v['done']}／{v['total']}", v["words"], "—" if v["buffer"] is None else v["buffer"],
            f"{s['open']}／{s['overdue']}", s["pending_decisions"], v["soul"], v["updated"])) + "</tr>")
    heat = []
    for v in views:
        if v.get("legacy") or not v["grid"]:
            continue
        head = "".join(f"<th>{i * bucket + 1}</th>" for i in range(v["nb"]))
        body = "".join(f"<tr><th>{e(t)}</th>" + "".join(
            f"<td style='background:rgba(214,96,42,{min(n / 5, 1):.2f})' title='第{i * bucket + 1}–{(i + 1) * bucket}章：{n} 次'>{n or ''}</td>"
            for i, n in enumerate(cells)) + "</tr>" for t, cells in v["grid"].items())
        over = f"<p class='warn'>逾期：{e('；'.join(v['overdue']))}</p>" if v["overdue"] else ""
        heat.append(f"<h2>承诺热力：《{e(v['title'])}》</h2><p class='note'>每格 {bucket} 章，数字是这几章里建立、推进、兑现的次数；表头是每格的起始章。</p>"
                    f"<div class='scroll'><table class='heat'><tr><th></th>{head}</tr>{body}</table></div>{over}")
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>书库仪表盘</title>
<style>
:root {{ --bg:#fbfaf7; --fg:#22201c; --line:#ddd8cf; --muted:#6b665d; --warn:#b3261e; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#1b1a18; --fg:#ece8e1; --line:#3a3732; --muted:#a39d92; --warn:#f2b8b5; }} }}
body {{ background:var(--bg); color:var(--fg); font:15px/1.6 -apple-system, "PingFang SC", "Noto Sans CJK SC", sans-serif; margin:0; padding:24px 16px; }}
main {{ max-width:1100px; margin:0 auto; }}
table {{ border-collapse:collapse; margin:8px 0 20px; }}
th, td {{ border:1px solid var(--line); padding:4px 8px; text-align:center; white-space:nowrap; }}
.heat td {{ min-width:28px; }}
.scroll {{ overflow-x:auto; }}
.note {{ color:var(--muted); font-size:13px; }}
.warn {{ color:var(--warn); }}
</style></head><body><main>
<h1>书库仪表盘（{len(views)} 本）</h1>
<p class="note">由 ncc_state.py dashboard 生成于 {now()}</p>
<div class="scroll"><table><tr><th>书</th><th>阶段</th><th>章（定稿／登记）</th><th>字数</th><th>存稿</th><th>承诺 开放／逾期</th><th>暂定决策</th><th>书魂</th><th>更新</th></tr>
{''.join(rows)}</table></div>
{''.join(heat)}
</main></body></html>
"""


# ---------- M7：导出 ----------

def chapter_text(book_dir: Path, c: dict):
    raw = (book_dir / c["file"]).read_text("utf-8")
    lines = raw.splitlines()
    title = ""
    while lines and not lines[0].strip():
        lines.pop(0)
    if lines and (lines[0].lstrip().startswith("#") or re.match(r"\s*第[一二三四五六七八九十百千零〇0-9]+章", lines[0])):
        title = lines.pop(0).lstrip("# ").strip()
    if not title:
        m = re.match(r"第0*(\d+)章[-_ ]?(.*)", Path(c["file"]).stem)
        title = f"第{m.group(1)}章 {m.group(2)}".strip() if m else Path(c["file"]).stem
    paras = []
    for l in lines:
        t = l.strip()
        if not t or re.match(r"rev\s*\d+\s*[:：]", t) or re.fullmatch(r"[-*_]{3,}", t):
            continue
        paras.append(re.sub(r"^(#+|>)\s*", "", t))
    return title, paras


def write_epub(dest: Path, title: str, author: str, chapters):
    e = html.escape
    uid = f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, 'ncc-workflow:' + title)}"
    modified = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    xhtml = ('<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n<html xmlns="http://www.w3.org/1999/xhtml" '
             'xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="zh-CN" lang="zh-CN">\n<head><meta charset="utf-8"/>'
             '<title>{t}</title><link rel="stylesheet" type="text/css" href="style.css"/></head>\n<body>\n{b}\n</body>\n</html>\n')
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        mt = zipfile.ZipInfo("mimetype")
        mt.compress_type = zipfile.ZIP_STORED
        z.writestr(mt, "application/epub+zip")
        z.writestr("META-INF/container.xml", '<?xml version="1.0" encoding="utf-8"?>\n<container version="1.0" '
                   'xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n<rootfiles><rootfile full-path="OEBPS/content.opf" '
                   'media-type="application/oebps-package+xml"/></rootfiles>\n</container>\n')
        z.writestr("OEBPS/style.css", "body { line-height: 1.8; }\np { text-indent: 2em; margin: 0 0 0.4em; }\n"
                   "h2 { text-align: center; margin: 1.5em 0 1em; }\n")
        items, refs, lis, points = [], [], [], []
        for i, (t, paras) in enumerate(chapters, 1):
            name = f"ch{i:04d}.xhtml"
            body = f"<h2>{e(t)}</h2>\n" + "\n".join(f"<p>{e(p)}</p>" for p in paras)
            z.writestr(f"OEBPS/{name}", xhtml.format(t=e(t), b=body))
            items.append(f'<item id="c{i}" href="{name}" media-type="application/xhtml+xml"/>')
            refs.append(f'<itemref idref="c{i}"/>')
            lis.append(f'<li><a href="{name}">{e(t)}</a></li>')
            points.append(f'<navPoint id="np{i}" playOrder="{i}"><navLabel><text>{e(t)}</text></navLabel><content src="{name}"/></navPoint>')
        z.writestr("OEBPS/nav.xhtml", xhtml.format(t="目录", b=f'<nav epub:type="toc" id="toc"><h1>目录</h1><ol>{"".join(lis)}</ol></nav>'))
        z.writestr("OEBPS/toc.ncx", f'<?xml version="1.0" encoding="utf-8"?>\n<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">\n'
                   f'<head><meta name="dtb:uid" content="{uid}"/><meta name="dtb:depth" content="1"/>'
                   f'<meta name="dtb:totalPageCount" content="0"/><meta name="dtb:maxPageNumber" content="0"/></head>\n'
                   f'<docTitle><text>{e(title)}</text></docTitle>\n<navMap>{"".join(points)}</navMap>\n</ncx>\n')
        creator = f"<dc:creator>{e(author)}</dc:creator>" if author else ""
        z.writestr("OEBPS/content.opf", f'<?xml version="1.0" encoding="utf-8"?>\n<package xmlns="http://www.idpf.org/2007/opf" '
                   f'version="3.0" unique-identifier="bookid" xml:lang="zh-CN">\n<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
                   f'<dc:identifier id="bookid">{uid}</dc:identifier><dc:title>{e(title)}</dc:title><dc:language>zh-CN</dc:language>'
                   f'{creator}<meta property="dcterms:modified">{modified}</meta></metadata>\n<manifest>'
                   '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>'
                   '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>'
                   f'<item id="css" href="style.css" media-type="text/css"/>{"".join(items)}</manifest>\n'
                   f'<spine toc="ncx">{"".join(refs)}</spine>\n</package>\n')


def cmd_export(a):
    book_dir = Path(a.book_dir)
    d = ensure_m3_fields(load(book_dir))
    chs = [c for c in d.get("chapters", []) if (a.from_ch or 1) <= c["seq"] <= (a.to_ch or 10 ** 9)]
    done = [c for c in chs if c.get("status") == "done" and (book_dir / c.get("file", "")).is_file()]
    if not done:
        die("范围内没有已定稿的章（只导出 complete 过的章）")
    skipped = [c["seq"] for c in chs if c not in done]
    chapters = [chapter_text(book_dir, c) for c in done]
    title = d.get("title") or book_dir.name
    lo, hi = done[0]["seq"], done[-1]["seq"]
    dest = book_dir / "07-导出" / f"{title}-第{lo}-{hi}章.{a.format}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if a.format == "md":
        dest.write_text(f"# {title}\n\n" + "\n\n".join(f"## {t}\n\n" + "\n\n".join(ps) for t, ps in chapters) + "\n", "utf-8")
    elif a.format == "txt":
        dest.write_text(f"{title}\n\n" + "\n\n".join(f"{t}\n\n" + "\n".join("　　" + p for p in ps) for t, ps in chapters) + "\n", "utf-8")
    else:
        write_epub(dest, title, a.author if a.author is not None else d.get("team", {}).get("主编", ""), chapters)
    words = sum(len(HAN.findall("".join(ps))) for _, ps in chapters)
    print(f"OK 导出 {len(done)} 章（{words} 字）→ {dest.relative_to(book_dir)}"
          + (f"；未定稿未导出：第 {'、'.join(map(str, skipped))} 章" if skipped else ""))


# ---------- 七律：视图只生成，历史只追加 ----------

GEN_BEGIN = "<!-- ncc:生成区块 开始（render 与 report --write 会整块重写；判断写在区块外） -->"
GEN_END = "<!-- ncc:生成区块 结束 -->"
GEN_RE = re.compile(re.escape(GEN_BEGIN) + r".*?" + re.escape(GEN_END), re.S)


def view_head(sources: str, how: str) -> str:
    return f"> 本文件由 `ncc_state.py render` 从 {sources} 生成，勿手改；要改就改源头：{how}。"


def outside_block(text: str) -> str:
    return GEN_RE.sub("", text)


def write_block(path: Path, body: str, skeleton: str = ""):
    """把生成内容写进文件里的生成区块；区块外作者与角色写的内容原样保留。"""
    block = f"{GEN_BEGIN}\n{body.rstrip()}\n{GEN_END}"
    if path.exists():
        old = path.read_text("utf-8")
        new = GEN_RE.sub(lambda m: block, old, count=1) if GEN_RE.search(old) else block + "\n\n" + old
    else:
        new = block + "\n\n" + skeleton
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new.rstrip() + "\n", "utf-8")


def focus_core(book_dir: Path, d: dict, seq: int) -> list:
    """前情：上一章结束在何时何地、下一章要接什么、近三章的翻转。全部取自源头（book.json、场景卡）。"""
    done = [c for c in d.get("chapters", []) if c["seq"] < seq and c.get("status") == "done"]
    out = []
    if done:
        last, end = done[-1], done[-1].get("end") or {}
        where = "，".join(x for x in (end.get("time"), f"在{end['place']}" if end.get("place") else "") if x)
        out.append(f"- 最近定稿：第{last['seq']}章" + (f"（结束时：{where}）" if where else "（结束时的时间地点还没登记）"))
        if end.get("next"):
            out.append(f"- 下一章要接：{end['next']}")
    else:
        out.append("- 还没有定稿的章")
    out += ["", "**近三章发生了什么**（取自场景卡的翻转）"]
    for c in done[-3:]:
        card = scene_path(book_dir, c["seq"])
        turns = [t.strip() for t in re.findall(r"翻转[：:]\s*([^\n]+)", card.read_text("utf-8"))] if card.exists() else []
        hook = c.get("hook") or {}
        out.append(f"- 第{c['seq']}章：" + ("；".join(turns) or "（场景卡缺失）") + (f"｜章尾钩子：{hook['type']}" if hook.get("type") else ""))
    if not done:
        out.append("- （无）")
    return out


def next_seq(d: dict) -> int:
    pending = [c["seq"] for c in d.get("chapters", []) if c.get("status") != "done"]
    return min(pending) if pending else current_chapter(d) + 1


def intent_view(book_dir: Path, d: dict) -> str:
    soul, ct = d.get("soul", {}), d.get("contract", {})
    v = lambda x: x or "（未填）"
    st = soul.get("status") or "未填"
    when = f"，最晚 {soul['deadline']} 定下" if st == "暂定" and soul.get("deadline") else ""
    dislikes = pref_load(pref_file(book_dir)).get("dislikes", [])
    signing = ct.get("signing", {})
    lines = [f"# 创作意图：{d.get('title')}", "",
             view_head("`book.json` 与 `_作者/偏好.json`", "书魂用 soul，类型契约与目标读者用 contract，签约点用 sign，雷点用 pref dislike"), "",
             f"## 书魂（{st}{when}）", "",
             f"- 主题之问：{v(soul.get('question'))}", f"- 主角的答案：{v(soul.get('answer'))}",
             f"- 世界的不公：{v(soul.get('injustice'))}", f"- 终局的回答：{v(soul.get('ending'))}",
             f"- 主角弧光：{v(soul.get('arc'))}", "",
             "## 类型契约", "", f"- 主契约：{v(ct.get('main'))}", f"- 附加契约：{'、'.join(ct.get('extras', [])) or '（无）'}",
             f"- 毒点：{'、'.join(ct.get('poison', [])) or '（未填）'}", f"- 目标读者：{v(ct.get('audience'))}", "",
             "### 签约点（黄金三章内必须落地）", "", "| 签约点 | 落在 |", "|---|---|"]
    lines += [f"| {pt} | {'第' + str(signing[pt]) + '章' if pt in signing else '（未落地）'} |" for pt in SIGNING_POINTS]
    lines += ["", "## 作者雷点（来自偏好，硬约束）", ""] + ([f"- {x}" for x in dislikes] or ["- （无）"])
    return "\n".join(lines) + "\n"


def focus_view(book_dir: Path, d: dict) -> str:
    seq = next_seq(d)
    lines = [f"# 续写状态卡（写第 {seq} 章前）", "",
             view_head("`book.json`、场景卡与三本账", "结束时的时间地点与下一章要接的事用 chapter end，其余改场景卡和台账"), "",
             "## 当前位置", ""] + focus_core(book_dir, d, seq) + [""] + reader_now_lines(book_dir, d, seq, top=3)
    return "\n".join(lines) + "\n"


def ledger_view(book_dir: Path, d: dict, kind: str) -> str:
    if kind == "promise":
        items, cur = ledger(book_dir, PROMISES)["items"], current_chapter(d)
        s = promise_summary(book_dir, d)
        row = lambda p: (f"| {p['id']} | {p['type']} | {p['content']} | {p.get('strength')} | {p.get('created_ch')} | "
                         + (f"{p['window'][0]}–{p['window'][1]}" if p.get("window") else (p.get("deadline") or "—"))
                         + f" | {p['status']}{'（逾期）' if promise_overdue(p, cur) else ''} |")
        head = ["| 编号 | 类型 | 内容 | 强度 | 建立 | 兑现窗口／最晚 | 状态 |", "|---|---|---|---|---|---|---|"]
        order = {t: i for i, t in enumerate(PROMISE_TYPES)}
        open_ = sorted((p for p in items if p.get("status") in OPEN_STATES),
                       key=lambda p: (order.get(p["type"], 99), -(p.get("strength") or 0)))
        lines = ["# 承诺台账", "", view_head("`06-台账/承诺台账.json`", "promise add/touch/resolve/reschedule/drop"), "",
                 f"开放 {s['open']}、已兑现 {s['resolved']}、作废 {s['dropped']}、逾期 {s['overdue']}；"
                 f"期权 {s['options']}、母题 {s['motifs']}、暂定决策 {s['pending_decisions']}", "",
                 "## 开放中", ""] + (head + [row(p) for p in open_] if open_ else ["（无）"])
        for title, t in (("名场面清单", "名场面"), ("核心意象（母题）", "母题")):
            ps = [p for p in items if p.get("type") == t]
            lines += ["", f"## {title}", ""] + (head + [row(p) for p in ps] if ps else ["（无）"])
        closed = [p for p in items if p.get("status") not in OPEN_STATES]
        lines += ["", "## 已兑现与作废", ""] + (head + [row(p) for p in closed] if closed else ["（无）"])
    elif kind == "know":
        items = ledger(book_dir, KNOWLEDGE)["items"]
        lines = ["# 知情台账", "", view_head("`06-台账/知情台账.json`", "know add/learn"), "",
                 "| 编号 | 事实 | 自第几章 | 知道 | 还不知道 |", "|---|---|---|---|---|"]
        lines += [f"| {k['id']} | {k['fact']} | {k.get('since_ch')} | {'、'.join(k.get('known_by', [])) or '—'} | "
                  f"{'、'.join(k.get('unknown_to', [])) or '—'} |" for k in items] or ["| — | （无） | | | |"]
    else:
        facts = read_json(book_dir / FACTS, {"facts": {}}).get("facts", {})
        lines = ["# 知识台账", "", view_head("`06-台账/知识台账.json`", "fact set"), "",
                 "| 键 | 值 | 类别 | 第几章 | 来源 |", "|---|---|---|---|---|"]
        lines += [f"| {k} | {f['value']} | {f.get('category') or '—'} | {f.get('ch')} | {f.get('source') or '未注'} |"
                  for k, f in facts.items()] or ["| — | （无） | | | |"]
    return "\n".join(lines) + "\n"


def views(book_dir: Path, d: dict) -> dict:
    out = {INTENT_VIEW: intent_view(book_dir, d), FOCUS_VIEW: focus_view(book_dir, d)}
    out.update({rel: ledger_view(book_dir, d, kind) for rel, kind in LEDGER_VIEWS.items()})
    return out


def render(book_dir: Path) -> list:
    d = read_json(book_dir / "book.json", {})
    changed = []
    for rel, text in views(book_dir, d).items():
        p = book_dir / rel
        if not p.exists() or p.read_text("utf-8") != text:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, "utf-8")
            changed.append(rel)
    return changed


def cmd_render(a):
    book_dir = Path(a.book_dir)
    load(book_dir)
    changed = render(book_dir)
    print("OK 视图已是最新" if not changed else "OK 重新生成：" + "、".join(changed))


def events_sha(events) -> str:
    return hashlib.sha256(json.dumps(events, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def history_problem(book_dir: Path, d: dict):
    mark = (d.get("history") or {}).get("events")
    if not mark:
        return None
    ev = read_json(book_dir / EVENTS, {"events": []}).get("events", [])
    if len(ev) < mark["count"] or events_sha(ev[:mark["count"]]) != mark["sha"]:
        return f"状态事件被改写或删除过（历史只允许追加）：登记时有 {mark['count']} 条，现在前 {mark['count']} 条对不上"
    return None


def cmd_event(a):
    """状态事件（世界账的历史）只经这里追加，不手改 JSON（七律三、六）。"""
    book_dir = Path(a.book_dir)
    d = load(book_dir)
    data = read_json(book_dir / EVENTS, {"events": []})
    ev = data.setdefault("events", [])
    if a.action == "list":
        for e in ev:
            if a.entity and e.get("entity") != a.entity:
                continue
            print(f"第{e.get('chapter')}章 {e.get('entity')}·{e.get('attribute')}：{e.get('old')} → {e.get('new')}  {e.get('reason', '')}")
        return
    bad = history_problem(book_dir, d)
    if bad:
        die(bad + "；先用 check 查清楚，再决定怎么修")
    ev.append({"entity": a.entity, "chapter": a.ch, "attribute": a.attr, "old": a.old or "", "new": a.new or "",
               "reason": a.reason or "", "evidence": a.evidence or ""})
    write_json(book_dir / EVENTS, data)
    d.setdefault("history", {})["events"] = {"count": len(ev), "sha": events_sha(ev)}
    save(book_dir, d)
    print(f"OK 第{a.ch}章 {a.entity}·{a.attr}：{a.old or '—'} → {a.new or '—'}")


DATA_IN_PROSE = re.compile(r"\d+(?:\.\d+)?\s*(?:里|公里|千米|日|天|时辰|两|文|贯|钱|斤|丈|尺|米|元|块)")


def cmd_check(a):
    """七律自查：视图与源头逐字一致、历史只追加、没有旧布局残留、数据不散在设定正文里。"""
    book_dir = Path(a.book_dir)
    d = load(book_dir)
    problems, warns = [], []
    for rel, text in views(book_dir, d).items():
        p = book_dir / rel
        if not p.exists():
            problems.append(f"缺视图：{rel}（render 生成）")
        elif p.read_text("utf-8") != text:
            problems.append(f"视图与源头不一致：{rel}（被手改了，或源头改了还没 render；手改的内容先改到源头，再 render）")
    bad = history_problem(book_dir, d)
    if bad:
        problems.append(bad)
    for old, new in OLD_BOOK_PATHS:
        if (book_dir / old).exists() and old not in (INTENT_VIEW, FOCUS_VIEW):
            problems.append(f"旧布局残留：{old}（应在 {new}；运行 migrate）")
    for old, new in OLD_ROOT_PATHS:
        if (book_dir.parent / old).exists():
            problems.append(f"书库根目录有旧布局残留：{old}（应在 {new}；运行 migrate）")
    bible = book_dir / "01-设定" / "世界观圣经.md"
    if bible.exists():
        hits = DATA_IN_PROSE.findall(bible.read_text("utf-8"))
        if hits:
            warns.append(f"世界观圣经里有具体数据（{'、'.join(dict.fromkeys(hits[:5]))}）：数据只放知识台账（fact set），圣经里写台账的键")
    for line in problems:
        print(f"CHECK FAIL  {line}")
    for line in warns:
        print(f"CHECK WARN  {line}")
    if not problems and not warns:
        print("CHECK OK  视图都是最新的，历史没被改写，没有旧布局残留")
    sys.exit(1 if problems else 0)


def migrate_layout(book_dir: Path, d: dict) -> list:
    """schema 2 → 3：机器工作件进 .ncc/，读者反馈进 05-审稿/，作者资产进书库根目录 _作者/，派生数据移出 book.json。"""
    import shutil
    moved = []
    for base, pairs in ((book_dir, OLD_BOOK_PATHS), (book_dir.parent, OLD_ROOT_PATHS)):
        for old, new in pairs:
            src, dst = base / old, base / new
            if not src.exists():
                continue
            if src.is_dir() and dst.is_dir():          # 目标目录已建好（init 会建）：逐个搬进去，不覆盖
                for child in sorted(src.iterdir()):
                    if not (dst / child.name).exists():
                        shutil.move(str(child), str(dst / child.name))
                if not any(src.iterdir()):
                    src.rmdir()
                moved.append(f"{old} → {new}")
            elif not dst.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dst))
                moved.append(f"{old} → {new}")
    d.pop("promises", None)
    d.setdefault("contract", {}).setdefault("audience", "")
    for c in d.get("chapters", []):
        pack = str(c.get("pack") or "")
        if pack.startswith("04-正文/_packs/") and pack.endswith(".md"):
            c["pack"] = pack.replace("04-正文/_packs/", f"{PACK_DIR}/")
        elif pack.endswith(".json"):
            c["pack"] = None
    return moved


RENDER_SKIP = {"render", "check", "sha", "dashboard", "export", "words"}


def auto_render(a):
    """写操作之后重新生成视图，保证副本永远来自源头（七律二）。"""
    if a.cmd in RENDER_SKIP or (a.cmd, getattr(a, "action", None)) in READ_ONLY or (a.cmd, None) in READ_ONLY:
        return
    if a.cmd == "gate" and getattr(a, "action", "") == "check":
        return
    if getattr(a, "book_dir", None):
        targets = [Path(a.book_dir)]
    elif a.cmd == "pref":
        p = Path(a.path)
        targets = [p] if (p / "book.json").exists() else [x.parent for x in p.glob("*/book.json")]
    else:
        return
    for b in targets:
        if (b / "book.json").exists() and read_json(b / "book.json", {}).get("schema_version", 1) >= SCHEMA:
            render(b)


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
        "era": "",
        "study": [],
        "writing_mode": "serial",
        "experience_level": level,
        "soul": {"question": "", "answer": "", "injustice": "", "ending": "",
                 "status": "未填", "deadline": "", "arc": ""},
        "contract": {"main": "", "extras": [], "poison": [], "signing": {}, "audience": ""},
        "gates": {k: {"status": "waiting"} for k in
                  ("soul", "settings_frozen", "outline_frozen", "opening_accepted")},
        "chapters": [],
        "units": [],
        "volumes": [{"n": 1, "start": 1, "end": None, "status": "open"}],
        "published_upto": 0,
        "team": {},
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
    copy_template("author-seeds.md", book_dir / SEEDS)


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
    pref_note_book(book_dir, a.title, genre)
    print(f"OK init {book_dir} stage=founding level={a.level} mode={a.mode}")


def cmd_migrate(a):
    book_dir = Path(a.book_dir)
    p = book_dir / "book.json"
    if not p.exists():
        die(f"book.json 不存在: {p}")
    d = read_json(p, {})
    ver = d.get("schema_version", 1)
    if ver >= SCHEMA:
        print(f"已是 schema {SCHEMA}，无需迁移")
        return
    if ver >= 2:
        moved = migrate_layout(book_dir, d)
        d["schema_version"] = SCHEMA
        ensure_m3_fields(d)
        save(book_dir, d)
        init_ledgers(book_dir)
        print(f"OK migrate schema {ver} → {SCHEMA}；按七律归位 {len(moved)} 处" + ("：" + "；".join(moved) if moved else "")
              + "。旧的 author-intent.md、current-focus.md 若是手写的，已移到 .ncc/迁移备份/，现在由 render 生成")
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
    moved = migrate_layout(book_dir, d)
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
    print(f"OK migrate → schema {SCHEMA}；stage={d['stage']}；mode={d['mode']}；伏笔迁入承诺台账 {migrated} 条"
          + ("（原伏笔台账.json 保留未删）" if migrated else "") + (f"；按七律归位 {len(moved)} 处" if moved else ""))


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
    pending_k = 0
    for c in chs:
        rows = knowledge_rows(book_dir, c["seq"]) or []
        pending_k += sum(1 for r in rows if len(r) >= 5 and r[4] == "待核")
    print(f"底蕴: 时代背景 {d.get('era') or '未设'}  一书一深学 {'、'.join(d.get('study', [])) or '未选'}  待核知识点 {pending_k}")
    st = d.get("style") or {}
    print(f"文风指纹: {st.get('source')}（{st.get('han')} 字）" if st else "文风指纹: 未生成（style --sample 旧文，或第 1 章定稿后 --from-chapters 1）")
    mats = material_cards(book_dir)
    if mats:
        own = sum(1 for k in mats if k.startswith("M-"))
        print(f"素材: {len(mats)} 张（本书 {own}、跨书 {len(mats) - own}），场景卡已引用 "
              f"{len([k for k in mats if k in material_usage(book_dir)])} 张")
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
        n = craft_pending(book_dir, d)
        if n and not (book_dir / CRAFT_EXCERPT).exists():
            problems.append(f"技艺库里有别的书的 {n} 条经验，开书前先读（ncc_state.py craft read，M6-4）")
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
        bible = book_dir / "01-设定" / "世界观圣经.md"
        if bible.exists() and not section(bible.read_text("utf-8"), "社会洞察"):
            problems.append("世界观圣经缺「社会洞察」一节或为空（看似不合理却存在的规矩：谁受益、谁受害、主角在哪，"
                            "对应书魂里世界的不公哪一面，见 worldbuilding.md；确实用不上就写一行理由）")
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
        tested = [p for p in blinds if "记忆测试" in p.read_text("utf-8")]
        if not blinds:
            problems.append("缺读者盲评报告（05-审稿/blind-*.md）")
        elif not tested:
            problems.append("盲评报告缺「记忆测试」一节")
        elif len(tested) < 2:
            problems.append("开篇盲评只有 1 个读者画像，至少 2 个（目标读者＋老白或懂行读者，各一份 "
                            "05-审稿/blind-ch-0001-0003-<画像>.md，见 reader-personas.md）")
        anchor = book_dir / STYLE_ANCHOR
        calib = section(anchor.read_text("utf-8"), "本书校准段") if anchor.exists() else ""
        if len(HAN.findall(re.sub(r"^\s*<.*>\s*$", "", calib, flags=re.M))) < 100:
            problems.append("文风基准.md 的「本书校准段」还没填（从第 1 章定稿里摘 200–400 字，见 golden-three.md）")
        if not (book_dir / STYLE_FP).exists():
            problems.append("缺文风指纹（有旧文样本用 style --sample；没有就 style --from-chapters 1）")
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
            problems.append(f"技艺库还没有这本书的条目：{CRAFT_LIBRARY}/{d.get('title')}.md（craft init 生成模板，见 loops.md 书循环）")
        elif not craft_entries(lib):
            problems.append(f"技艺库条目表是空的：{CRAFT_LIBRARY}/{d.get('title')}.md（每条一句话＋证据＋适用条件＋标签）")
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
    if a.audience is not None:
        ct["audience"] = a.audience
    save(book_dir, d)
    print(f"OK 主契约={ct['main'] or '未填'} 附加={len(ct['extras'])} 毒点={len(ct['poison'])}"
          + f" 目标读者={ct.get('audience') or '未填'}")


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
            "pack": None})
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
        elif a.action == "end":
            c["end"] = {k: v for k, v in (("time", a.time), ("place", a.place), ("next", a.next)) if v}
            msg = f"OK ch{a.seq} 结束于：" + "，".join(c["end"].values())
        elif a.action == "length":
            p = chapter_file(book_dir, c)
            n = han_words(p.read_text("utf-8"))
            lo, hi, _ = length_band(book_dir, a.seq)
            rec = c.setdefault("length", {})
            if a.compressed:
                rec.update({"compressed": True, "compressed_at": now()})
                msg = f"OK ch{a.seq} 已做过一次只删不加的压缩（现在 {n} 字）"
            elif a.accept:
                if n < lo / 2 and (a.tentative or not a.force):
                    if a.tentative:
                        die(f"第 {a.seq} 章只有 {n} 字，不到下限 {lo} 的一半：不能按推荐先收，要当场问作者")
                    die(f"第 {a.seq} 章只有 {n} 字，不到下限 {lo} 的一半：作者明确要收下时加 --force，并把原话写进 --note")
                if n > hi and not rec.get("compressed") and not a.force:
                    die(f"第 {a.seq} 章 {n} 字，超出上限 {hi}：先让 editor 做一次只删不加的压缩（chapter length --compressed），仍超再收下")
                rec.update({"accepted": n, "band": [lo, hi], "sha": sha16(p), "at": now(), "note": a.note or "",
                            "by": "recommendation" if a.tentative else "author"})
                msg = (f"OK ch{a.seq} 按推荐先收下 {n} 字（区间 {lo}–{hi}），单元复盘时请作者确认" if a.tentative
                       else f"OK ch{a.seq} 作者收下当前长度 {n} 字（区间 {lo}–{hi}）")
            else:
                die("chapter length 要给 --accept（作者收下当前长度）或 --compressed（已做过一次只删不加的压缩）")
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
    kp = knowledge_ready(book_dir, a.seq)
    if kp:
        die("章定稿闸：场景卡标了知识点，但知识点清单不合格——" + "；".join(kp))
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
    print("\n".join(reader_now_lines(book_dir, d, a.seq, a.top)))


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
    p.add_argument("--extra", action="append"); p.add_argument("--poison"); p.add_argument("--audience"); p.set_defaults(fn=cmd_contract)
    p = sub.add_parser("sign"); p.add_argument("book_dir"); p.add_argument("point")
    p.add_argument("--ch", type=int, required=True); p.set_defaults(fn=cmd_sign)

    p = sub.add_parser("scene"); ss = p.add_subparsers(dest="action", required=True)
    q = ss.add_parser("next"); q.add_argument("book_dir")
    q = ss.add_parser("check"); q.add_argument("book_dir"); q.add_argument("seq", type=int, nargs="+")
    q = ss.add_parser("review"); q.add_argument("book_dir"); q.add_argument("seq", type=int, nargs="+")
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
    q = cs.add_parser("end"); q.add_argument("book_dir"); q.add_argument("seq", type=int)
    q.add_argument("--time"); q.add_argument("--place"); q.add_argument("--next")
    q = cs.add_parser("length"); q.add_argument("book_dir"); q.add_argument("seq", type=int)
    q.add_argument("--accept", action="store_true"); q.add_argument("--compressed", action="store_true")
    q.add_argument("--force", action="store_true"); q.add_argument("--note"); q.add_argument("--tentative", action="store_true")
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
    p.add_argument("--write", action="store_true")
    p.set_defaults(fn=cmd_report)
    p = sub.add_parser("feedback"); fbs = p.add_subparsers(dest="action", required=True)
    q = fbs.add_parser("add"); q.add_argument("book_dir"); q.add_argument("--ch", type=int, required=True)
    q.add_argument("--source", required=True); q.add_argument("--kind", required=True); q.add_argument("--value", required=True)
    q.add_argument("--note"); q.add_argument("--persona")
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

    p = sub.add_parser("knowledge"); kns = p.add_subparsers(dest="action", required=True)
    q = kns.add_parser("plan"); q.add_argument("book_dir"); q.add_argument("seq", type=int, nargs="+")
    q = kns.add_parser("check"); q.add_argument("book_dir"); q.add_argument("seq", type=int, nargs="+")
    p.set_defaults(fn=cmd_knowledge)
    p = sub.add_parser("era"); p.add_argument("book_dir"); p.add_argument("era"); p.set_defaults(fn=cmd_era)
    p = sub.add_parser("study"); p.add_argument("book_dir"); p.add_argument("--add"); p.set_defaults(fn=cmd_study)
    p = sub.add_parser("material"); ms = p.add_subparsers(dest="action", required=True)
    q = ms.add_parser("add"); q.add_argument("book_dir"); q.add_argument("--content", required=True)
    q.add_argument("--source", required=True); q.add_argument("--use", required=True); q.add_argument("--trust")
    q.add_argument("--domain"); q.add_argument("--genre"); q.add_argument("--title"); q.add_argument("--shared", action="store_true")
    q = ms.add_parser("list"); q.add_argument("book_dir"); q.add_argument("--domain"); q.add_argument("--unused", action="store_true")
    q = ms.add_parser("check"); q.add_argument("book_dir")
    p.set_defaults(fn=cmd_material)
    p = sub.add_parser("style"); p.add_argument("book_dir"); p.add_argument("--sample", nargs="+")
    p.add_argument("--from-chapters"); p.set_defaults(fn=cmd_style)
    p = sub.add_parser("heat"); p.add_argument("book_dir"); p.add_argument("--ch"); p.set_defaults(fn=cmd_heat)
    p = sub.add_parser("pref"); prs = p.add_subparsers(dest="action", required=True)
    q = prs.add_parser("show"); q.add_argument("path"); q.add_argument("--key")
    for act in ("like", "confirm", "reject"):
        q = prs.add_parser(act); q.add_argument("path"); q.add_argument("--key", required=True)
        q.add_argument("--value", required=True); q.add_argument("--note")
    q = prs.add_parser("dislike"); q.add_argument("path"); q.add_argument("--value", required=True); q.add_argument("--key")
    p.set_defaults(fn=cmd_pref)
    p = sub.add_parser("craft"); crs = p.add_subparsers(dest="action", required=True)
    q = crs.add_parser("init"); q.add_argument("book_dir")
    q = crs.add_parser("read"); q.add_argument("book_dir"); q.add_argument("--top", type=int, default=12)
    p.set_defaults(fn=cmd_craft)
    p = sub.add_parser("dashboard"); p.add_argument("book_root"); p.add_argument("--bucket", type=int, default=10)
    p.add_argument("--html"); p.set_defaults(fn=cmd_dashboard)
    p = sub.add_parser("export"); p.add_argument("book_dir"); p.add_argument("--format", choices=["md", "txt", "epub"], default="md")
    p.add_argument("--from", dest="from_ch", type=int); p.add_argument("--to", dest="to_ch", type=int); p.add_argument("--author")
    p.set_defaults(fn=cmd_export)
    p = sub.add_parser("pack"); p.add_argument("book_dir"); p.add_argument("seq", type=int); p.add_argument("--note")
    p.set_defaults(fn=cmd_pack)
    p = sub.add_parser("review"); rs = p.add_subparsers(dest="action", required=True)
    q = rs.add_parser("plan"); q.add_argument("book_dir"); q.add_argument("seq", type=int)
    q = rs.add_parser("delta"); q.add_argument("book_dir"); q.add_argument("seq", type=int)
    p.set_defaults(fn=cmd_review)
    p = sub.add_parser("words"); p.add_argument("book_dir"); p.add_argument("seq", type=int); p.add_argument("--file")
    p.set_defaults(fn=cmd_words)
    p = sub.add_parser("render"); p.add_argument("book_dir"); p.set_defaults(fn=cmd_render)
    p = sub.add_parser("check"); p.add_argument("book_dir"); p.set_defaults(fn=cmd_check)
    p = sub.add_parser("event"); evs = p.add_subparsers(dest="action", required=True)
    q = evs.add_parser("add"); q.add_argument("book_dir"); q.add_argument("--entity", required=True)
    q.add_argument("--ch", type=int, required=True); q.add_argument("--attr", required=True)
    q.add_argument("--old"); q.add_argument("--new"); q.add_argument("--reason"); q.add_argument("--evidence")
    q = evs.add_parser("list"); q.add_argument("book_dir"); q.add_argument("--entity")
    p.set_defaults(fn=cmd_event)
    p = sub.add_parser("reader-now"); p.add_argument("book_dir"); p.add_argument("seq", type=int)
    p.add_argument("--top", type=int, default=5); p.set_defaults(fn=cmd_reader_now)
    p = sub.add_parser("sha"); p.add_argument("file"); p.set_defaults(fn=cmd_sha)

    a = ap.parse_args()
    a.fn(a)
    log_op(a)
    auto_render(a)


READ_ONLY = {("status", None), ("next", None), ("report", None), ("sha", None), ("water", None),
             ("reader-now", None), ("scene", "check"), ("scene", "next"), ("knowledge", "plan"), ("knowledge", "check"), ("promise", "list"), ("know", "list"),
             ("fact", "get"), ("fact", "list"), ("feedback", "list"), ("team", "list"), ("unit", "list"),
             ("material", "list"), ("material", "check"), ("heat", None), ("pref", "show"), ("dashboard", None),
             ("export", None), ("words", None), ("event", "list")}


def log_op(a):
    """团队交接用：每个成功的写操作追加一行到 .ncc/操作日志.jsonl。"""
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
