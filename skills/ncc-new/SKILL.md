---
name: ncc-new
description: "Use this skill to start a new book: S0 founding (author seeds first, optional scout directions grown from them, three-layer intake Q&A, the four soul questions with candidates, genre contract and poison list; G0 soul gate) and S1 skeleton (writing mode, character engine with interviews and protagonist arc, settings freeze G1, outline freeze G2 scaled to the mode). Every decision point offers a recommendation and alternatives. Stops at author confirmation points."
when_to_use: "User wants to start a new novel, has only a vague idea for one, or says /ncc-new. Do NOT use for continuing, reviewing or deconstructing."
---

# 开书（S0 立书 → S1 立骨）

目标：把一个想法——哪怕只是一句模糊的话——变成**可连载的冻结起点**：书魂闸（G0）、设定冻结（G1）、大纲冻结（G2），然后交给 ncc-write 写开篇。

每个需要作者决定的地方都按 [../ncc/references/guidance.md](../ncc/references/guidance.md) 执行：一次一问、推荐置顶、给备选、可以先用推荐以后再改。判据见 [../ncc/references/mind-frame.md](../ncc/references/mind-frame.md)。

设计来源：三层递进问答与偏好记忆来自 chinese-novelist-skill；一句灵感出多套整本方向来自 AI-Novel-Writing-Assistant；选题对标沿主流网文工业流；设定与规则表衔接《小说拆分总纲 5.0》。

## Step 0 — 入口

1. 读偏好：`ncc_state.py pref show {book_root}`（M6-3：权重按时间衰减，作者否决过的不首推，雷点是硬约束）。偏好驱动选项排序、⭐ 标记与推荐理由。
2. **第一问：引导档位**（guidance §三）。按作者自述推荐：第一次写长篇或只有模糊想法 → 新手；写过一两本 → 熟手；有成熟方法论 → 老手。
3. 建书：`python3 <PLUGIN_ROOT>/scripts/ncc_state.py init {book_root}/{书名或暂名} --title … --level …`。脚本会建目录、三本账、`00-策划/作者种子.md` 模板与几份生成的视图（`author-intent.md` 等，勿手改），`stage: founding`。书名未定就用暂名，L3 再定。
4. **作者种子**（上限引擎 U1，guidance §〇）：给任何题材选项之前，先问作者自己的材料——最先出现的画面、最在乎的问题、亲历的事、最爱作品里最打动他的时刻、最讨厌的写法、别人不知道的生活经验、最想让读者记住的场面。都可以跳过；新手只问第 1、2、7 条。原话写进种子文件。此后所有推荐都要标明从哪条种子长出来。种子只记在种子文件里，写手包会直接带上 #1、#3、#6，不再另抄成素材卡。
5. **快捷通道**：作者首条消息已含题材＋主角设定＋核心冲突时，跳过对应问答，把已给信息填表后请作者确认。信息不足才问，问题数按档位控制（新手每个决策点只问影响最大的 1–2 个）。

## Step 0.5 — 读技艺库（M6-4，写过书的作者）

方向定下（Step 1）、类型契约定下（Step 3）后各跑一次 `ncc_state.py craft read <书目录>`：从书库根目录 `_作者/技艺库/` 里挑出与本书题材、主契约、弧光、写作模式相关的条目（"适用条件"写"通用"的总会挑出来），写进 `00-策划/技艺库摘录.md`。此后的推荐理由可以写"源自技艺库《上一本》#3"，排在作者种子之后、题材常规之前。第一本书没有技艺库，跳过；有别的书的条目而没读，`gate soul` 会提醒。

## Step 1 — 选题与整本方向（S0）

