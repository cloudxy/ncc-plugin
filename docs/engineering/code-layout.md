# 代码归属与复用

现行规范。配置和日常命令见[数据后台指南](../guides/data-console.md)，开发阶段及交付证据见[开发工作流](workflow.md)。本文件只定义代码归属和依赖方向，不复制操作流程或业务规则。

## 后端与共享代码

```text
src/
├── ncc_shared/                 # 跨入口共享；配置按需加载Dynaconf
│   ├── configuration.py        # 唯一Dynaconf装配、覆盖、校验和初始化
│   ├── runtime.py              # 数据库操作按需进入项目.venv
│   ├── database.py             # 正式连接及唯一-test派生，不连库
│   ├── http.py                 # CLI的HTTP客户端、来源和profile保护
│   ├── workspace.py            # 文件扫描、路径校验、快照和本地标记
│   └── quality/                # 唯一评分策略资源及无状态计算
└── ncc_data/
    ├── runtime/                # 运行配置装配
    ├── domain/                 # 业务输入契约、定义校验、内容方案映射
    ├── persistence/            # SQLAlchemy模型、连接、系统定义种子
    │   └── migrations/         # 唯一Alembic配置、环境和历史迁移
    ├── application/            # 权限、事务服务、评分校准与用户操作
    │   └── knowledge/          # 查询、变更、维护、交换、工作副本
    ├── creation/               # 任务执行、模型网关与评分适配
    ├── mcp/                    # PostgreSQL只读stdio工具及宿主配置生成
    ├── api/                    # FastAPI装配、传输参数、各领域路由
    └── cli/                    # 命令装配、备份恢复、工作副本入口
```

`ncc_shared`不导入后台，文件、评分和路径部分仅用标准库；`configuration.py`在调用时加载Dynaconf及python-dotenv，数据库模式通过共用runtime进入项目.venv。`domain`不导入接口、持久化或任务执行器。`persistence`负责存储，不依赖接口。`application`组织领域校验、存储和权限；`creation`调用应用服务执行任务；`api`和`cli`负责输入输出与装配，不承载另一份业务规则。应用操作需要排队或解释创作结果时可延迟导入执行接口，不能让创建任务时执行外部模型请求。修改服务行为先找到所属操作，不向总服务文件继续堆独立功能。

`scripts/ncclib/`属于原文件工作流，`scripts/`顶层保留运行入口，`scripts/dev/`属于工程工具；标准库CLI不导入FastAPI/SQLAlchemy。`ncclib/__init__.py`只做一次源码路径引导，评分与数据库工作副本适配器直接复用`ncc_shared`。保留的命令入口只转发，不维护实现副本。数据库模式的`ncc-data`、`python -m ncc_data.cli`和`scripts/ncc_data.py`进入同一命令实现。

四类工程角色的元数据、触发和交付字段归registry的development域；agents目录保存具体角色方法，共用协议归ncc-dev参考文档。scripts/dev/development.py复用原任务记录和路径守卫，管理按需计划、有限派单、报告与来源新鲜度；原开发检查器调用同一验证实现。工程角色不进入创作角色、记忆或章循环列表。

迁移随Python包直接分发，源码与wheel都从`persistence/migrations`定位；不生成仓根和包内两份迁移。已有迁移只因归属搬迁，DDL变更必须新增迁移，不能重写历史。

运行配置统一归`config/`：`default/settings.toml`提供唯一公共默认，`<ENV>/settings.toml`按需覆盖，`.env`保存既定私有值，`.env.example`提供初始化模板。路径由`ncc_shared/paths.py`定义。wheel从同一来源构建包资源，不维护配置副本。`application/access.py`组织MCP及直接CLI的认证、事务和Service调用；MCP读取强制数据库只读事务，不注册写工具。宿主清单由`mcp/configuration.py`生成，`.mcp.json`与`.codex/config.toml`因宿主发现约定保留在各自位置，仅有启动接线、不存应用参数，忽略且不进入插件包。

## 前端

`apps/management-web/src/app/`只放启动、登录后的壳和路由装配。`features/`按session、creation、jobs、inbox、knowledge、definitions、exchange、quality、administration归属页面；领域专用组件进入该功能的`components/`，地图和图谱实现进入`knowledge/visuals/`。`shared/`放请求、作品上下文、编辑器、引用选择、反馈组件、评分元数据读取和任务阶段显示；样式归`styles/`。

只供一个功能使用的组件不要过早提升到shared。跨页面共用的实现先抽出，再由页面引用；页面不反向依赖应用壳。类型与内容的评分方案映射由后端`domain/creation.py`负责，前端从策略接口读取，不复制一套映射表。评分权重仅在`ncc_shared/quality/resources/policy.json`维护，旧CLI和后台均读取此资源；前端展示接口返回值。

## 测试与文档

| 归属 | 放置位置 | 范围 |
|---|---|---|
| 文件CLI与插件工程用例 | `scripts/tests/` | 标准库用例、规则接线和合成书项目 |
| 无数据库单元与边界用例 | `tests/unit/` | 配置、连接派生、路径保护、HTTP和依赖边界 |
| PostgreSQL集成与恢复 | `tests/backend/` | 事务、历史、权限、自动化及转储重放 |
| 浏览器与跨CLI集成 | `tests/browser/` | 真实页面及数据库工作副本往返 |
| 集成环境公共实现 | `tests/support/` | 唯一测试库校验、排他锁、迁移和测试服务生命周期 |
| 操作、规范、设计、任务、证据 | `docs/`对应子目录 | 具体归属见[文档组织规范](documentation.md) |

测试入口复用同一个`TestRuntime`；所有需要清理数据的操作只允许配置派生的-test库。禁止在用例里创建随机数据库或绕过公共守卫另写重置函数。集成验收串行执行，不用新库解决并行冲突。测试库仅存可丢弃合成数据；有未知表、其他业务schema或其他验收占用时停止。清理明确限定public中的NCC表，禁止CASCADE清理外部依赖。恢复演练需额外明确确认唯一测试库名，保留转储作为失败回退工件。

配置说明只在指南，目录职责只在本规范；设计记录说明理由，任务记录说明进度，冻结证据保留当次路径。新增前先按职责搜索已有实现，避免再建一份config、client、utils或页面总文件。
