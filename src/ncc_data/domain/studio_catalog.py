"""Stateless studio catalog: codex groups, commons cards, market playbooks, pipeline presets.

No database, no network, and no copyrighted text. Cards are original working notes
derived from NCC's own narrative method.
"""

import re

from ncc_shared.errors import require

# Exact Unicode Script=Han ranges matching ECMAScript /\p{Script=Han}/gu (including U+3007 〇 and U+3005 々).
_HAN_RE = re.compile(
    "["
    "\u2e80-\u2e99\u2e9b-\u2ef3\u2f00-\u2fd5\u3005\u3007\u3021-\u3029\u3038-\u303b"
    "\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufa6d\ufa70-\ufad9"
    "\U00016fe2-\U00016fe3\U00016ff0-\U00016ff6"
    "\U00020000-\U0002a6df\U0002a700-\U0002b81d\U0002b820-\U0002cead"
    "\U0002ceb0-\U0002ebe0\U0002ebf0-\U0002ee5d\U0002f800-\U0002fa1d"
    "\U00030000-\U0003134a\U00031350-\U00033479"
    "]"
)


def count_han_chars(text: str | None) -> int:
    """Count CJK Ideographs (汉字), matching CLI han_words and frontend countHanChars."""
    if not text:
        return 0
    return len(_HAN_RE.findall(text))


def _pos_int(data: dict | None, default: int = 0) -> int:
    value = (data or {}).get("position", default)
    if isinstance(value, bool) or not isinstance(value, int):
        return default
    return value


def ordered_book_chapters(volumes: list[dict], chapters: list[dict]) -> list[dict]:
    """Order chapters across the whole book and attach 1-based `book_order`.

    Loose chapters (no valid volume `parent_id`) appear before volume-grouped chapters,
    matching VolumeRail. Volumes sort by `(position, id)`, chapters within each container
    sort by `(position, id)`. Flat legacy books without volumes and with positive positions
    preserve explicit gaps (e.g. a single chapter at position=4 stays chapter 4).
    """
    sorted_vols = sorted(
        volumes or [],
        key=lambda v: (_pos_int(v.get("data") if "data" in v else v), str(v.get("id") or "")),
    )
    vol_rank = {str(v["id"]): idx for idx, v in enumerate(sorted_vols) if v.get("id")}

    def sort_key(ch: dict):
        data = ch.get("data") if isinstance(ch.get("data"), dict) else ch
        parent_id = str(data.get("parent_id") or "")
        group = vol_rank.get(parent_id, -1)
        pos = _pos_int(data, 0)
        return (group, pos, str(ch.get("id") or ""))

    ordered = [dict(ch) for ch in sorted(chapters or [], key=sort_key)]
    has_volumes = bool(vol_rank) or any(
        bool((c.get("data") if isinstance(c.get("data"), dict) else c).get("parent_id"))
        for c in ordered
    )
    raw_positions = [
        _pos_int(c.get("data") if isinstance(c.get("data"), dict) else c, 0) for c in ordered
    ]
    legacy_one_based = not has_volumes and bool(raw_positions) and min(raw_positions) >= 1
    for idx, ch in enumerate(ordered):
        raw_pos = raw_positions[idx]
        ch["book_order"] = max(idx + 1, raw_pos) if legacy_one_based else idx + 1
    return ordered

COMMONS_CATEGORIES = (
    {"id": "writing_routine", "label": "写作套路"},
    {"id": "character_portrait", "label": "人物描摹"},
    {"id": "plot_direction", "label": "剧情走向"},
    {"id": "character_arc", "label": "人物弧光"},
    {"id": "psychology", "label": "心理分析"},
    {"id": "relationship", "label": "关系分析"},
    {"id": "philosophy", "label": "哲学思考"},
    {"id": "management", "label": "管理"},
    {"id": "finance", "label": "财务"},
    {"id": "technology", "label": "技术"},
    {"id": "art", "label": "艺术"},
    {"id": "environment", "label": "环境"},
)

