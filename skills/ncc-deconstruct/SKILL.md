---
name: ncc-deconstruct
description: "Use this skill to deconstruct benchmark novels per the 小说拆分总纲 5.0 framework: chapter index as the single slicing source, evidence-and-confidence-tagged extraction, event-sourced state ledger. Feeds the setting vault and lexicon."
when_to_use: "User says /ncc-deconstruct, 拆这本书, 喂设定库, or provides a novel file to deconstruct. Only books the user legally holds."
---

# 拆书（喂设定库）

把一本对标书拆成结构化数据，喂给设定库与设定词典，供 worldbuilder 开书时吸收。字段口径完全按《小说拆分总纲 5.0》（授权随书、逐条带证据与置信级、事件溯源）。

## Step 0 — 前提与框架

1. **只拆作者合法持有、有权使用的作品**；产物只存定位词级引用（5–15 字），不复制原文段落（总纲 5.0 合规章）。
2. 定位总纲：读 `ncc.config.yaml` 的 `framework_candidates`，取第一个存在的路径。都没有 → 请作者给路径，不用记忆里的版本拼凑。
3. 拆书库结构按总纲 5.0 第十章：`{book_root}/_拆书库/{书名}/`（原文/、索引/、章节/、实体/、台账/、词典/）。

## Step 1 — 章节索引（唯一真源）

用脚本或严格手工建 `索引/chapter_index`（sequence、原文章号、标题、起止行、字数、hash）。**一切章节号引用它**；原文变更必须重建。索引有问题（跳号/重号/空章）→ 停下报告，不带病进抽取。

## Step 2 — 逐章抽取（派 deconstructor）

每章一次派单（task: deconstruct），包内容 = 该章原文 + 前情摘要 + 活跃实体别名表 + 未回收伏笔清单（跨章三件套，防指代抽飞）。产出按总纲 5.0 第十一章的输出契约：

- 每条 entity / relation / state_event / foreshadow / emotion_point **必须带 evidence（定位词）与 confidence（原文明说/强推断/弱推断）**；宁漏勿错。
- 已有实体必须引用库内 ID；新实体留空由归一步分配。
- 长章分块时块间传递已抽实体清单。

## Step 3 — 归一与台账

1. 别名归一：专名与有同指证据的绰号合并；描述性称谓永不自动合并。
2. 状态事件入台账（entity/chapter/attribute/old→new/reason/evidence）。
3. 伏笔登记状态机（待回收/已回收/疑似遗忘），超期（>60 章无强化）报警——这也是拆书最有价值的产出之一：看对标书怎么管伏笔。

## Step 4 — 产出喂料

- `词典/设定词典片段.md`：可直接并入本书设定词典的词条（标 `拆:{书名}`＋置信级）。
- `台账/伏笔手法.md`：该书伏笔的埋设/强化/回收节奏统计（多少章埋一次、平均等待多少章）。
- `报告/节奏与爽点.md`：情绪点密度、三维节奏抽样——给 outliner/pulse 当对标基线。

**逆向夹校（M5-3）**：拆书不只喂设定，还要拆出"成熟作者怎么把生活写进戏里"，和作者的正向素材互相校（`../ncc-new/references/material.md` 第五节）：

- `报告/质感细节样本.md`：对标书里让人信以为真的具体细节——行业动作、物件、行话、身体感受。每条一行：`| 细节（用自己的话概括） | 章＋5–15 字定位词 | 在戏里起什么作用 | 可借的写法 |`。只存定位词，不抄原文。
- `报告/机制因果链样本.md`：对标书写的社会规矩怎么运转，与世界观圣经"社会洞察"同一格式：`| 规矩 | 为什么存在 | 谁受益 | 谁受害 | 主角在哪 | 证据（章＋定位词） |`。
- `报告/书魂与契约.md`：对标书的书魂四问（主题之问、主角的答案、世界的不公、终局）与类型契约（主契约、附加契约、它小心避开的毒点）。都是推断，每条标置信级（强推断／弱推断）并附证据；立书时作为类型契约候选的"对标作品"参照。

样本可以挑出几条记成素材卡：`ncc_state.py material add <书目录> --trust 拆书 --source "拆:{书名} 第N章「定位词」" …`。拆书样本只借写法；与作者亲历冲突时，事实以亲历和文献为准。

## 边界

- 拆书不写本书正文；产出只进设定库与词典。
- 断点续跑：进度记在拆书库自己的 `_progress`（拆到哪章、跳过哪些）；续跑不重扫。
- 覆盖率闸门：聚合统计前核对「索引章数 = 已拆 + 显式跳过」。
