# AGY 升级修复与质量复验回执（11 月 24 日续办）

## 一、接单状态与执行纪律

- **当前状态**：创作 CLI 批次（**R06–R08**）**已修复并通过定向复验，现正式交付**。按 [任务单](../../tasks/2026-11-23-agy-upgrade-audit.md)「作者开放三个终端后的职责分配」，本会话（`ttys004`）严格只负责 **R06–R08**（即 W03、W04、W06、W07、W08 的创作 CLI 修复、临时合成书边界验证与相邻兼容性），其余批次分别由 `ttys000`（[agy-backend.md](agy-backend.md)）、`ttys005`（[agy-frontend.md](agy-frontend.md)）、`ttys006`（[agy-evaluation.md](agy-evaluation.md)）承接推进。
- **执行会话**：AGY 会话 `1b2192e6-001b-481e-83b3-ebac7e6864e3`（`ttys004`，接续首轮候选 `ed549dae-00c1-4357-9296-893e200ab8ba`）。
- **路径与版本**：
  - `repo_root`：`/Users/xuyun/Documents/ncc-workflow`
  - `plugin_root`：`/Users/xuyun/Documents/ncc-workflow`
  - 分支与版本：`main`（与 `origin/main` 同指向 `b80a21fdbeaea54bf8f49631ad189f01818b0504`），插件版本 `4.0.0`。
- **硬约束遵守声明**：
  - 全程亲自运行定向 CLI 单元测试与临时合成书（`tempfile.TemporaryDirectory`）边界验证，修复后重验，未放宽任何定稿闸、未删减任何测试场景。
  - 未执行任何清库，未触碰 `ncc-pro`、真实书稿（`novels/` 等）、密钥（`config/.env`）及其他三个窗口负责的源码和回执。
  - 未执行 `rm`、`git reset`、`git checkout --`、`git clean`、`git commit` 或 `git push`。

## 二、候选基线与首轮已实际完成的工作

- **基线提交**：`b80a21fdbeaea54bf8f49631ad189f01818b0504`（`docs: record platinum workflow upgrade publication`）。
- **工作树既有落盘成果（首轮已修基础项）**：
  - **数据与配置**：D01 普通夹具移除整库 `TRUNCATE` 并在 `reset()` 增加非空库保护（账号生命周期收尾归入 R03）；D02 本地默认环境选库与文档对齐；D03 总览接入 `redact_with_definitions` 字段级可见性投影；D04 跨范围参考不持久化原文、按实时权限裁剪；D05 调序请求幂等键前置并校验摘要；A03 模型凭据优先级对齐配置；A04 订阅登录态严格核验。
  - **白金创作 CLI**：W01 暗线作废（`dropped_ch`）与兑现（`resolved_ch`）分离并隔离未揭晓真义；W02 沙盘生成区块签名缺失/损坏/篡改防覆盖；W05 默认沙盘窗口收敛至在期单元或近 10 章（边界细节归入 R06–R08）。
  - **AI 工序与工作台**：A01/A02 显式与默认工序阶段校验、P5 与双评附加报告门禁及拒绝显式工序并传托管；A05/A08 工作副本双向同步实现与系统配置锁行合并实现（联调用例归入 R04/R10）；A06 双卷全书章序与开篇保护；A10 无目标单推细纲立新章只写 `beat_outline` 不污染正文与事实；U01/U02 创作台自动草稿全字段覆盖与新建章换章草稿保护。
  - **静态一致性初检**：`build_registry.py --check` 返回 `REGISTRY OK`，`build_docs.py --check` 返回 `DOCS OK`；`check_plugin.py -v` 此前唯一缺失引用即为本回执路径 `docs/evidence/2026-11-23-agy-upgrade-audit/agy-feedback.md`。

## 三、续办状态总表（本会话负责 R06–R08；其余见各终端专属回执）