CODEX_GROUPS = (
    {
        "id": "characters",
        "label": "人物与角色职业",
        "description": "人物、身份、法师与弧光。先写欲望、恐惧和关系位置，再写外貌。",
        "kinds": ["人物", "身份", "法师", "人物弧", "动机", "秘密", "血脉", "体质", "语言风格", "character"],
        "recommended_fields": ["motivation", "psychology", "arc_type", "voice", "factions", "pov"],
    },
    {
        "id": "beings",
        "label": "种族与异界生物",
        "description": "种族、妖兽、魔兽、异界生物与亡灵。每一种都要有栖息地、代价和不能做的事。",
        "kinds": ["种族", "妖兽", "魔兽", "异世界生物", "亡灵", "鬼", "魔", "异族人", "神兽", "灵宠", "妖", "兽", "精怪"],
        "recommended_fields": ["habitat", "limitations", "factions", "description"],
    },
    {
        "id": "techniques",
        "label": "功法技能与特效",
        "description": "功法、技能、特效、法术、神通、阵法与符箓。力量必须带限制和可见后果。",
        "kinds": ["功法", "技能", "特效", "法术", "神通", "阵法", "符箓", "境界", "招式"],
        "recommended_fields": ["limitations", "side_effects", "usage_guide", "description"],
    },
    {
        "id": "artifacts",
        "label": "丹药武器与器物",
        "description": "丹药、现代武器、法宝、道具、异火与配方。写清来源、用量和用完之后世界少了什么。",
        "kinds": ["丹药", "现代武器", "法宝", "武器", "器物", "道具", "异火", "配方", "丹方", "item"],
        "recommended_fields": ["limitations", "side_effects", "cost", "usage_guide"],
    },
    {
        "id": "places",
        "label": "场景地图与都市舞台",
        "description": "场景、地图、都市、城池、秘境、拍卖会与战场。地点要能逼人物做选择。",
        "kinds": ["场景", "地图", "都市", "城池", "秘境", "拍卖会", "拍卖行", "战场", "scene", "location"],
        "recommended_fields": ["description", "plotline", "hook"],
    },
    {
        "id": "orders",
        "label": "组织势力与世界规则",
        "description": "宗门、帝国、商会、法则、制度与货币。规则先于奇观，违约要有可见代价。",
        "kinds": ["组织", "势力", "宗门", "帝国", "商会", "法则", "制度", "货币", "家族", "王朝", "organization"],
        "recommended_fields": ["factions", "limitations", "description"],
    },
)

PIPELINE_PRESETS = (
    {"id": "plan_only", "label": "只推演细纲", "stages": ["plan"]},
    {"id": "plan_and_review", "label": "细纲并审结构", "stages": ["plan", "judge_plan"]},
    {"id": "write_only", "label": "只起草正文", "stages": ["write"]},
    {"id": "write_and_judge", "label": "起草并审评", "stages": ["write", "judge"]},
    {"id": "write_judge_revise", "label": "起草、审评并返修", "stages": ["write", "judge", "revise"]},
    {"id": "judge_only", "label": "只做审评", "stages": ["judge"]},
    {"id": "revise_and_judge", "label": "按批注返修并复评", "stages": ["revise", "judge"]},
    {
        "id": "full_pipeline",
        "label": "全流程一条龙",
        "stages": ["plan", "judge_plan", "write", "judge", "revise"],
    },
)

_PLAYBOOK_FIELDS = (
    "id",
    "name",
    "core_hook",
    "pacing_3_10_30",
    "hook_mix",
    "midgame_trap",
    "poison_list",
    "target_words_band",
)


def _card(card_id, category, title, summary, structure, hint, pitfalls, tags):
    return {
        "id": card_id,
        "category": category,
        "title": title,
        "summary": summary,
        "structure": structure,
        "ai_prompt_hint": hint,
        "pitfalls": pitfalls,
        "tags": tags,
    }


