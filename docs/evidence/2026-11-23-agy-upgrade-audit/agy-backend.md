# AGY 后台与数据库修复与复验交付回执（终端 ttys000）

- **终端号**：`ttys000`（后台与数据库窗口）
- **审核接收方**：`ttys004`（新任质量负责人）
- **更新时间**：`2026-11-24T09:35+08:00`
- **交付状态**：**全部已完成并通过真实 `ncc-dev` 定向验证与前后脱敏对账（0 失败、0 待办）** · `READY_FOR_BROWSER`（已与 `ttys005` 完成浏览器夹具随机凭据迁移）
- **归属边界与安全纪律声明**：
  - 仅修改 `ttys000` 负责的后端、数据库夹具与对应测试用例（`src/ncc_data/**`、`tests/backend/**`、`tests/support/**`、`tests/unit/test_studio_pipeline.py`、`tests/unit/test_runtime.py`）及本回执与证据日志。
  - 全程仅使用合成数据与既定 `ncc-dev`，**未执行任何清库（`TRUNCATE`/`reset`）**，未触碰 `ncc-pro`、私人书稿（`novels/`、`books/`、`_作者/`、`_拆书库/`）、`config/.env` 或其他窗口源码，未执行 `rm`、`git commit`、`git push`。

---

## 一、本轮返工项逐项结论总表（R01–R04、R02 补充、R10）