| 编号 | 领域 | 当前状态 | 修改路径 | 定向检查／操作 | 实际结果与证据 |
|---|---|---|---|---|---|
| R01 | 总览 JSONB 分组 SQL | 转由 `ttys000` 负责 | 见 [agy-backend.md](agy-backend.md) | 见 `ttys000` 回执 | [agy-backend.md](agy-backend.md) |
| R02（含补充） | 角色枚举、跨页全书统计、`〇` 汉字口径与待埋设暗线口径 | 转由 `ttys000` 负责 | 见 [agy-backend.md](agy-backend.md) | 见 `ttys000` 回执 | [agy-backend.md](agy-backend.md) |
| R03 | 合成测试账号隔离与收尾禁用 | 转由 `ttys000` 负责 | 见 [agy-backend.md](agy-backend.md) | 见 `ttys000` 回执 | [agy-backend.md](agy-backend.md) |
| R04 | A05/A08 联调用例缺导入修复 | 转由 `ttys000` 负责 | 见 [agy-backend.md](agy-backend.md) | 见 `ttys000` 回执 | [agy-backend.md](agy-backend.md) |
| R05 | 匿名化锚定章与白金判据独立盲审 | 转由 `ttys006` 负责 | 见 [agy-evaluation.md](agy-evaluation.md) | 见 `ttys006` 回执 | [agy-evaluation.md](agy-evaluation.md) |
| R06 | W03/W04 沙盘待复核保持、处境历史保留与历史沙盘单元定位 | **已修／已验证** | `scripts/ncclib/loops.py`、`scripts/ncclib/ledgers.py`、`scripts/tests/test_platinum_upgrade.py` | 单元测试 16/16 + 临时合成书探针 18/18 | 通过：[r06-r08-cli.log](r06-r08-cli.log)、[r06-r08-synthetic-probe.log](r06-r08-synthetic-probe.log) |
| R07 | W06/W07 同场 vs 同章合拢区分、延后/批注/否定不授权揭晓 | **已修／已验证** | `scripts/ncclib/loops.py`、`scripts/ncclib/scenes.py`、`scripts/tests/test_platinum_upgrade.py` | 单元测试 16/16 + 临时合成书探针 18/18 | 通过：[r06-r08-cli.log](r06-r08-cli.log)、[r06-r08-synthetic-probe.log](r06-r08-synthetic-probe.log) |
| R08 | W08 定稿报告结论/SHA 核验、旧报告兼容与正常字数免重批旧例外 | **已修／已验证** | `scripts/ncclib/book.py`、`scripts/tests/test_platinum_upgrade.py` | 单元测试 16/16 + 临时合成书探针 18/18 | 通过：[r06-r08-cli.log](r06-r08-cli.log)、[r06-r08-synthetic-probe.log](r06-r08-synthetic-probe.log) |
| R09 | 待办与任务中心跳创作台/具体任务定位及返回 | 转由 `ttys005` 负责 | 见 [agy-frontend.md](agy-frontend.md) | 见 `ttys005` 回执 | [agy-frontend.md](agy-frontend.md) |
| R10 | 三条新增 PostgreSQL 联调用例按任务推进打通 | 转由 `ttys000` 负责 | 见 [agy-backend.md](agy-backend.md) | 见 `ttys000` 回执 | [agy-backend.md](agy-backend.md) |
| R11 | 蓝图内存草稿绑定登录会话与注销/撤权清理 | 转由 `ttys005` 负责 | 见 [agy-frontend.md](agy-frontend.md) | 见 `ttys005` 回执 | [agy-frontend.md](agy-frontend.md) |

## 四、创作 CLI 批次（R06–R08）查明修正与真实合成书边界验证明细

### 1. 前次日志 `r06-r08-cli.log` 单项失败查明与修正

