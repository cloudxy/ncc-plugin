"""ncc_state.py — 书项目状态的确定性读写工具（书项目 schema 4；信息架构见 workflow/principles.md）。

状态只从这里（和经理派单回收）写入；视图（author-intent.md、current-focus.md、台账的 .md）由 render 生成，
脚本从不读视图当输入；正文永不回写状态。每次写操作后自动重新生成视图。
只依赖标准库。

书与闸门
  init <book> --title T [--genre a,b] [--chapters N] [--level {levels}] [--mode {modes}]
  status <book>                          状态摘要（退出码恒 0）
  next <book>                            第一个非 done 章（无则退出 1）
  migrate <book>                         旧书 → schema 4：按七律归位（.ncc/、_作者/、05-审稿/读者数据）；手写的角色记忆转成条目
  render <book>                          重新生成全部视图
  check <book>                           七律自查：视图与源头逐字一致、状态事件只追加、旧布局残留、圣经里的数据
  gate <book> soul|settings|outline|opening|volume|finale [--action check|pass|reject] [--quote Q] [--force]
  level <book> {levels}             引导档位
  mode <book> {modes}            写作模式（D15）
  soul <book> [--question Q] [--answer A] [--injustice I] [--ending E] [--status 暂定|确定] [--deadline D] [--arc {arcs}]
  contract <book> [--main M] [--extra X]... [--poison a,b] [--audience 目标读者]
  sign <book> <签约点> --ch N             签约点：{signing_points}

循环与收束（M3）
  unit open <book> --start N [--title T]   开一个剧情单元（10–40 章）
  unit close <book> --end N               关单元：须先有 00-策划/复盘/单元-Uk.md
  unit list <book>
  volume end <book> --end N               本卷写完，进入卷复盘（stage → volume），之后过 gate volume
  finale begin <book>                     进入收束（stage → finale），之后过 gate finale
  report <book> unit|volume|finale [--write]
                                         按台账生成复盘或收束清单的底稿；--write 写进对应文件的生成区块（判断写在区块外）
  feedback add <book> --ch N --source {feedback_sources} --kind {feedback_kinds} --value V [--note X] [--persona 画像]
  feedback list <book> [--ch N]
  team set <book> <位> <名字>              团队认领：{team_positions}
  team list <book>

场景卡（先审故事，后写文字；小批量，D16）
  scene next <book>                      按写作模式给出下一批要做场景卡的章（{scene_batch}）
  scene check <book> <seq>               校验 02-大纲/场景卡/ch-NNNN.md 的格式
  scene review <book> <seq>... --result pass|revise --by story-editor|author [--note N]
                                         可一次审一批；关键章须 --by author；有一张不合格则整批不写入

底蕴（M4，D3：场景触发、有据可依）
  knowledge plan <book> <seq>...         列出场景卡"知识"一栏，判断这一批要不要派 scholar
  knowledge check <book> <seq>...        校验 02-大纲/知识点/ch-NNNN.md（学科、来源、状态）
  era <book> {eras}     时代背景（机械检查的时代错置词据此启用）
  study <book> [--add 学科]               一书一深学

素材（M5：艺术源于生活；场景卡写"素材：M-0003"，写手包自动带上）
  material add <book> --content C --source S --use U [--trust {material_trust}] [--domain 学科]
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
  chapter mark <book> <seq> <status>     {chapter_states}
                                         （标 drafting 前，场景卡必须已过故事审且之后未改动）
  chapter mood <book> <seq> {tension} [--colors {colors}]
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

记忆与交接（M8：角色各有记忆；子代理按可见范围继承会话）
  memory add <book> --role R --kind {memory_kinds} --text T [--evidence E]... [--ch N]
                                         记一条角色记忆；独立证据不到两处先记为候选（约定除外）；相同正文合并证据，相近正文独立保存；
                                         写手与 editor 的记忆里不许有审稿判据词与书魂原文；作者偏好改用 pref
  memory reinforce <book> --role R <id> [--evidence E]... [--ch N] [--shared]
  memory merge <book> --role R --into ID <id>... [--text 合并后的说法] [--shared]
  memory edit <book> --role R <id> --text 修正后的说法 [--note N] [--shared]
  memory archive|restore <book> --role R <id> [--note N] [--shared]
  memory promote <book> [<id>...] --role R [--genre a,b]   进跨书记忆（不写编号则晋升够格的：独立证据 ≥3 处、已生效、不是本书约定）
  memory list <book> [--role R] [--all] [--shared]
  memory consolidate <book> [--role R] [--apply] [--shared]
                                         单元整理底稿：候选、可合并、久未出现、超上限、够格进跨书；--apply 自动归档久未出现的
  handoff add <book> --kind {handoff_kinds} --text T [--layer {handoff_layers}] [--ch N 或 A-B]
                                         会话交接卡：作者在会话里的原话、决定、情绪、待办（原话与决定要写作用层）
  handoff list <book> [--open] [--role R] [--ch N]     --role 时只列切给该角色的
  handoff close <book> <id> --to 去处 [--note N]        决定落进台账、场景卡、偏好或记忆后关掉
  recall <book> <词>... [--role R] [--from N] [--to M] [--top 10]
                                         在记忆、交接、场景卡、审稿报告、台账里全文检索；--role 按该角色的可见范围过滤
  brief <book> --role R [--seq N...] [--task T] [--persona 画像] [--note N]
                                         其余角色的派单头 .ncc/派单/：本角色记忆、作者刚说的、技法参考（写手用 pack）

设定类目（M10：门派、种族、血脉、企业……按题材研判）
  setting catalog <book>                 类目表：别名、必填字段；标出与本书题材相关的
  setting use <book> <类目>... --why 它会怎么进剧情
  setting new <book> <名称> --required a,b,c [--optional x,y] [--alias 别名] --why W --gap 为什么现有类目装不下
  setting none <book> --why W            一个类目都不用（如纯日常）
  setting drop <book> <类目>
  setting add <book> <类目> <名字>         按字段建卡 01-设定/类目/<类目>/<名字>.md
  setting list|check <book>              check：研判做了没有、选用的类目有没有卡、必填字段、进没进词典、卡里的数字

拆书与技法（M9：拆完一段学写法）
  decon index <拆书库/书名> [--source 原文/文件] [--config 配置] [--accept-reindex]
                                         唯一 seq/span/hash；跳号/短章警告，结构阻塞不可 force 绕过
  decon plan <拆书库/书名> [--goal structure|technique|full|transfer] [--select A-B,C --reason 理由] [--screenplay A-B|none]
                                         骨架、默认最多27关键章、明确全章或只读转化；无参数查看已有计划
  decon packet <拆书库/书名> [seq] [--layer L2|L3] [--framework 总纲文件] [--context 上下文] [--independent]
  decon ingest <拆书库/书名> [章JSON] [--layer L2|L3] [--recover]
                                         文件/条目/场次验收入库；从原子验收收据恢复台账和逐章进度
  decon mark <拆书库/书名> --done A-B | --skip N --why W [--layer L2|screenplay]
                                         旧库记 legacy；新层不绕过产物验收
  decon coverage <拆书库/书名> [--layer L0|L1|L2|L3|screenplay|legacy]
  decon stats <拆书库/书名> [--range A-B] [--layer L1|L2] [--write]
                                         全书/连续范围/稀疏样本分开；局部报告不覆盖全书基线
  decon link <book> <对标书名>                               本书的对标书（单元复盘拿它的基线作参照）
  technique add <书库或书目录> --kind {technique_kinds} --method 手法 --how 怎么做 --evidence "拆:书名 第N章「定位词」"...
                --applies "题材=a,b；阶段={technique_stages}；契约=…；承诺=…" --cost 代价与失效 --confidence {confidence}
                --source 来源书 [--data D] [--title T]
                                         写一张技法卡（只用自己的话；和原文连续重合超过 15 字就拒绝）
  technique check|list <书库或书目录> [--kind K]
  technique match <book> --role R [--seq N...]   给该角色挑卡（按题材、阶段、契约、承诺类型；同一本对标书最多两张）
  technique result <书库或书目录> <id> --outcome good|bad --note N [--ch N] [--book 书名]
  technique retire|restore <书库或书目录> <id> [--note N]

进化（M11：记忆自动、规则设闸）
  evolve propose <书库或书目录> --key K --value=V --why W --evidence E... [--parent 内置技法类别]
                                         词表增删写 --value=+词,-词（带等号，免得 -词 被当成选项）
  evolve eval <书库或书目录> <id>         评测＋作者确认档：锚定章回归，改动前后对比，变差就拒绝
  evolve apply <书库或书目录> <id> --quote 作者原话      写进作者覆盖层 _作者/进化/覆盖.json
  evolve reject|revert <书库或书目录> <id> [--note N]
  evolve list <书库或书目录> [--open]
  evolve rules <书库或书目录>            实际值与来源：插件默认 < 书库配置 < 作者覆盖 < 本书配置
  evolve scan <书库或书目录> [--propose]  从各书的证据里找规则级改动的苗头

书库与导出（M7）
  dashboard <书库根目录> [--bucket 10] [--html 文件]
                                         多书仪表盘：每本书的阶段、进度、存稿、承诺健康度，以及承诺热力图（每格 N 章里建立、推进、兑现的次数）
  export <book> [--format md|txt|epub] [--from N] [--to M] [--author A]
                                         合稿与导出到 07-导出/：只收已定稿的章；去掉修订注记；epub 为 EPUB 3（附 NCX 目录）

其他
  sha <file>

评测与模型横评见 scripts/ncc_eval.py。
环境变量 NCC_ACTOR：团队模式下写入操作日志（.ncc/操作日志.jsonl）的操作者名字。"""

