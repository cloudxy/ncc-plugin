# AGY 盲审与工程证据最终交付回执（ttys006）

- **终端窗口**：`ttys006`（作者窗口）
- **协调会话**：[`00f8374a-a056-4c06-b5b4-8e3042de496f`](conversation://00f8374a-a056-4c06-b5b4-8e3042de496f)
- **执行模型**：Gemini 4 Carbon (High)（`agy 1.5.15`，`inherit`）
- **交付时间**：2026-11-24 09:38 +08:00
- **交付状态**：**已完成（`R05`、`E02`、`E01` 全部实测结果与脱敏证据已落盘并复核全绿，提交新质量负责人 `ttys004` 审核验收）**
- **归属、脱敏与纪律核验**：
  - 本窗口修改的仓内源码严格限定于评测工具及其直接测试：
    - [scripts/ncc_eval.py](../../../scripts/ncc_eval.py)
    - [scripts/tests/test_ncc_eval.py](../../../scripts/tests/test_ncc_eval.py)
    - [scripts/tests/test_ncc_state.py](../../../scripts/tests/test_ncc_state.py)（仅 `TestEval.test_prepare_and_score`）
  - 新增/更新证据均位于 `docs/evidence/2026-11-23-agy-upgrade-audit/` 本窗口名下路径（`agy-evaluation.md`、`e01-checks.log`、`mech-9anchors.log`、`platinum-anchors/`、`blind-eval/`），未触碰其他窗口回执与产品源码；
  - **脱敏核验**：全部归档证据、JSON 清单、日志与回执均已脱敏（采用仓内相对路径与 `<APP_DATA_DIR>` / `$HOME` 占位符，不含本地用户名路径、不含 `.env` 密钥、不含 `novels/` 等私稿内容）；
  - 全程仅用合成数据，未触碰 `ncc-pro` 或私稿，未执行清库、`rm`、`git commit` 或 `git push`。

---

## 一、E01 入口复核与 9 样例（6 传统 + 3 白金）机检结果

### 1. 文档与中间工件归属核实
- **产品层长期基线**：归 `docs/product/`（由 `sdlc.config.yaml` 的 `product_root` 指定，已在 `docs/README.md` 与 `docs/engineering/documentation.md` 登记）。
- **本地切片中间工件**：归 `.sdlc/`，已在 `.gitignore` 与 `.zcodeignore` 忽略，并在 `scripts/dev/check_plugin.py` 的 `tracked()` 排除；对文档中带“不存在/已删除/已移除/缺失”前缀的否定式历史路径说明不误判为断链。

### 2. 收口入口检查与 9 题机检实测结果
完整输出见 [e01-checks.log](e01-checks.log) 与 [mech-9anchors.log](mech-9anchors.log)：

| 检查项 | 执行命令 | 退出码 | 实际结果 |
|---|---|---|---|
| 注册表分片与兼容视图 | `python3 scripts/dev/build_registry.py --check` | `0` | `REGISTRY OK` |
| 插件契约、软链、引用与角色读取预算 | `python3 scripts/dev/check_plugin.py -v` | `0` | `PLUGIN OK`（全部 22 个创作角色、经理入口与工程专业角色均在预算上限内；含本批归档后的 `docs/evidence/2026-11-23-agy-upgrade-audit/` 全量文件） |
| 生成文档同步检查 | `python3 scripts/dev/build_docs.py --check` | `0` | `DOCS OK` |
| `ncc_eval` 匿名盲审、反例防御与兼容单测 | `python3 -m unittest scripts/tests/test_ncc_eval.py scripts.tests.test_ncc_state.TestEval -v` | `0` | `Ran 5 tests ... OK`（覆盖多源目录、隔离包目录、标题剥离、正文同名名词不误拦、非法 `--runs <= 0` 拒绝、加粗判决与转义竖线解析、跨工作目录相对路径评分、历史未匿名报告兼容） |
| **9 样例机械层回归（6 传统 + 3 白金含 P02）** | `python3 scripts/ncc_eval.py mech --anchors-dir eval/anchors --anchors-dir docs/evidence/2026-11-23-agy-upgrade-audit/platinum-anchors` | `0` | **`A01`–`A06`、`P01`、`P02`、`P03` 共 9 题全部 `PASS`** |

9 题机检逐项实测输出（与 `mech-9anchors.log` 一致）：
```text
PASS A01-古代时代错置与称谓
PASS A02-月相与行程
PASS A03-待核项写了数字
PASS A04-视角越权与超前泄密
PASS A05-场景卡翻转没发生
PASS A06-干净对照
PASS P01
PASS P02
PASS P03
```
> 说明：因其他窗口正在并发推进各自归属源码，正式总交付冻结候选时由合并验收方重跑一次 `check_plugin.py -v` 绑定最终候选指纹即可。

---

## 二、R05 & E02 评分输入、白金样例设计与盲审隔离机制

### 1. 评分输入与证据归档位置
- **传统 6 题冻结输入**：`eval/anchors/A01-古代时代错置与称谓` 至 `eval/anchors/A06-干净对照`（共 8 处预期埋错 + 1 章干净对照）。
- **白金 3 题冻结输入（含 `P02`）**：[platinum-anchors/](platinum-anchors)（原创合成输入，无任何 `book.json` 或私稿内容）：
  - **`P01`**（[P01/answers.json](platinum-anchors/P01/answers.json)，应判 `不通过`，2 处核心白金埋错）：
    - `d1`（`critical`）：第 7 章末留有强度 5 悬剑钩（石室闸门砸落、周烈剑抵沈砚咽喉逼交残图），场景卡要求章首前 300 字正面秒接脱身，正文前 300 余字直接切镜头至次日清晨外门膳堂排队喝粥，并用一句“虚惊……抛在脑后”跳过生死绝境（切镜头断章诈骗）；
    - `d2`（`critical`）：在途暗线 `FS-0004` 计划第 28 章揭示且视角人物与读者当前均不知情，正文在未揭晓章直接点破焦黑木牌实为“前朝镇北军的虎符母印”（暗线未揭晓章提前剧透里层真相 + 限知越权）。
  - **`P02`**（[P02/answers.json](platinum-anchors/P02/answers.json)，应判 `不通过`，2 处核心白金埋错）：
    - `d1`（`critical`）：反派西院账房赵管事设定为老辣多疑、极度惜命护私、随身紧攥传唤六名护院的铜哨且不知沈砚有巡察接应，正文却让他无端挥退全部六名护院并主动取出贪墨真账拍在桌上任由学徒拿走（违背知情盲区与自身利益算盘，强行降智送人头）；
    - `d2`（`critical`）：场景卡规定的第一手受挫（撬暗格触铃、铁栅封门、铁片崩断）、两难代价（倾倒仅剩的疗伤凝血散造烟还是被擒灭口）与核心翻转均未发生，正文沦为无阻碍白捡平推。
  - **`P03`**（[P03/answers.json](platinum-anchors/P03/answers.json)，应判 `通过`，白金机制干净对照章）：
    - 上一章留有强度 4 悬剑钩（南巷口火把齐亮、捕头刀锋指箱搜查），本章首句前 80 字即正面紧接盘查危机；
    - 在途暗线 `FS-0005`（枣木断尺内封司天监星轨密图，第 30 章揭示）在捕头搜箱时仅呈现“磨损寸刻的寻常木工旧尺”明面伪装，零真义泄露；
    - 第一手受挫（夜行腰牌逾戌时三刻被扣）、两难代价（切开三年赤参主根折损三成药力自证急症救命）与配角陈捕头利益算盘（公事公办扣牌留底，但忌惮辖街耽误急症死人背黑锅而放行）严丝合缝。
- **27 份匿名派单包**：[blind-eval/packets/](blind-eval/packets)（`M01.md`–`M27.md`）
- **27 份原始盲审报告**：[blind-eval/reports/](blind-eval/reports)（`M01.md`–`M27.md`）
- **可移植脱敏揭盲清单**：[blind-eval/manifest.json](blind-eval/manifest.json)（存储仓内相对路径 `eval/anchors` 与 `docs/evidence/2026-11-23-agy-upgrade-audit/platinum-anchors`）
- **可复核评分输出**（在任意工作目录运行 `python3 scripts/ncc_eval.py score docs/evidence/2026-11-23-agy-upgrade-audit/blind-eval` 均可原样复现）：
  - 9 题合并评分：[blind-eval/score.md](blind-eval/score.md)
  - 传统 6 题拆分评分：[blind-eval/score-traditional-6.md](blind-eval/score-traditional-6.md)
  - 白金 3 题拆分评分：[blind-eval/score-platinum-3.md](blind-eval/score-platinum-3.md)

### 2. 匿名与独立盲审隔离保障
1. **输入零提示**：`ncc_eval.py prepare` 将 `9 章 × 3 轮 = 27` 个评测单元确定性洗牌编码为 `M01`–`M27`，包文件名、包内标题（`# 评测派单包：MXX`）与 `deliverable: reports/MXX.md` 均不含原题号、缺陷词、“干净对照”、轮次号或任务路径，并经 `_assert_no_spoiler` 自动断言零答案泄露（同时支持题号后缀含正文普通名词如 `A07-手表` 时仅拦截包头/标题泄露而不误拦正文词汇）。
2. **物理目录隔离**：盲审执行期间，评审者读取的隔离包目录不含 `manifest.json` 或 `answers.json`，白金题答案在全部 27 个子会话返回后才归档至 `docs/evidence/`。
3. **只读独立会话**：通过 `define_subagent` 定义只读 `blind-continuity-auditor`（`EnableWriteTools=false`、`EnableSubagentTools=false`、`EnableMCPTools=false`），每份 `MXX.md` 由一个全新 `invoke_subagent` 会话独立完成，27 个子会话互不共享记忆或报告；抽检多份子会话 `transcript.jsonl` 确认仅读取分配的单个 `MXX.md`、`agents/continuity.md` 与 `skills/ncc-review/references/review-domains.md`。

---

## 三、单轮结果 vs 3 轮重复稳定性统计与局限分析

### 1. 单轮（`r1`）与 3 轮重复运行（`r1`–`r3`）对照总表

| 评测子集 | 维度口径 | 应交／实收报告（缺份） | 埋错检出率 | 定级到位率（`critical`/`major`） | 结论准确率（通过／不通过） | 干净对照严重误报（`critical`/`major`） | 跨轮次不稳定项 |
|---|---|---|---|---|---|---|---|
| **传统 6 题（`A01`–`A06`）** | **单轮（`r1`）** | `6 / 6`（缺 `0`） | **8 / 8（100%）** | **8 / 8（100%）** | **6 / 6（100%）** | **0 条**（`A06` `r1`） | — |
| **传统 6 题（`A01`–`A06`）** | **3 轮重复（`r1`–`r3`）** | `18 / 18`（缺 `0`） | **24 / 24（100%）** | **24 / 24（100%）** | **18 / 18（100%）** | **0 条**（`A06` 3 轮全清） | **无**（6 题结论与 8 处核心埋错 3/3 全一致） |
| **白金 3 题（`P01`、`P02`、`P03`）** | **单轮（`r1`）** | `3 / 3`（缺 `0`，含 `P02`） | **4 / 4（100%）** | **4 / 4（100%）** | **3 / 3（100%）** | **0 条**（`P03` `r1`） | — |
| **白金 3 题（`P01`、`P02`、`P03`）** | **3 轮重复（`r1`–`r3`）** | `9 / 9`（缺 `0`，`P02` 3/3 收齐） | **12 / 12（100%）** | **12 / 12（100%）** | **9 / 9（100%）** | **0 条**（`P03` 3 轮全清） | **无**（`P01`、`P02`、`P03` 结论与 4 处白金埋错 3/3 全一致） |
| **全部 9 题合并** | **单轮（`r1`）** | `9 / 9`（缺 `0`） | **12 / 12（100%）** | **12 / 12（100%）** | **9 / 9（100%）** | **0 条** | — |
| **全部 9 题合并** | **3 轮重复（`r1`–`r3`）** | **`27 / 27`（缺 `0`）** | **36 / 36（100%）** | **36 / 36（100%）** | **27 / 27（100%）** | **0 条**（6 份干净章报告零误报） | **无** |

### 2. 逐题检出明细（3 轮汇总）

| 题号 | 类别与考察点 | 预期结论 | 3 轮实际结论（`r1／r2／r3`） | 预期埋错检出 |
|---|---|---|---|---|
| `A01-古代时代错置与称谓` | 古代出现“手表”＋自称“我令尊” | 不通过 | 不通过／不通过／不通过 | `d1` 3/3；`d2` 3/3 |
| `A02-月相与行程` | 腊月初三写满月＋三日路程半日走到 | 不通过 | 不通过／不通过／不通过 | `d1` 3/3；`d2` 3/3 |
| `A03-待核项写了数字` | 待核丹炉火候写出“一千二百度” | 不通过 | 不通过／不通过／不通过 | `d1` 3/3 |
| `A04-视角越权与超前泄密` | 限知越权写二叔主谋＋提前泄密青铜门洞天真相 | 不通过 | 不通过／不通过／不通过 | `d1` 3/3；`d2` 3/3 |
| `A05-场景卡翻转没发生` | 当众揭穿翻转落空＋强度 4 爽点承诺违约 | 不通过 | 不通过／不通过／不通过 | `d1` 3/3 |
| `A06-干净对照` | 传统底蕴、月相、三日路程与知情边界干净章 | 通过 | 通过／通过／通过 | （干净章，0 误报） |
| `P01` | 强度 5 跨章断章钩切镜头诈骗＋未揭晓暗线 `FS-0004` 剧透真义 | 不通过 | 不通过／不通过／不通过 | `d1` 3/3；`d2` 3/3 |
| `P02` | 反派赵管事违背知情盲区与利益算盘降智送账＋第一手受挫与两难落空 | 不通过 | 不通过／不通过／不通过 | `d1` 3/3；`d2` 3/3 |
| `P03` | 白金章首秒接、暗线只露伪装、受挫两难落地与配角利益自洽干净章 | 通过 | 通过／通过／通过 | （干净章，0 误报） |

### 3. 实测暴露的局限与答案之外的观察（`E02` 局限报告）
1. **跨章断章钩机械预检的二元词重合局限（重要发现）**：
   - `scripts/check_chapter.py` 中的 `hook_handoff_warnings` 通过提取上一章 `hook.line + end.next` 的汉字二元词（2-gram），检查本章前 350 个汉字是否出现任一二元词。
   - 在 `P01` 中，上一章断章句含主角姓名“沈砚”，而本章切镜头到次日清晨外门膳堂喝粥时同样出现“沈砚”，导致二元词命中，机械层输出 `- （无）`（漏发机械提醒）；只有当断章句不含下章开头共现人名时（已在 `scripts/tests/test_ncc_eval.py` 验证），机械层才会发出 `跨章断章承接` 告警。
   - **影响与结论**：同主角跨场切镜头诈骗不能仅靠当前 2-gram 机械启发式兜底，必须依赖 `continuity` 模型审计；本次盲审证明在无机械提醒的条件下，`continuity` 仍在 `P01` 的 3/3 轮中 100% 检出该断章诈骗。后续规则演进建议在 `hook_handoff_warnings` 计算呼应词时剔除主角名与高频称谓词。
2. **答案之外的附加观察分布**：
   - 两章干净对照（`A06`、`P03`，合计 6 份独立报告）均返回 `| 1 | 无 | | | 无 | |`，**零附加观察、零误报**。
   - 阳性缺陷章中，审稿人除 100% 命中预设埋错外，还指出了由埋错连带引发的次生逻辑/场景卡缺口：`P01` 全部 3 轮均额外指出跳过石室逃生连带导致场景卡第一手受挫落空及“一盏茶＋一刻钟”超出台账“步行一刻钟”；`P02` 全部 3 轮均额外指出门廊六名佩刀护院值守下主角直接推门而入缺少避哨潜行因果；`A03`（2/3 轮指出抽柴减火折中绕开两难、1/3 轮指出“吸热”偏现代理化词）与 `A04`（2/3 轮指出陆言未开口试探二叔即被单向警告）存在次要观察条目的轮次浮动，但不影响主缺陷检出（100%）与整章通过／不通过结论（100%）。

---

## 四、27 份独立盲审报告到子会话的完整定位表（已脱敏）

全部 27 个子会话均一次完成、零缺份、零重派，完整 64 位 SHA-256 固化于 [blind-eval/manifest.json](blind-eval/manifest.json)（轨迹日志均位于 `<APP_DATA_DIR>/brain/<conversation-id>/.system_generated/logs/transcript.jsonl`）：

| 盲审编号 | 揭盲题号 | 轮次 | 应为 → 实判 | 独立子会话 ID | 派单包 SHA-256（前 16 位） | 报告 SHA-256（前 16 位） | 脱敏轨迹定位 |
|---|---|---|---|---|---|---|---|
| `M01` | `P02` | `r1` | 不通过 → 不通过 | [`690f9f9b-bb53-4532-8ead-28b427fb9395`](conversation://690f9f9b-bb53-4532-8ead-28b427fb9395) | `372b1f8387f7101c` | `6600004738430719` | `<APP_DATA_DIR>/brain/690f9f9b-bb53-4532-8ead-28b427fb9395/.system_generated/logs/transcript.jsonl` |
| `M02` | `A03-待核项写了数字` | `r3` | 不通过 → 不通过 | [`a60ad773-8d59-4bbc-bd4a-f3eb99a4af20`](conversation://a60ad773-8d59-4bbc-bd4a-f3eb99a4af20) | `30412c354e96fdbd` | `d4a1a10a7607ba9e` | `<APP_DATA_DIR>/brain/a60ad773-8d59-4bbc-bd4a-f3eb99a4af20/.system_generated/logs/transcript.jsonl` |
| `M03` | `A02-月相与行程` | `r2` | 不通过 → 不通过 | [`f61aaa37-3b76-49a6-901e-fa82067f9cc3`](conversation://f61aaa37-3b76-49a6-901e-fa82067f9cc3) | `a0c24b6fa543ac94` | `757060f3dc92df28` | `<APP_DATA_DIR>/brain/f61aaa37-3b76-49a6-901e-fa82067f9cc3/.system_generated/logs/transcript.jsonl` |
| `M04` | `P03` | `r1` | 通过 → 通过 | [`8c7fc8f5-b7f4-4d04-9cc3-96127aff0cb7`](conversation://8c7fc8f5-b7f4-4d04-9cc3-96127aff0cb7) | `07b2657e1a2d440d` | `0937e786df3785cb` | `<APP_DATA_DIR>/brain/8c7fc8f5-b7f4-4d04-9cc3-96127aff0cb7/.system_generated/logs/transcript.jsonl` |
| `M05` | `A03-待核项写了数字` | `r1` | 不通过 → 不通过 | [`69b15e78-f930-46e5-98a0-38fcf6444000`](conversation://69b15e78-f930-46e5-98a0-38fcf6444000) | `1912114e2e77d15b` | `b35982f92e1ab243` | `<APP_DATA_DIR>/brain/69b15e78-f930-46e5-98a0-38fcf6444000/.system_generated/logs/transcript.jsonl` |
| `M06` | `P01` | `r3` | 不通过 → 不通过 | [`e3398084-4418-42f1-a6c2-299f001c97b0`](conversation://e3398084-4418-42f1-a6c2-299f001c97b0) | `448ba1979eeb3959` | `9db4ef3a92f07310` | `<APP_DATA_DIR>/brain/e3398084-4418-42f1-a6c2-299f001c97b0/.system_generated/logs/transcript.jsonl` |
| `M07` | `A04-视角越权与超前泄密` | `r2` | 不通过 → 不通过 | [`171cbf52-4c74-4f31-8395-28efe15aed73`](conversation://171cbf52-4c74-4f31-8395-28efe15aed73) | `ea5dd60e1228ea3a` | `77435c10dd4ea29e` | `<APP_DATA_DIR>/brain/171cbf52-4c74-4f31-8395-28efe15aed73/.system_generated/logs/transcript.jsonl` |
| `M08` | `A06-干净对照` | `r3` | 通过 → 通过 | [`222df2d2-1381-4f40-8629-467d8401b8ed`](conversation://222df2d2-1381-4f40-8629-467d8401b8ed) | `b25cb2562e17f723` | `0937e786df3785cb` | `<APP_DATA_DIR>/brain/222df2d2-1381-4f40-8629-467d8401b8ed/.system_generated/logs/transcript.jsonl` |
| `M09` | `A04-视角越权与超前泄密` | `r3` | 不通过 → 不通过 | [`e559bb5a-8d3a-4775-93a9-f160703e584a`](conversation://e559bb5a-8d3a-4775-93a9-f160703e584a) | `10554c96fe85a22c` | `d14ab717ffbf63e7` | `<APP_DATA_DIR>/brain/e559bb5a-8d3a-4775-93a9-f160703e584a/.system_generated/logs/transcript.jsonl` |
| `M10` | `A05-场景卡翻转没发生` | `r1` | 不通过 → 不通过 | [`9999c826-e0cc-4da2-9adb-5d9f5b2b207c`](conversation://9999c826-e0cc-4da2-9adb-5d9f5b2b207c) | `07015f88b86c7021` | `3a06c5353246dd16` | `<APP_DATA_DIR>/brain/9999c826-e0cc-4da2-9adb-5d9f5b2b207c/.system_generated/logs/transcript.jsonl` |
| `M11` | `A01-古代时代错置与称谓` | `r3` | 不通过 → 不通过 | [`3a65784a-fb7a-489e-9cbf-5633d867df5e`](conversation://3a65784a-fb7a-489e-9cbf-5633d867df5e) | `7b4217a092a8dc3a` | `a404c4a0987259ec` | `<APP_DATA_DIR>/brain/3a65784a-fb7a-489e-9cbf-5633d867df5e/.system_generated/logs/transcript.jsonl` |
| `M12` | `A02-月相与行程` | `r1` | 不通过 → 不通过 | [`8c763617-7023-4550-88cc-06caae505aaf`](conversation://8c763617-7023-4550-88cc-06caae505aaf) | `673111b38cff0524` | `e8ebfb3ebc0b289b` | `<APP_DATA_DIR>/brain/8c763617-7023-4550-88cc-06caae505aaf/.system_generated/logs/transcript.jsonl` |
| `M13` | `A06-干净对照` | `r1` | 通过 → 通过 | [`ba10b1b5-d6c0-469b-baa6-7d4fd0ad0223`](conversation://ba10b1b5-d6c0-469b-baa6-7d4fd0ad0223) | `b3e5a692776252ca` | `0937e786df3785cb` | `<APP_DATA_DIR>/brain/ba10b1b5-d6c0-469b-baa6-7d4fd0ad0223/.system_generated/logs/transcript.jsonl` |
| `M14` | `A04-视角越权与超前泄密` | `r1` | 不通过 → 不通过 | [`ccb473f9-1b88-4b77-a72a-07ba3d6a6306`](conversation://ccb473f9-1b88-4b77-a72a-07ba3d6a6306) | `dc64276507c7992a` | `898df575e5d617e2` | `<APP_DATA_DIR>/brain/ccb473f9-1b88-4b77-a72a-07ba3d6a6306/.system_generated/logs/transcript.jsonl` |
| `M15` | `P03` | `r3` | 通过 → 通过 | [`688e1203-7f00-4d74-ac65-6f2abc630daf`](conversation://688e1203-7f00-4d74-ac65-6f2abc630daf) | `c165ecfcd171b26e` | `0937e786df3785cb` | `<APP_DATA_DIR>/brain/688e1203-7f00-4d74-ac65-6f2abc630daf/.system_generated/logs/transcript.jsonl` |
| `M16` | `A05-场景卡翻转没发生` | `r3` | 不通过 → 不通过 | [`a7c0d8bb-5da2-4344-bad9-9244fe078791`](conversation://a7c0d8bb-5da2-4344-bad9-9244fe078791) | `96ad5c8c7c2e6d3a` | `ad4d83a5b3ebf92e` | `<APP_DATA_DIR>/brain/a7c0d8bb-5da2-4344-bad9-9244fe078791/.system_generated/logs/transcript.jsonl` |
| `M17` | `P01` | `r2` | 不通过 → 不通过 | [`c19e76d7-8832-49cc-b389-6d4bab186c4a`](conversation://c19e76d7-8832-49cc-b389-6d4bab186c4a) | `020e5eeb29d6823f` | `08f1f089833a075d` | `<APP_DATA_DIR>/brain/c19e76d7-8832-49cc-b389-6d4bab186c4a/.system_generated/logs/transcript.jsonl` |
| `M18` | `A01-古代时代错置与称谓` | `r1` | 不通过 → 不通过 | [`166b9c2a-39e0-4a65-8947-4bb841432d7c`](conversation://166b9c2a-39e0-4a65-8947-4bb841432d7c) | `8619057ad02477c6` | `0d53a7f89cd772b1` | `<APP_DATA_DIR>/brain/166b9c2a-39e0-4a65-8947-4bb841432d7c/.system_generated/logs/transcript.jsonl` |
| `M19` | `P02` | `r3` | 不通过 → 不通过 | [`5dc9bf69-046a-4988-bebc-3f29405d5b3e`](conversation://5dc9bf69-046a-4988-bebc-3f29405d5b3e) | `e085bad8aac9ea75` | `e366393480b4d188` | `<APP_DATA_DIR>/brain/5dc9bf69-046a-4988-bebc-3f29405d5b3e/.system_generated/logs/transcript.jsonl` |
| `M20` | `A05-场景卡翻转没发生` | `r2` | 不通过 → 不通过 | [`f521035f-bfff-4f6d-8d78-461691c2d4c1`](conversation://f521035f-bfff-4f6d-8d78-461691c2d4c1) | `c5f4c204f9ae065a` | `75637013e3563792` | `<APP_DATA_DIR>/brain/f521035f-bfff-4f6d-8d78-461691c2d4c1/.system_generated/logs/transcript.jsonl` |
| `M21` | `P02` | `r2` | 不通过 → 不通过 | [`7f2bbd11-4f7e-4935-a63b-b56ef901a6e6`](conversation://7f2bbd11-4f7e-4935-a63b-b56ef901a6e6) | `2d075e9dd6380df2` | `9f84269912300aa5` | `<APP_DATA_DIR>/brain/7f2bbd11-4f7e-4935-a63b-b56ef901a6e6/.system_generated/logs/transcript.jsonl` |
| `M22` | `A01-古代时代错置与称谓` | `r2` | 不通过 → 不通过 | [`6752e53c-ca6f-4081-955f-95af870e656d`](conversation://6752e53c-ca6f-4081-955f-95af870e656d) | `b617b6d627af8ca3` | `9a4cb11a83927379` | `<APP_DATA_DIR>/brain/6752e53c-ca6f-4081-955f-95af870e656d/.system_generated/logs/transcript.jsonl` |
| `M23` | `A06-干净对照` | `r2` | 通过 → 通过 | [`b51c8886-357b-4630-955e-97b650a6607e`](conversation://b51c8886-357b-4630-955e-97b650a6607e) | `8488c20cab37c00e` | `0937e786df3785cb` | `<APP_DATA_DIR>/brain/b51c8886-357b-4630-955e-97b650a6607e/.system_generated/logs/transcript.jsonl` |
| `M24` | `P01` | `r1` | 不通过 → 不通过 | [`01e0c284-1137-43cc-929a-78ac03bb4283`](conversation://01e0c284-1137-43cc-929a-78ac03bb4283) | `72efde49154e136a` | `68bae2c073a10562` | `<APP_DATA_DIR>/brain/01e0c284-1137-43cc-929a-78ac03bb4283/.system_generated/logs/transcript.jsonl` |
| `M25` | `A02-月相与行程` | `r3` | 不通过 → 不通过 | [`677cdd2e-5692-434b-a425-4c4de357a11b`](conversation://677cdd2e-5692-434b-a425-4c4de357a11b) | `fda09b1d3c24954f` | `8ef761423295986e` | `<APP_DATA_DIR>/brain/677cdd2e-5692-434b-a425-4c4de357a11b/.system_generated/logs/transcript.jsonl` |
| `M26` | `P03` | `r2` | 通过 → 通过 | [`5c002790-0999-4f4c-883f-85d8f5066aa7`](conversation://5c002790-0999-4f4c-883f-85d8f5066aa7) | `d7956b19b23ec28f` | `0937e786df3785cb` | `<APP_DATA_DIR>/brain/5c002790-0999-4f4c-883f-85d8f5066aa7/.system_generated/logs/transcript.jsonl` |
| `M27` | `A03-待核项写了数字` | `r2` | 不通过 → 不通过 | [`314aaa91-120b-4fec-b4c3-248ec20b3947`](conversation://314aaa91-120b-4fec-b4c3-248ec20b3947) | `d36652e5e3cd436a` | `2e8c4f347f6349fc` | `<APP_DATA_DIR>/brain/314aaa91-120b-4fec-b4c3-248ec20b3947/.system_generated/logs/transcript.jsonl` |

---

## 五、五宿主与当前执行宿主的实际覆盖状态（按能力实报）

按 `docs/engineering/workflow.md` 规范，严格区分项目级静态挂载／清单核验与新会话实际运行结果，不将静态读文件伪报为新会话加载通过：

| 宿主 | 本机二进制与配置核验 | 静态挂载／打包清单状态 | 新会话运行加载状态 | 实测依据与受阻原因说明 |
|---|---|---|---|---|
| **Antigravity（`agy`）** | `agy 1.5.15`（`/opt/homebrew/bin/agy`） | **`passed`**（`.agents/skills/` 12 项相对软链） | **`passed`** | 本窗口 `ttys006` 新会话实测自动发现 `.agents/skills/*` 全部 12 技能，定位 `plugin_root` = `repo_root`（版本 `4.0.0`），并实际派发与回收 27 个独立 fresh `continuity` 盲审子会话 |
| **`claude`** | `2.1.286 (Claude Code)`（`/opt/homebrew/bin/claude`） | **`passed`**（`.claude/skills`、`.claude/commands`、`.claude/agents` 相对软链及 `.claude-plugin/{plugin.json,marketplace.json}` 一致） | **`blocked`** | `ttys006` 标准沙盒无外网与 `$HOME/.claude` 登录凭据读取权限，无法在沙盒内发起外部模型新会话；静态接线已由 `check_plugin.py -v` 实测通过 |
| **`codex`** | `codex-cli 0.171.0`（`/opt/homebrew/bin/codex`） | **`passed`**（`.agents/skills`、`plugin.json`、`.agents/plugins/marketplace.json` 一致） | **`blocked`（本沙盒内）** | 本沙盒受禁网与 `$HOME/.codex` 凭据隔离限制，未在沙盒内伪造外部联网新会话 |
| **`kimi`** | `2.1.1`（`$HOME/.kimi-code/bin/kimi`） | **`passed`**（`.agents/skills` 12 项与 `.agents/agents` 16 项相对软链全部有效） | **`blocked`** | 标准沙盒禁网且隔离 `$HOME/.kimi` 认证状态，新会话模型调用需在宿主终端联网核验 |
| **`grok`** | `grok 1.0.92 (b06756fd6256)`（`/opt/homebrew/bin/grok`） | **`passed`**（`.claude/commands`、`.claude/skills`、`.agents/skills`、`.grok/agents` 均指向同一仓内源，无分叉副本） | **`blocked`** | 标准沙盒禁网且隔离 `$HOME/.grok` 认证状态；静态核实四处挂载软链同源无内容冲突，运行时的重复发现展示优先级待沙盒外新会话冒烟确认 |
| **`zcode`** | 当前 `PATH` 未检出 `zcode` 二进制；宿主机存在 `$HOME/.zcode/cli/config.json`（权限 `0600`） | **`passed`**（权威源 `.zcode-plugin/plugin.json` 版本 `4.0.0` 与目录指向校验通过） | **`unverified` / `blocked`** | 标准沙盒内无 `zcode` 可执行入口且按权限边界不读取 `$HOME/.zcode/cli/config.json`，保持 `unverified` 待宿主环境新会话验证 |