- **既有失败现象**：重启前日志显示 `Ran 16 tests` 中 15 项通过，`test_r06_r07_r08_rework_verifications` 在第 1 章 `complete --words 3240` 报 `ERROR: 章定稿闸：第 1 章当前 2700 字不在区间 3000–5000，请先经 chapter length --accept 确认`（若进区间仍会命中申报字数与实际汉字数核验）。
- **根因查明**：`scripts/ncclib/core.py:han_words` 按统一汉字口径仅统计汉字（不含中文标点 `，`、`。`）。原测试句 `"风雪寒鸦渡，孤灯照旧剑。"` 含 10 个汉字、2 个标点，乘 `270` 实际仅有 `2700` 汉字，与测试拟构造的正常区间 3240 字样本不符；此外新增历史单元关闭测试步骤中曾误写 `06-复盘/单元-U1.md`（实际注册表布局 `REVIEW_DIR` 为 `05-审稿/复盘`）。
- **修正措施**：保持 `scripts/ncclib/book.py:cmd_complete` 全部定稿闸（字数区间、申报字数容差、报告结论与 SHA 新鲜度）零放宽、零删减测试场景，在 `scripts/tests/test_platinum_upgrade.py` 中将该正常区间样本修正为 `"风雪寒鸦渡，孤灯照旧剑。" * 324`（精确 `3240` 汉字），并从 `report unit --write` 回执解析真实复盘底稿路径后补充更严密的边界断言。

### 2. R06–R08 代码修复要点

- **R06（W03/W04）— `scripts/ncclib/loops.py`、`scripts/ncclib/ledgers.py`**：
  - **沙盘待复核跨刷新保持**：`cmd_sandbox` 新增 `_has_explicit_digest_ack(outside, new_sha)` 与 `--ack-review` 当前快照一致性校验；区块外随手追加普通备忘再 `--write` 刷新不会清除 `stale_base`，未先刷新看到新快照而盲传 `--ack-review` 直接拒绝（`exit=1`），仅在拍板区明确写入 `已复核：<当前16位摘要>` 或对已落盘当前快照执行 `--ack-review` 时才解除待复核提示。
  - **清空当前处境保留旧章历史快照**：`plight_lines(d, seq)` 提取 `_history_plight_for_seq(history, seq)`，当第 6 章执行 `plight --clear` 使当前 `d["plight"]` 为空时，不再提前返回空列表，而是按目标章 `seq` 命中 `plight_history` 中 `since_ch <= seq <= until_ch` 的历史快照；`cmd_plight` 同时结合 `current_chapter`、已关单元 `end` 与在期单元 `start` 计算生效章并记录 `plight_cleared_ch`。
  - **历史沙盘按章取单元**：`sandbox_lines` 改用 `unit_for_chapter(d, lo)` 定位目标窗口所属单元（与 `focus_core` 同源），并过滤 `created_ch > hi` 的未来承诺；旧章窗口（`--from 1 --to 5`）准确读取历史单元 `U1` 倒计时与里程碑，无在期历史单元时显式隔离未来单元倒计时。
- **R07（W06/W07）— `scripts/ncclib/loops.py`、`scripts/ncclib/scenes.py`**：
  - **区分同章兑现与同场合拢**：`sandbox_lines` 仅当单章场景卡同一 `## 场景 N` 块内显式有效回收 ≥2 条具备资格的不同承诺时报告 `多线雪崩合拢达标`；仅有台账同章 `resolve` 无场景卡，或分属 `## 场景 1`、`## 场景 2` 不同场回收时，报告 `同章多线兑现（未证同场）`，绝不误报同场合拢。
  - **拒绝延后/批注/否定揭晓，支持明确本场有效回收**：重写 `declared_reveal_ids`，以 `_mask_parens` 与 `_split_top_level` 保证括号内逗号/分号不拆断延后修饰，拦截延后（`下章再揭晓`、`留到卷末再揭晓`、`第N章再揭晓`）、批注（`（批注：…）`、`【注】`、纯括号编号）、占位示例及否定/仅擦碰描述；并列声明如 `FS-0003（本场揭开密令）、FS-0004（下章再揭晓）` 精确放行 `FS-0003` 并隔离 `FS-0004`，同时避免对 `禁地`、`识别`、`不得不` 等正常叙事词误杀。