PUBLIC_COMMONS_CARDS = (
    _card(
        "routine-choice-cost",
        "writing_routine",
        "选择与代价",
        "每场只让人物做一个不可两全的选择，并立刻付出看得见的代价。",
        ["场初给出两难，两边都有损失", "人物用行动而不是声明做出选择", "代价落在关系、资源或时间上", "场末留下一个未付清的后果"],
        "把这场写成一次选择。不要新增设定解释。代价必须能在下一场被碰到。",
        ["两边都没有损失，选择是假的", "用旁白宣布人物成长", "代价留到很久以后才补"],
        ["节拍", "代价", "场景"],
    ),
    _card(
        "routine-chapter-hook",
        "writing_routine",
        "章尾五类钩",
        "章尾只留一个问题：危险、信息、关系、期限或反转，并让读者知道下一章能碰到它。",
        ["先收束本章的行动", "把未付清的后果推到门口", "用一句具体事实而不是感叹收尾", "不要同时埋三个新谜"],
        "给本章写一个章尾钩。类型只能是危险、信息、关系、期限、反转之一，并点名下一章会碰到的人或物。",
        ["以抒情空镜收束", "钩子与本章选择无关", "连续多章使用同一种钩"],
        ["钩子", "追读", "章节"],
    ),
    _card(
        "portrait-want-wound",
        "character_portrait",
        "欲望与伤口",
        "人物卡先写想要什么、害怕失去什么、旧伤口如何歪曲判断。外貌只服务于这三件事。",
        ["一句公开目标", "一句不肯承认的需要", "伤口触发时会做错的具体动作", "说话时会避开的词"],
        "按欲望、恐惧、伤口、口癖四行写人物，不要写完整小传。",
        ["只堆外貌和头衔", "伤口不改变任何选择", "所有人物同一套语气"],
        ["人物", "欲望", "伤口"],
    ),
    _card(
        "portrait-status-voice",
        "character_portrait",
        "身份与声口",
        "身份决定人物能说的话和不能说的话。声口来自职业、阶层和隐瞒，不来自形容词。",
        ["对上、对下、对敌人各一句", "一句因为身份说不出口的话", "一个反复出现的具体用词", "删掉不影响身份的外貌"],
        "改写这段对白，使说话人的身份不用旁白也能听出来。保留原信息。",
        ["用口音拼写代替性格", "身份只在介绍时出现一次", "人人都说作者的句子"],
        ["对白", "身份", "声口"],
    ),
    _card(
        "plot-three-rockets",
        "plot_direction",
        "前三、前十、前三十",
        "前3章给出主角的亏欠与第一次选择，前10章给出可重复的爽点杠杆，前30章让杠杆碰到更大的规则。",
        ["3章内：损失、选择、第一次小胜", "10章内：杠杆可被复用，对手记住了主角", "30章内：杠杆撞上制度或更强规则", "每一级都回收上一级的一个承诺"],
        "检查大纲是否在第3、10、30章改变了人物的选择成本。缺哪一级就补哪一级，不要重写全书。",
        ["开局只介绍世界观", "十章后仍在重复第一次胜利", "三十章没有新的规则压力"],
        ["节奏", "大纲", "杠杆"],
    ),
    _card(
        "plot-line-weight",
        "plot_direction",
        "明线暗线灰线",
        "明线是读者正在追的目标，暗线是作者知道而读者只看见迹象的因果，灰线是人物自己误判的解释。",
        ["明线用目标句写清", "暗线只记埋设章、迹象和计划兑现章", "灰线写成人物的错误信念", "同时活跃的暗线不超过五条"],
        "把材料分成明线、暗线、灰线。暗线只写迹象，不要在正文里解释真相。",
        ["暗线在埋设当章被说破", "灰线和暗线写成同一件事", "活暗线多到作者自己对不上"],
        ["线索", "伏笔", "误导"],
    ),
    _card(
        "arc-belief-break",
        "character_arc",
        "信念断裂",
        "弧光不是人变好，而是人物靠以生存的信念被事实打断，然后用新的行动付一次更大的代价。",
        ["开局信念能解释早期胜利", "中段用一次损失证明信念不够", "低谷时人物仍想守住旧信念", "终局用相反的行动完成选择"],
        "标出这个人物的旧信念、打断它的事件、以及新行动。不要写成性格说明书。",
        ["弧光只在总结段出现", "没有损失就宣布成长", "配角突然承担主角的转变"],
        ["弧光", "信念", "终局"],
    ),
    _card(
        "arc-flat-pressure",
        "character_arc",
        "扁平人物的压力弧",
        "有的主角信念不变。弧光就放在世界对他的压力上：代价变重，选择仍然相同，但读者看见他为此失去什么。",
        ["信念用一句否定句写死", "每卷提高一次遵守信念的价格", "旁人因他的坚持受伤或获益", "结局不奖励口头改变"],
        "不要修改主角信念。只提高下一场遵守信念的代价，并写出谁为此付出。",
        ["为了显得深刻而强行洗白", "代价不落在具体的人身上", "信念每章都变"],
        ["扁平弧", "代价", "坚持"],
    ),
    _card(
        "psyche-trigger",
        "psychology",
        "触发与防御",
        "心理只在触发时可见：一个感官细节激活旧伤，人物用习惯的防御动作保护自己，并因此误判眼前的人。",
        ["触发物必须具体", "防御是动作或沉默，不是诊断术语", "误判改变本场选择", "场末留下未处理的情绪事实"],
        "写这个人物被触发后的第一动作和因此看错的人。不要使用临床标签。",
        ["用病名代替行为", "触发了却不影响选择", "所有伤口都在同一章治愈"],
        ["心理", "触发", "误判"],
    ),
    _card(
        "psyche-need-vs-want",
        "psychology",
        "想要与需要",
        "想要是人物说得出口的目标，需要是他不肯要的关系或承认。故事让想要的成功妨碍需要。",
        ["想要用外部目标衡量", "需要用一句他拒绝的话写出", "一次胜利同时损害需要", "结局二选一，不两头都给满"],
        "列出想要和需要。设计一场胜利，使想要达成时需要被损害。",
        ["想要和需要写成同义词", "人物开场就明白主题", "结局把两样都奖励掉"],
        ["动机", "主题", "选择"],
    ),
    _card(
        "relation-debt",
        "relationship",
        "关系债务",
        "关系用未还清的行为记账：谁欠谁一个行动、一次沉默或一个秘密。好感不是关系。",
        ["写下债务的具体行为", "标明债权人与债务人", "安排一次偿还或赖账", "赖账要改变下一次合作"],
        "不要写他们关系很好。写出一笔还没清的债务，以及本场还是不还。",
        ["用关系标签代替事件", "债务从不影响行动", "所有关系都靠误会维持"],
        ["关系", "债务", "信任"],
    ),
    _card(
        "relation-triangle-pressure",
        "relationship",
        "三角压力",
        "第三方不是花瓶。他改变两人之间的成本：公开、站队或保密都会让某一方损失。",
        ["第三方有自己的目标", "他掌握一份两人不知道的事实或资源", "站队会伤害其中一方", "本场结束时联盟和开场不同"],
        "加入一个有自己目标的第三方，让原来的两人必须重新选择站队。",
        ["第三方只负责赞美主角", "三角变成无代价的感情说明", "三人目标完全一致"],
        ["三角", "站队", "联盟"],
    ),
    _card(
        "philosophy-rule-case",
        "philosophy",
        "规则与个案",
        "主题用一次具体违约来问：这条规则保护谁，压垮谁。不要让人物发表主题演讲。",
        ["先写规则保护的人", "再写被规则压垮的一个人", "主角必须执行或打破规则", "后果同时落到两边"],
        "把主题写成一条人们正在遵守的规则，并给一个它保护不了的人。",
        ["作者跳出来总结", "规则没有保护对象", "打破规则却没有后果"],
        ["主题", "规则", "个案"],
    ),
    _card(
        "philosophy-limit-of-good",
        "philosophy",
        "善的限度",
        "善意要有边界。人物做好事时必须拿走另一样他在乎的东西，读者才看见价值而不是姿态。",
        ["善意的行动写具体", "被牺牲的事物也具体", "受益者不是抽象的人民", "人物事后不自我表彰"],
        "让人物完成一件好事，并明确他为此永久失去什么。",
        ["善良不付代价", "用演讲证明人物高尚", "牺牲的是不在场的陌生人且无人记住"],
        ["价值", "牺牲", "善意"],
    ),
    _card(
        "management-decision-rights",
        "management",
        "决策权",
        "组织戏先写谁有权拍板、谁提供信息、谁承担后果。会议不是聊天，是一次权力使用。",
        ["标明拍板人", "信息持有者与拍板者不是同一人", "反对意见改变一个条款或被明确压下", "后果指定到人"],
        "把这场会议收成一个决定。写清谁签字，谁不同意，谁明天去执行。",
        ["众人轮流表态却没有决定", "权力只靠头衔介绍", "决定不影响任何资源"],
        ["组织", "会议", "权责"],
    ),
    _card(
        "management-span",
        "management",
        "管辖幅度",
        "一个人直接指挥的人有限。超过幅度，命令就会被延误、曲解或中饱。这是冲突的来源。",
        ["写出直接下属的人数或层级", "命令经过谁的嘴", "指出延误发生的那一环", "主角只能修理一个环节"],
        "不要增加新部门。写出命令从发出到执行多出来的那一个人，以及他如何改动命令。",
        ["主角一声令下全图响应", "组织无限可靠", "腐败没有具体的经手人"],
        ["组织", "命令", "层级"],
    ),
    _card(
        "finance-cash-cycle",
        "finance",
        "现金循环",
        "钱从谁手里来、在谁手里过夜、何时必须离开。断一天，就有一个具体的人过不下去。",
        ["标明收入来源", "标明必须支付的日期和对象", "安排一次提前或拖欠", "拖欠改变人物的选择"],
        "给这个势力写三笔账：一笔收入、一笔到期支出、一笔还没到的债。不要写完整财政史。",
        ["财富只是一个巨大数字", "开支没有收款人", "缺钱却从不改变行动"],
        ["金钱", "期限", "债务"],
    ),
    _card(
        "finance-price-signal",
        "finance",
        "价格是消息",
        "价格变动是有人知道了角色还不知道的事。写价格，就要写谁因此改了买卖。",
        ["给出前后两个价格", "指出先行动的买家或卖家", "主角晚知道一步", "他的补救要花掉另一项资源"],
        "用一次价格变化透露一条消息。不要解释经济学，写谁在涨价前搬走了货。",
        ["价格永不变化", "用讲座代替交易", "主角总能第一个知道"],
        ["市场", "价格", "信息差"],
    ),
    _card(
        "technology-constraint",
        "technology",
        "技术约束",
        "技术先写它做不到什么、依赖什么、坏了由谁修理。新器具只解决一个旧问题，并带来一个新问题。",
        ["做不到的事写在能做的事前面", "依赖一种会耗尽的材料或手艺", "修理人有名字或职位", "使用后留下可见的新麻烦"],
        "给这件技术补三条：不能做的事、依赖的材料、用一次产生的新问题。",
        ["技术无代价地解决剧情", "只有发明者能使用且从不失灵", "原理说明长过行动"],
        ["技术", "约束", "故障"],
    ),
    _card(
        "technology-procedure",
        "technology",
        "工序可见",
        "读者相信手艺，是因为看见步骤和出错点。省略中间步骤，就不要声称它很精湛。",
        ["列出三到五个可见步骤", "其中一步容易失败", "失败的痕迹留在物体上", "旁人能据此判断水平"],
        "把这项手艺写成现场步骤。删掉原理课，留下一个会失败的动作。",
        ["用很精湛三个字代替过程", "步骤永不失败", "成品没有制作痕迹"],
        ["手艺", "步骤", "失败"],
    ),
    _card(
        "art-form-function",
        "art",
        "形式为场面服务",
        "景物、服饰和歌曲只保留能改变本场距离、身份或情绪的细节。其余删掉。",
        ["选择一个感官", "细节指向身份或危险", "人物对它做出反应", "不反应的描写删去"],
        "把这段景物收成一个会改变人物下一步的细节。",
        ["开场风景与正文无关", "每件衣服都写全套", "用形容词堆砌气氛"],
        ["景物", "细节", "删减"],
    ),
    _card(
        "art-motif-return",
        "art",
        "母题回声",
        "同一个具体物件出现三次：第一次是事实，第二次变味，第三次成为选择的理由。",
        ["物件要小、可携带或可看见", "第二次的意义和第一次不同", "第三次迫使人物动手或放手", "不要另起一个象征来解释它"],
        "选定一个已经出现的物件，写出它下一次意义如何改变。不要新造象征。",
        ["象征只出现一次", "作者直接解释含义", "每次都换成新物件"],
        ["母题", "物件", "回声"],
    ),
    _card(
        "environment-pressure",
        "environment",
        "环境压力",
        "天气、地形和资源不是背景板。它们限制本场能走的路、能带的东西和能躲的时间。",
        ["写出一个硬限制", "人物因此改路线或改时机", "限制对双方不一定公平", "场末环境比场初更差或被利用"],
        "给这场加一个环境限制，并让原计划因此少一个选项。",
        ["天气只负责抒情", "地形不影响追逃", "资源无限"],
        ["环境", "地形", "资源"],
    ),
    _card(
        "environment-season-clock",
        "environment",
        "季节是时钟",
        "季节提供期限：播种、封路、涨水、取暖。期限比反派的威胁更难讨价还价。",
        ["标明还有多少天或哪一季", "到期时会发生的具体变化", "准备行动占用另一件要事", "错过之后不能用同一方法补救"],
        "把季节写成一个到期日。写出错过之后哪条路会消失。",
        ["季节永远停在方便剧情的那一天", "期限到了却没有变化", "主角不受供给影响"],
        ["季节", "期限", "供给"],
    ),
)