| 编号 | 问题描述 | 当前状态 | 修改文件 | 定向验证命令（受影响文件 / node id） | 实测结果与证据 |
|---|---|---|---|---|---|
| **R01 · P1** | `studio.py` 在 `SELECT` 与 `GROUP BY` 分别构造 JSONB 表达式，真实 PostgreSQL 报 `GroupingError`，普通作者总览失败 | **已修 · 已验证** | `src/ncc_data/api/routes/studio.py`、`tests/backend/test_studio.py` | `.venv/bin/pytest tests/backend/test_studio.py::test_r01_r02_r03_ordinary_author_paged_aggregates_and_ephemeral_lifecycle -v` | 普通非管理员作者（`admin=False`）请求 `GET /api/v1/scopes/{sid}/studio/overview` 实测返回 **`200 OK`**；已通知 `ttys005` 开展浏览器联调。见 [r01-r04-r10-backend.log](r01-r04-r10-backend.log) |
| **R02 · P1** | `studio.py` 接受 `role=character` 与 `Query.role` 不一致；结构分页后全书章节数/字数/暗线/预警/跨卷章序随 `offset/limit` 变化；受限视角跨卷截止章与标准查询需对齐 | **已修 · 已验证** | `src/ncc_data/api/routes/studio.py`、`src/ncc_data/application/knowledge/queries.py`、`tests/backend/test_studio.py` | `.venv/bin/pytest tests/backend/test_studio.py::test_r01_r02_r03_ordinary_author_paged_aggregates_and_ephemeral_lifecycle tests/backend/test_studio.py::test_d03_d05_a07_a09_a11_overview_projection_reorder_idempotency_scale_and_metrics -v` | `role` 严格校验 `{"author","writer","reader"}`（`role=character` 返回 `422`）；先对全书可见结构对象做 `redact_with_definitions` 投影并汇总全书 `diagnostics`、`codex_counts` 与跨卷 `book_order`，再按 `offset/limit` 切片返回当页（`offset=0,2,4,6,8&limit=2` 五页全书 `diagnostics`/`codex_counts` 恒等，`book_order` 恒为 `1..4`）；`role=reader&chapter_id=...` 跨卷章节与场景裁剪和 `POST /entities/search` 完全一致。见 [r01-r04-r10-backend.log](r01-r04-r10-backend.log) |
| **R02 补充** | 后台对“二〇二六”计 3 汉字而前端计 4；标记“待埋设”的临期暗线被计入活跃五条上限 | **已修 · 已验证** | `src/ncc_data/domain/studio_catalog.py`、`src/ncc_data/api/routes/studio.py`、`tests/unit/test_studio_pipeline.py`、`tests/backend/test_studio.py` | `.venv/bin/pytest tests/unit/test_studio_pipeline.py -v`；`test_r01_r02_r03_...` | `_HAN_RE` 精确对齐 ECMAScript `/\p{Script=Han}/gu` 全码位范围（含 `U+3007` `〇`、`U+3005` `々` 及扩展区），`"二〇二六。"` 前后端统一计 **`4`**；新增 `foreshadow_lifecycle` 拆出 `planted` 与 `due_state`，`"status": "待埋设"` 临期暗线输出 `planted=False, due_state="due_soon"`，计入 `planned_hidden_lines=1` 与 `unplanted_due_foreshadow_count=1`，**不计入** `active_hidden_lines`（保持 `1`）。见 [d01-d02-a03-a04-unit.log](d01-d02-a03-a04-unit.log)、[r01-r04-r10-backend.log](r01-r04-r10-backend.log) |
| **R03 · P1** | 合成测试管理员与后端夹具使用固定密码，收尾仅撤会话未停用账号；需消除固定凭据过渡路径且不触碰既有账号 | **已修 · 已验证** | `tests/backend/conftest.py`、`tests/support/runtime.py`、`tests/backend/run_recovery.py`、`tests/backend/test_api_automation.py`、`tests/backend/test_studio.py`、`tests/unit/test_runtime.py` | `.venv/bin/pytest tests/unit/test_runtime.py -v`；`test_r01_r02_r03_...`；`run_r01_r10_audit.py` 实测重登与对账 | 移除全部固定密码与静态 `USERNAME`/`PASSWORD` 过渡路径；每次运行生成一次性随机凭据（`factory.credentials`、`runtime.username`、`runtime.password`、`runtime.new_credentials()`，已由 `ttys005` 同步迁移 `tests/browser/*.py` 全部 5 个脚本）；收尾执行 `active=False` + 轮换 32 字节随机密码哈希 + 撤销 `Session`/`Delegation` + 取消未完成 `Job`。实测运行中登录 `200`，收尾后原会话访问返回 **`401`**、管理员与子账号原密码重登均返回 **`401`**，库内既有 91 个用户（含历史同名 `browser-author`）100% 未改动，本次新建 13 个临时账号残留活跃数为 **`0`**。见 [r01-r04-r10-backend.log](r01-r04-r10-backend.log) |
| **R04 · P1** | `tests/backend/test_studio.py` 导入不存在的 `DefaultModelBindingInput`，并缺 `pytest` 与 `DomainError` 导入 | **已修 · 已验证** | `tests/backend/test_studio.py` | `.venv/bin/pytest tests/backend/test_studio.py::test_a05_a08_cli_studio_bidirectional_workspace_and_concurrent_model_settings -v` | 修正为真实契约模型 `ModelDefaultInput` 并补齐 `pytest`、`DomainError` 导入，同时将 `ncc_state.py init --mode` 对齐合法枚举 `混合`；在真实 `ncc-dev` 完整跑通 A08 并发系统配置保留与 A05 CLI↔Studio 双向工作副本往返及冲突拦截全部最终业务断言。见 [r01-r04-r10-backend.log](r01-r04-r10-backend.log) |
| **R10 · P1** | 三条新增 PostgreSQL 联调用例因 R01、按顺序盲领 `index` 任务及 R04 未走到最终业务断言 | **已修 · 已验证** | `src/ncc_data/creation/worker.py`、`tests/backend/test_studio.py` | `test_d03_d05_a07_a09_a11_...`、`test_d04_a01_a02_a06_a10_...`、`test_a05_a08_...`、`test_r01_r02_r03_...`（4 个 node id） | `Worker` 支持 `job_ids` 与 `run_job(job_id)` 按目标任务身份定向认领推进（不再误领 `adopt` 产生的 `index` 任务）；4 条 PostgreSQL 集成用例在真实 `ncc-dev` 隔离合成范围下 **4/4 全部 `PASSED`**（退出码 `0`），逐项抵达最终业务断言。见 [r01-r04-r10-backend.log](r01-r04-r10-backend.log) |

