# 配置、共享代码与接口拆分独立评审

日期：2026-10-19。评审会话：`/root/upgrade_review`。plugin_root/repo_root 均为 `/Users/xuyun/Documents/ncc-workflow`，分支 main，基线 `4b50690a696a4483dc1fb9f4c68d92b4e0db770f`。按 ncc-dev 的独立评审要求执行，输入为[本轮方案](../../designs/engineering/configuration-ownership.md)与冻结工作树。

本报告绑定候选 `19f5281e2c08dae8300800d76733f250491ec1e9805c1db8573d245555a6c9b1`，主代理登记的精确产品范围为190个路径。下述结论只适用于所列代码检查和无数据库验证：本轮报告的 C01–C12 已修复并完成相应独立复核，受检范围没有遗留已复现的 P1/P2 问题。真实 PostgreSQL 联调、完整 UI 行为和全局交付验收仍未完成；本报告不能证明全仓或运行环境通过。

已独立运行 `python3 scripts/dev/check_dev_workflow.py check docs/tasks/2026-10-19-configuration-ownership.md --repo /Users/xuyun/Documents/ncc-workflow`，退出码0，返回 RECORD OK 及上述同一候选指纹；当时尚未登记通过证据。该结果只核对记录、归属和指纹，不替代行为验收。

## 范围与限制

检查共享配置、连接派生、HTTP客户端、工作副本路径、运行 Settings、CLI/备份/迁移装配及单测试库执行器。对拆分后的63个 HTTP method/path 做基线 AST 等价比较，定向复核鉴权、来源/CSRF、profile 栅栏。定向查看前端共享评分策略、创作任务 payload、方案展示与导入方向；没有完整评审全部新前端模块。

没有新建、连接、重置、恢复或删除任何数据库，没有启动原临时集群，也没有读取或打印真实 `.env` 值。配置和路径反例仅操作自建的仓外临时合成文件。SQLAlchemy 只做驱动参数解析或替换为 Mock 的 engine 构造，ASGI 请求完全在内存运行；Mock 业务端点不证明数据库应用层权限。

## 已修复问题与复核

| 编号 | 级别 | 可复现条件与影响 | 修复位置与独立结果 |
|---|---|---|---|
| C01 | P1 | URL 路径派生 story-test，但 query `dbname=story` 覆盖驱动目标，原 require_test 通过而实际仍指向 story，可误重置正式库。 | `src/ncc_shared/database.py:11` 拒绝 dbname/database 及编码、大小写变体；驱动解析确认只改数据库名，其他连接参数相同。 |
| C02 | P1 | CLI request/workspace 分支原在读取 Settings 前返回，忽略显式 --config，可使用另一配置的 API 地址/凭据。 | `src/ncc_data/cli/main.py:38` 先装配选定配置；显式合成配置与 Mock APIClient 证明所选值传到两个分支。 |
| C03 | P2 | bind marker 原从进程环境取 API 地址，实际请求却取项目文件；文件配置非默认地址时绑定后旧 CLI 拒绝继续。 | `src/ncc_data/cli/workspace.py:20` 保存 client.origin/profile；合成绑定返回的 marker 与实际客户端一致。 |
| C04 | P1 | 备份/恢复原只取 host/port/user/password，丢弃既定 TLS、证书及 options，与应用连接不等价。 | `src/ncc_data/persistence/database.py:17` 与 `src/ncc_data/cli/backup.py:15` 共用驱动解释；合成 TLS 参数完整保留，服务文件0600、不含密码、退出删除。 |
| C05 | P1 | baseline hashes 含 `../outside.txt: null`，旧 pull 手工删除循环绕过脏检查，删除根外合成文件。 | `src/ncc_shared/workspace.py:59` 先校验全部历史及新路径；重跑拒绝恶意 baseline，根外文件和本地现有内容不变。 |
| C06 | P1 | 显式不存在的配置路径原静默回退环境变量数据库，维护/迁移可落到未明确选择的连接。 | `src/ncc_shared/configuration.py:48` 对显式路径缺失直接拒绝；合成旧环境连接不能接管。 |
| C07 | P2 | Settings 原接受 ftp、携带凭据或路径的来源，HTTP客户端却拒绝，两套校验不一致。 | `src/ncc_data/runtime/settings.py:32` 复用 `src/ncc_shared/http.py:11`；合成非法来源均拒绝。 |
| C08 | P1 | 全局 --test 原对 RPC request/workspace 无作用，测试操作可能送往正式 API。 | `src/ncc_shared/http.py:52` 与 CLI 使用专用 test origin/profile；APIClient 首次只向无凭据 health 查询 profile，错误服务在发送凭据/操作前拒绝，每个后续请求带 profile，服务端有逐请求栅栏。 |
| C09 | P1 | STATE 软链原被扫描跳过，快照最后直接写元数据可覆盖根外文件；marker 有相邻风险。 | `src/ncc_shared/workspace.py:16` 及 read_metadata/write_metadata 统一拒绝 STATE/MARKER 软链和目录、原子替换；扫描、CLI及旧 bridge 接线复用，合成外部文件不变。 |
| C10 | P2 | 共享策略未载入时前端原将章节 P5 内容方案兜底为 P3，并显式发送覆盖后端 P1 推导。 | `apps/management-web/src/features/creation/CreativePage.tsx:226` 在策略未载入时拒绝生成，不再发送猜测的 content_scheme；类型映射由 `domain/creation.py` 经 policy 接口提供。此项为代码复核，未跑浏览器。 |
| C11 | P1 | 测试执行器原只核查 public 表，TRUNCATE CASCADE 可波及其他 schema；有效 search_path 也可能不同。 | `tests/support/runtime.py:79` 及 reset 要求 current_schema=public，按字面 pg_ 前缀排除系统 schema，拒绝其他业务表；TRUNCATE 明确 public 且无 CASCADE。Mock 反例证明错误 schema/未知表在清理前停止。未实际执行数据库清理。 |
| C12 | P2 | 范围 token 含换行时 stdlib 非法头异常包含完整 Bearer，CLI 可打印秘密。 | `src/ncc_shared/http.py:35` 拒绝非可见ASCII字符并返回无凭据的通用错误；换行、回车、NUL、中文和空格5项单元通过。 |

