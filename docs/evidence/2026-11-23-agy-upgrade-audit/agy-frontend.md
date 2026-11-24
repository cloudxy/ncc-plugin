# AGY 前端与浏览器修复与复验交付回执（终端 ttys005）

- **终端号**：`ttys005`（前端与浏览器窗口）
- **会话标识**：`39261857-19f2-423d-9c5d-871cc26218f9`
- **审核接收方**：`ttys004`（新任质量负责人）
- **完成时间**：`2026-11-24T10:10+08:00`
- **交付状态**：**全部已完成并通过真实 Chromium + FastAPI + `ncc-dev` 合成作品正反例验收与全量浏览器回归（0 失败、0 阻塞、0 待验）**
- **归属边界与安全纪律声明**：
  - 仅修改 `ttys005` 归属的 `apps/management-web/**`、`tests/browser/**` 以及本回执与日志证据，未触碰后端、`tests/backend/**`、`tests/support/**`、创作 CLI 或评测工具。
  - 全程仅使用合成作品与一次性合成测试身份操作既定本地库 `ncc-dev`，**未执行任何清库（`TRUNCATE` / `reset`）**，未触碰线上库 `ncc-pro`、私人书稿（`novels/`、`books/`、`_作者/`、`_拆书库/`）或真实密钥，未执行 `rm`、`git commit`、`git push`。

> [!IMPORTANT]
> **致 `ttys000` 联调确认**：
> 1. 已消费 `READY_FOR_BROWSER`：普通非管理员作者在真实 Chromium 与 `ncc-dev` 打开总览（创作台、大纲与暗线、市场与风向）均返回 `200 OK`，无页面异常。
> 2. 已完成 `R03` 浏览器夹具迁移：`tests/browser/` 下全部 5 支脚本（`run_studio_browser.py`、`run_browser.py`、`run_access_browser.py`、`run_auto_adoption_browser.py`、`run_cli_bridge.py`）均已彻底移除静态固定账号口令，切换为 `runtime.username`、`runtime.password` 与 `runtime.new_credentials(...)`，收尾后实测新建临时账号活跃残留为 `0`。

---

## 一、负责事项逐项结论总表（R09、R11、U01–U03 及 R01/R02/R03 浏览器联调）

