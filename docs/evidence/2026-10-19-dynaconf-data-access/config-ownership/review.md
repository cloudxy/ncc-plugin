# config 归属与产品职责方案增量独立评审

日期：2026-10-19。评审会话：`/root/upgrade_review`。活动工作树及技能根均为 `/Users/xuyun/Documents/ncc-workflow`，main；基线 `ac0fc44990a4f8c8e8d22a3a0a4a0540c4446393`。按 ncc-dev 独立评审要求检查配置归属、旧配置迁移、MCP入口迁移及产品职责方案，不重复全仓审查。

最终绑定候选 **`af3787bbe3b355b5c6c91512049060190c8d8a73b84ee81b547153a8ff0bcb57`**（38个精确产品路径）。初始候选 `1d65b717f90bafca919ca433cd1aeb3764330cef65ba94fc27f4302dcd0f7424` 的 O01/P1、O02/P2 已修复并独立复核；受检增量未遗留已复现 P1/P2。该结论仅覆盖下列代码、合成文件及macOS本地系统调用验证，不代表真实PostgreSQL、完整UI、宿主新会话或全局交付验收通过。

已运行工程记录检查，返回 RECORD OK、退出码0及上述同一最终指纹；这只证明归属和候选一致，不能代替业务验收。上一份[根评审报告](../review.md)保持原字节，SHA-256仍为 `7e9bdf4177fd1a8f45789fa6e5efdae76414cf5c36d069da7f2492910139df65`，其历史结论没有直接沿用到本候选。

## 发现及最终复核

| 编号 | 严重度 | 初始可复现条件与影响 | 最终修复与复核 |
|---|---|---|---|
| O01 | P1 | 旧配置迁移先link后unlink；合成探针在真实os.link之后原子替换旧根.env时，initialize返回成功并删除作者新配置，只留下旧值；反向替换目标时，原始源字节完全丢失。已有用例只覆盖link前目标存在。 | `src/ncc_shared/configuration.py:125` 与 `src/ncc_shared/configuration.py:150` 完全移除link/unlink，改用系统原子排他rename。持有原源fd，移动后核对目标身份及源是否重建；只对原fd执行fchmod，冲突没有删除清理。独立macOS临时目录实际系统调用验证正常迁移、目标抢先创建、源替换、目标替换、源重建5类均通过，并发新文件未被迁移器删除。 |
| O02 | P2 | TOML重写器把多行notes字符串里的假表头/args当作真实入口。真实入口用合法带引号表头，command/旧args完整匹配；安装返回成功、TOML可解析，但改了notes，真实入口仍指旧根.env。 | `src/ncc_data/mcp/configuration.py:15` 将重写后完整解析对象与“原解析对象仅修改真实入口args”的期望比较。独立假notes反例现在拒绝，Claude/Codex两份完整文件逐字节不变；正常完整匹配入口迁移及其他服务器/同入口设置保持由当前定向单元覆盖。 |

这两项属于初始候选中的缺陷，不表示最终候选仍存在对应行为。

## 配置与入口检查

`paths.py`统一config目录、默认私有文件及旧路径定位；模板位于config/.env.example，wheel声明也从该单一来源打包。默认加载与显式指定规范config/.env时，都检查旧根配置及双文件冲突；没有静默读回旧根值。正常迁移不解析或重新序列化旧字节，合成BOM/CRLF/注释保持，成功后0600、旧名移除，重复init不改内容。显式的其他合成配置路径仍可用于测试。

MCP安装器默认参数使用同一config_path。只对符合生成command/完整旧参数的入口尝试迁移；手改的不匹配入口拒绝，且所有候选准备、语法和目标语义检查先于写入。Codex原有enabled/timeout和其他服务器保持；不支持安全重写的TOML布局明确拒绝。没有把“安装器返回成功”等同于宿主新会话加载或数据库连接成功。

## 独立执行的验证

本机macOS，Python3.12.14项目环境；只操作自建临时目录，未读取真实config/.env或旧根.env，未连接、创建、重置、恢复或删除数据库，未启动旧PG集群，也未修改产品代码。

- `.venv/bin/pytest tests/unit/test_configuration.py tests/unit/test_mcp.py -q -k 'not real_stdio'`：**40 passed、1 deselected in 0.49s，退出码0**。读取当前测试后执行；选择配置/MCP直接受影响部分，真实stdio子进程用例未计入本评审独立执行。
- 合成旧文件使用BOM、CRLF及注释，默认init经本机真实renamex_np迁移，字节不变、权限0600、重复init保留内容。macOS排他拒绝目标抢先创建时，源/目标各自内容不变。
- 在真实排他rename前后交错本探针的编辑器原子保存，独立检查源替换、目标替换和源重建；均拒绝完成声明，保留并发文件，没有路径unlink清理或回退覆盖。该验证不意味着可以阻止编辑器自身有意覆盖它保存的目标。
- 用Mock平台名触发不支持分支，确认明确拒绝、源文件保留、目标不产生；没有普通rename或link/unlink降级。此为分支探针，未在另一操作系统原生执行。
- 重跑O02合法多行notes反例，验证两份宿主文件无损拒绝。定向单元另覆盖生产/test旧参数迁移、保留enabled/timeout、重复执行、非字典/inline-table拒绝及正常注册。
- 工程check确认最终候选指纹及38路径；候选和实际差异均无skills/agents/workflow/现行开发工作流接线变更。注册表仍为十二个创作角色，根review文件摘要重核未变。