---

## 二、首轮后台与跨入口事项（D01–D05、A01–A11）关联证据与专项核对

按质量负责人要求，以下将首轮涉及后端、数据库与 AI/跨入口的 **D01–D05** 与 **A01–A11** 全部关联到本次可复查的真实测试结果与脱敏日志：

| 编号 | 验收要点 | 状态 | 对应实现文件 | 验证用例 / 日志证据与关键实测值 |
|---|---|---|---|---|
| **D01 · P0** | 共用 `ncc-dev` 禁止清库；测试仅操作合成数据，前后既有作品/身份/修订摘要一致；恢复演练拒绝非空共用库 | **已修 · 已验证** | `tests/backend/conftest.py`、`tests/support/runtime.py`、`tests/backend/run_recovery.py` | 1. 非空库拒绝清库：`test_reset_refuses_nonempty_shared_ncc_dev_database`（[d01-d02-a03-a04-unit.log](d01-d02-a03-a04-unit.log)）及 `run_recovery.py:guard_nonempty_shared_database`。<br>2. 真实 `ncc-dev` 前后对账（[r01-r04-r10-backend.log](r01-r04-r10-backend.log)）：既有 `Scope` `75 -> 75`（摘要 `5c1ef900742813b0` 不变）、既有 `Revision` `5593 -> 5593`（摘要 `528ad1586ea03c96` 不变）、既有 `User` `91` 条零改动。 |
| **D02 · P1** | 本地 CLI 上手命令默认落 `ncc-dev`，正式部署显式选 `ncc-pro` 并兼容既有入口 | **已修 · 已验证** | `src/ncc_shared/database.py`、`src/ncc_data/cli/main.py`、`docs/guides/data-console.md` | `tests/unit/test_configuration.py::test_local_cli_onboarding_selects_ncc_dev_and_formal_deploy_selects_ncc_pro` `PASSED`（[d01-d02-a03-a04-unit.log](d01-d02-a03-a04-unit.log)）。 |
| **D03 · P1** | 总览复用 `redact_with_definitions` 字段级投影，无 `secret` 权限协作者在总览与 `/entities/{id}` 脱敏一致 | **已修 · 已验证** | `src/ncc_data/api/routes/studio.py`、`src/ncc_data/application/knowledge/queries.py` | `test_d03_d05_a07_a09_a11_...` `PASSED`（[r01-r04-r10-backend.log](r01-r04-r10-backend.log)）：自定义 `chapter` 定义将 `beat_outline`、`hook` 标为 `secret=True`，作者总览可见原文，只读协作者总览返回空串且 `/entities/{id}` 不含两私有键，公开字段 `pov="沈砚"` 一致保留。 |
| **D04 · P1** | 跨范围参考仅存引用版本与摘要；无来源权限协作者与来源撤权后续跑均裁剪原文 | **已修 · 已验证** | `src/ncc_data/creation/worker.py`、`src/ncc_data/application/service.py` | `test_d04_a01_a02_a06_a10_...` `PASSED`（[r01-r04-r10-backend.log](r01-r04-r10-backend.log)）：数据库 `packet.sources` 不落盘跨范围 `text`（保留 `revision` 与 `content_hash`）；无来源库权限的目标库管理员读取任务见 `redacted=True`；来源库撤权后作者读取见 `redacted=True`，且续跑 `write` 模型包实测不含已撤权原文。 |
| **D05 · P2** | 相同调序请求重放幂等返回同一回执与单一新版本；过期不同调序返回 `409` | **已修 · 已验证** | `src/ncc_data/api/routes/studio.py` | `test_d03_d05_a07_a09_a11_...` `PASSED`（[r01-r04-r10-backend.log](r01-r04-r10-backend.log)）：原样重试 `POST /studio/reorder` 两次均返 `200` 且回执全等、仅产生 `cur_ver + 1` 一个版本；用旧 `base_version` 提交不同顺序返回 `409`。 |
| **A01 · P1** | UI/API 全部显式工序组合逐步执行，不合法组合创建前明确拒绝 | **已修 · 已验证** | `src/ncc_data/creation/worker.py` | 单元：`tests/unit/test_studio_pipeline.py`（[d01-d02-a03-a04-unit.log](d01-d02-a03-a04-unit.log)）；PostgreSQL 集成：`test_d04_a01_a02_a06_a10_...`（[r01-r04-r10-backend.log](r01-r04-r10-backend.log)）实测 `["plan","revise"]` 与 `["judge_plan","revise","judge"]` 逐步完整执行。 |
| **A02 · P1** | 显式与默认工序均执行双评与 P5 修订复评；缺 P5 报告阻止采用；拒绝显式工序与托管授权同传 | **已修 · 已验证** | `src/ncc_data/creation/worker.py` | `test_d04_a01_a02_a06_a10_...` `PASSED`（[r01-r04-r10-backend.log](r01-r04-r10-backend.log)）：并传 `delegation_id` + `stages` 抛 `DomainError("显式拆分工序")`；P5 `["judge_plan","revise","judge"]` 候选同时具备 `evaluation`、`second_evaluation`、`revision_evaluation` 全部 `qualified`；篡改移除 `revision_assessment_id` 后 `accept_task` 抛 `DomainError("P5")` 拦截采用，恢复后正常采用。 |
| **A03 · P2** | 模型默认凭据遵循已解析配置优先级，自定义 `auth_ref` 按约定生效且不泄露密钥 | **已修 · 已验证** | `src/ncc_data/creation/model_route.py` | `tests/unit/test_model_route.py::test_describe_and_materialize_honor_config_precedence_and_hide_credentials` 等 7 项 `PASSED`（[d01-d02-a03-a04-unit.log](d01-d02-a03-a04-unit.log)）。 |
| **A04 · P2** | 订阅通道区分已安装、状态文件、已证实授权与空输出失败 | **已修 · 已验证** | `src/ncc_data/creation/subscription_auth.py` | `tests/unit/test_subscription_auth.py` 5 项（含 `test_verify_does_not_return_cli_output_and_rejects_empty_success`、`test_expired_grok_login_is_not_treated_as_an_api_key`）全部 `PASSED`（[d01-d02-a03-a04-unit.log](d01-d02-a03-a04-unit.log)）。 |
| **A05 · P1** | **专项核对（最终业务断言）**：CLI↔Studio 双向工作副本深度打通 | **已修 · 已验证** | `src/ncc_data/application/knowledge/workspace.py`、`tests/backend/test_studio.py` | `test_a05_a08_...` `PASSED`（[r01-r04-r10-backend.log](r01-r04-r10-backend.log)）：① CLI `ncc_state.py init` + `promise add`（`FS-0001` 含秘密真义）+ `chapter add` + 场景卡 → `workspace_commit`（`typed_chapters=1, typed_foreshadows=1` 且返回明确 `bidirectional` 边界声明）；② Studio 总览读出第 1 章 `beat_outline` 与 `FS-0001`，秘密真义隔离在 `data.secret_note` 不入公开 `text`；③ Studio 新建无 `legacy_path` 的第 2 章 `studio_ch2_id`（`芦苇暗箭`）及新伏笔 → `workspace_snapshot` 导出 `04-正文/第0002章.md` 与 `02-大纲/章纲/ch-0002.md`；④ CLI `status` 与 `promise list` 正常识别双章双伏笔，CLI 续写第 2 章再 `workspace_commit` **精确更新原 `studio_ch2_id`**（保留身份、章名与新正文），旧 `base_version` 触发 `DomainError("三方比较")` 冲突保护。 |
| **A06 · P1** | 双卷各四章验证全书章序、排除当前章、跨卷取前 3 章上下文及仅全书前 3 章受开篇保护 | **已修 · 已验证** | `src/ncc_data/creation/worker.py`、`src/ncc_data/domain/studio_catalog.py` | `test_d04_a01_a02_a06_a10_...` `PASSED`（[r01-r04-r10-backend.log](r01-r04-r10-backend.log)）：第一卷首章（`position=0, book_order=1`）前文为 `[]` 且托管自动采用被 `auto_hold.code == "key_chapter"` 拦截；第二卷首章（卷内 `position=0`、全书 `book_order=5`）上下文精确取 `["第一卷第2章","第一卷第3章","第一卷第4章"]`（跨卷且不含自身与后文），托管自动采用进入 `applied`。 |
| **A07 · P2** | **专项核对（>1000 混合对象）**：超过 1000 个混合对象下完整统计、权限先于截断、分页可对账 | **已修 · 已验证** | `src/ncc_data/api/routes/studio.py`、`tests/backend/test_studio.py` | `test_d03_d05_a07_a09_a11_...` `PASSED`（[r01-r04-r10-backend.log](r01-r04-r10-backend.log)）：单书写入 **1060 个混合对象**（2 章含 `secret` 字段章节 + 8 条不同状态暗线伏笔 + 1050 条 `魔兽`/`丹药` 设定），并 `retire` 停用 2 条构造混合已删对象；实测有效对象总数 **`total_entities == 1058`**（`魔兽 == 524`、`丹药 == 524` + 10 结构对象 = 1058 精确对账），默认全量 `truncated=False`，显式 `?limit=3` 返回 `truncated=True, returned_structural=3`，且 `codex_counts` 与全书 `diagnostics` 与未截断结果 100% 一致。 |
| **A08 · P2** | **专项核对（最终业务断言）**：两个并发事务同时写系统 `Scope.config` 不同分区不互相覆盖 | **已修 · 已验证** | `src/ncc_data/application/model_settings.py`、`src/ncc_data/application/subscription_settings.py`、`tests/backend/test_studio.py` | `test_a05_a08_...` `PASSED`（[r01-r04-r10-backend.log](r01-r04-r10-backend.log)）：通过 `SELECT ... FOR UPDATE` + `populate_existing=True` 锁行合并；`asyncio.gather(tx_save_model(), tx_save_subscription())` 并发执行后实测 `len(model_registry.configurations) == 1`、`defaults["write"] != ""` 且 `subscription_auth["grok"]["model"] == "grok-imagine-image-2.0"` 两份更改同时完整保留。 |
| **A09 · P2** | **专项核对（六条已埋未收暗线与预警）**：超期/临期已埋暗线不从五条上限消失，已兑现/作废另计 | **已修 · 已验证** | `src/ncc_data/domain/studio_catalog.py`、`src/ncc_data/api/routes/studio.py`、`tests/backend/test_studio.py` | `test_d03_d05_a07_a09_a11_...` `PASSED`（[r01-r04-r10-backend.log](r01-r04-r10-backend.log)）：构造 6 条已埋未收暗线（2 条超期 `expected=1`、2 条临期 `expected=2,3`、2 条在途 `expected=9,10`）+ 1 条 `已兑现` + 1 条 `作废`；实测返回 **`active_hidden_lines == 6`**、**`hidden_line_cap_exceeded == True`**（五条上限预警触发）、`overdue_foreshadow_count == 2`、`due_soon_foreshadow_count == 2`、`planted_overdue_foreshadow_count == 2`、`planted_due_soon_foreshadow_count == 2`、`resolved_hidden_lines == 1`、`dropped_hidden_lines == 1`。 |
| **A10 · P1** | 无目标单推章节细纲采用后新建章节细纲落 `beat_outline`、正文保持空、不落计划事实；大纲实体路径保留 | **已修 · 已验证** | `src/ncc_data/creation/worker.py`、`tests/backend/test_studio.py` | `test_d04_a01_a02_a06_a10_...` `PASSED`（[r01-r04-r10-backend.log](r01-r04-r10-backend.log)）：无 `entity_id` 的 `chapter` `stages=["plan"]` 采用后新章 `text == ""`、`"铁牌现世" in data["beat_outline"]`、事实表 `category="fact"` 为 `0`；同流程创建 `kind="outline"` 则同时保留 `text` 与 `data["beat_outline"]`。 |
| **A11 · P2** | 前后端章节字数统计统一为汉字口径并保留非空白字符指标可核对 | **已修 · 已验证** | `src/ncc_data/domain/studio_catalog.py`、`src/ncc_data/api/routes/studio.py` | `"甲，A1。"` 实测 `char_count == 1`（`test_d03_...`），`"二〇二六。"` 实测 `char_count == 4`、`non_whitespace_chars == 5`、`char_metric == "han"`（`test_r01_r02_r03_...`，见 [r01-r04-r10-backend.log](r01-r04-r10-backend.log)）。 |

