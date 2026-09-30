---
name: ncc-new
description: "Use this skill to start a new book: optional scout briefing, three-layer intake Q&A with preference memory, settings freeze (G1) and three-level outline freeze (G2). Stops at author confirmation points."
when_to_use: "User wants to start a new novel, or /ncc-new. Do NOT use for continuing, reviewing or deconstructing."
---

# 开书（S0 选题 → S1 设定 → S2 大纲）

目标：把一个想法变成**可连载的冻结起点**——设定冻结（G1）、大纲冻结（G2）、然后交给 ncc-write 写黄金三章。

设计来源：三层递进问答与偏好记忆来自 chinese-novelist-skill；选题对标沿主流网文工业流（先看市场再动笔）；设定与规则表结构衔接《小说拆分总纲 5.0》（字段同源，拆书产物可直接喂进来）。

## Step 0 — 入口与快捷通道

1. 读 `{book_root}/_preferences.json`（无则初始化空偏好）。偏好驱动后续所有选项的排序与 ⭐ 标记。
2. **快捷通道**（chinese-novelist-skill 的教训：问答是成本）：作者首条消息已含 题材＋主角设定＋核心冲突 时，跳过问答直接进 Step 2，把已给信息填表后呈示确认。信息不足才问。
3. 建书目录：`{book_root}/{书名}/`（按 [ncc skill 的目录契约](../ncc/references/book-state.md)），从模板初始化 `book.json`，`stage: ideation`。

## Step 1 — 选题（S0，可跳过）

- 作者已有明确选题 → 记 `briefing.md` 一页纸（题材/对标3本/差异点/目标读者/爽点承诺），跳过 scout，在 book.json 记 `S0 skipped: 作者已有选题`。
- 作者只有模糊想法 → 派 scout 子代理（task: ideation）：扫榜＋对标分析＋briefing。呈示后作者点头才进 S1。

## Step 2 — 三层递进问答（S1 入口）

问答只在**开书时**发生；执行阶段禁停顿（自动化边界）。逐层进行，每层答完静默同步偏好。详见 [references/qa-layers.md](references/qa-layers.md)。

- **L1 必答三问**：题材（若 S0 已定则带出）、主角（职业/性格/金手指）、核心冲突（驱动力）。
- **L2 可选五问**：世界观、视角与基调、主题、读者与风格参考、章节数与特殊要求——每题可 🎲 随机 / 跳过；奇幻/仙侠类强制补世界观。
- **L3 书名**：按题材映射＋多种技法生成 3–5 个候选（各用不同技法），可重生成，>5 轮提示作者自拟。

## Step 3 — 设定（S1）→ G1

派 worldbuilder 子代理（task: settings），产出：

- `01-设定/世界观圣经.md` —— 世界层/力量源/地理/势力/规则，按 [references/worldbuilding.md](references/worldbuilding.md) 的结构。
- `01-设定/力量体系.md` —— 境界阶梯＋**量纲定义**（每个数值：定义域/阈值效应/恢复机制）＋越级例外。
- `01-设定/设定词典.md` —— 专有名词表：`词条 | 首现章计划 | 读者已知 | 完整真相 | 计划揭示章`（chinese-novelist-skill 的四栏词典，跨章一致性的地基）。
- `01-设定/规则表.md` —— per-book 克制链/兑换率（总纲 5.0 铁律：规则随书，不跨书）。
- `01-设定/人物卡/` —— 主角团每人一卡（A1–A8 字段参照总纲 5.0 的底卡分级，只填有的）。

若有拆书产物（设定库/词典片段），worldbuilder 直接吸收并在卡上记来源。

**G1 冻结**：跑 `ncc_state.py gate <书目录> settings`，呈示脚本结果＋空白项清单；作者确认后 `gate <书目录> settings --action pass --quote "作者原话"`，`stage → outline`。冻结后的改动走经理的 `revise-settings`（状态事件留痕＋受影响章节标记复评）。

## Step 4 — 大纲（S2）→ G2

派 outliner 子代理（task: outline），按 [references/outline.md](references/outline.md)：

1. **总纲**：主线一句话、三幕/起承转合、主角弧光、大结局方向、卷目录。
2. **卷纲**：先只做卷一完整版（钩子链、阶段目标、新设定引入计划、情绪曲线）。
3. **章纲**：黄金三章逐章细纲（每章 must-keep / avoid、钩子类型与强度）＋后续 **50 章滚动窗**（只含近期，写完一卷再扩——Openwrite 的滚动规划）。
4. **伏笔种子表**：埋到大纲层的伏笔登记进台账（id、预计埋设章、预计回收窗口）。

**G2 冻结**：`ncc_state.py gate <书目录> outline`，呈示总纲主线＋卷一钩子链＋情绪曲线；作者确认后 `--action pass`，`stage → golden`，交接 ncc-write。

## 边界

- 本流程停在 G2；黄金三章属于 ncc-write。
- 问答阶段作者不答的题不编造：记「未定」，worldbuilder 用保守默认并显式标注。
- 偏好文件只增不删；`creationHistory` 超过 50 条滚动裁剪最旧的（修正源项目的无限增长问题）。