Linux renameat2(RENAME_NOREPLACE)分支只完成代码阅读，没有Linux原生系统调用或文件系统实测。macOS之外的真实运行、跨文件系统失败及权限异常环境未验；实现不支持安全移动时保留原文件并拒绝，不承诺自动兼容所有平台。

## 产品职责方案审查

完整阅读[小说创作主线与工程职责](../../../designs/engineering/product-architecture.md)，并定向核对Shell菜单/路由、CreativePage的200项通用实体查询、十二创作角色注册及既有工程阶段。

方案如实区分当前能力、缺口和后续目标：创作台为当前默认入口，通用对象选择仍有长篇导航局限；资源可独立治理且应支撑创作；没有把数据库后台等同于小说创作完成。四类工程职责有进入条件、输入、工件、反例、验收任务及回退，说明可以顺序承担、不得把自查伪称独立专家评审。A–E批次给出前置条件和可观察交付，没有以空代理名称或“最佳实践”代替执行步骤。

四职责接线、卷章导航、自动资源回写、真实作者任务验收仍是候选目标；没有在本轮注册四代理或改创作判据。评分/授权引用既有设计，没有另建阈值或用产品简化删除作者关键决策。文档能证明方案的内容和边界，不能证明四职责已具备能力或小说创作体验已经改善。

## 外部证据与未验范围

主代理[迁移记录](migration.md)说明：本机真实私有文件首次移动发生在算法修正前；最终算法通过合成并发样例验证，本机仅再次init确认字节不变，没有为了测试将真实配置迁回根。本评审未操作或读取该真实私有文件，不把前一次首次移动当作最终函数的真实首迁证据。

主代理[验证报告](validation.md)记录84 passed/38 skipped及包/静态等结果；其[本机MCP报告](local-mcp.md)记录实际stdio重接成功、状态configured=false/connected=false。以上仅作为阅读到的外部证据，不冒称独立执行。PG配置来源仍缺失，实际小说数据读取、落库、数据库只读强制、历史/审计/CAS、恢复、完整UI和五宿主新会话均未独立验证。产品职责候选仍待作者审核，未发布新版本。

## 已读文件 SHA-256

以下记录本增量实际读取或定向比对文件的当前字节。大界面文件只用于方案依据核对，消费者模块主要核对路径提示/装配变动；列出摘要不表示穷尽其功能。任务和证据元数据不纳入产品逐文件摘要。

```text
8dd370e7d6d045c61becd8ce88eea37b5382e7e46b9c7c327edcb78d2e20859e  apps/management-web/src/app/Shell.tsx
d0332560000c97dcccbeaf7b88b8eb4436f4c444d438f2e2e98a7fd1ed20f300  apps/management-web/src/features/creation/CreativePage.tsx
53bb1f2eb22a9ae55b50d80d8ea42b42d4c400bc5c8a03e8b30dd188d80e1c35  config/.env.example
3302f3313d015c686842fc095c7e9b9551314fa50a274afc3a7e5ba060325c75  config/default/settings.toml
f4977e90970a115abbf09338ab371dcf75d006f135c304971ea650e21aea5857  docs/designs/engineering/product-architecture.md
84e9e517995b76ff906ba5640e015b79e8745c045a1a717f1724b918123e9cbb  docs/engineering/workflow.md
6f771d57e76bab1ffd64e2600c3f1f2fe0cd94702166c615fdeafcc1ae524865  docs/guides/data-access.md
0828b285321134c3d72bebc69880cc7354bdaac3209536c53aed9d03369e8bd3  docs/guides/data-console.md
2442bc1b26fd44d51695affcfbe164e183a8d14f195a28d8551f3a5f4ca0d9a6  pyproject.toml
322bf5b364d1c1924564b7780d9a738de37998701e22e386ef022e031090e902  src/ncc_data/cli/main.py
1decd946dce612cee4fe16b0b3cda8391e2e645334dc728c0be554100bc6283b  src/ncc_data/cli/workspace.py
7aace5143225989be7614efa8338fe66017ee9e53ba048c604ab1b92655acd08  src/ncc_data/mcp/configuration.py
0ab383e5db8b9f247d7c2f9cba2ad04e8e9aa7bfbe98e46acc907aeea3358fe4  src/ncc_data/runtime/settings.py
73fbc3bcb35da3d46389992463f4cfa46b5c1b1c411218f72573f2d4e722f1a9  src/ncc_shared/configuration.py
27ac281dff85fbd42423a280491f5c8f27ab57c03623eb47581eacc80f06804c  src/ncc_shared/database.py
67590301f1388207b47b1a367452ca162af7af0df9dd9f4b7d7b7a94159a1d4a  src/ncc_shared/http.py
3d3b4d0a865eb80e148c895c71a4d4d6bcb9049bee0f897fd183d608fa2b3db1  src/ncc_shared/paths.py
13d793c9f824dd72cd76152f6eeccd71b392a74c1696940f7a02e6303b1a7ac6  tests/backend/conftest.py
fd3a032a9f2c5ef7a049444923a9a4904bf009e58517d396b118b97913dc05dd  tests/unit/test_configuration.py
21e8f9fc550077e66721d2fcf6352b0eb840bbb38f4637731e3507f34d569345  tests/unit/test_mcp.py
38bf4023449614a12a9548c66ac7c6648e9319050471d931093abe4e33e59881  workflow/registry/roles.json
```
