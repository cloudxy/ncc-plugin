#!/usr/bin/env python3
"""check_chapter.py — 章节机械检查（确定性脚本，替代 LLM 自评）。

用法: check_chapter.py <书目录> <章号seq> [章文件路径]

结论（JSON 里的 status，与退出码一致）:
  ready           0  可以进审稿
  blocked         1  有必须修的问题（下列标"必须修"的项），就地修完重跑
  needs_decision  3  只是字数不在区间：不让写手补写或重写（硬凑会注水），交作者定——收下当前长度
                     （ncc_state.py chapter length --accept）、改场景卡或字数范围后重写、或不要这章；
                     超长先让 editor 做一次只删不加的压缩（chapter length --compressed），仍超再问作者
  （用法错误退出 2）

检查项:
  1. 字数：汉字数与本章区间（场景卡「字数范围：A-B」，没写就用 ncc.config.yaml 的 words_min/words_max，
     默认 3000–5000）；不在区间 → needs_decision；作者收下过且正文未改 → 视为通过
  2. book.json 该章已登记章尾钩子（type + intensity）（必须修）
  3. AI 味分级（M3-5）：
       A 级（计入退出码）：五星句式"不是A，而是B"出现即须改；其余高危句式与一级禁用词合计超过 ai_level1_max（默认 3）
       B 级（只告警）：二级词密度（缓缓/微微/轻轻/淡淡 每千字 > 3）、总结升华句式、章末空泛预告
     作者放行：03-文风/放行清单.md 里用「」括起的原句不计入（有意为之，须写理由）
  4. 水章：本章未建立、推进或兑现任何读者向承诺（读 06-台账/承诺台账.json；无台账则告警跳过）
  5. 句长起伏（诊断参考，不计入退出码）：句长变异系数、落在 15–35 字"舒适区"的句子占比
  6. 底蕴提醒（M4，只告警，交 continuity 核对）：时代错置词（book.json era 为古代或架空古代时启用，
     可在 01-设定/时代错置词.md 追加本书的词）、敬称谦称用反、月相与日期不符；并列出本章用到的知识台账条目
  7. 规避点（M5，只告警）：长段（单段超过 para_max 汉字，默认 200）、长句（一句 sentence_commas_max 个逗号以上，
     默认 10）、对白流（连续 dialogue_run_max 段以引号开头，默认 10）；对话占比只作参考
  8. 文风漂移（M6，只告警）：有 03-文风/文风指纹.json 时，对照句长、段长、对话占比、人称
  9. 退化与元信息（v1.1）：
       必须修：长句复读（叙述里同一句 ≥12 字出现 3 次以上，或相邻两行一模一样）、结尾截断（末字不是收句标点）、
               占位与拒绝语（此处省略、TODO、未完待续、乱码、"作为AI"、"我无法继续写"）、
               叙述里出现纯工程词（细纲、章纲、场景卡、情节点、写手包、写作简报、承诺台账……）
       只告警：叙述里的"本章、上一章、下一章、伏笔、读者、前文"等词，台词里的工程词，场景卡原句照搬进正文，
               用身体小动作标注情绪（指尖、指节、喉结、呼吸、心跳……）超过 2 处

只数汉字、剔除 Markdown 标记与修订注记（rev N:）。
AI 味词表与句式整理自 oh-story-claudecode 的 story-deslop（MIT License，Copyright (c) 2025-2026 oh-story-claudecode），
只借清单，判定逻辑为本插件自写；退化检查、欠字不补与身体小动作的处理借鉴其 check-degeneration 与
craft-stock-reaction 实验（v0.8.4，MIT），代码为本插件自写。规避点的三条整理自作者自有的 novel_guide「13 规避点」。
"""
import json
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ncc_state import (EVOLUTION, FACTS, PROMISES, REGISTRY, REV_LINE, L, chapter_touches, han_words, length_band,  # noqa: E402
                       overlay_values, scene_path, sha16, style_drift_lines, with_words)