- 作者已有明确选题 → 记 `00-策划/briefing.md` 一页纸（题材、对标 3 本、差异点、目标读者、爽点承诺）。
- 作者只有模糊想法 → 派 scout（task: ideation），派单包里带上作者种子：扫榜＋对标，并出 **2–3 套整本方向**（每套：题材组合、主角、金手指、核心冲突、一句话卖点、书名组），每套标明从哪条种子长出来，标推荐与理由；至少一套非主流。作者可以选一套、只重做某一套，或只换某一部分。选定后写 briefing。

## Step 2 — 三层递进问答（S0）

按 [references/qa-layers.md](references/qa-layers.md)。L1 必答三问（题材、主角、核心冲突）；L2 可选四问（世界观、视角与基调、读者与风格参考、篇幅）；L3 书名。主题不再放在 L2，而是进入 Step 3 的书魂流程。

## Step 2.5 — 旧文采样（M6-1，可选）

问作者（问题卡格式，推荐置顶）：**有没有你自己写过的文字，3 章或 1 万字以上？** 写过的网文、日记、长帖都行，体裁不限，越像你想写的这本越好。

- **有（推荐）**：`ncc_state.py style <书目录> --sample <文件或目录>…` 算出文风指纹（句长、段长、对话占比、人称、标点习惯，存 `03-文风/文风指纹.json`，只给审稿看），并列出校准段候选。派 worldbuilder（task: style）写 `03-文风/文风基准.md`：一两句"语感"、2–3 段原文校准段、三五条负面清单；作者确认。此后写手动笔前最后读的就是作者自己的声音。
- **没有**：跳过。黄金三章第 1 章定稿后用 `style --from-chapters 1` 反推（golden-three.md），G3 会查。
- 样本不足 1 万字也能用，脚本会标"只作参考"。

## Step 3 — 书魂与类型契约（S0）→ G0

按 [references/book-soul.md](references/book-soul.md)：

1. **类型契约**：按已选方向给 2–3 种主契约组合，各附对标作品与典型毒点；作者选定后 `ncc_state.py contract <书目录> --main … --poison a,b --audience …`；`author-intent.md` 会据此自动生成，不手写。
2. **书魂四问**：不直接问"你的主题是什么"。从已选方向、主角、核心冲突推出 2–3 个主题候选，每个附一句预览和一部名著参照；作者选、改或全部否决。答不出就用推荐项标**暂定**（D7），最晚第一卷卷复盘时定下：`ncc_state.py soul <书目录> --question … --answer … --injustice … --ending … --status 暂定 --deadline 第一卷卷复盘`，并登记 `promise add --type 暂定决策 --content 书魂定稿 --ch 0 --deadline 第一卷卷复盘`。
3. **G0 书魂闸**：跑 `ncc_state.py gate <书目录> soul`，呈示书魂（标暂定／确定）＋主契约＋毒点清单；作者确认后 `--action pass --quote "作者原话"`，`stage → settings`。

## Step 4 — 设定（S1 立骨）→ G1

**先定写作模式**（D15，按 guidance 给推荐）：建筑师（大纲冻结后动笔）／园丁（只定书魂、第一卷方向与主要人物，按场景探索着写，台账事后补记，每单元整理一次）／混合（默认：书魂与人物先定，情节只规划到当前单元）。`ncc_state.py mode <书目录> 混合`。

派 worldbuilder（task: settings），产出：

