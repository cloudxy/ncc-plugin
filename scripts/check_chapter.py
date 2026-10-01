#!/usr/bin/env python3
"""check_chapter.py — 章节机械检查（确定性脚本，替代 LLM 自评；v0.7）。

用法: check_chapter.py <书目录> <章号seq> [章文件路径]

检查项（退出码非 0 = 不及格）:
  1. 汉字字数在 [words_min, words_max]（默认 3000–5000；读 ncc.config.yaml）
  2. book.json 该章已登记章尾钩子（type + intensity）
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

只数汉字、剔除 Markdown 标记。
AI 味词表与句式整理自 oh-story-claudecode 的 story-deslop（MIT License，Copyright (c) 2025-2026 oh-story-claudecode），
只借清单，判定逻辑为本插件自写。规避点的三条整理自作者自有的 novel_guide「13 规避点」。
"""
import json
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ncc_state import PROMISES, chapter_touches, style_drift_lines  # noqa: E402

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
# A 级：一级禁用词（真人语料里几乎不出现的 AI 特有词）
LEVEL1_WORDS = [
    "仿佛", "犹如", "宛若", "一丝", "一抹", "些许", "几不可闻", "微不可察", "毫无征兆",
    "深吸一口气", "不禁", "眉头微皱", "瞳孔微缩", "瞳孔一缩", "指节泛白",
    "心中一动", "心头一震", "心下了然", "心中暗道", "心中一凛", "不由得",
    "不容置疑", "不容置喙", "不易察觉", "显而易见", "毫无疑问", "不可否认",
    "不由自主", "情不自禁", "话锋一转", "取而代之的是",
]
# B 级：二级词（密度控制）与总结、预告句式
LEVEL2_DENSITY_WORDS = ["缓缓", "微微", "轻轻", "淡淡"]
SUMMARY_PATTERNS = {
    "才刚刚开始": r"才刚刚开始",
    "从这一刻开始": r"从这一刻(?:开始|起)",
    "他/她这才意识到": r"[他她]这才意识到",
    "他/她不知道的是（章末空泛预告）": r"[他她]不知道的是",
}


# 古代背景下的时代错置词（只告警；穿越者等有意为之的写进放行清单）
ANACHRONISM_WORDS = [
    "手机", "电话", "电脑", "电视", "网络", "上网", "汽车", "火车", "飞机", "地铁", "公交", "OK", "拜拜", "哈喽",
    "沙发", "咖啡", "巧克力", "冰箱", "空调", "手表", "分钟", "秒钟", "公里", "厘米", "星期", "周末", "上班", "下班",
    "加班", "打卡", "效率", "经理", "员工", "拍照", "照片", "信号", "细胞", "基因", "病毒", "维生素", "卡路里",
    "概率", "智商", "情商", "颜值", "吐槽", "内卷", "躺平", "靠谱",
]
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
        words = list(ANACHRONISM_WORDS)
        extra = book_dir / "01-设定" / "时代错置词.md"
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
    fp = book_dir / "06-台账" / "知识台账.json"
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
    cfg = {"words_min": 3000, "words_max": 5000, "ai_level1_max": 3,
           "para_max": 200, "sentence_commas_max": 10, "dialogue_run_max": 10}
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
        hits = sorted((book_dir / "04-正文").glob(pat))
        if hits:
            return hits[0]
    return None


def strip_md(text: str) -> str:
    return re.sub(r"^[#>*\-|`\s]+", "", text, flags=re.M)


def han_count(text: str) -> int:
    return len(re.findall(r"[一-鿿]", strip_md(text)))


def waived_snippets(book_dir: Path):
    p = book_dir / "03-文风" / "放行清单.md"
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
    if words < cfg["words_min"]:
        problems.append(f"字数 {words} < {cfg['words_min']}")
    elif words > cfg["words_max"]:
        warns.append(f"字数 {words} > {cfg['words_max']}（超上限，确认是否拆章）")

    hook = None
    bj = book_dir / "book.json"
    if bj.exists():
        try:
            d = json.loads(bj.read_text("utf-8"))
            hook = next((c.get("hook") for c in d.get("chapters", []) if c.get("seq") == seq), None)
        except json.JSONDecodeError:
            warns.append("book.json 解析失败，跳过钩子核对")
    if not hook or not hook.get("type") or not hook.get("intensity"):
        problems.append("book.json 未登记章尾钩子（type+intensity）")

    # AI 味分级
    waived = waived_snippets(book_dir)
    text = mask_waived(raw, waived)
    block = {k: len(re.findall(p, text)) for k, p in BLOCK_PATTERNS.items()}
    block = {k: v for k, v in block.items() if v}
    if block:
        problems.append("A 级五星句式（出现即须改，或把原句写进 03-文风/放行清单.md 并说明理由）："
                        + "，".join(f"{k}×{v}" for k, v in block.items()))
    high = {k: len(re.findall(p, text)) for k, p in HIGH_RISK_PATTERNS.items()}
    high = {k: v for k, v in high.items() if v}
    l1 = {w: text.count(w) for w in LEVEL1_WORDS if text.count(w)}
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

    k_warns, facts_used = knowledge_warnings(book_dir, text)
    warns += k_warns
    warns += avoidance_warnings(raw, cfg)
    warns += style_drift_lines(book_dir, raw)
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

    result = {
        "seq": seq, "file": str(f), "han_words": words,
        "band": [cfg["words_min"], cfg["words_max"]], "hook": hook,
        "ai": {"block": block, "high_risk": high, "level1": l1, "level2_per_1000": round(per_k, 1), "summary": summ,
               "waived_snippets": len(waived)},
        "rhythm_reference": rhythm,
        "facts_mentioned": facts_used,
        "promise_touches": [f"{i} {k}" for i, k in touches],
        "warnings": warns, "problems": problems, "pass": not problems,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if not problems else 1)


if __name__ == "__main__":
    main()
