---
name: ncc-write
description: "Use this skill for chapter drafting: S2 opening (golden three chapters, G3 opening gate) and S3 serialized daily chapters. Every chapter runs register → scene cards → story review → writing brief + reader-now → draft (key beats in 2–3 versions) + ledger write-back → mechanical check → hard-defect review → pairwise pick (key chapters) → commit."
when_to_use: "User says /ncc-write, 写下一章, 今更N章, 黄金三章, or resume a drafting loop. Do NOT use for outline or settings work."
---

# 写章（S2 开篇 → S3 连载）

**先审故事，后写文字。** 每章都是同一条流水线；关键章多两步（写多版、作者比选），开篇另加 G3 验收：

```
chapter add → 场景卡(outliner) → 故事审(story-editor；关键章作者过目) → scene review pass
  → 写作简报 + reader-now → 上下文包(留档) → writer 草稿(关键节拍 2–3 版) + 三本账回写
  → check_chapter.py(字数/钩子/AI味/水章) → 不过: writer 重写(chapter retry)
  → 硬伤审(continuity + pulse) → editor 修订 → 复审(SHA 重绑)
  → 关键章: 成对比较(pulse) + 记忆测试(reader) → 作者选定(chapter pick)
  → ncc_state.py complete --hard pass
```

执行阶段**禁停顿**：循环里的决策点（常规章的故事审结论、审稿问题放不放行）按推荐项执行，登记为 `暂定决策`，到单元复盘时集中呈给作者（guidance §五）。当场打断作者的只有：关键章的场景卡与版本选定（在单元设计时集中批）、G3、返工满 3 轮、设定级矛盾、战略分歧。

## Step 0 — 定位

1. `ncc_state.py status <书目录>` 确认 stage、写作模式与断点。`opening` 阶段从第 1 章开始；`serial` 阶段找第一个非 done 章。
2. 单元开始时（每 10–40 章一次）：`ncc_state.py unit open <书目录> --start N --title …`；经理和作者一起确认本单元的**关键章**（系统按"卷首卷末、名场面兑现、重要人物登场与退场、主题显形"先推荐，作者确认，约占两成，D8），用 `chapter key` 标注。第 1–3 章默认是关键章。
3. `status` 提示存稿低于存稿线时，按 `../ncc/references/sustain.md` 进入保更模式（关键章后挪或降为常规工序，登记为暂定决策）。
4. `writing_mode: batch` 时按批推进（每批 3–5 章），批间走一次审稿；默认 `serial` 单章循环。

## Step 1 — 登记与场景卡

1. `ncc_state.py chapter add <书目录> <章号> --file 04-正文/第NNNN章-标题.md [--key]`。
2. 派 outliner（task: scene）按 [references/scene-card.md](references/scene-card.md) 写 `02-大纲/场景卡/ch-NNNN.md`：一章 1–3 场；常规章每场五项，关键章九项全写。园丁模式可以没有章纲，从上一章结尾与人物欲望推出本章场景。
3. `ncc_state.py scene check <书目录> <章号>` 过格式。

## Step 2 — 故事审

1. 派 story-editor（task: story-review）：按场景卡的故事审清单审——翻转、两难、目标情感、风险升级、人物欲望与需要、意料之外情理之中、一个画面。
2. 常规章：通过 → `scene review … --result pass --by story-editor`；退回 → outliner 按推荐改法改卡再审。结论记为暂定，单元复盘时作者复看。
3. 关键章：story-editor 的意见连同场景卡呈给作者，作者确认后 `scene review … --result pass --by author`。
4. 场景卡在审过之后又改动，脚本会要求重审。

## Step 3 — 写作简报与上下文包

1. `ncc_state.py reader-now <书目录> <章号>`。
2. 按 [references/writing-brief.md](references/writing-brief.md) 由场景卡组装写作简报（一场一份）：视角与盲区、要什么与挡着什么、翻转、两难、目标情感、一个画面、本场必须发生的事件、可用材料、人物声音、**最容易想到的写法（经理具体列出）**、风险升级。关键章在关键节拍上标"写 2–3 版"。
3. 按 [../ncc/references/context-pack.md](../ncc/references/context-pack.md) 组装并落档 `_packs/ch-XXXX.json`。**不放**审稿清单、分数阈值、书魂原文、author-intent.md。
4. `chapter mark … drafting`（场景卡没过故事审会被拒）。