| 编号 | 缺陷与返工要求 | 状态 | 修改路径 | 定向检查命令与真实界面操作 | 实测结果与证据 |
|---|---|---|---|---|---|
| **R09 · 待办定位与返回** | 待办点击「到创作台查看」未传章节与任务、`jobCandidate.ts` 无 `entityId` 不选任务、同章多任务无法区分定位、失败任务跳任务中心未选中目标行、缺少返回路径 | **已修 · 已验证** | `apps/management-web/src/features/inbox/InboxPage.tsx`<br>`apps/management-web/src/features/jobs/JobsPage.tsx`<br>`apps/management-web/src/features/creation/jobCandidate.ts`<br>`apps/management-web/src/features/creation/components/ScoreCard.tsx`<br>`apps/management-web/src/features/creation/CreativePage.tsx`<br>`apps/management-web/src/shared/studioApi.ts` | `.venv/bin/python tests/browser/run_studio_browser.py`<br>真实 Chromium 在 `/inbox` 依次点击：① 甲章任务 → `/work`；② 乙章**同章任务一**（含 2 版候选，点「上一候选」切换）→ `/work`；③ 乙章**同章任务二** → `/work`；④ 无目标（`entity_id=null`）新章细纲任务 → `/work`；⑤ 非首行 `failed` 任务 → `/admin/jobs` → 再跳 `/work` → 「返回任务中心」→ 「返回我的待办」 | 每次点击均准确载入对应章节（无目标任务保持「新稿」态并选中该任务）、自动展开「质量把控」面板展示对应任务名称/目标/评分/候选摘录；乙章同章双任务互不串台且支持面板内「同章候选任务」直接切换；失败任务在 `/admin/jobs` 精确高亮第 5 行（`aria-current="true"`）而非首行，展示超时原因；各入口「返回我的待办 / 返回任务中心 / 返回大纲与暗线」一键往返通过。见 [r09-r11-u01-u03-browser.log](r09-r11-u01-u03-browser.log) |
| **R11 · 草稿会话归属** | `BlueprintPage.tsx` 原模块级明文草稿 `Map` 键仅含范围/对象，未绑定登录会话，注销仅清查询缓存 | **已修 · 已验证** | `apps/management-web/src/shared/studioApi.ts`<br>`apps/management-web/src/shared/WorkspaceContext.tsx`<br>`apps/management-web/src/app/Shell.tsx`<br>`apps/management-web/src/features/blueprint/BlueprintPage.tsx` | 前端纯逻辑校验 + `.venv/bin/python tests/browser/run_studio_browser.py`<br>真实 Chromium **同一标签页（同一 JS 内存堆）**验证三组反例：① 协作者编辑蓝图草稿后被所有者撤去 `edit` 权限（SSE `permissions` 触发）；② 协作者重新编辑未保存草稿后点「退出」，换作者账号登录打开蓝图；③ 同账号编辑未保存草稿后点「退出」再以**同一账号**重登新会话打开蓝图 | 内存草稿与跨页 handoff 均强绑定 `sessionOwner`（`userId:csrf:loginEpoch`）与范围 `actionsStamp`（绝不写 `localStorage`）；权限撤回、会话过期（`ncc-auth-expired`）、跨账号注销重登及同账号注销重登后，旧会话未保存草稿 **100% 立即销毁**，页面与内存零残留。见 [r09-r11-u01-u03-browser.log](r09-r11-u01-u03-browser.log) |
| **U01 · P1 · 创作台全字段自动草稿** | 自动草稿忽略细纲/钩子/视角/剧情线/目标字数/关键章，修改 `scheme` 未标脏导致仍有未保存字段时显示保存成功；需验证只改元数据、只清空正文、同改在刷新/离开后恢复同一章同一基线 | **已修 · 已验证** | `apps/management-web/src/features/creation/CreativePage.tsx`<br>`apps/management-web/src/features/creation/components/StudioCockpit.tsx` | `.venv/bin/python tests/browser/run_studio_browser.py`<br>真实 Chromium 实测三组路径并向服务端读回 `/author-drafts/{id}`：① **只改元数据**（细纲、钩子、POV、剧情线、目标字数、关键章、评分方案切 `P5`）；② **只清空正文**保留元数据；③ **正文与元数据同改**；分别执行 `page.reload()` 刷新及切去「作品资料」再返回 | ① 改 `scheme` 立即进入「未保存修改 · 自动保存尚未成功」，未落盘前绝不显示全部成功；② 修正首次未触发自动草稿即点「保存修订」时 `DELETE /author-drafts` 返回无 `version` 导致后续自动草稿误增版本号报 409 的隐患，并在 `phase !== "idle"` 期间锁定把控栏输入防并发冲掉；③ 三组路径刷新与离开重进后均精确恢复**同一章、同一 `baseline` 版本及全部 8 项字段**。见 [r09-r11-u01-u03-browser.log](r09-r11-u01-u03-browser.log) |
| **U02 · P1 · 新建章与换章草稿保护** | 编辑未保存时目录新建下一章绕开离开保护，导致丙章混入乙章草稿或保存写回乙章 | **已修 · 已验证** | `apps/management-web/src/features/creation/CreativePage.tsx` | `.venv/bin/python tests/browser/run_studio_browser.py`<br>真实 Chromium：在乙章保存正式版后输入未保存草稿 → 点「新建章节（丙章）」→ 先点「继续编辑」取消 → 再点「新建章节」并点「离开当前章节」→ 在丙章写入正文并保存 → 服务端读回 `/entities/{乙}`、`/author-drafts/{乙}`、`/entities/{丙}` | 新建章与换章共用 `confirmSwitchIfDirty` 拦截弹窗：取消时停留在乙章且不建丙章；确认离开时先将乙章未落盘草稿刷入乙章草稿键，丙章标题为「第三章 · 夜渡芦苇」、稿纸为空，保存后服务端读回核实：**乙章正式版未变、乙章草稿完整保留在乙章下、丙章正式版仅写入丙章**。见 [r09-r11-u01-u03-browser.log](r09-r11-u01-u03-browser.log) |
| **U03 · P1 · 蓝图离开保护与并发冲突双版本** | 蓝图卡片编辑切走无壳层保护，刷新/并发更新后可能静默覆盖他人更改；原正常入口曾受 R01 总览阻断 | **已修 · 已验证** | `apps/management-web/src/features/blueprint/BlueprintPage.tsx`<br>`apps/management-web/src/features/creation/CreativePage.tsx` | `.venv/bin/python tests/browser/run_studio_browser.py`<br>真实 Chromium 正常打开 `/blueprint`（HTTP 200）：① 编辑总纲后切换三切片往返；② 点侧栏「市场与风向」触发壳层拦截（先留后走再返回）；③ 他窗并发更新总纲后返回蓝图，核验双版本并点「基于新版保存我的草稿」；④ 细纲卡片墙在页并发更新后直接点「保存这张卡」（触发 409 保护），核验双版本并点「采用服务器最新版」；⑤ 创作台章节并发冲突双版本核验 | ① 切片切换与壳层离开后返回均保留本会话草稿及冻结的 `baseVersion`；② 并发更新时旧保存按钮禁用、直接保存亦被 `expected` 版本守卫拦截（服务端新版零被覆盖），冲突横幅同时展示**服务器最新版本**与**本地草稿**全文，两种恢复动作（「基于新版保存我的草稿」与「采用服务器最新版」）及创作台章节冲突恢复均实测通过。见 [r09-r11-u01-u03-browser.log](r09-r11-u01-u03-browser.log) |
| **R01 / R02 补充 / R03 · 前端口径消费与全套浏览器回归** | 普通作者正常进入总览；`"二〇二六"` 汉字口径前后一致、待埋设暗线提醒展示；浏览器夹具一次性凭据迁移与全套脚本无回归 | **已修 · 已验证** | `apps/management-web/src/shared/studioApi.ts`<br>`apps/management-web/src/features/market/MarketPage.tsx`<br>`tests/browser/run_studio_browser.py`<br>`tests/browser/run_browser.py`<br>`tests/browser/run_access_browser.py`<br>`tests/browser/run_auto_adoption_browser.py`<br>`tests/browser/run_cli_bridge.py` | 串行执行 `tests/browser/` 全部 5 支脚本 + 前后 `ncc-dev` 摘要与临时账号锁死核查 | ① 普通非管理员作者打开六大空间与四档视口（`1440/1280/768/390`）全部通过，`page_errors == []`；② `"二〇二六。"` 在编辑器页脚与 `/studio/overview` 均计 `汉字 4`；③ **5/5 浏览器回归脚本全部退出码 `0`**。见 [r09-r11-u01-u03-browser.log](r09-r11-u01-u03-browser.log) |

