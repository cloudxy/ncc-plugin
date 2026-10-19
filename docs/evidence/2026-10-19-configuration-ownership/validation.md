# 项目配置与代码归属验证

日期：2026-10-19。仓库与加载技能根均为`/Users/xuyun/Documents/ncc-workflow`，main，基线`4b50690a696a4483dc1fb9f4c68d92b4e0db770f`。最终候选`19f5281e2c08dae8300800d76733f250491ec1e9805c1db8573d245555a6c9b1`，190个精确产品路径；任务记录、受检日志和独立评审属于证据，不纳入产品指纹。

环境：macOS，文件CLI Python 3.9.6，后台/pytest Python 3.12.14，Node.js v25.9.0；数据库服务未连接，模型未调用。

## 输入与实际结果

| 检查 | 实际结果 | 原始记录 |
|---|---|---|
| `python3 -m unittest discover -s scripts/tests -t scripts -p 'test_*.py'` | 最终204项通过，退出0。最初一次运行203通过/1失败：规范文档尚未创建导致链接检查失败；补齐后架构7项及最终全量重跑通过。日志中的数据库标记拒绝和陈旧registry提示为预期反例。 | [legacy.log](legacy.log) |
| `.venv/bin/pytest tests/unit tests/backend -q` | 43 passed，35 skipped，退出0。36项无数据库新用例，7项已有评分用例。35项PostgreSQL集成因缺既定连接来源跳过，不能算通过。 | [unit.log](unit.log) |
| `npm --prefix apps/management-web run build` | TypeScript和Vite生产构建通过，3418模块；28个归属清晰的TS模块。保留既有编辑器/组件库体积提示，不把构建当真实浏览器验收。 | [frontend.log](frontend.log) |
| `python3 scripts/dev/check_plugin.py -v` | 插件接线、链接及预算通过。 | [plugin.log](plugin.log) |
| `python3 scripts/dev/build_docs.py --check`；`build_registry.py --check` | 生成视图新鲜，通过。 | [docs.log](docs.log)、[registry.log](registry.log) |
| `python3 scripts/ncc_eval.py mech` | A01–A06机械样例均通过；本轮未改变创作判据，不新增模型锚定回归。 | [mechanical.log](mechanical.log) |
| `.venv/bin/ruff check src tests/conftest.py tests/unit tests/backend tests/browser tests/support` | 通过；历史迁移不格式化。 | 本命令退出0，历史字节另作对比。 |
| `uv build --wheel`及隔离解包探针 | wheel构建通过；一个模板源、一份评分资源、唯一迁移目录4修订。隔离工作目录初始化含全部配置键、600权限、再次初始化不覆盖；评分包含5方案，标准库共享包通过Python3.9语法解析。 | [package.log](package.log) |
| OpenAPI与迁移静态对照 | 基线完整OpenAPI相同：54路径/63方法路径；4个历史迁移与基线字节完全相同；评分资源与基线字节相同；仅以显式合成URL生成离线迁移SQL，禁止创建engine。 | [package.log](package.log) |
| 浏览器/CLI验收入口导入 | 4个直接脚本导入成功，没有打开数据库连接。 | 独立入口导入探针退出0。 |
| `python3 -S scripts/ncc_state.py --help` | 无site-packages时原CLI可加载，退出0。 | 标准库入口探针退出0。 |

无数据库用例覆盖：文件优先级、既定值与特殊字符、重复初始化、配置缺失/歧义、唯一-test派生、其他连接及query dbname重定向拒绝、维护TLS/options保留、工作副本路径/软链/摘要校验、HTTP错误profile无凭据预检、服务逐请求隔离、显式CLI配置、非法头令牌不泄漏、共享包与领域导入方向、测试清理schema边界和无CASCADE外溢。

## 私有边界与未验范围

此前项目无`.env`，本轮使用初始化入口生成本地600权限文件；其实际PostgreSQL字段留空等待作者提供已确定配置的文件路径。没有读取或复制其他项目MySQL/Redis凭据，没有改动数据库服务器、账号、端口或正式库。没有新建、删除、重命名数据库，没有启动此前临时集群。`.env`同时被Git和插件忽略；真实书稿、资料、备份和私有配置不在190个候选路径中。

PostgreSQL集成35项、真实浏览器交互、数据库CLI往返及唯一-test库恢复重放尚未执行。需要先原值填入既定正式连接，并由维护者确认唯一-test库已存在；随后按指南串行执行。当前证据不能推断真实数据库权限、DDL应用、恢复成功或前端全部交互正确，也不能替代五端新会话验证。没有再次提交/推送。

独立评审详见[review.md](review.md)，其结论仅覆盖读取的代码、纯本地反例和内存HTTP检查。下一步及精确范围见[任务记录](../../tasks/2026-10-19-configuration-ownership.md)。代码回退只回退本轮路径，保留私有.env与数据库；没有数据库迁移回滚动作。
