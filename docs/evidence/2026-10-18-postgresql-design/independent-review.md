# v4 数据服务与后台独立代码评审

日期：2026-10-19。评审者：独立评审会话 `/root/upgrade_review`。输入为[实施计划](../../designs/storage/implementation.md)、工程 D5 要求及当前工作树候选；不是实现者自查。评审期间产品仍在修改，以下修复均经实现会话处理，本会话仅编写此报告及仓外合成探针。最终已读产品字节见文末 SHA-256，任务级候选指纹由交付记录绑定。

## 结论与覆盖

针对本次检查路径，发现的 12 类问题均已修复复核，没有遗留的已复现 P1/P2 阻断项。这是限定范围的代码评审与反例验证，不能解释为全仓、真实模型效果或五端验收通过。

完整阅读了权限模块、变更服务、管理服务、自动化主要编排、数据交换、维护、工作副本、校准、评分核、模型、字段校验和 Provider 实现；抽查了 API 相关端点、查询与历史方法、CLI 备份/恢复及数据库桥接路径、前端会话与请求封装、创作台和资料编辑器。大型文件按上述路径检查，未声称逐行评审全部前端或全部旧工作流。读取的测试文件用于核对覆盖和构造合成反例。

实际数据检查仅使用显式命名的临时数据库 `ncc_test_review`，位于本轮临时 PostgreSQL 实例。该库独立于实现会话的测试库；探针只创建合成用户、范围、章节、关系和附件。没有读取真实小说或真实业务数据库，没有进行提交、推送或发布。

## 发现、复现与修复复核

P1 表示会造成越权、数据错误、质量硬闸绕过或主流程无法按约定完成；P2 表示特定恢复路径失效。下列行号用于定位当前修复路径，旧行为由复现描述和观察记录说明。

| 编号 | 级别 | 缺陷与复现条件 | 修复及独立复核 |
|---|---|---|---|
| R01 | P1 | 成员曾有秘密权限并创建秘密变更，撤销秘密权限后，普通对象读取拒绝，但本人 `/changes` 仍返回秘密原文。 | `changes.py:16`、`service.py:142` 以持久保密标记重新校验。相同合成探针不再返回原文。 |
| R02 | P1 | 秘密导出附件仅校验范围与 export；撤销秘密权限后仍可凭此前获得的附件 ID 下载完整内容。 | `exchange.py:20`、`:41` 及附件迁移保存保密标记，每次下载重新授权。原探针现返回 not_found。 |
| R03 | P1 | 正常导入每完成一批重新 queued，也累加全任务 attempts；超过三批后一直 queued，余下批次无法执行。 | `automation.py:393` 成功正常续批重置失败尝试计数。四批合成持久任务完成 succeeded；最终回归亦通过。 |
| R04 | P1 | 章节上下文只查前 100 章；已有 101 章时新章位置仍取 101，默认上下文也取错章节。 | `automation.py:422` 分别按位置查询邻近前章和最大章位。101 章探针获得 next_position=102，来源为 99/100/101 章。 |
| R05 | P1 | 模型返回无效正文时，用量在失败事务中回滚；预算 1000、三次各 600 token 的合成响应，实际调用 1800 而记录 0。 | `automation.py:358`、`:383`、调用后计账路径保留用量，调用前检查剩余预算。修复后记录 600、1200，第三次不再调用；Provider 实际消耗超过请求剩余额度的合成情况被计入总额并暂停。 |
| R06 | P1 | CLI 只改 book.json 的状态、标题或章序时未更新 typed chapter，随后快照用旧状态覆盖；删除正文后 typed chapter 又重建该文件。 | `workspace.py:165` 对元数据变化统一投影，删除或移出元数据时停用对应章节。仅元数据更新后 status/title 正确；删除后快照不再返回正文。 |
| R07 | P1 | 成员知晓秘密事实 ID，撤销 secret 后仍可通过 retract 撤回该事实；supersedes 同类缺少原事实权限检查。 | `changes.py:500`、`:579` 校验原事实秘密权限。撤权后撤回预检拒绝，所有者仍查询到原事实；supersedes 检查路径作代码复核。 |
| R08 | P1 | v3 存在物品归属关系，v4 停用物品后查询相同 as_of=v3 的关系从 1 条变 0 条；对象端错误使用当前状态。 | `queries.py:386`、`:456` 将引用对象解析绑定同一历史版本。相同探针停用前后历史关系均为 1 条。 |
| R09 | P1 | 主评 qualified；次评同分且 raw hard=pass，但含 major observation，确定性结果 blocked；disagreement 原返回 False，次评硬伤会被主评结果覆盖。 | `scoring.py:15` 任一 blocked/incomplete 先判分歧，采用端另查附加评价硬闸。纯函数同分探针现为 qualified/blocked/disputed=True；采用端作代码复核，没有用真实模型验证识别能力。 |
| R10 | P1 | EntityDrawer 保留脏表单，但 React Query 刷新 entity.data 后保存使用新版本 expected，可能覆盖另一窗口已提交的修改。 | `materials.tsx:253`、`:277`、`:298` 冻结 editingBaseline，刷新不替换脏编辑的 expected。该修复完成代码复核；本独立会话未运行双窗口浏览器反例。 |
| R11 | P2 | 删除后再次新增相同路径时尝试创建已有身份；后续恢复相同正文的 early-return 又漏恢复 typed chapter。 | `workspace.py:126`、`:186`、`:206` 保留稳定身份并显式 reactivate，跳过相同内容前检查未停用。相同正文恢复探针中原件与 chapter 投影均恢复。 |
| R12 | P1 | 从未获 secret 的 edit 成员可对公共对象发送 unset:[秘密字段键]，先删除字段再校验剩余属性，从而删除不可见值。 | `changes.py:440` 删除前检查字段秘密权限。探针现被 secret_field 拒绝，所有者原值仍在；定义升级、历史恢复和定义发布的完整权限检查另作代码核对。 |