---

## 三、R03 前后对账、重登失败与脱敏证据摘要

完整原始执行输出与 JSON 对账存档见 [r01-r04-r10-backend.log](r01-r04-r10-backend.log) 与 [d01-d02-a03-a04-unit.log](d01-d02-a03-a04-unit.log)，核心脱敏对账数据如下：

```json
{
  "timestamp": "2026-11-24T09:34:02+08:00",
  "database": "ncc-dev",
  "pytest_exit_code": 0,
  "pre_existing_scopes": {
    "count_before": 75,
    "count_after": 75,
    "digest_before": "5c1ef900742813b0",
    "digest_after": "5c1ef900742813b0",
    "preserved": true
  },
  "pre_existing_revisions": {
    "count_before": 5593,
    "count_after": 5593,
    "digest_before": "528ad1586ea03c96",
    "digest_after": "528ad1586ea03c96",
    "preserved": true
  },
  "pre_existing_users": {
    "count": 91,
    "unchanged": true,
    "legacy_browser_author_untouched": true
  },
  "ephemeral_users_created_this_run": {
    "count": 13,
    "sample_masked": [
      "browser-author-EWl7***",
      "test-other-gBvm***",
      "test-author-yuoy***",
      "browser-author-mF3Q***",
      "test-other-wXlE***",
      "test-ordinary-4wsz***"
    ],
    "remaining_active_count": 0,
    "remaining_unrevoked_sessions": 0,
    "remaining_unrevoked_delegations": 0,
    "remaining_open_jobs": 0
  },
  "r03_live_relogin_probe": {
    "ephemeral_admin": "browser-author-mF3Q***",
    "ephemeral_sub_author": "studio-author-iBS0***",
    "admin_login_during_status": 200,
    "sub_user_create_status": 201,
    "sub_login_during_status": 200,
    "session_access_after_teardown_status": 401,
    "admin_relogin_after_teardown_status": 401,
    "sub_relogin_after_teardown_status": 401
  }
}
```

---

## 四、浏览器夹具调用约定（已与 `ttys005` 对齐生效）

- `tests/support/runtime.py` 已彻底移除固定账号 `USERNAME = "browser-author"` 与固定口令 `PASSWORD = "synthetic-browser-password"`，不重新启用库内现存同名账号。
- `@browser_test` 传入的 `runtime` 实例提供：
  - 本次运行隔离管理员：`runtime.username`（`browser-author-<token>`）与 `runtime.password`（24 字节随机口令）。
  - 子账号凭据生成器：`runtime.new_credentials(prefix="studio-author")`。
  - 退出 `with TestRuntime(..., server=True)` 时自动执行 `teardown_browser()`，停用本次新建临时账号、轮换密码哈希、吊销全部会话与托管授权并取消未完成任务。
- 经核对 [agy-frontend.md](agy-frontend.md)，`ttys005` 已完成 `tests/browser/*.py` 全部 5 个浏览器脚本向该约定的迁移。
