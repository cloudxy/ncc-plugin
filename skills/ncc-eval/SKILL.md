---
name: ncc-eval
description: "Use this skill to evaluate the workflow itself: regression tests of the review criteria on anchor chapters with planted defects (detection rate, severity, verdict accuracy, false alarms on a clean chapter, stability across repeated runs), and model comparison on one frozen writer pack (blind drafts, pairwise comparison, mechanical metrics). The scripts never call a model; the manager dispatches the packets and the scripts score the reports."
when_to_use: "User says /ncc-eval, 测一下审稿准不准, 改了判据之后回归一下, 比一比哪个模型写得好, 横评, or wants to know whether the reviewers catch planted errors. Do NOT use for reviewing a real chapter (that is ncc-review)."
---

# 评测（M7）：判据层回归与模型横评

**为什么要评测。** 审稿判据写在文档里、靠模型执行。文档改一句，审稿的行为可能就变了；换一个模型，写出来的东西也不一样。没有评测，每次改动都只能凭感觉说"应该更好了"。这里给两把尺子：

| 尺子 | 量什么 | 怎么量 |
|---|---|---|
| 锚定章回归 | 审稿抓不抓得住错、会不会冤枉好稿、同一章审几次结论稳不稳 | 一组故意埋了错的锚定章（`eval/anchors/`，含一章干净的对照），对着答案打分 |
| 模型横评 | 同一个写手包，换不同模型写，谁写得好 | 冻结写手包 SHA，盲稿成对比较＋记忆测试，揭盲算胜率 |

脚本（`scripts/ncc_eval.py`）不调用任何模型：它生成派单包、读回报告、打分。派单由本窗口的经理按常规方式完成（continuity、pulse、reader 都是 fresh 上下文）。

## 一、锚定章回归

1. **机械层**（不花模型调用，先跑）：`python3 <PLUGIN_ROOT>/scripts/ncc_eval.py mech`——`check_chapter.py` 的提醒是否命中埋的错（时代错置、称谓、月相），干净章是否零误报。退出码非 0 就先修脚本。
2. **生成派单包**：`ncc_eval.py prepare <评测目录> [--suite 底蕴|连贯|承诺|对照] [--runs 3]`。每章每次一个包，包里只有台账摘录、场景卡、知识点清单、机械提醒和正文，**没有答案**。`--runs` 是同一章审几次（量稳定性），默认 3。
3. **派单**：每个包派一次 continuity（task: audit），一次一个、互不看别的报告；报告按包里的 deliverable 路径存到 `<评测目录>/reports/`。报告格式按包里的要求：第一行"硬伤层: 通过/不通过"，再一张 observation 表。
4. **打分**：`ncc_eval.py score <评测目录>`，写 `score.md`：
   - **检出率**：埋的错被指出了几处（按正文引用或关键词匹配答案）；
   - **定级到位**：指出时定成 critical 或 major 的比例；
   - **结论准确率**：通过／不通过判对的比例；
   - **干净章误报**：对照章里被判成 critical／major 的条数；
   - **不稳定**：同一章几次结论不一致，或同一处错时有时无；
   - **答案之外的发现**：逐条人工看——是真问题就补进答案，是误报就记进判据的改进项。
5. **什么时候跑**：改了 `review-domains.md`、`agents/continuity.md`、底蕴卡的典型硬伤，或换了审稿用的模型之后。把前后两次的 `score.md` 并排呈给作者，按问题卡格式给"保留改动／回退"的推荐。

**加锚定章**：见 `eval/README.md`。好的锚定章像真书的一章：只埋一两处错，错要埋在审稿真正会漏的地方（视角越权、超前泄密、待核项写了数字、翻转没发生），并且至少保留一章干净的对照。

## 二、模型横评

1. 选一章（建议关键章或典型常规章），先正常走到 `pack`。
2. `ncc_eval.py bench init <书目录> <章号>`：冻结写手包 SHA。
3. 用同一个写手包，分别让不同模型的 writer 写一版（宿主支持按派单指定模型时直接指定；否则在不同模型的会话里各写一版），`bench add <书目录> <章号> --model <名字> --file <草稿>` 登记。写手包变过，登记会被拒绝——比的必须是同一个包。
4. `bench blind`：打乱成 A/B/C… 盲稿（对照表只存在 manifest 里），列出成对比较组合。
5. 每组派 pulse 做成对比较（按 `review-domains.md` 品质层：只选一个，说清好在哪，交换顺序再比一次，不一致记平局），`bench vote --winner A --loser B [--tie]` 登记；可加派 reader（目标读者画像）对每份盲稿做记忆测试，作为说明理由的材料。
6. `bench score`：揭盲，列各模型的胜率与机械指标（五星句式、高危句式与一级词、规避点、文风漂移）。胜率说明好不好看，机械指标只说明有没有毛病。一章的结论只作参考；要定"日常用哪个模型"，至少横评三章（开篇、常规、兑现各一）。

## 边界

- 评测不改书：锚定章回归不碰任何书项目；横评只在 `05-审稿/_bench/` 里存草稿与结果，不改正文、不改台账。
- 评测结果是给作者做决定的依据（改不改判据、换不换模型），不自动生效。