MARKET_PLAYBOOKS = (
    {
        "id": "xuanhuan-slow-longevity",
        "name": "东方玄幻·苟道长生",
        "core_hook": "主角用更低的暴露换更长的活路，每一次示弱都换到一项可积累的生存资源。",
        "pacing_3_10_30": "3章内死过一次或差点死；10章内建立可重复的隐蔽收益；30章内隐蔽收益被更大的搜索规则盯上。",
        "hook_mix": "期限与信息为主，危险次之，关系用来暴露身份，少用空反转。",
        "midgame_trap": "三十万字后仍在换地图重复同一种捡漏，旧仇和旧规则不再升级。",
        "poison_list": ["无代价的系统奖励", "敌人集体降智", "主角主动暴露后毫无后果"],
        "target_words_band": [2800, 4200],
    },
    {
        "id": "xuanhuan-force",
        "name": "东方玄幻·极道横推",
        "core_hook": "主角用一次更狠的公开行动打碎当前层级的面子，并立刻承担报复。",
        "pacing_3_10_30": "3章内完成一次公开打脸；10章内报复落到身边的人；30章内打脸对象换成制度而不是单个废物。",
        "hook_mix": "危险和关系对半，信息用来预告报复，反转只用于规则本身。",
        "midgame_trap": "对手永远比上一场更弱，主角没有失去任何盟友。",
        "poison_list": ["连续羞辱无还手之力的人", "胜利不带来仇恨", "实力跳跃没有修炼或代价"],
        "target_words_band": [3000, 4500],
    },
    {
        "id": "mystery-rules",
        "name": "诡秘悬疑·规则序列",
        "core_hook": "读者先看见一条会杀人的规则，再看见主角用规则的空档活过一次，空档本身是下一道规则。",
        "pacing_3_10_30": "3章内规则杀死或标记一个人；10章内主角靠遵守而不是蛮力活下来；30章内规则的制定者露出利益。",
        "hook_mix": "信息钩最多，危险钩收束，关系钩用来怀疑同伴，期限钩用来限制试错。",
        "midgame_trap": "规则越加越多，却不再回收旧规则，读者记不住哪条还有效。",
        "poison_list": ["规则开口就解释全部真相", "主角靠外挂无视规则", "恐怖只来自形容词"],
        "target_words_band": [2800, 4000],
    },
    {
        "id": "urban-martial-ascent",
        "name": "都市高武·阶层跃迁",
        "core_hook": "力量提升改变的是主角付得起的账单和进得去的门，不是抽象战力。",
        "pacing_3_10_30": "3章内一场公开测验或冲突；10章内资源门槛挡住他；30章内他用新身份进入旧阶层进不去的场。",
        "hook_mix": "关系与期限为主，危险用来保护具体的人，信息用来透露阶层规则。",
        "midgame_trap": "城市背景消失，只剩一层层打怪，亲人和账单不再出现。",
        "poison_list": ["现代社会对力量毫无反应", "金钱和证件永远够用", "女性和路人只负责震惊"],
        "target_words_band": [2500, 4000],
    },
    {
        "id": "history-court",
        "name": "历史朝堂·权谋种田",
        "core_hook": "一次小治理的成功换来朝堂的注意，注意本身带来更大的摊派或怀疑。",
        "pacing_3_10_30": "3章内一件民生难题被接住；10章内本地收益引来上级；30章内制度冲突压过个人能力。",
        "hook_mix": "期限和关系为主，信息是奏折与谣言，危险少而具体。",
        "midgame_trap": "种田数字越来越大，朝廷和人都不记得最初的债。",
        "poison_list": ["主角全知全能", "对手不会算账", "历史人物被写成工具人"],
        "target_words_band": [3000, 4500],
    },
    {
        "id": "infinite-dungeon",
        "name": "诸天无限·副本双螺旋",
        "core_hook": "副本里赢得的能力必须在主世界付出关系或身份成本，两条线互相欠债。",
        "pacing_3_10_30": "3章内规则杀一个人；10章内主世界的损失反馈进副本；30章内副本奖励改变主世界的阵营。",
        "hook_mix": "危险与信息在副本，关系和期限在主世界，交替出现。",
        "midgame_trap": "副本一套、现实一套，奖励永不带回主世界。",
        "poison_list": ["副本规则中途改口", "队友死亡没有后续", "奖励直接解决主线"],
        "target_words_band": [3000, 4500],
    },
    {
        "id": "western-mage",
        "name": "西幻魔兽·法师史诗",
        "core_hook": "法术是一笔有材料、有学徒、有政治后果的公共技术，不是个人灯光。",
        "pacing_3_10_30": "3章内一次法术失败或成功改变一个小队；10章内材料或学徒链条绷紧；30章内法术传统与王国利益冲突。",
        "hook_mix": "信息钩写规则，危险钩写远征，关系钩写师承与阵营。",
        "midgame_trap": "魔法无限制升级，组织和生态不再被波及。",
        "poison_list": ["法术没有材料和失误", "异族只是经验包", "史诗场面没有个人选择"],
        "target_words_band": [3200, 4800],
    },
)


