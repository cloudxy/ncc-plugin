---
name: ncc-write
description: "Use this skill for chapter drafting: S2 opening (golden three chapters, G3 opening gate) and S3 serialized daily chapters. Every chapter runs register → scene cards → story review → writing brief + reader-now → draft (key beats in 2–3 versions) + ledger write-back → mechanical check → hard-defect review → pairwise pick (key chapters) → commit."
when_to_use: "User says /ncc-write, 写下一章, 今更N章, 黄金三章, or resume a drafting loop. Do NOT use for outline or settings work."
---

# 写章（S2 开篇 → S3 连载）

**先审故事，后写文字。** 场景卡小批量做、小批量审；每章由脚本组装写手包；常规章一人审硬伤、复审只看改动（D16–D18）：

```
每批（章数按写作模式，scene next 给出）：
  scene next → chapter add ×N → 场景卡 ×N(outliner 一次写完) → 故事审(story-editor 一次审完；关键章作者过目)
  → knowledge plan：有章标了"知识"才派 scholar（一次），写知识点清单 → knowledge check
每章：
  pack(脚本组装写手包) → writer 草稿(关键节拍 2–3 版) + 三本账回写 → check_chapter.py
  → review plan(continuity 必派；pulse 仅兑现章/关键章/开篇) → 有 major/critical: editor 修订 → review delta → 原审稿人只复审改动
  → 关键章: 成对比较(pulse) + 记忆测试(reader) → 作者 chapter pick
  → complete --hard pass
```

常规章顺利时约 2.7 次角色调用（写手 1、continuity 1、场景卡批量摊约 0.7），返工一轮约 4.7 次；兑现章多一次 pulse；关键章另走多版比选。

执行阶段**禁停顿**（铁律 5）：循环里的决策按推荐项执行、登记为暂定；哪几种情况可以当场打断作者，见 guidance 的"与执行阶段禁停顿的关系"。

## Step 0 — 定位

1. `ncc_state.py status <书目录>` 确认 stage、写作模式与断点。`opening` 阶段从第 1 章开始；`serial` 阶段找第一个非 done 章。
2. 单元开始时（每 10–40 章一次）：`ncc_state.py unit open <书目录> --start N --title …`；经理和作者一起确认本单元的**关键章**（系统按"卷首卷末、名场面兑现、重要人物登场与退场、主题显形"先推荐，作者确认，约占两成，D8），用 `chapter key` 标注。第 1–3 章默认是关键章。
3. `status` 提示存稿低于存稿线时，按 `../ncc/references/sustain.md` 进入保更模式（关键章后挪或降为常规工序，登记为暂定决策）。
4. `writing_mode: batch` 时按批推进（每批 3–5 章），批间走一次审稿；默认 `serial` 单章循环。

## Step 1 — 一批场景卡

1. `ncc_state.py scene next <书目录>` 给出下一批章号；逐章 `chapter add <书目录> <章号> --file 04-正文/第NNNN章-标题.md [--key]`。
2. `ncc_state.py brief <书目录> --role outliner --seq 4 5 6` 出派单头（本角色记忆、作者刚说的、技法参考），派 outliner（task: scene）按 [references/scene-card.md](references/scene-card.md) 一次写完这一批 `02-大纲/场景卡/ch-NNNN.md`：每章 1–3 场；常规章每场五项（能写出"默认写法"就加上），关键章十项全写；作者的素材卡用得上就挂一行"素材：M-NNNN"（`material list` 看索引），技法卡用得上就挂一行"技法：T-NNNN"。园丁模式可以没有章纲，从上一章结尾与人物欲望往下推。
3. `ncc_state.py scene check <书目录> 4 5 6` 过格式。

## Step 2 — 故事审（一批一次）

1. `brief --role story-editor --seq 4 5 6` 出派单头，派 story-editor（task: story-review）审这一批：逐张过故事审清单，再横着看一遍——风险有没有逐场升级、情绪有没有连着几章一个颜色、承诺有没有在批内推进。
2. 常规章：通过 → `scene review <书目录> 4 5 6 --result pass --by story-editor`；退回的卡由 outliner 按推荐改法改完再审那一张。结论记为暂定，单元复盘时作者复看。
3. 关键章：story-editor 的意见连同场景卡呈给作者，作者确认后 `scene review <书目录> <章号> --result pass --by author`。
4. 写着写着偏了、要改后面的卡：改哪张重审哪张。