---

## 二、共用库 `ncc-dev` 前后无损对账与 R03 临时身份收尾证据（脱敏）

完整执行日志见 [r09-r11-u01-u03-browser.log](r09-r11-u01-u03-browser.log)，五支浏览器套件串行跑完前后的真实 `ncc-dev` 对账结果如下：

```json
{
  "database": "ncc-dev",
  "all_browser_suites_passed": true,
  "suite_count": 5,
  "suites_exit_codes": {
    "run_studio_browser": 0,
    "run_browser": 0,
    "run_access_browser": 0,
    "run_auto_adoption_browser": 0,
    "run_cli_bridge": 0
  },
  "pre_existing_integrity": {
    "scopes": {
      "count_before": 94,
      "count_after": 94,
      "digest_before": "f929de1003c1bfbf",
      "digest_after": "f929de1003c1bfbf",
      "preserved": true
    },
    "revisions": {
      "count_before": 6800,
      "count_after": 6800,
      "digest_before": "6b298026b9dabd0f",
      "digest_after": "6b298026b9dabd0f",
      "preserved": true
    },
    "users": {
      "count_before": 135,
      "count_after": 135,
      "digest_before": "738605a14439df21",
      "digest_after": "738605a14439df21",
      "preserved": true
    }
  },
  "r03_ephemeral_browser_accounts": {
    "created_count": 9,
    "sample_masked": [
      "studio-author-CNboiG***",
      "auto-fixture-MT7ZoL5***",
      "browser-author-PuIit***",
      "browser-author-tMKSA***",
      "studio-author-ZgnUiR***",
      "access-fixture-unW_g***",
      "browser-author-ueZb-***",
      "browser-author-rjyhP***"
    ],
    "remaining_active_count": 0,
    "remaining_unrevoked_sessions": 0,
    "remaining_unrevoked_delegations": 0,
    "remaining_open_jobs": 0
  }
}
```

---

## 三、构建与静态一致性验证汇总

- `npm --prefix apps/management-web run format:check` → `0`（All matched files use Prettier code style）
- `npm --prefix apps/management-web run build`（`tsc -b && vite build`）→ `0`（产物已同步构建至 `apps/management-web/dist`）
- `python3 scripts/dev/check_plugin.py -v` → `0`（`PLUGIN OK`）
- `python3 scripts/dev/build_registry.py --check` → `0`（`REGISTRY OK`）
- `python3 scripts/dev/build_docs.py --check` → `0`（`DOCS OK`）
- **仍失败 / 待验项**：**无（0 项）**，现正式提交 `ttys004` 质量负责人审核验收。
