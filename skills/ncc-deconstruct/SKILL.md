---
name: ncc-deconstruct
description: "Use this skill to deconstruct benchmark novels per the 小说拆分总纲 5.0 framework: chapter index as the single slicing source, evidence-and-confidence-tagged extraction, event-sourced state ledger, entities tagged with the setting categories; then learn from it: technique cards on overall design, plot and payoff planning, hidden lines, emotion, character, setting construction and prose, plus a benchmark baseline. Feeds the setting vault, lexicon and the cross-book technique library."
when_to_use: "User says /ncc-deconstruct, 拆这本书, 喂设定库, 学这本书怎么写, or provides a novel file to deconstruct. Only books the user legally holds."
---

# 拆书（喂设定库，学写法）

把一本对标书拆成结构化数据，喂给设定库与设定词典；拆完一段再学它**怎么写**——剧情怎么排、爽点怎么铺、暗线怎么埋、情绪怎么调、大局怎么搭，写成跨书共用的技法卡。字段口径完全按《小说拆分总纲 5.0》（授权随书、逐条带证据与置信级、事件溯源）。

## Step 0 — 前提与框架

1. **只拆作者合法持有、有权使用的作品**；产物只存定位词级引用（5–15 字），不复制原文段落（总纲 5.0 合规章）。技法卡同样只用自己的话。
2. 定位总纲：读 `ncc.config.yaml` 的 `framework_candidates`，取第一个存在的路径。都没有 → 请作者给路径，不用记忆里的版本拼凑。
3. 拆书库：`{book_root}/_拆书库/{书名}/`（原文/、索引/、章节/、实体/、台账/、词典/、报告/，进度在 `_progress.json`）。原文放进 `原文/`。

## Step 1 — 章节索引（唯一真源）

`ncc_state.py decon index {book_root}/_拆书库/{书名}`：按章标题切分，写 `索引/chapter_index.json`（序号 seq、原文章号、标题、起止行、字数、hash）。**一切章节号引用索引的序号**；原文变更必须重建（覆盖率检查会发现）。索引有跳号、重号、空章，脚本停下报告，不带病进抽取；核对后确认原书本来如此，才加 `--force`。

## Step 2 — 逐章抽取（派 deconstructor）

每章一次派单（task: deconstruct），包内容 = 该章原文 + 前情摘要 + 活跃实体别名表 + 未回收伏笔清单（跨章三件套，防指代抽飞）。产出按总纲 5.0 第十一章的输出契约：

- 每条 entity / relation / state_event / foreshadow / emotion_point **必须带 evidence（定位词）与 confidence（原文明说/强推断/弱推断）**；宁漏勿错。
- 已有实体必须引用库内 ID；新实体留空由归一步分配。
- **实体按设定类目归类**（门派、种族、血脉、企业……类目表见 `skills/ncc-new/references/worldbuilding.md` 的"设定类目研判"）；装不进任何类目的标"未归类"，攒够了会提议新类目。
- 长章分块时块间传递已抽实体清单。
- 拆完一段记进度：`decon mark <拆书库/书名> --done 1-30`；有意跳过的章 `--skip N --why …`。

## Step 3 — 归一与台账

1. 别名归一：专名与有同指证据的绰号合并；描述性称谓永不自动合并。
2. 状态事件入台账（entity/chapter/attribute/old→new/reason/evidence）。
3. 伏笔登记状态机（待回收/已回收/疑似遗忘），超期（>60 章无强化）报警——这也是拆书最有价值的产出之一：看对标书怎么管伏笔。
4. 统计要用的几项另写一份机器可读的台账（每行一个 JSON，`chapter` 一律用索引序号，每条带 `evidence` 与 `confidence`）：

| 文件 | 每行写什么 |
|---|---|
| `台账/伏笔.jsonl` | `id`、`op`（埋／强化／回收）、`chapter` |
| `台账/爽点.jsonl` | `chapter`、`setup`（铺垫起于第几章，可空）、`parts`（欠账、兑现、超额、见证里写到了哪几件） |
| `台账/情绪点.jsonl` | `chapter`、`tension`（压／放／平）、`colors`（可空） |
| `台账/钩子.jsonl` | `chapter`、`type`、`intensity` |
| `台账/单元.jsonl` | `start`、`end`、`title` |
| `实体/实体.jsonl` | `name`、`category`（设定类目，装不进的留空）、`first_ch` |

## Step 4 — 产出喂料

- `词典/设定词典片段.md`：可直接并入本书设定词典的词条（标 `拆:{书名}`＋置信级）。
- **对标基线**：`decon stats <拆书库/书名> --write` 从上面几份台账算出伏笔从埋到回收的等待章数、每 10 章的爽点密度与铺垫间隔、最长连续压抑、钩子类型、单元长度、实体类目分布，写 `报告/基线.json` 与视图。全书统计先过覆盖率闸门（`decon coverage`：索引章数 = 已拆 + 显式跳过）；只统计拆完的一段用 `--range A-B`。本书 `decon link <书目录> {书名}` 之后，单元复盘底稿会拿基线作参照（只作参照，不作判据）。