def catalog_payload():
    return {
        "codex_groups": [dict(item) for item in CODEX_GROUPS],
        "commons_categories": [dict(item) for item in COMMONS_CATEGORIES],
        "commons_cards": [dict(item) for item in PUBLIC_COMMONS_CARDS],
        "market_playbooks": [dict(item) for item in MARKET_PLAYBOOKS],
        "pipeline_presets": [dict(item) for item in PIPELINE_PRESETS],
    }


def commons_card(card_id):
    return next((dict(item) for item in PUBLIC_COMMONS_CARDS if item["id"] == card_id), None)


def market_playbook(playbook_id):
    return next((dict(item) for item in MARKET_PLAYBOOKS if item["id"] == playbook_id), None)


def producer_guidance(payload, scope_config=None):
    """Public card and playbook text for the model. Tokens and secrets are not read here."""
    cards = []
    for card_id in payload.get("builtin_commons_ids") or []:
        card = commons_card(card_id)
        require(card is not None, "commons_card", f"未知的内置公共陈列卡：{card_id}")
        cards.append(card)
    market = {}
    if isinstance(scope_config, dict):
        raw = scope_config.get("studio_market") or {}
        market = raw if isinstance(raw, dict) else {}
    playbook_id = (payload.get("market_playbook_id") or market.get("playbook_id") or "").strip()
    playbook = None
    if playbook_id:
        playbook = market_playbook(playbook_id)
        require(playbook is not None, "market_playbook", f"未知的赛道母本：{playbook_id}")
    return {
        "guidance": payload.get("guidance") or "",
        "beat_outline": payload.get("beat_outline") or "",
        "cards": cards,
        "playbook": playbook,
        "market_config": market,
    }