# A 级：五星句式，命中一处即须改
BLOCK_PATTERNS = {
    "不是A，而是B": r"不是[^，。！？\n]{1,20}[，,]\s*(?:而)?是",
}
# A 级：其余高危句式（正则），与一级禁用词合计计数
HIGH_RISK_PATTERNS = {
    "，带着……（万能状语）": r"[，,]带着(?:一丝|一抹|几分|些许)",
    "他/她知道……（直接告知）": r"[他她]知道[^道]",
    "眼中闪过／嘴角勾起": r"眼中闪过|嘴角勾起",
    "心中涌起一股": r"心中涌起一股|心头涌起一股",
    "命运的齿轮／棋局／獠牙": r"(?:命运|宿命)[^。！？\n]{0,6}(?:齿轮|棋局|獠牙)",
    "这一刻终于明白": r"这一刻[，,]?[他她]?终于(?:明白|意识到)",
}
# A 级：一级禁用词（真人语料里几乎不出现的 AI 特有词）：在注册表 check_words.level1，作者覆盖层可增删
LEVEL1_WORDS = REGISTRY["check_words"]["level1"]
# B 级：二级词（密度控制）与总结、预告句式
LEVEL2_DENSITY_WORDS = ["缓缓", "微微", "轻轻", "淡淡"]
SUMMARY_PATTERNS = {
    "才刚刚开始": r"才刚刚开始",
    "从这一刻开始": r"从这一刻(?:开始|起)",
    "他/她这才意识到": r"[他她]这才意识到",
    "他/她不知道的是（章末空泛预告）": r"[他她]不知道的是",
}


# 古代背景下的时代错置词（只告警；穿越者等有意为之的写进放行清单）：在注册表 check_words.anachronism，作者覆盖层可增删
ANACHRONISM_WORDS = REGISTRY["check_words"]["anachronism"]
HONORIFIC_MISUSE = {
    "敬称用在自己身上": r"我(?:的|家)?(?:令尊|令堂|令郎|令爱|令兄|令妹|贵府|尊夫人)",
    "谦称用在对方身上": r"(?:你|您)(?:的)?(?:家父|家母|家兄|舍弟|舍妹|寒舍|拙荆|犬子)",
}
EARLY_DAY = r"初[一二三四五六七八]|月初|二十[五六七八九]|月底|朔日|晦日"
FULL_MOON = r"满月|圆月|月圆|月如银盘|一轮明月"
MID_DAY = r"十五|十六|望日"
CRESCENT = r"月牙|弯月|新月|残月|一钩"


def knowledge_warnings(book_dir: Path, text: str):
    warns, era = [], ""
    bj = book_dir / "book.json"
    if bj.exists():
        try:
            era = json.loads(bj.read_text("utf-8")).get("era", "")
        except json.JSONDecodeError:
            pass
    if era in ("古代", "架空古代"):
        words = with_words(ANACHRONISM_WORDS, overlay_values(book_dir).get("check.anachronism_words"))
        extra = book_dir / L("anachronism")
        if extra.exists():
            words += [w.strip() for w in re.findall(r"^[-*]\s*(\S+)", extra.read_text("utf-8"), flags=re.M)]
        hits = {w: text.count(w) for w in words if text.count(w)}
        if hits:
            warns.append("底蕴：时代错置词（" + era + "）：" + "，".join(f"{k}×{v}" for k, v in hits.items()))
    for k, pat in HONORIFIC_MISUSE.items():
        found = re.findall(pat, text)
        if found:
            warns.append(f"底蕴：{k}：{'、'.join(found[:5])}")
    for sent in re.split(r"[。！？!?\n]", text):
        if re.search(EARLY_DAY, sent) and re.search(FULL_MOON, sent):
            warns.append(f"底蕴：月相与日期可能不符（月初或月底写了满月）：「{sent.strip()[:40]}」")
        elif re.search(MID_DAY, sent) and re.search(CRESCENT, sent):
            warns.append(f"底蕴：月相与日期可能不符（十五前后写了月牙）：「{sent.strip()[:40]}」")
    facts = {}
    fp = book_dir / FACTS
    if fp.exists():
        try:
            facts = json.loads(fp.read_text("utf-8")).get("facts", {})
        except json.JSONDecodeError:
            pass
    used = [f"{k}={v.get('value')}" for k, v in facts.items() if k in text]
    return warns, used


QUOTE_OPEN = "“「『\""