- **R08（W08）— `scripts/ncclib/book.py`**：
  - **审稿报告结论与正文摘要校验及旧报告兼容**：`cmd_complete` 新增 `_inspect_review_report`，解析 `--report` 中的硬伤/总体结论（支持普通列表、Markdown 加粗、未填模板占位 `通过 | 不通过` 识别及 `## 复审记录` `rev 1（SHA old→new）` 末尾结论覆盖）、可判定率与绑定 SHA；传入 `不通过` 或摘要与当前正文 SHA256 前缀不一致的报告时，即使命令行传 `--hard pass` 也严拒定稿；无 SHA 元数据的历史合格简版报告保持兼容。
  - **正常字数区间免重批旧例外**：当正文此前因偏短（如 `1800` 字）做过 `chapter length --accept`，后续扩写回正常区间（`3000–5000`，如 `3200` 字）时，`in_normal_band` 为真，不再因旧 `length.sha` 变化拦截定稿，并在定稿时自动清理已失效的旧篇幅例外记录；若改后仍处异常区间（如 `2100` 字）且 SHA 变化，则继续严格拦截。

### 3. 临时合成书逐项边界对比结果（证据见 [r06-r08-synthetic-probe.log](r06-r08-synthetic-probe.log)）

| 核验维度 | 对照场景 | CLI 实际输出与状态结果 |
|---|---|---|
| **R06 · 待复核状态** | 改台账后在沙盘区块外补 `- 普通随手备忘：…` 再 `--write` 刷新 vs 拍板区写明 `已复核：39299f9f70f87c82`（或对已见快照执行 `--ack-review`） | 普通备忘刷新后仍保留 `> ⚠ 底层台账或场景卡已变更`；盲传 `--ack-review`（未先刷新新快照）返回 `exit=1` 拒绝；明确复核当前摘要后刷新，告警正常解除。 |
| **R06 · 旧章 vs 当前章** | 第 1 章设处境「第1章司礼监封库死令」并完成关闭 `U1`（1–5 章，倒计时「距离焚档仅剩三更」）；第 6 章开 `U2`（倒计时「第6章新开七日诏狱死限」）并 `plight --clear` | **旧章（第 2 章 `pack` & 第 1–5 章 `sandbox`）**：均命中 `U1`（「距离焚档仅剩三更」）并完整保留「第1章司礼监封库死令」，零泄露第 6 章 `U2` 倒计时。<br>**当前章（第 6–10 章 `sandbox`）**：命中 `U2`（「第6章新开七日诏狱死限」），处境反映已清空（`⚠ 未登记`），不含第 1 章旧处境。 |
| **R07 · 同章 vs 同场** | 第 7 章 `FS-0001`+`FS-0002`：①仅台账同章兑现无场景卡；②分属 `## 场景 1` 与 `## 场景 2`；③同一 `## 场景 1` 显式并列回收 | ①与②均输出 `同章多线兑现（未证同场）：第 7 章`，未报合拢达标；③输出 `**多线雪崩合拢达标**：第 7 章同场引爆兑现 ≥2 条线索`。 |
| **R07 · 拒绝 vs 允许揭晓** | **拒绝揭晓**：第 6 章填 `FS-0003（下章再揭晓）`、`（表面写旧疤，实留到卷末再揭晓）`、`（批注：…）`、`暂不揭晓 FS-0003`，以及重打旧章第 2 章 `pack`<br>**允许揭晓**：第 6 章填 `伏笔回收：FS-0003（本场当众刮去药泥揭穿死士刺青）` | **拒绝揭晓（第 6 章 & 旧章第 2 章）**：写手包均不含里层真义「前朝皇城司死士编号」，第 6 章仅带出公开伪装「烫伤遮住的旧疤」。<br>**允许揭晓（第 6 章）**：写手包正常注入 `伏笔回收揭晓：前朝皇城司死士编号`。 |
| **R08 · 无效 vs 有效/旧报告** | **无效报告**：①`硬伤层: 不通过`+过期 SHA + `--hard pass`；②未填模板 `通过 \| 不通过`；③`硬伤层: 通过` 但 SHA `1111222233334444` ≠ 当前 `8e4af1ed1336625f`<br>**有效报告**：④含 `rev 1（SHA 1111222233334444→8e4af1ed1336625f）…结论：通过`；⑤第 8 章无 SHA 元数据旧式合格报告 | ①、②、③全部被定稿闸拦截（`exit=1`），章节保持未定稿；④与⑤均通过定稿（`exit=0`，分别写入 `sha=8e4af1ed1336625f` 与 `sha=e93a79d4c9c86348`）。 |
| **R08 · 篇幅例外恢复** | 第 6 章初稿 `1800` 字 `length --accept --force` → 改 `2100` 字（仍低于 `3000`）直接 `complete` vs 扩写至 `3200` 字（正常区间 `3000–5000`）直接 `complete` | `2100` 字返回 `exit=1`（提示篇幅确认后已改动且仍不在区间，须重确认）；`3200` 字无需重跑 `length --accept` 直接 `OK complete ch6 words=3200`，并自动移除过期的 `length` 例外字段。 |