_RESOLVED_STATUSES = {"resolved", "已兑现", "兑现", "已回收", "完全兑现"}
_DROPPED_STATUSES = {"dropped", "abandoned", "作废", "已作废", "放弃"}
_UNPLANTED_STATUSES = {"planned", "待埋设", "未埋设"}
_PLANTED_STATUSES = {"active", "推进中", "已埋设", "悬置", "due_soon", "临期预警", "overdue", "超期未回收"}


def foreshadow_lifecycle(data, max_written_chapter):
    """Evaluate both planting state and due/overdue reminder state independently.

    Returns ``{"planted": bool, "due_state": str, "alert_state": str}`` where:
    - ``planted`` is True iff the foreshadow/hidden line has actually been planted in the text
      and is not yet resolved/dropped (explicit ``待埋设`` / ``planned`` / future ``planted_chapter``
      keeps ``planted=False`` even when ``expected_chapter`` is due or overdue).
    - ``due_state`` is ``"overdue"``, ``"due_soon"``, or ``"none"`` based on ``expected_chapter``
      relative to ``max_written_chapter`` (unless ``planted_chapter`` is explicitly in the future
      or the row is already resolved/dropped).
    - ``alert_state`` is one of ``"resolved"``, ``"dropped"``, ``"overdue"``, ``"due_soon"``,
      ``"active"``, or ``"planned"``.
    """
    data = data or {}
    status = str(data.get("status") or "").strip()
    if status in _RESOLVED_STATUSES:
        return {"planted": False, "due_state": "none", "alert_state": "resolved"}
    if status in _DROPPED_STATUSES:
        return {"planted": False, "due_state": "none", "alert_state": "dropped"}

    expected = data.get("expected_chapter")
    planted_ch = data.get("planted_chapter")
    expected_ok = isinstance(expected, int) and not isinstance(expected, bool)
    planted_ok = isinstance(planted_ch, int) and not isinstance(planted_ch, bool)
    written = max_written_chapter if isinstance(max_written_chapter, int) else 0

    if planted_ok and written < planted_ch:
        return {"planted": False, "due_state": "none", "alert_state": "planned"}

    if status in _UNPLANTED_STATUSES:
        is_planted = False
    elif planted_ok:
        is_planted = written >= planted_ch
    elif status in _PLANTED_STATUSES:
        is_planted = True
    elif expected_ok and status == "":
        is_planted = True
    else:
        is_planted = False

    if expected_ok and written > expected:
        due_state = "overdue"
    elif expected_ok and 0 <= expected - written <= 3:
        due_state = "due_soon"
    else:
        due_state = "none"

    if due_state != "none":
        alert_state = due_state
    elif is_planted:
        alert_state = "active"
    else:
        alert_state = "planned"

    return {"planted": is_planted, "due_state": due_state, "alert_state": alert_state}


def foreshadow_alert_state(data, max_written_chapter):
    """Compare a foreshadow row with the latest written chapter index."""
    return foreshadow_lifecycle(data, max_written_chapter)["alert_state"]