## Step 2.5 — 知识点（按需，M4）

1. `ncc_state.py knowledge plan <书目录> 7 8 9`：列出场景卡"知识"一栏。一章都没有 → 这一批不派 scholar。
2. 有的话派 scholar（task: knowledge）一次，按 `../ncc/references/domains/README.md` 的"本章知识点清单格式"为这些章写 `02-大纲/知识点/ch-NNNN.md`（知识点｜学科｜写成什么｜来源｜状态），核实过的数据写进知识台账。
3. `ncc_state.py knowledge check <书目录> <章号>…` 逐章通过。待核项不阻塞写作——写手包会提示按宁缺律写；待核项在单元复盘时交作者。

## Step 3 — 写手包

`ncc_state.py pack <书目录> <章号> [--note "本章特别提醒：只写意图与材料"]`：脚本把场景卡逐场转成写作简报（含"默认写法——不要这样写"、关键节拍写多版的提示），附本章知识点（scholar 写的"写成什么"，不带来源与卡）、读者此刻、出场人物的欲望恐惧与声音、可用材料（作者种子 #1、#3、#6，场景卡挂的素材卡，场景卡提到的知识台账数据）、前情（上一章结束时的时间地点、下一章要接的事、近三章的翻转，从源头现算）、前一章结尾原文、文风基准，写到 `.ncc/写手包/ch-NNNN.md`。审稿文件、书魂原文、author-intent 一律不进；场景卡里混进书魂原文时脚本拒绝组装。然后 `chapter mark … drafting`。

## Step 4 — 派 writer

task: draft，派单包只给写手包路径。写手按 [references/chapter-loop.md](references/chapter-loop.md) 写：从视角人物的感知写起、把两难演出来、情绪落在选择与后果上（不拿身体小动作标注情绪）、绕开默认写法、先写后删；分两段写，前半段写完跑一次 `ncc_state.py words` 量字数，写完简报里的事就停，不为凑字数加内容。关键节拍写 2–3 版存到 `04-正文/_versions/`，不自己挑。写完回写三本账（承诺、知情、世界；主角失去了什么记为状态事件）、`chapter hook`、`chapter mood`，开篇章登记签约点（`sign`）。

## Step 5 — 机械检查

`python3 <PLUGIN_ROOT>/scripts/check_chapter.py <书目录> <章号>`：钩子登记、AI 味、水章、退化与元信息（复读、截断、占位与拒绝语、工程词漏进叙述）、字数。按结果走：

| 结果（退出码） | 意思 | 怎么办 |
|---|---|---|
| ready（0） | 可以审稿 | 进 Step 6 |
| blocked（1） | 有必须修的问题 | 派 writer 就地改受影响的段落（复读、截断只重写那一段），改完重跑；同一章改满 3 轮（`chapter retry`）停下问作者 |
| needs_decision（3） | 只是字数不在区间 | **不让写手补写或重写**——硬凑会注水。低于下限、但不少于下限的一半：按推荐先收下（`chapter length <书目录> <章号> --accept --tentative`），单元复盘时作者确认；不到下限一半：当场问作者（收下／改场景卡或字数范围后重写／不要这章）。超出上限：派 editor 做一次只删不加的压缩，`chapter length --compressed` 登记后重跑，仍超就按推荐先收下 |

只告警的项（身体小动作标注情绪、场景卡原句照搬、元信息词、规避点、底蕴提醒、文风漂移）交给审稿判断，不阻断。关键章的字数决定随版本选定一起问作者。

## Step 6 — 审稿（三层评价，D13；常规章减重，D17）

按 [../ncc-review/references/review-domains.md](../ncc-review/references/review-domains.md)：