### 4. 定向检查命令、通过数与证据路径汇总

1. **白金升级与 CLI 架构契约单元测试（16/16 通过，`exit=0`）**
   - 命令：`python3 -m unittest scripts/tests/test_platinum_upgrade.py scripts/tests/test_architecture.py -v`
   - 结果：`Ran 16 tests in 22.375s — OK`（16/16 全绿，含预升级 CLI 参数快照与运行产物契约守卫）
   - 证据路径：[r06-r08-cli.log](r06-r08-cli.log)
2. **R06–R08 临时合成书定向边界探针（18/18 断言通过，`exit=0`）**
   - 命令：使用 `tempfile.TemporaryDirectory` 执行独立 CLI 探针（逐项验证旧章/当前章、拒绝/允许揭晓、无效/有效/旧报告与篇幅区间恢复）
   - 结果：`ALL R06–R08 SYNTHETIC PROBES PASSED (18/18 assertions)`
   - 证据路径：[r06-r08-synthetic-probe.log](r06-r08-synthetic-probe.log)
3. **相邻创作 CLI 兼容性与静态一致性复验**
   - `python3 -m unittest scripts/tests/test_ncc_state.py scripts/tests/test_v3_regressions.py scripts/tests/test_quality.py scripts/tests/test_registry.py scripts/tests/test_plugin_manifests.py scripts/tests/test_ncc_prepare.py scripts/tests/test_ncc_library.py scripts/tests/test_deconstruction.py`：实际输出 `Ran 161 tests in 91.440s — FAILED (errors=1)`，即共运行 `161` 项，其中 `160` 项通过、`0` 项断言失败（`failures=0`）、`1` 项受沙箱阻断报错（`errors=1`：`TestEvolution.test_anchor_new` 向仓内 `eval/anchors/A99-测试骨架` 写入时受终端沙箱写保护阻断，后续读取 `answers.json` 报 `FileNotFoundError`；`eval/` 归 `ttys006` 负责，未触碰）。
   - `python3 scripts/ncc_eval.py mech`：`6/6 PASS`（A01–A06 机械锚定全通过）。
   - `python3 scripts/dev/build_registry.py --check`：`REGISTRY OK`。
   - `python3 scripts/dev/build_docs.py --check`：`DOCS OK`。
   - `python3 scripts/dev/check_plugin.py -v`：`PLUGIN OK`。