def avoidance_warnings(raw: str, cfg: dict):
    """规避点（M5-2，整理自 novel_guide 13：长段、长句、对白流）。只告警。"""
    warns = []
    paras = [p.strip() for p in strip_md(raw).splitlines() if p.strip()]
    long_p = [i for i, p in enumerate(paras, 1) if len(re.findall(r"[一-鿿]", p)) > cfg["para_max"]]
    if long_p:
        warns.append(f"规避点：长段 {len(long_p)} 处（单段超过 {cfg['para_max']} 字，手机上满屏，读者会扫过去）："
                     f"第 {'、'.join(map(str, long_p[:5]))} 段")
    sents = re.split(r"[。！？!?…\n]+", strip_md(raw))
    long_s = [s.strip() for s in sents if s.count("，") + s.count(",") >= cfg["sentence_commas_max"]]
    if long_s:
        warns.append(f"规避点：长句 {len(long_s)} 处（一句 {cfg['sentence_commas_max']} 个逗号以上）：「{long_s[0][:30]}……」")
    run = best = start = best_start = 0
    for i, p in enumerate(paras, 1):
        if p[0] in QUOTE_OPEN:
            start = i if run == 0 else start
            run += 1
            if run > best:
                best, best_start = run, start
        else:
            run = 0
    if best >= cfg["dialogue_run_max"]:
        warns.append(f"规避点：对白流——第 {best_start}–{best_start + best - 1} 段连续 {best} 段以引号开头，"
                     "中间没有动作、神态或叙述")
    return warns


def dialogue_share(raw: str):
    body = strip_md(raw)
    total = len(re.findall(r"[一-鿿]", body))
    inside = sum(len(re.findall(r"[一-鿿]", m)) for m in re.findall(r"[“「『\"]([^”」』\"]*)[”」』\"]", body))
    return round(inside / total, 2) if total else None


def load_config(book_dir: Path):
    """阈值：插件默认（注册表 evolution.keys 的 default）< 作者覆盖层（evolve apply）< ncc.config.yaml。"""
    cfg = {"words_min": 3000, "words_max": 5000}
    over = overlay_values(book_dir)
    for key, spec in EVOLUTION["keys"].items():
        if key.startswith("check.") and spec["type"] == "int":
            cfg[key[6:]] = int(over.get(key, spec["default"]))
    for p in (book_dir.parent / "ncc.config.yaml", book_dir / "ncc.config.yaml"):
        if p.exists():
            text = p.read_text("utf-8")
            for k in cfg:
                m = re.search(rf"{k}:\s*(\d+)", text)
                if m:
                    cfg[k] = int(m.group(1))
            break
    return cfg


def find_chapter(book_dir: Path, seq: int, explicit: str):
    if explicit:
        p = Path(explicit)
        return p if p.exists() else None
    for pat in (f"第{seq:04d}章-*.md", f"第{seq}章-*.md"):
        hits = sorted((book_dir / L("chapters")).glob(pat))
        if hits:
            return hits[0]
    return None


def strip_md(text: str) -> str:
    return re.sub(r"^[#>*\-|`\s]+", "", text, flags=re.M)


def han_count(text: str) -> int:
    return han_words(text)


# ---------- 退化与元信息（v1.1） ----------

QUOTED = re.compile(r"“[^”]*”|「[^」]*」|『[^』]*』|\"[^\"]*\"")
TERMINAL = "。！？!?…”」』）)】》~—＿"   # ＿：放行清单遮掉的原句
ENGINEERING_HARD = ["细纲", "章纲", "卷纲", "场景卡", "情节点", "写手包", "写作简报", "知识点清单", "承诺台账",
                    "知情台账", "知识台账", "状态事件", "故事审", "任务描述"]
ENGINEERING_SOFT = {"本章": r"本章(?!程|法)", "上一章": r"上一章", "下一章": r"下一章", "前文": r"前文(?!明|化|件|字)",
                    "后文": r"后文(?!件|字)", "伏笔": r"伏笔", "读者": r"读者"}