1. `ncc_state.py review plan <书目录> <章号>`：给出该派谁，并存正文快照。
2. **硬伤层**：continuity（task: audit）必派，常规章顺带查契约与毒点；pulse（task: pulse）只在本章兑现了爽点欠账或名场面、关键章、开篇时参加。fresh 上下文，只产带正文引用的 observation，结论是通过或不通过；包括核对"场景卡里的翻转与两难，正文是否真的写出来了"。
3. 有 critical 或 major → 派 editor 显式修订 → `ncc_state.py review delta <书目录> <章号>` 列出改动的段落 → **只由上次给出不通过项的审稿人**复审这些段落与那几项（不再全文重审）。
4. 设定级矛盾（与圣经、词典、三本账冲突且不是笔误）→ 停，回作者：给"改设定／改本章"的推荐与理由。不允许写手悄悄圆。
5. **品质层（仅关键章）**：pulse 对各版本做**成对比较**，reader 做**记忆测试**；经理把比较结论、记忆测试和推荐呈给作者，作者 `chapter pick <书目录> <章号> --version B --note "…"`。选中版本接进正文后，`review delta` 看改动，再过一次硬伤层。常规章不评品质分。

## Step 7 — 定稿

`ncc_state.py complete <书目录> <章号> --words N --hard pass --decidable 0.9 --report 05-审稿/ch-XXXX-review.md`。脚本会拒绝：场景卡没过故事审（或审后改动过）、场景卡标了知识但知识点清单缺失或不合格、硬伤层未通过、关键章没有作者选定。定稿前确认已登记 `chapter end`（续写状态卡由脚本生成，不手改）；设定词典的「首现章」改成实值。

## 开篇特有（S2 → G3）

1. 第 1–3 章都是关键章，作为第一批场景卡：十项全写、作者过目；关键节拍写多版、作者选定。
2. 三章全过后：第 1 章定稿回填**文风校准段**到 `03-文风/文风基准.md`（写手执行）；开书时没有旧文样本的，`ncc_state.py style <书目录> --from-chapters 1` 反推文风指纹（M6-1）。
3. 派 reader（task: blind-read）盲评 1–3 章，**至少 2 个读者画像**、各一次独立派单（`../ncc-review/references/reader-personas.md`），报告写入 `05-审稿/blind-ch-0001-0003-<画像>.md`，每份须含「记忆测试」。各画像的追读、弃读、略读、划线与出戏（模拟读者没有评论）用 `feedback add --source 模拟 --persona <画像>` 登记，`ncc_state.py heat <书目录> --ch 1-3` 合成弃读热力；把各画像的"我在等什么"和 `reader-now` 对照，写进报告末尾的「读者此刻对照」。
4. `ncc_state.py gate <书目录> opening` 检查：三章 done 且硬伤层通过、关键章有作者选定、至少 2 份含记忆测试的盲评、文风校准段已填且文风指纹已生成、五个签约点都在前三章落地。
5. 呈示作者：签约点落地情况＋各画像的盲评、弃读热力与记忆测试＋读者此刻对照＋推荐 → 过 / 改 / 重写。过 → `--action pass`，`stage: serial`。

## 连载节奏（S3）

- 每章完成即是一个可发布单元；要合稿或做电子书时 `ncc_state.py export <书目录> --format md|txt|epub [--from N --to M]`，产物在 `07-导出/`（只收已定稿的章，修订注记自动去掉）。
- 存稿：作者可要求「先攒 N 章再更」——batch 模式即为此设计。
- 每次发布后 `ncc_state.py chapter publish <书目录> --upto N`，存稿线才有意义。
- 每个剧情单元结束：按 `../ncc/references/loops.md` 的"单元循环"做单元复盘（`report unit` 生成底稿 → 发展编辑的单元问题 → 下一单元走向 → 作者集中确认暂定决策 → `unit close`）。
- 每卷收官：按 `loops.md` 的"卷循环"做卷复盘（`volume end` → `report volume` → 承诺盘点、书魂检验、数据归因、变更提议 → G4）。
- 最后一卷：按 `../ncc/references/finale.md` 进入收束（`finale begin` → 收束清单 → G5）。
- 读者数据：真实数据与模拟判断都用 `feedback add` 登记，复盘时用来校准模拟读者。