- `01-设定/世界观圣经.md`——按 [references/worldbuilding.md](references/worldbuilding.md) 的结构；"世界的不公"要落在具体的社会结构上（对应书魂）。
- `01-设定/力量体系.md`——境界阶梯＋**量纲定义**＋越级例外。金手指、力量体系这两个决策点按 guidance 给 2–3 套方案。
- `01-设定/设定词典.md`——`词条 | 首现章计划 | 读者已知 | 完整真相 | 计划揭示章`。
- `01-设定/规则表.md`——per-book 克制链／兑换率。
- `01-设定/人物卡/`——**人物引擎**（上限引擎 U2），按 [references/character.md](references/character.md)：主角与主要配角用完整版（欲望、需要、恐惧、伤口、信错的那句话、内在矛盾、秘密、声音、关系），并做**角色采访**，产出声音样例；主角弧光类型（正向／负向／平弧）按 guidance 给推荐，作者选定后 `ncc_state.py soul <书目录> --arc …`。
- 知识台账初值：已定的距离、物价、历法、称谓等用 `ncc_state.py fact set` 写入。
- 时代背景：`ncc_state.py era <书目录> …`（按 guidance 给推荐）。
- **社会洞察**（M5-4）：世界观圣经里"看似不合理却存在"的规矩清单，每条写谁受益、谁受害、主角在哪、对应书魂"世界的不公"哪一面（`gate settings` 会查）。
- **小说底盘**（M5-2，玄幻、仙侠类）：力量体系与资源设定可以用作者的小说底盘做底料（`ncc.config.yaml` 的 `setting_base_candidates`），改成只对本书有效的版本并标 `底盘:` 来源；新手档推荐套用成熟体系再改名。
- **设定规律核对**（M4，按需）：虚构设定借用了真实规律的，派 scholar（task: rules）核一遍运转规律，问题按推荐呈作者。
- 一书一深学（可选，也可以第一卷卷复盘时再选）：按题材常涉及学科给推荐，`ncc_state.py study <书目录> --add …`（`../ncc/references/domains/reading-list.md`）。

若有拆书产物（设定库／词典片段），worldbuilder 直接吸收并在卡上记来源；拆书得出的对标书书魂与契约（`报告/书魂与契约.md`）可作类型契约候选的对标参照。

**G1 冻结**：`ncc_state.py gate <书目录> settings`，呈示脚本结果＋空白项清单；作者确认后 `--action pass`，`stage → outline`。冻结后的改动走变更提议（`workflow/architecture.md` §一）。

## Step 5 — 大纲（S1 立骨）→ G2

派 outliner（task: outline），按 [references/outline.md](references/outline.md)：

大纲的深浅随写作模式：

| 模式 | 总纲 | 卷纲 | 章纲 | 承诺登记 |
|---|---|---|---|---|
| 建筑师 | 完整 | 卷一完整 | 黄金三章细纲＋50 章滚动窗 | 大纲层承诺全部登记 |
| 混合（默认） | 主线、结局方向、各卷一句话 | 只写到当前单元 | 只写当前单元 | 当前单元的承诺 |
| 园丁 | 书魂与第一卷方向 | 不要求 | 不要求（场景卡即写即做） | 事后补记 |

1. **总纲**：主线一句话、分卷目录（每卷写明从哪个角度考验主题之问）、情绪曲线、结局方向、名场面与 2–3 个核心意象（登记进承诺台账，类型"名场面""母题"；总纲里只引用编号，不另列清单）。卷走向按 guidance：只要求定第一卷和全书大方向，后续各卷给 2–3 种走向。
2. **卷纲与章纲**：按上表。黄金三章的章纲要分配五个签约点（园丁模式在场景卡里分配）。**场景卡不在这里做**——它们即写即做，见 ncc-write。
3. **承诺登记**：`ncc_state.py promise add` 登记进承诺台账（带强度与兑现窗口）。

**G2 冻结**：`ncc_state.py gate <书目录> outline`（按写作模式检查），呈示总纲主线＋名场面与意象＋承诺台账摘要；作者确认后 `--action pass`，`stage → opening`，交接 ncc-write。

## 边界

- 本流程停在 G2；开篇（黄金三章）属于 ncc-write。
- 作者不答的题不编造：用推荐项记"暂定"并登记最晚决定点，worldbuilder 保守处理并显式标注。
- 推测出来的候选只是选项；作者没选之前，不写进任何文件当结论。
- 偏好由 `pref` 维护：作者选了 `pref like`，明确认可 `pref confirm`，否决 `pref reject --note 原因`，雷点 `pref dislike`；`creationHistory` 由 `init` 自动记、保留最近 50 条。
