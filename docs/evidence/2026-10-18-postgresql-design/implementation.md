# v4 本地升级实施与验证

2026-10-19，作者已授权按三份方案实现，并追加“自动定稿资格尚未启用：启用。提交并推送”。本轮使用隔离合成数据，不接触真实书库，不自动迁移生产数据库。发布结果见[任务记录](../../tasks/2026-10-18-postgresql-design.md)与[发布核验](release.md)。

## 实施范围

- PostgreSQL稳定身份、类型/属性/关系定义、不可覆盖修订、双时态事实、来源、范围权限、固定基线分支、审计、幂等与持久任务；16领域目录273项通过种子定义承接。
- FastAPI统一应用服务与同源会话/CSRF/范围令牌；React、Ant Design、CodeMirror、Cytoscape和OpenLayers管理后台，日常三个入口。
- 草稿自动保存、人工编辑与接管、按类型评分、有限返修、选段改写、仅评分、二评争议、P5执行质量、校准、托管授权与可撤销凭据。
- 受控变更、定义发布、资料和关系维护、历史恢复、身份合并/拆分、三方分支合并、来源附件、导入导出、质量、任务、审计和权限。
- 标准库文件CLI继续可用；数据库模式显式影子导入、绑定和受控回写。新Python依赖与原CLI分离。

设计与操作步骤见[实施计划](../../designs/storage/implementation.md)、[使用指南](../../guides/data-console.md)；独立发现及修复见[独立报告](independent-review.md)。

## 实际验证

以下检查均已实际运行，退出码为0。代码、锁文件、生成规则和精确范围由[任务记录](../../tasks/2026-10-18-postgresql-design.md)的最终候选指纹绑定；没有把历史设计静态报告当实现证据。环境为macOS、原CLI Python 3.9.6、新服务Python 3.12.14、PostgreSQL 17.11、Node 25.9及本机Chromium。数据库均为临时 `ncc_test_*` 合成空间。

| 检查 | 实际命令与结果 | 原始证据 |
|---|---|---|
| 原CLI全量 | `python3 -m unittest discover -s scripts/tests -t scripts -p 'test_*.py'`，204项通过 | [unit.log](unit.log) |
| 数据服务 | `.venv/bin/pytest tests/data --database-url '<隔离测试连接>' -q`，初始32项、追加自动定稿后42项通过；含事务、幂等、权限、历史、分支、导入、评分、任务及评审反例 | [初始](postgres.log)、[最终42项](auto-adoption-postgres.log) |
| 前端 | `npm --prefix apps/management-web run build`，TypeScript与Vite构建通过；`run format:check`通过 | [最终构建](auto-adoption-web.log)、[格式](release-format.log) |
| 真实浏览器 | `.venv/bin/python tests/web/run_browser.py --output '<仓外合成截图目录>'`：登录、建空间、快速输入与服务端自动保存、正式保存、已保存草稿清理、资料/历史/定义/任务/设置、桌面及390px布局通过，页面错误0 | [browser.log](browser.log)、[桌面截图](web/desktop.png)、[移动截图](web/mobile.png) |
| 断线撤权 | `.venv/bin/python tests/web/run_access_browser.py`：断网期间撤销秘密权限，重连清理本地脏表单；撤销read后移出范围，页面错误0 | [access.log](access.log) |
| 旧CLI接入 | `.venv/bin/python tests/web/run_cli_bridge.py`：影子导入、显式绑定、CLI读写、外部正文修改回写、typed章同步、安全pull及原件保留 | [cli-bridge.log](cli-bridge.log) |
| 备份恢复 | `.venv/bin/python tests/data/run_recovery.py --database-url '<隔离源>' --target-database ncc_test_recovery_final --pg-bin '<PG17工具目录>'`：16张事实表全行摘要一致，含正文、历史、事实、二进制附件及合成评分记录；会话/托管撤销、未完成任务暂停，拒绝重复恢复到非空库 | [recovery.log](recovery.log) |
| 接线与机械层 | `build_registry.py --check`、`check_plugin.py -v`、`build_docs.py --check`、`ncc_eval.py mech`全部通过 | [registry](registry.log)、[plugin](plugin.log)、[docs](docs.log)、[mech](mech.log) |
| 代码与打包 | `.venv/bin/ruff check src/ncc_data tests/data tests/web`、`git diff --check`通过；`uv --cache-dir /private/tmp/ncc-upgrade-uv-cache build`成功生成wheel与源码包，最终wheel包含量表和4份迁移且无字节码缓存 | [lint](release-lint.log)、[package](auto-adoption-package.log) |