PLACEHOLDER_HARD = {
    "乱码": r"�",
    "括号省略": r"[（(](?:此处|以下|这里|下文|后续)?\s*(?:省略|略)(?:去|过)?[^）)]{0,10}[）)]",
    "占位符": r"未完待续|TODO|占位符|placeholder",
    "英文 AI 腔": r"(?m)^(?:Sure|Certainly|Here'?s|As an AI|I (?:cannot|can't|am unable|apologize))",
}
PLACEHOLDER_SOFT = {   # 只在叙述里判；台词里可能是合法对话（"对不起，我无法答应你"）
    "AI 自指": r"作为(?:一个)?(?:AI|人工智能|大?语言模型|智能助手)(?:语言模型|大?模型|助手)?(?=[，,。、；;：:！!？?\s]|我|无法|不能|$)",
    "生成拒绝语": r"我(?:无法|不能)(?:继续(?:写|创作|生成|下去)|生成|创作|续写)",
}
BODY = r"(?:指尖|指节|指腹|喉结|喉咙|呼吸|心跳|心脏|眼皮|睫毛|眉心|眉头|嘴角|唇角|下颌|脊背|后背|头皮|太阳穴)"
TIC = r"(?:微微|轻轻|一紧|一顿|一僵|一滞|一窒|泛白|发白|发紧|收紧|滚动|颤动|颤了|发颤|蜷缩|蜷起|绷紧|一跳|跳了一下|发麻|发凉|一沉|一松)"
STOCK_REACTION = re.compile(BODY + r"[^。！？\n“”「」]{0,6}?" + TIC)


def narration_of(text: str) -> str:
    return QUOTED.sub("", text)


def degeneration_findings(raw: str):
    """返回 (必须修, 只告警)。修订注记不算正文。"""
    body = strip_md(re.sub(r"(?m)^\s*#{1,6}\s.*$", "", REV_LINE.sub("", raw))).strip()   # 标题行可以写第X章
    body = re.sub(r"\A第[一二三四五六七八九十百千零〇0-9]+章[^\n]*\n", "", body).strip()      # 不带 # 的标题行
    hard, soft = [], []
    if not body:
        return ["正文为空"], soft
    if body[-1] not in TERMINAL:
        hard.append(f"结尾像是截断了：最后一句「{body[-20:]}」没有收句标点")
    narr = narration_of(body)
    sents = [s.strip() for s in re.split(r"[。！？!?…\n]+", narr) if len(HAN_RE.findall(s)) >= 12]
    repeated = {s: sents.count(s) for s in set(sents) if sents.count(s) >= 3}
    if repeated:
        s, k = max(repeated.items(), key=lambda x: x[1])
        hard.append(f"复读：「{s[:24]}」在叙述里出现 {k} 次")
    lines = [l.strip() for l in body.splitlines() if l.strip()]
    for a, b in zip(lines, lines[1:]):
        if a == b and a[0] not in "“「『\"" and len(HAN_RE.findall(a)) >= 8:
            hard.append(f"复读：相邻两行一模一样「{a[:24]}」")
            break
    for label, pat in PLACEHOLDER_HARD.items():
        m = re.search(pat, body)
        if m:
            hard.append(f"占位或元信息：{label}「{m.group(0)[:20]}」")
    for label, pat in PLACEHOLDER_SOFT.items():
        m = re.search(pat, narr)
        if m:
            hard.append(f"元信息泄漏：{label}「{m.group(0)[:20]}」")
    dialogue = "".join(QUOTED.findall(body))
    eng = [w for w in ENGINEERING_HARD if w in narr]
    if eng:
        hard.append("工程词漏进叙述：" + "、".join(eng) + "（改成角色能感知的事件或时间）")
    soft_eng = [w for w, pat in ENGINEERING_SOFT.items() if re.search(pat, narr)] + [w for w in ENGINEERING_HARD if w in dialogue]
    chap = re.findall(r"第[一二三四五六七八九十百千0-9]+章", narr)
    if chap:
        soft_eng.append(chap[0])
    if soft_eng:
        soft.append("元信息：叙述里有「" + "、".join(dict.fromkeys(soft_eng)) + "」，确认是故事里的东西，不是写作用语")
    return hard, soft


HAN_RE = re.compile(r"[一-鿿]")


