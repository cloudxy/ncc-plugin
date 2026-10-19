# 项目配置与目录归属整治

plugin_root/repo_root均为`/Users/xuyun/Documents/ncc-workflow`，main/v4.0.0，基线`4b50690a696a4483dc1fb9f4c68d92b4e0db770f`，开始时工作树干净。使用ncc-dev结构路径，继承作者已确定的PostgreSQL参数，不新选数据库服务或账号。

按[方案与实施批次](../designs/engineering/configuration-ownership.md)推进。配置读取、正式/test派生、前后端分层与共用实现已经落地。目录和依赖规则唯一见[代码归属规范](../engineering/code-layout.md)，操作唯一见[使用指南](../guides/data-console.md)。配置、连接选项、工作副本、评分策略及内容方案映射各保留单一实现；既有迁移仅移动，历史字节不变。

已参考作者指定项目的路径定位与自动加载方式；其中查到MySQL/Redis配置，没有移植其账号。项目此前不存在`.env`，现已初始化为本地600权限文件并被Git及插件忽略；既定PostgreSQL实际连接值仍待作者提供来源路径，没有猜测或替换。初始化再次执行保留原文件。真实配置、书库和转储不纳入Git候选。

当前不具备真实数据库集成证据：35项用例明确跳过，浏览器与恢复脚本只完成入口/代码核查，不冒称实际通过。没有连接、创建、删除或改名任何数据库；没有重启此前临时集群。作者已收到配置文件路径问题，余下独立代码工作继续完成；此项为真实来源缺失，不能靠自动化推断。

已完成204项旧CLI回归、43项单元/评分检查、前端构建、安装包隔离验证和限定范围独立评审。详细输入、实际结果与未验边界见[验证报告](../evidence/2026-10-19-configuration-ownership/validation.md)和[独立评审](../evidence/2026-10-19-configuration-ownership/review.md)。回退仅还原本轮代码路径，保留私有.env和数据库；不执行库级回滚。

作者本轮已明确授权提交和推送，并安排专项任务测试。本次只交付当前源码候选，保留原required、实际阻塞及待验状态，不因发布重写历史通过证据；同步与结果见[源码交付记录](../evidence/2026-10-19-configuration-ownership/delivery.md)。