还核对了两个相邻修复：评分任务使用 assess 授权，生成另需 edit；旧版本分支配置通过 configuration_at 回放定义与采用记录。此次没有为这两条另做独立端到端探针，相关结果不能扩大表述。

## 追加定向复核：撤权与会话重连

后续追加仅覆盖权限变化通知、当前范围缓存/本地表单清理及撤销 read 后的范围列表。原实现仅在既有 SSE 连接观察到动作变化时发通知，断线期间撤权后重新连接可能缺少变化通知；新连接若在初始授权阶段即被拒绝，也不会进入流内 access_revoked 分支。本会话指出了这两个代码边界。

最新修复在 SSE 首帧及权限变化时发送动作集合；主页面比较动作指纹、直接监听 scope.actions 变化，清理该范围查询缓存并重新挂载页面；连接错误后重新核对范围权限，只在 401/403/404 时按撤权清理，网络失败不直接当作撤权。上述路径已定向代码复核，没有把代码检查表述为真实浏览器重连验证。

范围列表跳过已撤销 read 的成员范围，避免单个不可访问范围使整个列表失败。新增 `test_revoked_membership_does_not_break_or_expose_scope_list` 在独立测试库运行：退出码 0，1 passed、7 deselected。最终独立数据服务回归为 **32 passed in 10.25s**，退出码 0；此前 31 项结果保留为原轮次记录。

相邻边界仅抽查：GET delegations 限本人记录，校准读取需 admin+secret，历史秘密属性筛选按对象绑定的 definition_id 排除计数探测，偏好按钮调用既有 feedback 接口。新增 TrustControls 仅核对这些请求及权限接线，未完整评审新表单或执行其浏览器操作。完整阅读了 `tests/data/run_recovery.py` 的临时库限制、行摘要对账与恢复后凭据/任务校验；本会话未执行该恢复脚本，不复用实现会话的恢复结果为独立执行证据。

当前已读文件的 Python 语法检查通过。相邻文件的格式整理按更新后字节刷新文末摘要，未因此扩大原检查范围或原 12 类问题的复核结论。

## 实际检查记录

- 原轮最终命令：`.venv/bin/pytest tests/data --database-url '<显式 ncc_test_review 临时连接>' -q`。退出码 0，**31 passed in 9.76s**。早一轮独立运行是 29 passed in 9.05s，不以旧结果替代最终结果。
- 仓外探针：`/private/tmp/ncc-independent-review.py`、`ncc-review-workspace.py`、`ncc-review-history.py`、`ncc-review-secret-facts.py`、`ncc-review-secret-unset.py`。分别覆盖撤权读回、预算、正常分批、长篇上下文、CLI 元数据/删除/恢复、历史关系与秘密写权限。路径用于说明本机检查过程，不作为必须安装的项目依赖。
- 次评价严重问题由 `evaluate` 与 `disagreement` 的独立纯函数探针复现和复核。生成 Provider 均为明确的合成测试替身，未将其评分当成真实模型或读者效果证据。
- 报告没有重复实现会话的备份恢复、浏览器和插件测试，也没有把他方报告当成本独立会话执行结果。