## Step 4 — 派 writer

task: draft。写手按 [references/chapter-loop.md](references/chapter-loop.md) 写：从视角人物的身体写起、把两难演出来、绕开最容易想到的写法、先写后删。关键节拍写 2–3 版存到 `04-正文/_versions/`，不自己挑。写完回写三本账（承诺、知情、世界；主角失去了什么记为状态事件）、`chapter hook`、`chapter mood`，开篇章登记签约点（`sign`）。

## Step 5 — 机械检查

`python3 <PLUGIN_ROOT>/scripts/check_chapter.py <书目录> <章号>`：汉字字数、章尾钩子登记、AI 味词表、水章（本章没有建立、推进或兑现任何读者向承诺）。退出码非 0 → writer 重写（`chapter retry`）。

## Step 6 — 审稿（三层评价，D13）

按 [../ncc-review/references/review-domains.md](../ncc-review/references/review-domains.md)：

1. **硬伤层**：派 continuity（task: audit）＋ pulse（task: pulse），fresh 上下文，只产带正文引用的 observation，结论是通过或不通过。其中包括核对"场景卡里的翻转与两难，正文是否真的写出来了"。
2. 有 critical 或 major → 派 editor 显式修订；正文 SHA 变更后**必须复审**。
3. 设定级矛盾（与圣经、词典、三本账冲突且不是笔误）→ 停，回作者：给"改设定／改本章"的推荐与理由。不允许写手悄悄圆。
4. **品质层（仅关键章）**：pulse 对各版本做**成对比较**（两两比，说明哪版更好、好在哪），reader 做**记忆测试**（读完记住了什么、想截图哪句、哪里想跳过）；经理把比较结论、记忆测试和推荐呈给作者，作者选定：`chapter pick <书目录> <章号> --version B --note "…"`。选中版本接进正文后，再过一次硬伤层。常规章不评品质分。

## Step 7 — 定稿

`ncc_state.py complete <书目录> <章号> --words N --hard pass --decidable 0.9 --report 05-审稿/ch-XXXX-review.md`。脚本会拒绝：场景卡没过故事审（或审后改动过）、硬伤层未通过、关键章没有作者选定。写手同步更新 `current-focus.md` 与设定词典的「首现章」实值。

## 开篇特有（S2 → G3）

1. 第 1–3 章都是关键章：场景卡全写、作者过目；关键节拍写多版、作者选定。
2. 三章全过后：第 1 章定稿回填**文风校准段**到 `03-文风/文风基准.md`（写手执行）。
3. 派 reader（task: blind-read）盲评 1–3 章，报告写入 `05-审稿/blind-ch-0001-0003.md`，须含「记忆测试」一节。
4. `ncc_state.py gate <书目录> opening` 检查：三章 done 且硬伤层通过、关键章有作者选定、盲评含记忆测试、五个签约点都在前三章落地。
5. 呈示作者：签约点落地情况＋盲评与记忆测试＋推荐 → 过 / 改 / 重写。过 → `--action pass`，`stage: serial`。

## 连载节奏（S3）

- 每章完成即是一个可发布单元；`07-导出/` 由作者手动或要求时生成合稿。
- 存稿：作者可要求「先攒 N 章再更」——batch 模式即为此设计。
- 每次发布后 `ncc_state.py chapter publish <书目录> --upto N`，存稿线才有意义。
- 每个剧情单元结束：按 `../ncc/references/loops.md` §一做单元复盘（`report unit` 生成底稿 → 发展编辑的单元问题 → 下一单元走向 → 作者集中确认暂定决策 → `unit close`）。
- 每卷收官：按 `loops.md` §二做卷复盘（`volume end` → `report volume` → 承诺盘点、书魂检验、数据归因、变更提议 → G4）。
- 最后一卷：按 `../ncc/references/finale.md` 进入收束（`finale begin` → 收束清单 → G5）。
- 读者数据：真实数据与模拟判断都用 `feedback add` 登记，复盘时用来校准模拟读者。