import argparse
import json
import os
import sys
from pathlib import Path
from .core import MODES, OPLOG, SCHEMA, V, die, now, read_json
from .views import render

from .cli_parsers import COMMAND_ORDER, REGISTRARS

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


def build_parser():
    words = {k: "|".join(v) for k, v in V.items() if isinstance(v, list)}   # 词表只在注册表里写一份
    words.update(modes="|".join(MODES), colors=",".join(V["colors"]), scene_batch="、".join(f"{m} {n}" for m, n in V["scene_batch"].items()))
    ap = argparse.ArgumentParser(description=__doc__.format(**words), formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    for name in COMMAND_ORDER:
        REGISTRARS[name](sub)
    return ap


def main():
    a = build_parser().parse_args()
    from .database_bridge import dispatch
    try:
        code = dispatch(Path(__file__).resolve().parents[1] / 'ncc_state.py', sys.argv[1:],
                        [getattr(a, key, None) for key in ('book_dir', 'lib', 'lib_dir', 'root', 'path')])
    except ValueError as exc:
        die(str(exc))
    if code is not None:
        raise SystemExit(code)
    a.fn(a)
    log_op(a)
    auto_render(a)


READ_ONLY = {("status", None), ("next", None), ("report", None), ("sha", None), ("water", None),
             ("reader-now", None), ("scene", "check"), ("scene", "next"), ("knowledge", "plan"), ("knowledge", "check"), ("promise", "list"), ("know", "list"),
             ("fact", "get"), ("fact", "list"), ("feedback", "list"), ("team", "list"), ("unit", "list"),
             ("material", "list"), ("material", "check"), ("heat", None), ("pref", "show"), ("dashboard", None),
             ("export", None), ("words", None), ("event", "list"), ("memory", "list"), ("handoff", "list"), ("recall", None),
             ("setting", "catalog"), ("setting", "list"), ("setting", "check"), ("decon", "coverage"),
             ("technique", "check"), ("technique", "list"), ("technique", "match"), ("evolve", "list"), ("evolve", "rules")}


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