## 未验边界

没有逐行审查整个仓库、全部旧 CLI、全部 UI 路由或迁移 DDL；没有运行生产部署、真实数据迁移、真实模型调用、作者偏好/评分校准、长时间负载、五端新会话加载或独立浏览器双窗口操作。完整导入超过 1500 条的公共 API 负载未在本会话重跑；R03 使用四个真实持久批次复核调度逻辑。正式发布仍应以任务要求的其他证据和作者确认判定，本报告不授予发布权限。

## 已读文件摘要

摘要绑定此报告生成时的文件字节；后续改动须重核相邻评审路径并更新摘要。完整阅读与按路径抽查的区别以上述覆盖说明为准，摘要本身不证明全文件语义通过。

| 文件 | SHA-256 |
|---|---|
| `docs/designs/storage/implementation.md` | `8709debecf3117bd988d5517fd58913eae2d9b5c2a08634a8f738a8c7347f28f` |
| `src/ncc_data/security.py` | `2383543210b188613c52f6b072e6ccb76f84a3d29f03cbe6d4fd5d7afb84ef5b` |
| `src/ncc_data/api.py` | `c2180be45f4f216257d6e18b339d087f0a0c6f09ac503540d5b921098f993894` |
| `src/ncc_data/queries.py` | `d85905a742f761e260c6c1bfe60ea58d427f638a99dfc9abb4837a704f07b804` |
| `src/ncc_data/changes.py` | `75870682a50c7e21c09ef8804542c4c40c0e971b0ab13afe7222452dc7ab80ed` |
| `src/ncc_data/service.py` | `35f24fe29bfc00f5adf6cee50a4105c8df2df35dadacd8fabbd808ae03ee600a` |
| `src/ncc_data/automation.py` | `ff5b780cc263152cf907200e556c0419aa4b9c53d2750f4ae221da009ae92f70` |
| `src/ncc_data/exchange.py` | `a035f353645a31fbd4eed1195d6f66ad321afffa677d1aa98d11b0e61c516364` |
| `src/ncc_data/maintenance.py` | `7673d66caadd81acaa44bda04fafa44d9837e4ca98beab60003f71a5583a4faf` |
| `src/ncc_data/workspace.py` | `cdf0edbdca80211e72ccba4d7a3f42b4cd2bdd705897f7960382f7901961f541` |
| `src/ncc_data/calibration.py` | `a20f8d6523ef5b684f3a16fac6f6871952abe02b5861c0987df0d51ca1f3fe54` |
| `src/ncc_data/scoring.py` | `4d73c3b91ef1e8d748463236d8f61e45dddcc5304114b38618480d0b8076f0de` |
| `src/ncc_data/quality_core.py` | `2d97a55c3e24bfaa51d3bfce78d9c931b6a1385088ac33f6e72bf0059734a07d` |
| `src/ncc_data/models.py` | `8235ef8f9a5fa025fa7a90445a3539edd3acb07d6b21c5f7af678828fbd315f8` |
| `src/ncc_data/validation.py` | `d5400481641c0edad12d9c585cee984d900f0abc052209f42ddc61b6832ef7bf` |
| `src/ncc_data/provider.py` | `c8693d317ffa38c66c6751f13fb63183c876164016670b6f02564935b0519618` |
| `src/ncc_data/contracts.py` | `10f8fedc7024ea6175f8585a938afb43c41d3f97f7ed8edfc62973aad8ef1b3f` |
| `src/ncc_data/db.py` | `e32af53f5952b49c1b4ff2e26540dd0c0a370ba699fb4a81706559e0a0dc95bd` |
| `src/ncc_data/cli.py` | `9a763088e51f06848efeb79cbd7d5e5135c1c6a106cf6be9e3eefaf92a591066` |
| `src/ncc_data/workspace_client.py` | `1447d870bb91bbd7ab95b65f4d99ced99028a58601bdfb6b2e3f528e6352f535` |
| `scripts/ncclib/database_bridge.py` | `cdd406a774eabbf328ea6e76e3da910750498b3a064933c684b5df18f13be700` |
| `apps/management-web/src/api.ts` | `7fbabbf22f84e8625e68ba28a84f5624488889677fc1c0f443712bee61c0b230` |
| `apps/management-web/src/main.tsx` | `74ab470f16db561e57bba04cb899315415d9b699a35fb389be56b15b6f289cdd` |
| `apps/management-web/src/creative.tsx` | `06ce190544443621c19576456346433a3566d45515c02a0c9b3bdfb3554e1d04` |
| `apps/management-web/src/materials.tsx` | `6a09e6537b2f1f5ff3b55a094d5edee98a31f6aaf84bef227103382e62ffddac` |
| `tests/data/conftest.py` | `5e5cb8876541d24da5e0c2b60f47668d320a5b9553a14d632e21805e7db13c3d` |
| `tests/data/test_core.py` | `ed8b21531f4cba5b43ecde9467b2eaa791ee946203578018ef8f4017d68c5a34` |
| `tests/data/test_scoring.py` | `e4bf7a0c2c5d26cc2b65fa3af67f9db6db3095d550120363dcd857cfad0d7686` |
| `tests/data/test_api_automation.py` | `14dcf13459a74ae43aa79e92f9ba2c922fcb781cf5a917f074e8451be8d0d53c` |
| `tests/data/test_exchange_maintenance.py` | `8cef1056fdf5160a78f4d030e4eec05ffb23f78e1ec4d2180c20fbd274ffc996` |
| `tests/data/test_review_regressions.py` | `210fdaa0e19c35dd64ffd7c773c16cc6937d9116573af805f5ac55c05f5edd85` |
| `tests/data/run_recovery.py` | `4ad246e7ae263f8560f6cf269a2454b9847d2561ac8acbd57199a4580f8f80cd` |
| `apps/management-web/src/trust.tsx` | `c9483f92bcc2b0e9b4026e6f270e68da05209ee6e9c36b3ec4504eeeff2603f5` |
| `apps/management-web/src/management.tsx` | `a0108621cae0e6fc1b59d332ec32700a29566d6f29a1a37c02d28146887d121d` |
| `tests/data/test_automation_boundaries.py` | `8a42ecd836f2dd6b690d15f1dd639f9d3939b959495806b08d7d66f32c4e3caa` |