**逆向夹校（M5-3）**：拆书不只喂设定，还要拆出"成熟作者怎么把生活写进戏里"，和作者的正向素材互相校（`../ncc-new/references/material.md` 的"拆书样本与正向素材互校"）：

- `报告/质感细节样本.md`：对标书里让人信以为真的具体细节——行业动作、物件、行话、身体感受。每条一行：`| 细节（用自己的话概括） | 章＋5–15 字定位词 | 在戏里起什么作用 | 可借的写法 |`。只存定位词，不抄原文。
- `报告/机制因果链样本.md`：对标书写的社会规矩怎么运转，与世界观圣经"社会洞察"同一格式：`| 规矩 | 为什么存在 | 谁受益 | 谁受害 | 主角在哪 | 证据（章＋定位词） |`。
- `报告/书魂与契约.md`：对标书的书魂四问（主题之问、主角的答案、世界的不公、终局）与类型契约（主契约、附加契约、它小心避开的毒点）。都是推断，每条标置信级（强推断／弱推断）并附证据；立书时作为类型契约候选的"对标作品"参照。

样本可以挑出几条记成素材卡：`ncc_state.py material add <书目录> --trust 拆书 --source "拆:{书名} 第N章「定位词」" …`。拆书样本只借写法；与作者亲历冲突时，事实以亲历和文献为准。

## Step 5 — 学法：写技法卡

每拆完一段（30–50 章或一卷）做一次，全书拆完再做一次。deconstructor 读本段的抽取台账、基线和样本报告，不重读原文，回答"这段为什么好看、它是怎么做到的"，写成技法卡：

```bash
ncc_state.py technique add {book_root} --kind 爽点规划 \
  --method "憋屈要攒够再一次兑现，兑现时要有旁观者" \
  --how "先连压三章，每章加一层代价；第四章一次放出来；安排一个之前看不起主角的人在场" \
  --evidence "拆:{书名} 第12章「定位词」" --evidence "拆:{书名} 第40章「定位词」" \
  --applies "题材=都市,玄幻；阶段=连载；承诺=爽点欠账" \
  --cost "压超过五章读者会走；见证人每次都是同一类人会腻" --confidence 强推断 --source {书名}
```

- **类别**：大局设计（卷结构、主线与副线的配比、升级曲线）、剧情规划（单元怎么起承转合、翻转怎么排）、爽点规划（欠账怎么攒、怎么兑现、谁来见证）、暗线伏笔（埋、强化、回收的节奏）、情绪调用（压抑与释放怎么交替）、人物塑造、设定构造（设定怎么变成冲突的发动机）、文笔参考（句式、描写、节奏）。八类装不下的手法（比如群像调度），在返回摘要里提新类别，经理走进化提议。
- **证据**：同一本书里找到两处以上才算"手法"，一处只是"样本"。定位词 5–15 字。
- **适用条件**写具体：题材、阶段（开篇、连载、卷末、收束）、主契约、哪类承诺。
- **代价与失效**必写：什么情况下这招会变成套路、踩毒点。
- 只用自己的话；脚本拿卡片和原文比，连续重合超过 15 字就拒绝写入。`technique check {book_root}` 查全部卡片。

卡片存在 `{book_root}/_作者/技法库/<类别>/`，跨书共用。规划角色派单时由 `brief` 按题材、阶段、契约挑卡；场景卡写"技法：T-NNNN"引用；单元关闭时脚本按那几章的结果自动结算，卡的状态随之升降。

<!-- ncc:gen technique-roles 开始（scripts/build_docs.py 由 workflow/registry.json 生成，勿手改） -->
| 角色 | 拿哪些类别 | 最多几张 | 最多几字 |
|---|---|---|---|
| scout | 大局设计 | 3 | 900 |
| worldbuilder | 设定构造、人物塑造 | 3 | 900 |
| outliner | 大局设计、剧情规划、爽点规划、暗线伏笔、情绪调用 | 5 | 1500 |
| story-editor | 大局设计、剧情规划、爽点规划、暗线伏笔、情绪调用、人物塑造 | 5 | 1500 |
| writer | 文笔参考（只拿场景卡引用了的） | 2 | 300 |
| continuity、pulse、reader | 不拿 | — | — |

技法一进审稿就成了判据；reader 盲读。写手拿到的由脚本转成"写成什么"，不带证据、出处与代价。同一本对标书每次最多 2 张。

状态：一处证据是样本，同一本书 2 处以上是手法；用过且结果好是已验证；连续 2 次结果差自动停用（technique restore 可恢复）；2 本书以上都有的标"通用"。定位词 5–15 字；卡片正文和原文连续重合超过 15 字就拒绝写入。
<!-- ncc:gen technique-roles 结束 -->

## 边界

- 拆书不写本书正文；产出只进设定库、词典、技法库。
- 断点续跑：进度记在拆书库的 `_progress.json`（`decon mark`）；续跑不重扫。
- 覆盖率闸门：全书统计前 `decon coverage` 核对「索引章数 = 已拆 + 显式跳过」。
- 借写法，不借事件链：技法卡写的是"怎么做"，不是"这本书发生了什么"。推荐理由仍先从作者种子长出来。