上述位置采用当前模块名；旧缺陷属于本轮实现过程中的版本，不代表冻结候选仍存在该行为。

## 独立执行的检查

- `.venv/bin/pytest tests/unit -q`：36 passed in 0.76s，退出码0。先读取全部4个单元文件及测试装配，确认只用合成配置、临时文件、Mock 或内存 ASGI，不读取真实配置、不连库。
- 基线旧 `src/ncc_data/api.py` 与新路由有相同的63个 method/path：60个处理函数 AST 相同，3个差异是 GET policy 增加共享方案元数据、DELETE calibration 的导入路径，以及 GET health/live 增加 profile。鉴权/CSRF service 依赖与三类异常处理 AST 相同；安全中间件新增 profile 栅栏及响应头，未把该变更冒称为完全相同。
- 内存 ASGI 8项请求检查：公开存活接口、匿名 me/openapi/events 拒绝、跨来源写入拒绝、浏览器会话不能充当范围 Bearer、缺 CSRF 拒绝、有效 CSRF 进入 Mock 业务端点。最终单元另验证 profile 不符在鉴权/数据库调用前返回409。
- 配置、CLI与工作副本合成探针覆盖明确路径优先、缺文件不回退、来源校验、marker 地址/profile、上跳路径与元数据软链拒绝，以及初始化不覆盖、0600和特殊字符往返。破坏性反例只操作本探针创建的临时文件。
- `driver_url` 最终增量独立核对10个正式/test URL：中文名、字面 `%2F`、斜杠、空格及 `?#` 均只解码一次；特殊密码保持原值，Mock engine 与维护参数的实际 dbname 一致。TLS/sslrootcert/options 在临时服务文件保留，密码仅置入合成子进程环境。没有调用真实驱动连接。
- 使用显式合成 URL 执行 Alembic `upgrade head --sql`，同时将 create_async_engine 与 Settings.load 替换为禁止调用的探针；成功发出全部4个修订 SQL。另与 HEAD 的旧目录逐字节比较，4个搬迁历史迁移全部相同。此项不证明真实数据库在线迁移成功。
- 对现有 wheel 进行仓外隔离解包、`python -I` 导入验证：源码项目外通过包资源读取模板，合成 `.env` 初始化、0600和拒绝覆盖通过；包含4个迁移资源及 policy 内5个 profiles。wheel SHA-256 为 `aa629d3d8f082168e23ab0962fb5a91fda46dda310b2917bf0887a22de9ce9f6`。另将包内64个源码/资源逐一与当前 src 对照，无缺失或字节差异，模板也与根 .env.example 相同。没有启动包内 API/worker 或联网。
- 最后检查 `application/calibration.py` 迁移与 Service 装配，校准仍由应用层组织，Service 不再顶层导入 creation；共享标准库和 domain 的依赖边界由当前单元检查，前端共享策略 hook 被创作页与评分卡消费。该检查不替代全部应用行为测试。