## 最后定向补充：新空间切换与私人草稿清理

本轮仅复核最后追加的数据编辑路径。主页面创建空间后先将 POST 返回加入范围缓存；显式 scopeId 尚未匹配时不回退到旧空间。旧 SSE 的权限回调和异步权限核对忽略非当前范围，避免旧事件修改当前页面的本地状态。

创作台正式保存前等待已排队的私人草稿操作，保存期间暂停自动草稿队列并限制标题和正文输入；保存成功后按草稿版本清理本人的私人草稿。DELETE 接口经过会话/CSRF及范围编辑授权；服务端按本人、author-draft 类型和 key 查找，重新校验秘密访问权限，持有范围锁并比较版本。旧版本清理拒绝，新版本草稿保留供比较。EntityDrawer 的保存状态也用于禁用表单和正文编辑器。以上新增前端接线为定向代码复核，没有借此扩展整套 UI 或浏览器验收结论。

独立运行 `test_automation_boundaries.py -k human_autosave`：1 passed、5 deselected，退出码 0，覆盖草稿清理 CAS、旧版本不清理及人工接管围栏。首次误用筛选 `-k author_intervention` 未匹配用例，6 deselected、退出码 5；纠正后才得到上述有效结果。未重做原 12 类检查，也未把实现会话正在进行的最终浏览器操作当成本会话执行结果。原全量独立结果仍为前轮 32 passed；此补充只新增一个受影响用例检查。

## 末次定向补充：私人草稿加载竞态

本次仅检查共享工作树实际存在的 `apps/management-web/src/creative.tsx`；派单中提及的 `src/pages/creative.tsx` 在本工作树不存在，未另造路径或修改产品代码。