def scene_copy_warnings(book_dir: Path, seq: int, raw: str):
    """场景卡原句照搬进正文（只告警）：场景卡是给写手的意图，不是正文。"""
    card = scene_path(book_dir, seq)
    if not card.exists():
        return []
    norm = lambda s: "".join(HAN_RE.findall(s))
    body = norm(raw)
    hits = []
    for m in re.finditer(r"^[-*]\s*([^：:\n]{1,6})[：:]\s*(.+)$", card.read_text("utf-8"), flags=re.M):
        field = m.group(1).strip()
        for value in re.split(r"　+", m.group(2)):
            v = norm(value.split("：", 1)[-1])
            if len(v) >= 10 and any(v[i:i + 10] in body for i in range(0, len(v) - 9, 2)):
                hits.append(field)
                break
    if not hits:
        return []
    extra = "；「默认写法」是要绕开的走法，更不该出现在正文里" if "默认写法" in hits else ""
    return ["场景卡照搬：「" + "、".join(dict.fromkeys(hits)) + "」一栏的原句进了正文，改成演出来的戏" + extra]


def stock_reaction_warnings(text: str):
    hits = [m.group(0) for m in STOCK_REACTION.finditer(narration_of(text))]
    if len(hits) < 3:
        return []
    return [f"身体小动作标注情绪 {len(hits)} 处（{'、'.join(hits[:5])}）：只留有后果的，其余改成选择、台词、物件或后果"]


def waived_snippets(book_dir: Path):
    p = book_dir / L("waivers")
    if not p.exists():
        return []
    return [s for s in re.findall(r"「([^」]+)」", p.read_text("utf-8")) if s.strip()]


def mask_waived(text: str, snippets):
    for s in snippets:
        text = text.replace(s, "＿" * len(s))
    return text


def burstiness(text: str):
    body = strip_md(text)
    sents = [s for s in re.split(r"[。！？!?…\n]+", body) if re.search(r"[一-鿿]", s)]
    lens = [len(re.findall(r"[一-鿿]", s)) for s in sents]
    if len(lens) < 5:
        return None
    mean = statistics.mean(lens)
    cv = statistics.pstdev(lens) / mean if mean else 0
    band = sum(1 for n in lens if 15 <= n <= 35) / len(lens)
    return {"sentences": len(lens), "mean_len": round(mean, 1), "cv": round(cv, 2), "mid_band_share": round(band, 2)}