```ncc-dev-json
{
  "schema": 1,
  "id": "2026-10-19-configuration-ownership",
  "goal": "保持PostgreSQL原配置，落地项目.env自动加载与正式库/-test双库约束，整理前后端代码归属并合并重复实现",
  "route": "architectural",
  "risk_tags": [
    "architecture"
  ],
  "repo_root": "/Users/xuyun/Documents/ncc-workflow",
  "plugin_root": "/Users/xuyun/Documents/ncc-workflow",
  "branch": "main",
  "base_commit": "4b50690a696a4483dc1fb9f4c68d92b4e0db770f",
  "stage": "D6",
  "next": "按作者授权提交并推送当前源码候选，核对远端SHA；专项测试由作者另行安排，保留35项数据库及浏览器/跨CLI/恢复待验，不擅自改PostgreSQL参数。",
  "blocked": "既定PostgreSQL连接配置来源尚未提供；35项数据库集成、真实浏览器与恢复演练待验。",
  "decisions": [
    {
      "source": "作者本轮要求",
      "scope": "项目.env自动加载；正式库及同连接的正式库-test；明确目录归属、共享复用与单一来源。保留原PostgreSQL参数。"
    },
    {
      "source": "作者本轮明确指令：“提交并推送，我会安排专项任务来测试”",
      "scope": "授权当前源码、文档与既有证据提交并推送main；真实数据库、完整浏览器、跨CLI和恢复验证移交专项任务，保留原状态，不宣称完整验收。"
    }
  ],
  "spec": "docs/designs/engineering/configuration-ownership.md",
  "plan": "docs/designs/engineering/configuration-ownership.md",
  "scope": [
    ".env.example",
    ".zcodeignore",
    "ACKNOWLEDGMENTS.md",
    "AGENTS.md",
    "README.md",
    "alembic.ini",
    "alembic/README",
    "alembic/env.py",
    "alembic/script.py.mako",
    "alembic/versions/070970fe2f0a_private_knowledge_temporal_history_and_.py",
    "alembic/versions/5c4c6e012a90_scoped_credentials_and_history_guards.py",
    "alembic/versions/6d30bb12e441_attachment_access.py",
    "alembic/versions/7e419c2d608b_author_trial_delegation.py",
    "apps/management-web/index.html",
    "apps/management-web/src/api.ts",
    "apps/management-web/src/app/Shell.tsx",
    "apps/management-web/src/app/main.tsx",
    "apps/management-web/src/common.tsx",
    "apps/management-web/src/context.tsx",
    "apps/management-web/src/creative.tsx",
    "apps/management-web/src/editor.tsx",
    "apps/management-web/src/features/administration/AdminPage.tsx",
    "apps/management-web/src/features/administration/components/TrustControls.tsx",
    "apps/management-web/src/features/creation/CreativePage.tsx",
    "apps/management-web/src/features/creation/components/ScoreCard.tsx",
    "apps/management-web/src/features/definitions/DefinitionsPage.tsx",
    "apps/management-web/src/features/exchange/ExchangePage.tsx",
    "apps/management-web/src/features/inbox/InboxPage.tsx",
    "apps/management-web/src/features/jobs/JobsPage.tsx",
    "apps/management-web/src/features/knowledge/MaintenancePage.tsx",
    "apps/management-web/src/features/knowledge/MapPage.tsx",
    "apps/management-web/src/features/knowledge/MaterialsPage.tsx",
    "apps/management-web/src/features/knowledge/RelationsPage.tsx",
    "apps/management-web/src/features/knowledge/components/EntityDrawer.tsx",
    "apps/management-web/src/features/knowledge/components/KnowledgeVisuals.tsx",
    "apps/management-web/src/features/knowledge/components/PropertyFields.tsx",
    "apps/management-web/src/features/knowledge/visuals/GraphCanvas.tsx",
    "apps/management-web/src/features/knowledge/visuals/WorldMap.tsx",
    "apps/management-web/src/features/quality/QualityPage.tsx",
    "apps/management-web/src/features/session/LoginPage.tsx",
    "apps/management-web/src/main.tsx",
    "apps/management-web/src/maintenance.tsx",
    "apps/management-web/src/management.tsx",
    "apps/management-web/src/materials.tsx",
    "apps/management-web/src/shared/WorkspaceContext.tsx",
    "apps/management-web/src/shared/api.ts",
    "apps/management-web/src/shared/components/Feedback.tsx",
    "apps/management-web/src/shared/components/TextEditor.tsx",
    "apps/management-web/src/shared/inputs/ReferenceInput.tsx",
    "apps/management-web/src/shared/jobStages.ts",
    "apps/management-web/src/shared/useCreationPolicy.ts",
    "apps/management-web/src/style.css",
    "apps/management-web/src/styles/base.css",
    "apps/management-web/src/trust.tsx",
    "apps/management-web/src/visuals.tsx",
    "docs/README.md",
    "docs/designs/engineering/configuration-ownership.md",
    "docs/engineering/code-layout.md",
    "docs/engineering/documentation.md",
    "docs/guides/data-console.md",
    "pyproject.toml",
    "scripts/ncc_data.py",
    "scripts/ncclib/__init__.py",
    "scripts/ncclib/database_bridge.py",
    "scripts/ncclib/quality.py",
    "scripts/tests/test_quality.py",
    "src/ncc_data/api.py",
    "src/ncc_data/api/__init__.py",
    "src/ncc_data/api/app.py",
    "src/ncc_data/api/problems.py",
    "src/ncc_data/api/routes/__init__.py",
    "src/ncc_data/api/routes/administration.py",
    "src/ncc_data/api/routes/creation.py",
    "src/ncc_data/api/routes/events.py",
    "src/ncc_data/api/routes/exchange.py",
    "src/ncc_data/api/routes/knowledge.py",
    "src/ncc_data/api/routes/session.py",
    "src/ncc_data/api/routes/system.py",
    "src/ncc_data/api/routes/workspace.py",
    "src/ncc_data/api/schemas.py",
    "src/ncc_data/application/__init__.py",
    "src/ncc_data/application/calibration.py",
    "src/ncc_data/application/knowledge/__init__.py",
    "src/ncc_data/application/knowledge/changes.py",
    "src/ncc_data/application/knowledge/exchange.py",
    "src/ncc_data/application/knowledge/maintenance.py",
    "src/ncc_data/application/knowledge/queries.py",
    "src/ncc_data/application/knowledge/workspace.py",
    "src/ncc_data/application/security.py",
    "src/ncc_data/application/service.py",
    "src/ncc_data/automation.py",
    "src/ncc_data/calibration.py",
    "src/ncc_data/changes.py",
    "src/ncc_data/cli.py",
    "src/ncc_data/cli/__init__.py",
    "src/ncc_data/cli/__main__.py",
    "src/ncc_data/cli/backup.py",
    "src/ncc_data/cli/main.py",
    "src/ncc_data/cli/workspace.py",
    "src/ncc_data/config.py",
    "src/ncc_data/contracts.py",
    "src/ncc_data/creation/__init__.py",
    "src/ncc_data/creation/gateway.py",
    "src/ncc_data/creation/scoring.py",
    "src/ncc_data/creation/worker.py",
    "src/ncc_data/db.py",
    "src/ncc_data/domain/__init__.py",
    "src/ncc_data/domain/contracts.py",
    "src/ncc_data/domain/creation.py",
    "src/ncc_data/domain/definitions.py",
    "src/ncc_data/domain/validation.py",
    "src/ncc_data/errors.py",
    "src/ncc_data/exchange.py",
    "src/ncc_data/maintenance.py",
    "src/ncc_data/models.py",
    "src/ncc_data/persistence/__init__.py",
    "src/ncc_data/persistence/database.py",
    "src/ncc_data/persistence/migrations/README",
    "src/ncc_data/persistence/migrations/alembic.ini",
    "src/ncc_data/persistence/migrations/env.py",
    "src/ncc_data/persistence/migrations/script.py.mako",
    "src/ncc_data/persistence/migrations/versions/070970fe2f0a_private_knowledge_temporal_history_and_.py",
    "src/ncc_data/persistence/migrations/versions/5c4c6e012a90_scoped_credentials_and_history_guards.py",
    "src/ncc_data/persistence/migrations/versions/6d30bb12e441_attachment_access.py",
    "src/ncc_data/persistence/migrations/versions/7e419c2d608b_author_trial_delegation.py",
    "src/ncc_data/persistence/models.py",
    "src/ncc_data/persistence/seeds.py",
    "src/ncc_data/policy.py",
    "src/ncc_data/provider.py",
    "src/ncc_data/quality_core.py",
    "src/ncc_data/queries.py",
    "src/ncc_data/resources/policy.json",
    "src/ncc_data/runtime/__init__.py",
    "src/ncc_data/runtime/settings.py",
    "src/ncc_data/scoring.py",
    "src/ncc_data/security.py",
    "src/ncc_data/seeds.py",
    "src/ncc_data/service.py",
    "src/ncc_data/utils.py",
    "src/ncc_data/validation.py",
    "src/ncc_data/workspace.py",
    "src/ncc_data/workspace_client.py",
    "src/ncc_shared/__init__.py",
    "src/ncc_shared/configuration.py",
    "src/ncc_shared/database.py",
    "src/ncc_shared/errors.py",
    "src/ncc_shared/http.py",
    "src/ncc_shared/paths.py",
    "src/ncc_shared/quality/__init__.py",
    "src/ncc_shared/quality/policy.py",
    "src/ncc_shared/quality/resources/policy.json",
    "src/ncc_shared/quality/scoring.py",
    "src/ncc_shared/serialization.py",
    "src/ncc_shared/workspace.py",
    "tests/backend/__init__.py",
    "tests/backend/conftest.py",
    "tests/backend/run_recovery.py",
    "tests/backend/test_api_automation.py",
    "tests/backend/test_auto_adoption.py",
    "tests/backend/test_automation_boundaries.py",
    "tests/backend/test_core.py",
    "tests/backend/test_exchange_maintenance.py",
    "tests/backend/test_review_regressions.py",
    "tests/backend/test_scoring.py",
    "tests/browser/_bootstrap.py",
    "tests/browser/run_access_browser.py",
    "tests/browser/run_auto_adoption_browser.py",
    "tests/browser/run_browser.py",
    "tests/browser/run_cli_bridge.py",
    "tests/conftest.py",
    "tests/data/__init__.py",
    "tests/data/conftest.py",
    "tests/data/run_recovery.py",
    "tests/data/test_api_automation.py",
    "tests/data/test_auto_adoption.py",
    "tests/data/test_automation_boundaries.py",
    "tests/data/test_core.py",
    "tests/data/test_exchange_maintenance.py",
    "tests/data/test_review_regressions.py",
    "tests/data/test_scoring.py",
    "tests/support/__init__.py",
    "tests/support/runtime.py",
    "tests/unit/test_boundaries.py",
    "tests/unit/test_configuration.py",
    "tests/unit/test_runtime.py",
    "tests/unit/test_workspace.py",
    "tests/web/run_access_browser.py",
    "tests/web/run_auto_adoption_browser.py",
    "tests/web/run_browser.py",
    "tests/web/run_cli_bridge.py"
  ],
  "foreign_changes": {},
  "evidence_paths": [
    "docs/evidence/2026-10-19-configuration-ownership/delivery.md",
    "docs/evidence/2026-10-19-configuration-ownership/docs.log",
    "docs/evidence/2026-10-19-configuration-ownership/frontend.log",
    "docs/evidence/2026-10-19-configuration-ownership/legacy.log",
    "docs/evidence/2026-10-19-configuration-ownership/mechanical.log",
    "docs/evidence/2026-10-19-configuration-ownership/package.log",
    "docs/evidence/2026-10-19-configuration-ownership/plugin.log",
    "docs/evidence/2026-10-19-configuration-ownership/registry.log",
    "docs/evidence/2026-10-19-configuration-ownership/review.md",
    "docs/evidence/2026-10-19-configuration-ownership/unit.log",
    "docs/evidence/2026-10-19-configuration-ownership/validation.md"
  ],
  "candidate": {
    "base_commit": "4b50690a696a4483dc1fb9f4c68d92b4e0db770f",
    "files": [
      {
        "path": ".env.example",
        "type": "file",
        "sha256": "5b08534bc9c79f0d050690c5eda03bcc2658f134cb9b703686ffff49417b05de",
        "executable": false
      },
      {
        "path": ".zcodeignore",
        "type": "file",
        "sha256": "a7faf591ad323bc4424d7752755b5a7950f8eea43f3c043864421e8600f96e8f",
        "executable": false
      },
      {
        "path": "ACKNOWLEDGMENTS.md",
        "type": "file",
        "sha256": "42a168d56780fb4be5239470656a3d483221fb0bb75070cfc238ec56a977a99d",
        "executable": false
      },
      {
        "path": "AGENTS.md",
        "type": "file",
        "sha256": "69c7a4289bb9fe79311536c5397f92b6ca900eaef313cf3e00733d07694105df",
        "executable": false
      },
      {
        "path": "README.md",
        "type": "file",
        "sha256": "ac4c4eaf5b65152af3401e0edea9373f17b90417eb5ffbf541802a762a60346f",
        "executable": false
      },
      {
        "path": "alembic.ini",
        "type": "deleted"
      },
      {
        "path": "alembic/README",
        "type": "deleted"
      },
      {
        "path": "alembic/env.py",
        "type": "deleted"
      },
      {
        "path": "alembic/script.py.mako",
        "type": "deleted"
      },
      {
        "path": "alembic/versions/070970fe2f0a_private_knowledge_temporal_history_and_.py",
        "type": "deleted"
      },
      {
        "path": "alembic/versions/5c4c6e012a90_scoped_credentials_and_history_guards.py",
        "type": "deleted"
      },
      {
        "path": "alembic/versions/6d30bb12e441_attachment_access.py",
        "type": "deleted"
      },
      {
        "path": "alembic/versions/7e419c2d608b_author_trial_delegation.py",
        "type": "deleted"
      },
      {
        "path": "apps/management-web/index.html",
        "type": "file",
        "sha256": "10f30185cff19dc96049c7e04202aef165356932bcd92d4f9edd5982b377b618",
        "executable": false
      },
      {
        "path": "apps/management-web/src/api.ts",
        "type": "deleted"
      },
      {
        "path": "apps/management-web/src/app/Shell.tsx",
        "type": "file",
        "sha256": "8dd370e7d6d045c61becd8ce88eea37b5382e7e46b9c7c327edcb78d2e20859e",
        "executable": false
      },
      {
        "path": "apps/management-web/src/app/main.tsx",
        "type": "file",
        "sha256": "010f132d483de0971e0e539df19fafb746841bd29b290668e8b5b1d9140ffc58",
        "executable": false
      },
      {
        "path": "apps/management-web/src/common.tsx",
        "type": "deleted"
      },
      {
        "path": "apps/management-web/src/context.tsx",
        "type": "deleted"
      },
      {
        "path": "apps/management-web/src/creative.tsx",
        "type": "deleted"
      },
      {
        "path": "apps/management-web/src/editor.tsx",
        "type": "deleted"
      },
      {
        "path": "apps/management-web/src/features/administration/AdminPage.tsx",
        "type": "file",
        "sha256": "ed17497fa87bd98240999b1083e58683b550dfda2b52b5e97212455c5530c860",
        "executable": false
      },
      {
        "path": "apps/management-web/src/features/administration/components/TrustControls.tsx",
        "type": "file",
        "sha256": "922293491cffd00f6b1d288380012de06996711c8c8e04d9afba5b481e3a1d93",
        "executable": false
      },
      {
        "path": "apps/management-web/src/features/creation/CreativePage.tsx",
        "type": "file",
        "sha256": "d0332560000c97dcccbeaf7b88b8eb4436f4c444d438f2e2e98a7fd1ed20f300",
        "executable": false
      },
      {
        "path": "apps/management-web/src/features/creation/components/ScoreCard.tsx",
        "type": "file",
        "sha256": "259a69a35e88bbb2222679d7c0902f2c368d4b5bfd18e9745c9dfcad82fe7a52",
        "executable": false
      },
      {
        "path": "apps/management-web/src/features/definitions/DefinitionsPage.tsx",
        "type": "file",
        "sha256": "db2fa0bac4db2b4ac556c01d07a56f0e1a071cdf47b2b657fdc35141ac7c72e5",
        "executable": false
      },
      {
        "path": "apps/management-web/src/features/exchange/ExchangePage.tsx",
        "type": "file",
        "sha256": "10ef8bf971b7915aad47fdfc6a556d676483e098b1eac752e629070c7e462376",
        "executable": false
      },
      {
        "path": "apps/management-web/src/features/inbox/InboxPage.tsx",
        "type": "file",
        "sha256": "fd4b848b4fcd4ef3deb0b57d569e17d029821dd1d7190146f6efc8639a78c7bd",
        "executable": false
      },
      {
        "path": "apps/management-web/src/features/jobs/JobsPage.tsx",
        "type": "file",
        "sha256": "fe515975470cf45328748d3bcd1cf92fef2feffd421e109937388389191254e5",
        "executable": false
      },
      {
        "path": "apps/management-web/src/features/knowledge/MaintenancePage.tsx",
        "type": "file",
        "sha256": "771445e2895f793a1a3185c833090acd879c670655a51c09912a227d516b9e08",
        "executable": false
      },
      {
        "path": "apps/management-web/src/features/knowledge/MapPage.tsx",
        "type": "file",
        "sha256": "7310143a9d8aa841bc17efcb042a94a70fcd134d85b147059391ca92d0409b2a",
        "executable": false
      },
      {
        "path": "apps/management-web/src/features/knowledge/MaterialsPage.tsx",
        "type": "file",
        "sha256": "422933650578362969952239ecfbc55e4261aef2a59d3d6568eec0635fe4044e",
        "executable": false
      },
      {
        "path": "apps/management-web/src/features/knowledge/RelationsPage.tsx",
        "type": "file",
        "sha256": "304c7b34f8226d351b623397fe333656af0f02e28ceb71f457b53889638b70e2",
        "executable": false
      },
      {
        "path": "apps/management-web/src/features/knowledge/components/EntityDrawer.tsx",
        "type": "file",
        "sha256": "688557e562bb24dd50a7d72ac999a187119eff1260faf61c1d33f2bff6869d7b",
        "executable": false
      },
      {
        "path": "apps/management-web/src/features/knowledge/components/KnowledgeVisuals.tsx",
        "type": "file",
        "sha256": "e99195355527695928a405cce2d46854913e128b284764714e11f001def78027",
        "executable": false
      },
      {
        "path": "apps/management-web/src/features/knowledge/components/PropertyFields.tsx",
        "type": "file",
        "sha256": "cc88cb2afb24dc4b15e636ba6cd6333e8ecaa8a716458dcc4849bd8663ca50b3",
        "executable": false
      },
      {
        "path": "apps/management-web/src/features/knowledge/visuals/GraphCanvas.tsx",
        "type": "file",
        "sha256": "91e505ffebd0bf7cb01eb58667c1abfb78b369ee1d12dfa312897f736e6a22ba",
        "executable": false
      },
      {
        "path": "apps/management-web/src/features/knowledge/visuals/WorldMap.tsx",
        "type": "file",
        "sha256": "b8b5b6e4587b62344279c902c67fdf0d85d32aead38e5cfdcc6bbe5db4371d22",
        "executable": false
      },
      {
        "path": "apps/management-web/src/features/quality/QualityPage.tsx",
        "type": "file",
        "sha256": "e97c2adbb4176919eaf7f10277a846d64560955c40ec8a8a51f8b5143a14499b",
        "executable": false
      },
      {
        "path": "apps/management-web/src/features/session/LoginPage.tsx",
        "type": "file",
        "sha256": "05d4c2e7e60589f7b74c3bd1da688486eb65ba7f80cee25b82204170595b0e6b",
        "executable": false
      },
      {
        "path": "apps/management-web/src/main.tsx",
        "type": "deleted"
      },
      {
        "path": "apps/management-web/src/maintenance.tsx",
        "type": "deleted"
      },
      {
        "path": "apps/management-web/src/management.tsx",
        "type": "deleted"
      },
      {
        "path": "apps/management-web/src/materials.tsx",
        "type": "deleted"
      },
      {
        "path": "apps/management-web/src/shared/WorkspaceContext.tsx",
        "type": "file",
        "sha256": "8d611dea5ea84953050418f623c813952e98f7fb14f4e493841b79264db3f9b0",
        "executable": false
      },
      {
        "path": "apps/management-web/src/shared/api.ts",
        "type": "file",
        "sha256": "7fbabbf22f84e8625e68ba28a84f5624488889677fc1c0f443712bee61c0b230",
        "executable": false
      },
      {
        "path": "apps/management-web/src/shared/components/Feedback.tsx",
        "type": "file",
        "sha256": "7558e1f8cba733dfe05ead426249bf85dae8054b5a6aa81e39e904953a8d06eb",
        "executable": false
      },
      {
        "path": "apps/management-web/src/shared/components/TextEditor.tsx",
        "type": "file",
        "sha256": "7148fc1c5fc9e3715418324c703d92b1d8f4b135e204a7a6df5c85f01e700a75",
        "executable": false
      },
      {
        "path": "apps/management-web/src/shared/inputs/ReferenceInput.tsx",
        "type": "file",
        "sha256": "fe79f20c139d6a5274cd4381ceeddf3b579806b0e95ef95fd4135f7dfcc859c9",
        "executable": false
      },
      {
        "path": "apps/management-web/src/shared/jobStages.ts",
        "type": "file",
        "sha256": "461a18871a2e1a1fe73f3844d0eb0d8ebaa6253638a09736d2af43fc2a6f6cb1",
        "executable": false
      },
      {
        "path": "apps/management-web/src/shared/useCreationPolicy.ts",
        "type": "file",
        "sha256": "155c65953bfe72576f4e9a9368a4429c4beea5df39ec2c571a887a9fd15fdc8e",
        "executable": false
      },
      {
        "path": "apps/management-web/src/style.css",
        "type": "deleted"
      },
      {
        "path": "apps/management-web/src/styles/base.css",
        "type": "file",
        "sha256": "a13f9ff453f39e14cb0f73eb8ba8f9526a961eea31a11f5ab5d7759f551cf0d1",
        "executable": false
      },
      {
        "path": "apps/management-web/src/trust.tsx",
        "type": "deleted"
      },
      {
        "path": "apps/management-web/src/visuals.tsx",
        "type": "deleted"
      },
      {
        "path": "docs/README.md",
        "type": "file",
        "sha256": "a95569ed0f2dd8cd556696c2ea8e3baefe59edc060569d172954f8e0bada2a9d",
        "executable": false
      },
      {
        "path": "docs/designs/engineering/configuration-ownership.md",
        "type": "file",
        "sha256": "5e62ac7d65f02de491cf1f1a93bcc30068d5107e7c53afe78531877c5baab9c6",
        "executable": false
      },
      {
        "path": "docs/engineering/code-layout.md",
        "type": "file",
        "sha256": "8169e44334c16b2cdb4363b82ccf246d9ea0d30eac8c7be6ef2d3af8be327e83",
        "executable": false
      },
      {
        "path": "docs/engineering/documentation.md",
        "type": "file",
        "sha256": "da9df93c534eccb21420b0a19f20669003f4f9e245a867a8afc102ff502a95d3",
        "executable": false
      },
      {
        "path": "docs/guides/data-console.md",
        "type": "file",
        "sha256": "d06b8a8b148f52f3ee4dfa7ca035fd1b30c7d4a037969fe847d82033ccd395e5",
        "executable": false
      },
      {
        "path": "pyproject.toml",
        "type": "file",
        "sha256": "2ce3c5443a85864c2604756408af21479aa17fdef087c2c2dbd5e3655202a938",
        "executable": false
      },
      {
        "path": "scripts/ncc_data.py",
        "type": "file",
        "sha256": "b15c714123684fdb0bfb4d1ea9a7f05e8987eb89fb8714864424a2f208bc791a",
        "executable": false
      },
      {
        "path": "scripts/ncclib/__init__.py",
        "type": "file",
        "sha256": "a8efe08adeb47e3697ddce153fb227a60d240b01133ce01b4f0a36f0883318f2",
        "executable": false
      },
      {
        "path": "scripts/ncclib/database_bridge.py",
        "type": "file",
        "sha256": "ab2b4f6d1dc411f80ce2b77d3b6ab8090d36b20525c25a2adbe1f906092366f5",
        "executable": false
      },
      {
        "path": "scripts/ncclib/quality.py",
        "type": "file",
        "sha256": "3c4d024b2299fa670b724245ab8f0373f9753bcb7a42c3febc00c1fd92c0d3cf",
        "executable": false
      },
      {
        "path": "scripts/tests/test_quality.py",
        "type": "file",
        "sha256": "7b965b56f595ebaa09b685c537a8190748f09c70f5dcd5f6167bb4848804af1c",
        "executable": false
      },
      {
        "path": "src/ncc_data/api.py",
        "type": "deleted"
      },
      {
        "path": "src/ncc_data/api/__init__.py",
        "type": "file",
        "sha256": "11960d94ebc8f0b9c19726715551e634893d6cba92f4d010fbffa9611a25a5db",
        "executable": false
      },
      {
        "path": "src/ncc_data/api/app.py",
        "type": "file",
        "sha256": "eea1625108789874f4be368269971125128b1687aeacc0d2b13615322daa613a",
        "executable": false
      },
      {
        "path": "src/ncc_data/api/problems.py",
        "type": "file",
        "sha256": "750a5dbd62c3a48221e048334e735132b6ef96e55a5254540e07d1939bada888",
        "executable": false
      },
      {
        "path": "src/ncc_data/api/routes/__init__.py",
        "type": "file",
        "sha256": "646870e44d18a8d51d912a6ec79f4264ef3649ecb429089c0dd0a16a5c81b308",
        "executable": false
      },
      {
        "path": "src/ncc_data/api/routes/administration.py",
        "type": "file",
        "sha256": "a7e71e3f3e05e4715cb7ac8aa659584c993113146bcad4ce2bde2809bcfd648b",
        "executable": false
      },
      {
        "path": "src/ncc_data/api/routes/creation.py",
        "type": "file",
        "sha256": "66add675d606bccc5ae82161ac34e3287edecbd61291a751c0bdca61578d08dc",
        "executable": false
      },
      {
        "path": "src/ncc_data/api/routes/events.py",
        "type": "file",
        "sha256": "81f36d204ffd37bc12335ad712c3f988da25e3fa4ab02c73c41fbb067700d63f",
        "executable": false
      },
      {
        "path": "src/ncc_data/api/routes/exchange.py",
        "type": "file",
        "sha256": "e89f4babfeb8bbbb3a338257e9d46da19016053486a6578fe61b1b2d404caa24",
        "executable": false
      },
      {
        "path": "src/ncc_data/api/routes/knowledge.py",
        "type": "file",
        "sha256": "3d37d9a144453abd27e810e574f18e2c834ca305773afdfe8a879f870a66fd0a",
        "executable": false
      },
      {
        "path": "src/ncc_data/api/routes/session.py",
        "type": "file",
        "sha256": "42b609ed1b0dbf5881122004f307153d724487ff88fcd09723f92c5b7ab1835f",
        "executable": false
      },
      {
        "path": "src/ncc_data/api/routes/system.py",
        "type": "file",
        "sha256": "65298f0b5e1f9d231d764d8565c5c58461f65ac11d397e0a33564463e1c4ca46",
        "executable": false
      },
      {
        "path": "src/ncc_data/api/routes/workspace.py",
        "type": "file",
        "sha256": "76b9bd460b04f499da65d4b761c8819ade62c4d69ab10cd7e50b62ad620a0e30",
        "executable": false
      },
      {
        "path": "src/ncc_data/api/schemas.py",
        "type": "file",
        "sha256": "f3364c93744655e9981617072fc35181eb8d2ea7db00c37bfff534bffdabb748",
        "executable": false
      },
      {
        "path": "src/ncc_data/application/__init__.py",
        "type": "file",
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "executable": false
      },
      {
        "path": "src/ncc_data/application/calibration.py",
        "type": "file",
        "sha256": "060250e831612562aebabbfa8dfe533ddd9773008f7111ee01bc97d94662020d",
        "executable": false
      },
      {
        "path": "src/ncc_data/application/knowledge/__init__.py",
        "type": "file",
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "executable": false
      },
      {
        "path": "src/ncc_data/application/knowledge/changes.py",
        "type": "file",
        "sha256": "b05b2764f693f14dc27f0527552751ebad74f34fa8d92c52498e9642a6a8632e",
        "executable": false
      },
      {
        "path": "src/ncc_data/application/knowledge/exchange.py",
        "type": "file",
        "sha256": "e14b176be64590475909e6f505f3bd7686112c22c24158f6c2c03af73cffe953",
        "executable": false
      },
      {
        "path": "src/ncc_data/application/knowledge/maintenance.py",
        "type": "file",
        "sha256": "5447fbf1e2bd0a44f413e4c391c97677b10bd956101510cbbb3b20fd2788d602",
        "executable": false
      },
      {
        "path": "src/ncc_data/application/knowledge/queries.py",
        "type": "file",
        "sha256": "0bb31946e9d386dad77e209427963b2664f1ddce337ec8f06e054fee8967bba5",
        "executable": false
      },
      {
        "path": "src/ncc_data/application/knowledge/workspace.py",
        "type": "file",
        "sha256": "93a78a703f71899b75f1bdea096eb3a19dacb3f1798818dd6167fb5b12696cb1",
        "executable": false
      },
      {
        "path": "src/ncc_data/application/security.py",
        "type": "file",
        "sha256": "1d4d6c71c297353323f92318a4cab1e984877cdf6099ebb54bd08e795aadbfcb",
        "executable": false
      },
      {
        "path": "src/ncc_data/application/service.py",
        "type": "file",
        "sha256": "82f185aacf4c649fcefe6b45e2c4c97ea311bc659dba37a0ca091057f7844976",
        "executable": false
      },
      {
        "path": "src/ncc_data/automation.py",
        "type": "deleted"
      },
      {
        "path": "src/ncc_data/calibration.py",
        "type": "deleted"
      },
      {
        "path": "src/ncc_data/changes.py",
        "type": "deleted"
      },
      {
        "path": "src/ncc_data/cli.py",
        "type": "deleted"
      },
      {
        "path": "src/ncc_data/cli/__init__.py",
        "type": "file",
        "sha256": "372c8513f88a1ae19c5272444a832d01a5c5bd468ddc04b9eb7d58b0286adfa4",
        "executable": false
      },
      {
        "path": "src/ncc_data/cli/__main__.py",
        "type": "file",
        "sha256": "bc143cdb7df8917d3a2260db1653c582205188b2229f0364df3f0a86cea177be",
        "executable": false
      },
      {
        "path": "src/ncc_data/cli/backup.py",
        "type": "file",
        "sha256": "6dec2d2366d5270f2251cc810036014aa1967fce6253f51314d43b8541f64430",
        "executable": false
      },
      {
        "path": "src/ncc_data/cli/main.py",
        "type": "file",
        "sha256": "cae66f47b0e9ff0b6c3b3155685d924ae306a20b89db165f85f3f03c68f57f7e",
        "executable": false
      },
      {
        "path": "src/ncc_data/cli/workspace.py",
        "type": "file",
        "sha256": "011e6879164ec929f3887032835849ce225a05bfb7794ced4c4e5c665ebc5535",
        "executable": false
      },
      {
        "path": "src/ncc_data/config.py",
        "type": "deleted"
      },
      {
        "path": "src/ncc_data/contracts.py",
        "type": "deleted"
      },
      {
        "path": "src/ncc_data/creation/__init__.py",
        "type": "file",
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "executable": false
      },
      {
        "path": "src/ncc_data/creation/gateway.py",
        "type": "file",
        "sha256": "d232fec6ec8ac96a8edb59d85cc704952b71f0d43bf5f7084284fd1461c1bcb4",
        "executable": false
      },
      {
        "path": "src/ncc_data/creation/scoring.py",
        "type": "file",
        "sha256": "d57a4328513b8e2566d343b6e11f6be47936ef7587f0a90d849089684fa41aa3",
        "executable": false
      },
      {
        "path": "src/ncc_data/creation/worker.py",
        "type": "file",
        "sha256": "53e8a545076bd6805dd8132156d0c854f982a3f55399e9a946f36d6d658d6816",
        "executable": false
      },
      {
        "path": "src/ncc_data/db.py",
        "type": "deleted"
      },
      {
        "path": "src/ncc_data/domain/__init__.py",
        "type": "file",
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "executable": false
      },
      {
        "path": "src/ncc_data/domain/contracts.py",
        "type": "file",
        "sha256": "10f8fedc7024ea6175f8585a938afb43c41d3f97f7ed8edfc62973aad8ef1b3f",
        "executable": false
      },
      {
        "path": "src/ncc_data/domain/creation.py",
        "type": "file",
        "sha256": "7ea62e3b7365f9ecf80b3934501056d628b12b683307b8e274a1300629014d27",
        "executable": false
      },
      {
        "path": "src/ncc_data/domain/definitions.py",
        "type": "file",
        "sha256": "d30cdebb0cd062b07fc93cd48cf80bac5016978150011b514de9de97fd535011",
        "executable": false
      },
      {
        "path": "src/ncc_data/domain/validation.py",
        "type": "file",
        "sha256": "9c6042e0fc73c9284e859ddeba776768fee173e3b54889857cd208c684da6bb3",
        "executable": false
      },
      {
        "path": "src/ncc_data/errors.py",
        "type": "deleted"
      },
      {
        "path": "src/ncc_data/exchange.py",
        "type": "deleted"
      },
      {
        "path": "src/ncc_data/maintenance.py",
        "type": "deleted"
      },
      {
        "path": "src/ncc_data/models.py",
        "type": "deleted"
      },
      {
        "path": "src/ncc_data/persistence/__init__.py",
        "type": "file",
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "executable": false
      },
      {
        "path": "src/ncc_data/persistence/database.py",
        "type": "file",
        "sha256": "c1d171609b06f3d6729126b13a68e5a961bfe75f1e5d8ba7bea9e63bc20acd5d",
        "executable": false
      },
      {
        "path": "src/ncc_data/persistence/migrations/README",
        "type": "file",
        "sha256": "21256d00ebeabca93fe5384ce62a0913e94c92f7fd21b92715415553fbcf99ae",
        "executable": false
      },
      {
        "path": "src/ncc_data/persistence/migrations/alembic.ini",
        "type": "file",
        "sha256": "d79d0a7e65e1a39f82a608b63f99759aa3b8a2ed9ba2b7135cb137e4bbf67cf2",
        "executable": false
      },
      {
        "path": "src/ncc_data/persistence/migrations/env.py",
        "type": "file",
        "sha256": "f394479f37bb146a408f0f30b3f81912307fb1332e31464c9f3801b45e1f048a",
        "executable": false
      },
      {
        "path": "src/ncc_data/persistence/migrations/script.py.mako",
        "type": "file",
        "sha256": "d38920781b4d31ae1c0a71bc09f41c2ade8feab9e5a087e3f30cb4bbf0c1c9d3",
        "executable": false
      },
      {
        "path": "src/ncc_data/persistence/migrations/versions/070970fe2f0a_private_knowledge_temporal_history_and_.py",
        "type": "file",
        "sha256": "3c692659530625a8af5145f9ae04dff5748922f44a3610dc6718eab9cb0d0a72",
        "executable": false
      },
      {
        "path": "src/ncc_data/persistence/migrations/versions/5c4c6e012a90_scoped_credentials_and_history_guards.py",
        "type": "file",
        "sha256": "e6f02cfb5299b3e8be8a2221dca52de1e28fc4c6fc61f8d4ed141d71f9d49f11",
        "executable": false
      },
      {
        "path": "src/ncc_data/persistence/migrations/versions/6d30bb12e441_attachment_access.py",
        "type": "file",
        "sha256": "920af50067773d644ad95d1575151fed6f69371a873e17162fb05eca6764666b",
        "executable": false
      },
      {
        "path": "src/ncc_data/persistence/migrations/versions/7e419c2d608b_author_trial_delegation.py",
        "type": "file",
        "sha256": "acb147a5b4de8bdda3c5a4729cdd8d2f0819723f52818b2952f3455e685dc769",
        "executable": false
      },
      {
        "path": "src/ncc_data/persistence/models.py",
        "type": "file",
        "sha256": "8235ef8f9a5fa025fa7a90445a3539edd3acb07d6b21c5f7af678828fbd315f8",
        "executable": false
      },
      {
        "path": "src/ncc_data/persistence/seeds.py",
        "type": "file",
        "sha256": "0132a53724f5e2df1c4f20489034c769b5b2d60f82a467bb577aa27df668fbb7",
        "executable": false
      },
      {
        "path": "src/ncc_data/policy.py",
        "type": "deleted"
      },
      {
        "path": "src/ncc_data/provider.py",
        "type": "deleted"
      },
      {
        "path": "src/ncc_data/quality_core.py",
        "type": "deleted"
      },
      {
        "path": "src/ncc_data/queries.py",
        "type": "deleted"
      },
      {
        "path": "src/ncc_data/resources/policy.json",
        "type": "deleted"
      },
      {
        "path": "src/ncc_data/runtime/__init__.py",
        "type": "file",
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "executable": false
      },
      {
        "path": "src/ncc_data/runtime/settings.py",
        "type": "file",
        "sha256": "2a4b086356a2e9ac489a402b8323276e1b96a286a724c0433a6819fbd09f7aef",
        "executable": false
      },
      {
        "path": "src/ncc_data/scoring.py",
        "type": "deleted"
      },
      {
        "path": "src/ncc_data/security.py",
        "type": "deleted"
      },
      {
        "path": "src/ncc_data/seeds.py",
        "type": "deleted"
      },
      {
        "path": "src/ncc_data/service.py",
        "type": "deleted"
      },
      {
        "path": "src/ncc_data/utils.py",
        "type": "deleted"
      },
      {
        "path": "src/ncc_data/validation.py",
        "type": "deleted"
      },
      {
        "path": "src/ncc_data/workspace.py",
        "type": "deleted"
      },
      {
        "path": "src/ncc_data/workspace_client.py",
        "type": "deleted"
      },
      {
        "path": "src/ncc_shared/__init__.py",
        "type": "file",
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "executable": false
      },
      {
        "path": "src/ncc_shared/configuration.py",
        "type": "file",
        "sha256": "753bac891225be15431e06acecc40a802a95603eaf1c9ecea0f015195ef5405b",
        "executable": false
      },
      {
        "path": "src/ncc_shared/database.py",
        "type": "file",
        "sha256": "890b606868b20de1f8ef6db3307d60b3fb012e76bec47477fef1b1f84d270160",
        "executable": false
      },
      {
        "path": "src/ncc_shared/errors.py",
        "type": "file",
        "sha256": "987a2753131846fc08482d63de1d141434336b09bd94aadea18c9646719a6ec9",
        "executable": false
      },
      {
        "path": "src/ncc_shared/http.py",
        "type": "file",
        "sha256": "a358fed7939ffa4a66894a846ee260bcf7f60d2e06e76ff22b4ed23b9c4a2dca",
        "executable": false
      },
      {
        "path": "src/ncc_shared/paths.py",
        "type": "file",
        "sha256": "12d447d1993bca04e78d6e736dfed6c7a22a3f92e7bafa6c663d1a0caec8ea68",
        "executable": false
      },
      {
        "path": "src/ncc_shared/quality/__init__.py",
        "type": "file",
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "executable": false
      },
      {
        "path": "src/ncc_shared/quality/policy.py",
        "type": "file",
        "sha256": "09b1f41e43c5565170b91955eef248377042f4b2a6529be7f7d1e7980cbf89e9",
        "executable": false
      },
      {
        "path": "src/ncc_shared/quality/resources/policy.json",
        "type": "file",
        "sha256": "96d46b8c9cbce6cee972a580cbf3986406ddb994ab6bcae2489999c2730272d5",
        "executable": false
      },
      {
        "path": "src/ncc_shared/quality/scoring.py",
        "type": "file",
        "sha256": "2d97a55c3e24bfaa51d3bfce78d9c931b6a1385088ac33f6e72bf0059734a07d",
        "executable": false
      },
      {
        "path": "src/ncc_shared/serialization.py",
        "type": "file",
        "sha256": "9141de40be4c4b30e1340876a2968c26e243444ad6eeaf83e7a72729d3a64cfe",
        "executable": false
      },
      {
        "path": "src/ncc_shared/workspace.py",
        "type": "file",
        "sha256": "99a7f7c74191bad77b817fbb0f1f09990b812f30e98a93012b016df18f25ed35",
        "executable": false
      },
      {
        "path": "tests/backend/__init__.py",
        "type": "file",
        "sha256": "94c960d65fa0871eeb40f78af44a719efd821c8d8652eefdce9c4dce21d20c75",
        "executable": false
      },
      {
        "path": "tests/backend/conftest.py",
        "type": "file",
        "sha256": "daed0377c6a4bf7b75140e33e87e980e586d019604386387fc4b49fef5fb39f4",
        "executable": false
      },
      {
        "path": "tests/backend/run_recovery.py",
        "type": "file",
        "sha256": "b89df5a93c39dce4cdda9cfa84d104430243b7e9be25afbc3bc05d4a52892bd4",
        "executable": false
      },
      {
        "path": "tests/backend/test_api_automation.py",
        "type": "file",
        "sha256": "63ef3e63c4ce8ecea9642db00afa967262a7ee08a31f5a0c8bdd99dcd238766a",
        "executable": false
      },
      {
        "path": "tests/backend/test_auto_adoption.py",
        "type": "file",
        "sha256": "bf0f6fe4ec1100b9bd4275c21fe00d93511667d679af1f21d1e540c3fe2b5cc0",
        "executable": false
      },
      {
        "path": "tests/backend/test_automation_boundaries.py",
        "type": "file",
        "sha256": "fe670f335e5246bced708bef7561af645ebc1791395aacc783fc5372e60c9cdd",
        "executable": false
      },
      {
        "path": "tests/backend/test_core.py",
        "type": "file",
        "sha256": "4f389d20968a60256832ed1e78c3a73c69917c76a604cbcd9c706327b2701368",
        "executable": false
      },
      {
        "path": "tests/backend/test_exchange_maintenance.py",
        "type": "file",
        "sha256": "febf8cb9f613b09524388fcf8ed12fdb0d322c458c25cbccddd4473525ca9bdf",
        "executable": false
      },
      {
        "path": "tests/backend/test_review_regressions.py",
        "type": "file",
        "sha256": "17630a7916f15c5f1e1d28fd082587e9a6c69726a65e7a172251a60299b0cd5e",
        "executable": false
      },
      {
        "path": "tests/backend/test_scoring.py",
        "type": "file",
        "sha256": "a97df959d605a05131acc05d75d37233ad642f819e1d520e4e978e12ad3e1c19",
        "executable": false
      },
      {
        "path": "tests/browser/_bootstrap.py",
        "type": "file",
        "sha256": "6558373f0df55792038cbf4873fbd6dda7c5f44fe90cc4f1706e390efa78d46c",
        "executable": false
      },
      {
        "path": "tests/browser/run_access_browser.py",
        "type": "file",
        "sha256": "81dbff468956fb1a356b51cb3c78e454772331dfc5a435bf1cc2c38180af90af",
        "executable": false
      },
      {
        "path": "tests/browser/run_auto_adoption_browser.py",
        "type": "file",
        "sha256": "aeeee7cc118d3ffd7b28fbb6e44049a5f21da61c7bc5027a3640020701d8ee07",
        "executable": false
      },
      {
        "path": "tests/browser/run_browser.py",
        "type": "file",
        "sha256": "c37c211d37456ef3f08ce5e4519cab9d1ed70b2f34e5ab28a63012ef4b1567d9",
        "executable": false
      },
      {
        "path": "tests/browser/run_cli_bridge.py",
        "type": "file",
        "sha256": "9ad045a0e22f098d10425a0a590d0dd6663b147dba6779cc30334817469140cd",
        "executable": false
      },
      {
        "path": "tests/conftest.py",
        "type": "file",
        "sha256": "77d06aeb6a0ae679d49ab85fe6bd3aca1b71314d9dda63bab4eac6d2d39b78ac",
        "executable": false
      },
      {
        "path": "tests/data/__init__.py",
        "type": "deleted"
      },
      {
        "path": "tests/data/conftest.py",
        "type": "deleted"
      },
      {
        "path": "tests/data/run_recovery.py",
        "type": "deleted"
      },
      {
        "path": "tests/data/test_api_automation.py",
        "type": "deleted"
      },
      {
        "path": "tests/data/test_auto_adoption.py",
        "type": "deleted"
      },
      {
        "path": "tests/data/test_automation_boundaries.py",
        "type": "deleted"
      },
      {
        "path": "tests/data/test_core.py",
        "type": "deleted"
      },
      {
        "path": "tests/data/test_exchange_maintenance.py",
        "type": "deleted"
      },
      {
        "path": "tests/data/test_review_regressions.py",
        "type": "deleted"
      },
      {
        "path": "tests/data/test_scoring.py",
        "type": "deleted"
      },
      {
        "path": "tests/support/__init__.py",
        "type": "file",
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "executable": false
      },
      {
        "path": "tests/support/runtime.py",
        "type": "file",
        "sha256": "37a75b06cf8c8a553db1c52748d430eae68ddb88788ec63d3052532b19b8b292",
        "executable": false
      },
      {
        "path": "tests/unit/test_boundaries.py",
        "type": "file",
        "sha256": "dde8a4771b3aadfda659b46ecd96e864b4f86b34e93e02752b19d6d3344cc858",
        "executable": false
      },
      {
        "path": "tests/unit/test_configuration.py",
        "type": "file",
        "sha256": "a981f9a2ef06f485ff3f84866088d106a15ac1e71ea03ec6f66728c6e78146c6",
        "executable": false
      },
      {
        "path": "tests/unit/test_runtime.py",
        "type": "file",
        "sha256": "b25fac92bb96b2769cd5e4c1534f44a747cee851f5ceaaae16073e36c60f8386",
        "executable": false
      },
      {
        "path": "tests/unit/test_workspace.py",
        "type": "file",
        "sha256": "837247ec5f99c0caf45d6758ef8b5f3a70ccf7febc36819cd16ba097edad003a",
        "executable": false
      },
      {
        "path": "tests/web/run_access_browser.py",
        "type": "deleted"
      },
      {
        "path": "tests/web/run_auto_adoption_browser.py",
        "type": "deleted"
      },
      {
        "path": "tests/web/run_browser.py",
        "type": "deleted"
      },
      {
        "path": "tests/web/run_cli_bridge.py",
        "type": "deleted"
      }
    ],
    "fingerprint": "19f5281e2c08dae8300800d76733f250491ec1e9805c1db8573d245555a6c9b1"
  },
  "required": [
    "unit",
    "postgres",
    "web",
    "plugin",
    "docs",
    "review"
  ],
  "evidence": [
    {
      "candidate": "19f5281e2c08dae8300800d76733f250491ec1e9805c1db8573d245555a6c9b1",
      "environment": "macOS；旧CLI Python3.9.6，后端Python3.12.14，Node v25.9.0；没有真实数据库连接或模型调用",
      "id": "regression",
      "kind": "unit",
      "status": "passed",
      "command": "python3 -m unittest discover -s scripts/tests -t scripts -p 'test_*.py'；.venv/bin/pytest tests/unit tests/backend -q",
      "exit_code": 0,
      "summary": "204项旧CLI回归及43项无数据库/评分检查通过，35项数据库用例跳过",
      "coverage": "配置、连接派生、路径、客户端、profile、测试清理与原CLI兼容",
      "report": "docs/evidence/2026-10-19-configuration-ownership/validation.md",
      "report_sha256": "3c407670652ca4633e7285339152144d4cf38b6be3e4721d8672db0686fc4cc6"
    },
    {
      "candidate": "19f5281e2c08dae8300800d76733f250491ec1e9805c1db8573d245555a6c9b1",
      "environment": "macOS；旧CLI Python3.9.6，后端Python3.12.14，Node v25.9.0；没有真实数据库连接或模型调用",
      "id": "postgres-pending",
      "kind": "postgres",
      "status": "blocked",
      "command": ".venv/bin/pytest tests/unit tests/backend -q",
      "exit_code": 0,
      "summary": "35项依赖真实PostgreSQL的用例明确跳过；未建立、删除或连接其他库",
      "coverage": "配置来源缺失，在线迁移、事务、权限、恢复未验",
      "report": "docs/evidence/2026-10-19-configuration-ownership/validation.md",
      "report_sha256": "3c407670652ca4633e7285339152144d4cf38b6be3e4721d8672db0686fc4cc6"
    },
    {
      "candidate": "19f5281e2c08dae8300800d76733f250491ec1e9805c1db8573d245555a6c9b1",
      "environment": "macOS；旧CLI Python3.9.6，后端Python3.12.14，Node v25.9.0；没有真实数据库连接或模型调用",
      "id": "frontend",
      "kind": "web",
      "status": "blocked",
      "command": "npm --prefix apps/management-web run build；4个浏览器验收入口导入",
      "exit_code": null,
      "summary": "TypeScript/Vite构建及入口导入通过；真实浏览器交互与跨CLI往返待唯一-test连接后验证",
      "coverage": "静态前端及拆分接线；不证明页面完整运行",
      "report": "docs/evidence/2026-10-19-configuration-ownership/validation.md",
      "report_sha256": "3c407670652ca4633e7285339152144d4cf38b6be3e4721d8672db0686fc4cc6"
    },
    {
      "candidate": "19f5281e2c08dae8300800d76733f250491ec1e9805c1db8573d245555a6c9b1",
      "environment": "macOS；旧CLI Python3.9.6，后端Python3.12.14，Node v25.9.0；没有真实数据库连接或模型调用",
      "id": "plugin",
      "kind": "plugin",
      "status": "passed",
      "command": "python3 scripts/dev/check_plugin.py -v",
      "exit_code": 0,
      "summary": "静态接线、链接和预算通过",
      "coverage": "项目级入口静态检查；五端新会话仍未验证",
      "report": "docs/evidence/2026-10-19-configuration-ownership/validation.md",
      "report_sha256": "3c407670652ca4633e7285339152144d4cf38b6be3e4721d8672db0686fc4cc6"
    },
    {
      "candidate": "19f5281e2c08dae8300800d76733f250491ec1e9805c1db8573d245555a6c9b1",
      "environment": "macOS；旧CLI Python3.9.6，后端Python3.12.14，Node v25.9.0；没有真实数据库连接或模型调用",
      "id": "documentation",
      "kind": "docs",
      "status": "passed",
      "command": "python3 scripts/dev/build_docs.py --check；python3 scripts/dev/build_registry.py --check；git diff --check",
      "exit_code": 0,
      "summary": "生成内容与链接一致，差异格式通过",
      "coverage": "活动指南、目录规范、生成视图及项目说明",
      "report": "docs/evidence/2026-10-19-configuration-ownership/validation.md",
      "report_sha256": "3c407670652ca4633e7285339152144d4cf38b6be3e4721d8672db0686fc4cc6"
    },
    {
      "candidate": "19f5281e2c08dae8300800d76733f250491ec1e9805c1db8573d245555a6c9b1",
      "environment": "macOS；旧CLI Python3.9.6，后端Python3.12.14，Node v25.9.0；没有真实数据库连接或模型调用",
      "id": "package",
      "kind": "package",
      "status": "passed",
      "command": "uv build --wheel；.venv/bin/python /private/tmp/ncc-ownership-package-check.py",
      "exit_code": 0,
      "summary": "隔离wheel初始化、资源与4个迁移发现通过；OpenAPI相同、历史迁移及策略字节未改",
      "coverage": "不加载实际.env、不在线迁移、不启动模型",
      "report": "docs/evidence/2026-10-19-configuration-ownership/validation.md",
      "report_sha256": "3c407670652ca4633e7285339152144d4cf38b6be3e4721d8672db0686fc4cc6"
    },
    {
      "candidate": "19f5281e2c08dae8300800d76733f250491ec1e9805c1db8573d245555a6c9b1",
      "environment": "macOS；旧CLI Python3.9.6，后端Python3.12.14，Node v25.9.0；没有真实数据库连接或模型调用",
      "id": "independent",
      "kind": "review",
      "status": "passed",
      "command": "独立会话/root/upgrade_review：代码、合成反例、内存HTTP、单元与离线包复核",
      "exit_code": 0,
      "summary": "C01–C12修复后独立复核通过；受检范围无遗留已复现P1/P2",
      "coverage": "限定配置/共享代码/接口/指定前端增量，完整数据库/UI及全局验收未完成",
      "report": "docs/evidence/2026-10-19-configuration-ownership/review.md",
      "report_sha256": "fede0b36b180c151889a2a8f326f8336a9e217da4328b5092e1304bae6299290"
    }
  ],
  "delivery": {
    "local": "implemented_pending_integration",
    "commit": "requested_pending",
    "remote": "requested_pending",
    "clone": "not_requested",
    "runtime": "unverified",
    "review": "passed_scoped_no_database",
    "acceptance_scope": "本次为源码提交推送；local保留implemented_pending_integration，不以发布冒充完整验收",
    "tests": "author_scheduled_separate_task"
  }
}
```