浏览器截图只含合成文本。桌面全页截图会在本机Chrome的全页捕获期间触发布局重排，故保留正常视口截图并记录[实际布局尺寸](web/layout.json)：桌面侧栏228px，移动侧栏64px，移动无横向溢出。构建仍提示编辑器、图谱与组件库大分包，已使用按路由延迟加载；未将构建通过等同于大书库性能达标。

独立会话复现并复核了12类问题，另对撤权重连、范围切换、草稿CAS清理与异步加载竞态作定向复核；独立数据服务回归32项通过，最后草稿增量另跑1项通过。其范围与未验事项以[独立报告](independent-review.md)为准，未宣称逐行审查全部产品。最后仅追加浏览器脚本的桌面尺寸断言与截图记录，不改变业务代码；前端交互修复已重新构建并重跑浏览器。

## 行为样例与证据边界

[ncc-eval单轮报告](behavior/score.md)：6个合成锚定章，每章独立fresh continuity盲审一次；8/8植入问题检出、8/8定级到位、6/6结论正确、干净对照严重误报0。没有重复运行，报告中的“不稳定：无”仅说明单轮没有可比较的不一致，不能证明稳定性，也没有做旧候选与新候选的配对比较。

另由fresh pulse执行P1质量任务，返回[原始评分报告](behavior/pulse-report.json)：逐维提供半分、原文短引及理由；因缺少作者目标、契约和前文而报告hard=unknown、coverage=incomplete。标准库quality ingest正确输出score=null/verdict=incomplete，没有为了达质量线虚构放行。该样例验证职责及缺证据路由，不证明创作品质或模型网关已经校准。

## 自动定稿启用复核

新增`author_trial`与`calibrated`两种有限授权。前者限作品所有者明确登记授权依据，绑定目标、方案、策略hash、期限和次数；不创建校准记录，采用结果及审计标为校准未验证。后者仍要求真实留出校准。两者都保留质量线、维度底线、硬伤/证据、二评、P5、故事、版本、权限、开篇和关键章闸门。P5按目标实际内容类型选量表，无策略hash的旧授权需续授权。

最终数据回归42项通过；独立会话新增10项通过，并复现修复了P5人物修订误要求P1、旧授权缺hash两个问题。浏览器[授权接线](auto-adoption-browser.log)实际登记了合成对象的试运行授权，在创作台选中并核对任务payload绑定，页面错误0；没有启动真实模型。原[创作台浏览器](release-browser.log)重新通过。新增迁移后的[恢复演练](auto-adoption-recovery.log)也通过，恢复后包括试运行在内的授权撤销、未完成任务暂停。

本轮首次数据库回归因重启时遗漏测试端口参数而连接失败，恢复专用55439端口后重跑通过。浏览器首次定位未滚动到历史空间，改用独立合成账号；其后按钮定位漏算图标名称、主流程在建空间弹窗关闭前向旧表单输入，均修正脚本并实际重跑通过。没有把这些失败当作通过证据，也没有因脚本定位失败修改质量门槛。

## 运行边界

真实模型网关、作者留出集和目标实例未配置，已校准资格仍未验证；试运行功能已接通，尚无真实作品激活记录。五端新会话加载与正式大规模性能、长期运行、RPO/RTO仍待实际环境验证。基础中文字面/结构化/关系查询可用，向量提供方未接入。CLI非章节旧台账以受管原件兼容，不冒充已经完成全部领域的语义转换。可视化及质量扫描明确有界，未声称覆盖整个大书库。Python wheel包含迁移与定义，前端需另行构建/配置路径。

提交推送按本轮作者授权处理；真实小说、连接凭据和转储均未纳入候选。测试账号、文本、附件和评分替身全部明确为合成验证数据。临时服务在验收结束后停止。