def ai_findings(book_dir: Path, text: str, words: int, cfg: dict):
    """AI 味分级（M3-5）：返回（必须修、只告警、明细）。一级词按注册表＋作者覆盖层。"""
    problems, warns = [], []
    block = {k: len(re.findall(p, text)) for k, p in BLOCK_PATTERNS.items()}
    block = {k: v for k, v in block.items() if v}
    if block:
        problems.append("A 级五星句式（出现即须改，或把原句写进 03-文风/放行清单.md 并说明理由）："
                        + "，".join(f"{k}×{v}" for k, v in block.items()))
    high = {k: len(re.findall(p, text)) for k, p in HIGH_RISK_PATTERNS.items()}
    high = {k: v for k, v in high.items() if v}
    level1 = with_words(LEVEL1_WORDS, overlay_values(book_dir).get("check.level1_words"))
    l1 = {w: text.count(w) for w in level1 if text.count(w)}
    a_hits = {**high, **l1}
    a_total = sum(a_hits.values())
    detail = "，".join(f"{k}×{v}" for k, v in sorted(a_hits.items(), key=lambda x: -x[1])[:8])
    if a_total > cfg["ai_level1_max"]:
        problems.append(f"A 级高危句式与一级禁用词合计 {a_total} 处 > {cfg['ai_level1_max']}：{detail}")
    elif a_total:
        warns.append(f"A 级命中 {a_total} 处（未超限）：{detail}")
    per_k = sum(text.count(w) for w in LEVEL2_DENSITY_WORDS) / max(words / 1000, 1)
    if per_k > 3:
        warns.append(f"B 级：缓缓/微微/轻轻/淡淡 每千字 {per_k:.1f} 次 > 3")
    summ = {k: len(re.findall(p, text)) for k, p in SUMMARY_PATTERNS.items()}
    summ = {k: v for k, v in summ.items() if v}
    if summ:
        warns.append("B 级总结升华或空泛预告：" + "，".join(f"{k}×{v}" for k, v in summ.items()))
    return problems, warns, {"block": block, "high_risk": high, "level1": l1, "level2_per_1000": round(per_k, 1), "summary": summ}


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    book_dir = Path(sys.argv[1])
    seq = int(sys.argv[2])
    explicit = sys.argv[3] if len(sys.argv) > 3 else ""
    problems, warns = [], []

    f = find_chapter(book_dir, seq, explicit)
    if not f:
        print(json.dumps({"seq": seq, "pass": False,
                          "problems": [f"找不到章节文件（04-正文/第{seq:04d}章-*.md）"]}, ensure_ascii=False))
        sys.exit(1)
    raw = f.read_text("utf-8")
    cfg = load_config(book_dir)
    words = han_count(raw)
    lo, hi, band_src = length_band(book_dir, seq)

    hook, length_rec = None, {}
    bj = book_dir / "book.json"
    if bj.exists():
        try:
            d = json.loads(bj.read_text("utf-8"))
            ch = next((c for c in d.get("chapters", []) if c.get("seq") == seq), {})
            hook, length_rec = ch.get("hook"), ch.get("length") or {}
        except json.JSONDecodeError:
            warns.append("book.json 解析失败，跳过钩子核对")
    if not hook or not hook.get("type") or not hook.get("intensity"):
        problems.append("book.json 未登记章尾钩子（type+intensity）")

    length = {"actual": words, "band": [lo, hi], "band_source": band_src, "status": "ok", "actions": []}
    if length_rec.get("accepted") is not None and length_rec.get("sha") == sha16(f):
        length["status"] = "accepted"
    elif words < lo:
        length.update(status="under", below_half=words < lo / 2, actions=[
            "收下当前长度（chapter length --accept）" + ("——不到下限一半，作者明确要才收（--force）" if words < lo / 2 else "（推荐）"),
            "改场景卡或字数范围后重写", "不要这章"])
    elif words > hi:
        length.update(status="over", compressed=bool(length_rec.get("compressed")), actions=(
            ["收下当前长度（chapter length --accept）", "拆章或改场景卡后重写"] if length_rec.get("compressed") else
            [f"editor 做一次只删不加的压缩，约删 {words - hi} 字（之后 chapter length --compressed）"]))

    hard, soft = degeneration_findings(mask_waived(raw, waived_snippets(book_dir)))
    problems += hard
    warns += soft

    # AI 味分级
    waived = waived_snippets(book_dir)
    text = mask_waived(raw, waived)
    ai_problems, ai_warns, ai = ai_findings(book_dir, text, words, cfg)
    problems += ai_problems
    warns += ai_warns
    ai["waived_snippets"] = len(waived)

    k_warns, facts_used = knowledge_warnings(book_dir, text)
    warns += k_warns
    warns += avoidance_warnings(raw, cfg)
    warns += style_drift_lines(book_dir, raw)
    warns += scene_copy_warnings(book_dir, seq, text)
    warns += stock_reaction_warnings(text)
    rhythm = burstiness(raw) or {}
    rhythm["dialogue_share"] = dialogue_share(raw)

    # 水章
    ledger = book_dir / PROMISES
    touches = []
    if ledger.exists():
        try:
            items = json.loads(ledger.read_text("utf-8")).get("items", [])
            touches = chapter_touches(items, seq)
            if not touches:
                problems.append("水章：本章未建立、推进或兑现任何读者向承诺（先回写承诺台账，或补写推进）")
        except (json.JSONDecodeError, AttributeError):
            warns.append("承诺台账解析失败，跳过水章检测")
    else:
        warns.append("无承诺台账，跳过水章检测（v0.1 书先运行 ncc_state.py migrate）")

    status = "blocked" if problems else ("needs_decision" if length["status"] in ("under", "over") else "ready")
    result = {
        "seq": seq, "file": str(f), "status": status, "han_words": words,
        "band": [lo, hi], "length": length, "hook": hook,
        "ai": ai,
        "rhythm_reference": rhythm,
        "facts_mentioned": facts_used,
        "promise_touches": [f"{i} {k}" for i, k in touches],
        "warnings": warns, "problems": problems, "pass": status == "ready",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit({"ready": 0, "blocked": 1, "needs_decision": 3}[status])


if __name__ == "__main__":
    main()