`draftLoaded` 以 React state 表示异步私人草稿读取完成，并进入自动保存 effect 的依赖；读取完成后会重新判断脏编辑和预算中的 busy 状态，不再依赖 ref 变化触发渲染。`editGeneration` 在正文或名称输入时递增，晚到的草稿恢复仅在尚无输入时回填；切换对象时仍通过 live 围栏排除旧请求。这次定向代码复核未发现该增量的新阻断项。

此补充只刷新上述文件摘要，未重做原 12 类问题或其他产品路径的验证。没有将实现会话的前端构建及正在进行的真实浏览器结果表述为本独立会话执行的检查；异步实际交互效果仍以对应浏览器证据为准。

## 本轮授权增量：限额自动定稿试运行

作者本轮原话要求启用自动定稿并提交推送。实现会话已说明默认试运行方案并异步询问选项；本评审时尚无选项回复、真实 NCC 目标数据库/模型配置或真实校准样本。此次审查的是代码中的限额 `author_trial` 能力与 `calibrated` 模式分隔，不能写成作者已经提供校准、已经选择该默认方式或已在真实实例激活。本独立会话没有创建真实作品授权，没有执行提交推送。

定向检查包括 checked_delegation、任务创建与采用、授权服务及 API、契约/模型、新迁移 7e419c2d608b、创作台授权选择的实际 payload、授权表单，以及 test_auto_adoption.py。作者试运行只能由作品所有者创建，必须保留授权依据，并绑定对象、方案、期限、剩余次数与策略 hash；采用时再次校验，次数消耗与正文修订和审计在同一事务内。试运行采用结果明确记为 calibration=unverified，没有伪造 Calibration 记录。校准模式仍检查主评、二评和修订评价对应的有效校准。

| 增量发现 | 实际反例 | 修复与独立复核 |
|---|---|---|
| A01 · P2：P5 目标方案不一致 | 人物资料持 P3+P5 授权，创建 P5 修订仍被要求无关 P1，返回 delegation；Worker 默认又按 P3 评价。 | 新增 creation_scheme 统一按目标 kind 解析，任务采用目标实际类型；前端按相同内容方案筛选授权并发送 content_scheme。相同独立探针现可创建；新增永久用例验证实际自动采用。 |
| A02 · P2：旧授权缺少策略绑定 | 模拟迁移遗留 authorization={} 的校准授权，checked_delegation 用当前策略兜底而接受，旧授权没有真正冻结 hash。 | 缺少 hash 明确返回 delegation_policy，要求续授权；新迁移默认空记录不会被当作已绑定授权。相同独立探针现被拒绝，新增永久用例验证旧记录等待续授权。 |

独立数据库测试命令为 `pytest tests/data/test_auto_adoption.py --database-url '<ncc_test_review 临时连接>' -q`，修复后 **10 passed in 2.51s**、退出码 0；首轮修复前原有 8 项也曾通过，不能替代新增边界测试。覆盖一次采用与幂等不重复扣次、校准模式缺样本仍等待、授权撤销/过期/策略变化、开篇阻断、二评未达标阻断、所有者/授权依据，以及上述 P5 与旧授权修复。最小独立探针为 `/private/tmp/ncc-review-auto-adoption.py`，仅使用合成数据库。测试中的 Provider 与授权依据均明确为合成材料。

85 分与维度/证据/严重硬伤判定沿用既有确定性评分核；本轮代码检查确认自动采用要求 qualified，二评与 P5 附加评价另有质量闸门，开篇前三章和关键章仍保留作者选择。没有以这些合成结果声称真实模型质量、人工偏好或校准准确率。前端仅检查表单请求、授权筛选与 payload 接线，没有独立运行本轮浏览器授权流程；全量数据服务的此前 32 项独立结果与本轮 10 项分开记录，不拼接为未执行的全量结果。使用说明须同步区分“未校准试运行”和“已校准策略”，真实实例配置与作者选项仍属于实际启用边界。

本轮新增已读文件摘要如下；其余已读产品摘要已按上述定向检查刷新。本轮发现的 A01/A02 均已修复复核，未保留已复现阻断项。

| 文件 | SHA-256 |
|---|---|
| `alembic/versions/7e419c2d608b_author_trial_delegation.py` | `acb147a5b4de8bdda3c5a4729cdd8d2f0819723f52818b2952f3455e685dc769` |
| `tests/data/test_auto_adoption.py` | `7048412f243d2c71602131aa33b3a6e06645524c8fae3b9997c88d5f90811c77` |