## 尚未验证

既定 PostgreSQL 配置来源待作者提供，因此没有证明保留原参数后的真实连接、唯一正式库/-test库数量、在线迁移、事务/权限/历史、备份恢复、并发排他锁及模型 worker 在真实环境可运行。没有执行完整浏览器、跨CLI往返或五端新会话加载。主代理的其他测试结果没有冒充本评审独立执行结果；本报告也不评判真实模型的文学质量、评分校准效果或自动定稿已激活情况。

## 已读文件摘要

以下 SHA-256 记录本轮实际读取或比对的核心文件字节。路由文件主要用于63项 AST 等价核对；Service、前端 CreativePage/ScoreCard 等为指定增量定向阅读，列出摘要不表示其全部行为都已独立验证。任务记录及本报告属于会更新的证据元数据，不作为产品逐文件摘要。

```text
5b08534bc9c79f0d050690c5eda03bcc2658f134cb9b703686ffff49417b05de  .env.example
d0332560000c97dcccbeaf7b88b8eb4436f4c444d438f2e2e98a7fd1ed20f300  apps/management-web/src/features/creation/CreativePage.tsx
259a69a35e88bbb2222679d7c0902f2c368d4b5bfd18e9745c9dfcad82fe7a52  apps/management-web/src/features/creation/components/ScoreCard.tsx
155c65953bfe72576f4e9a9368a4429c4beea5df39ec2c571a887a9fd15fdc8e  apps/management-web/src/shared/useCreationPolicy.ts
5e62ac7d65f02de491cf1f1a93bcc30068d5107e7c53afe78531877c5baab9c6  docs/designs/engineering/configuration-ownership.md
8169e44334c16b2cdb4363b82ccf246d9ea0d30eac8c7be6ef2d3af8be327e83  docs/engineering/code-layout.md
84e9e517995b76ff906ba5640e015b79e8745c045a1a717f1724b918123e9cbb  docs/engineering/workflow.md
2ce3c5443a85864c2604756408af21479aa17fdef087c2c2dbd5e3655202a938  pyproject.toml
a8efe08adeb47e3697ddce153fb227a60d240b01133ce01b4f0a36f0883318f2  scripts/ncclib/__init__.py
ab2b4f6d1dc411f80ce2b77d3b6ab8090d36b20525c25a2adbe1f906092366f5  scripts/ncclib/database_bridge.py
3c4d024b2299fa670b724245ab8f0373f9753bcb7a42c3febc00c1fd92c0d3cf  scripts/ncclib/quality.py
24d9ead8832068f0aa2811bc0a8793ee6ea0abe4124d17a73dca29caa65fe704  skills/ncc-dev/SKILL.md
eea1625108789874f4be368269971125128b1687aeacc0d2b13615322daa613a  src/ncc_data/api/app.py
750a5dbd62c3a48221e048334e735132b6ef96e55a5254540e07d1939bada888  src/ncc_data/api/problems.py
a7e71e3f3e05e4715cb7ac8aa659584c993113146bcad4ce2bde2809bcfd648b  src/ncc_data/api/routes/administration.py
66add675d606bccc5ae82161ac34e3287edecbd61291a751c0bdca61578d08dc  src/ncc_data/api/routes/creation.py
81f36d204ffd37bc12335ad712c3f988da25e3fa4ab02c73c41fbb067700d63f  src/ncc_data/api/routes/events.py
e89f4babfeb8bbbb3a338257e9d46da19016053486a6578fe61b1b2d404caa24  src/ncc_data/api/routes/exchange.py
3d37d9a144453abd27e810e574f18e2c834ca305773afdfe8a879f870a66fd0a  src/ncc_data/api/routes/knowledge.py
42b609ed1b0dbf5881122004f307153d724487ff88fcd09723f92c5b7ab1835f  src/ncc_data/api/routes/session.py
65298f0b5e1f9d231d764d8565c5c58461f65ac11d397e0a33564463e1c4ca46  src/ncc_data/api/routes/system.py
76b9bd460b04f499da65d4b761c8819ade62c4d69ab10cd7e50b62ad620a0e30  src/ncc_data/api/routes/workspace.py
060250e831612562aebabbfa8dfe533ddd9773008f7111ee01bc97d94662020d  src/ncc_data/application/calibration.py
82f185aacf4c649fcefe6b45e2c4c97ea311bc659dba37a0ca091057f7844976  src/ncc_data/application/service.py
6dec2d2366d5270f2251cc810036014aa1967fce6253f51314d43b8541f64430  src/ncc_data/cli/backup.py
cae66f47b0e9ff0b6c3b3155685d924ae306a20b89db165f85f3f03c68f57f7e  src/ncc_data/cli/main.py
011e6879164ec929f3887032835849ce225a05bfb7794ced4c4e5c665ebc5535  src/ncc_data/cli/workspace.py
7ea62e3b7365f9ecf80b3934501056d628b12b683307b8e274a1300629014d27  src/ncc_data/domain/creation.py
c1d171609b06f3d6729126b13a68e5a961bfe75f1e5d8ba7bea9e63bc20acd5d  src/ncc_data/persistence/database.py
d79d0a7e65e1a39f82a608b63f99759aa3b8a2ed9ba2b7135cb137e4bbf67cf2  src/ncc_data/persistence/migrations/alembic.ini
f394479f37bb146a408f0f30b3f81912307fb1332e31464c9f3801b45e1f048a  src/ncc_data/persistence/migrations/env.py
3c692659530625a8af5145f9ae04dff5748922f44a3610dc6718eab9cb0d0a72  src/ncc_data/persistence/migrations/versions/070970fe2f0a_private_knowledge_temporal_history_and_.py
e6f02cfb5299b3e8be8a2221dca52de1e28fc4c6fc61f8d4ed141d71f9d49f11  src/ncc_data/persistence/migrations/versions/5c4c6e012a90_scoped_credentials_and_history_guards.py
920af50067773d644ad95d1575151fed6f69371a873e17162fb05eca6764666b  src/ncc_data/persistence/migrations/versions/6d30bb12e441_attachment_access.py
acb147a5b4de8bdda3c5a4729cdd8d2f0819723f52818b2952f3455e685dc769  src/ncc_data/persistence/migrations/versions/7e419c2d608b_author_trial_delegation.py
2a4b086356a2e9ac489a402b8323276e1b96a286a724c0433a6819fbd09f7aef  src/ncc_data/runtime/settings.py
753bac891225be15431e06acecc40a802a95603eaf1c9ecea0f015195ef5405b  src/ncc_shared/configuration.py
890b606868b20de1f8ef6db3307d60b3fb012e76bec47477fef1b1f84d270160  src/ncc_shared/database.py
987a2753131846fc08482d63de1d141434336b09bd94aadea18c9646719a6ec9  src/ncc_shared/errors.py
a358fed7939ffa4a66894a846ee260bcf7f60d2e06e76ff22b4ed23b9c4a2dca  src/ncc_shared/http.py
12d447d1993bca04e78d6e736dfed6c7a22a3f92e7bafa6c663d1a0caec8ea68  src/ncc_shared/paths.py
09b1f41e43c5565170b91955eef248377042f4b2a6529be7f7d1e7980cbf89e9  src/ncc_shared/quality/policy.py
96d46b8c9cbce6cee972a580cbf3986406ddb994ab6bcae2489999c2730272d5  src/ncc_shared/quality/resources/policy.json
2d97a55c3e24bfaa51d3bfce78d9c931b6a1385088ac33f6e72bf0059734a07d  src/ncc_shared/quality/scoring.py
9141de40be4c4b30e1340876a2968c26e243444ad6eeaf83e7a72729d3a64cfe  src/ncc_shared/serialization.py
99a7f7c74191bad77b817fbb0f1f09990b812f30e98a93012b016df18f25ed35  src/ncc_shared/workspace.py
daed0377c6a4bf7b75140e33e87e980e586d019604386387fc4b49fef5fb39f4  tests/backend/conftest.py
b89df5a93c39dce4cdda9cfa84d104430243b7e9be25afbc3bc05d4a52892bd4  tests/backend/run_recovery.py
77d06aeb6a0ae679d49ab85fe6bd3aca1b71314d9dda63bab4eac6d2d39b78ac  tests/conftest.py
37a75b06cf8c8a553db1c52748d430eae68ddb88788ec63d3052532b19b8b292  tests/support/runtime.py
dde8a4771b3aadfda659b46ecd96e864b4f86b34e93e02752b19d6d3344cc858  tests/unit/test_boundaries.py
a981f9a2ef06f485ff3f84866088d106a15ac1e71ea03ec6f66728c6e78146c6  tests/unit/test_configuration.py
b25fac92bb96b2769cd5e4c1534f44a747cee851f5ceaaae16073e36c60f8386  tests/unit/test_runtime.py
837247ec5f99c0caf45d6758ef8b5f3a70ccf7febc36819cd16ba097edad003a  tests/unit/test_workspace.py
```
