# 数据底座、后台与创作自动化全面升级

plugin_root/repo_root均为 /Users/xuyun/Documents/ncc-workflow，main，基线de8d1ab，当前v4.0.0。继承三份设计及2026-10-19全面升级授权；作者最新追加“自动定稿资格尚未启用：启用。提交并推送”，已完成D6发布，D7实际加载仍待验证。原README任务与证据保留并随本次交付，历史证据不冒充v4功能验证。

设计依据：[底座](../designs/storage/postgresql-foundation.md)、[后台](../designs/storage/management-console.md)、[自动化评分](../designs/storage/creation-automation.md)。实施/回退见[计划](../designs/storage/implementation.md)，操作见[指南](../guides/data-console.md)，实际结果见[实施证据](../evidence/2026-10-18-postgresql-design/implementation.md)与[发布核验](../evidence/2026-10-18-postgresql-design/release.md)。

v4数据底座、专业后台、创作自动化与旧CLI显式接入已实现。本轮新增作者授权试运行模式，限定对象、方案、期限、次数与策略hash；保留原校准模式和评分/硬伤/证据/二评/P5/版本/权限/关键章闸门，试运行不会生成“已校准”资格。创作台可实际选择授权，Worker自动采用达标结果并记录审计。

跨模块初始验证为204项CLI、32项数据服务、构建/接线/浏览器/恢复及规则样例。本轮启用增量的数据回归42项通过，独立10项通过，两条真实浏览器链路、构建/格式/插件/文档/注册表、代码与备份恢复再次通过。CLI和模型角色判据未再改变，其原证据按未改路径保留，不扩张为本轮真实模型效果。

当前无真实目标数据库/模型配置，已提出配置问题，尚无回复；代码启用不等于具体作品已激活。真实模型校准、五端新会话、向量与规模性能仍未验。测试仅用临时合成范围，真实书库未迁移；发布不包含真实小说、凭据或数据库转储。临时服务验收结束后停止，回退按实施计划保留最新真实数据备份。

```ncc-dev-json
{
  "schema": 1,
  "id": "2026-10-18-postgresql-design",
  "goal": "按已授权三份升级方案全面实现PostgreSQL小说底座、专业管理后台、简洁创作自动化和AI评分，验证并交付本地候选；真实数据切换与发布独立授权",
  "route": "architectural",
  "risk_tags": [
    "architecture",
    "rules"
  ],
  "repo_root": "/Users/xuyun/Documents/ncc-workflow",
  "plugin_root": "/Users/xuyun/Documents/ncc-workflow",
  "branch": "main",
  "base_commit": "de8d1abee1a71d169451c994a8de0c9f64242289",
  "stage": "D7",
  "next": "功能提交已推送并核对origin/main；本记录通过纯元数据提交补齐。真实目标服务/作品配置待作者提供，五端新会话及真实模型校准仍待验证。",
  "blocked": "",
  "decisions": [
    {
      "source": "作者本轮请求及提供的 DeepSeek 方案",
      "scope": "只交设计方案和补充清单，不给数据库表结构、DDL或SQL，不连接/写入数据库、不安装依赖、不迁移私有资料。保留未来承接机制，关键取舍以推荐和备选呈作者审核，不冒称已确认。"
    },
    {
      "source": "作者追加请求：为数据关系体系设计专业基础数据管理后台",
      "scope": "Python与FastAPI已指定，前端授权开发方选型，本方案采用React/TypeScript/Ant Design；补充配套设计、操作步骤和验收，不写运行代码、不安装依赖、不操作真实数据库。"
    },
    {
      "source": "作者追加：创作流程简洁、复杂工作自动化、人工审核或主动介入编写修改、AI成果评分",
      "scope": "设计改为三入口创作台、系统自动编排、作者随时接管；AI成果按内容类型评分并有限返修。修订未来方案，不直接修改现行技能/registry/角色/脚本；阈值和权重为候选，启用前验证。"
    },
    {
      "source": "作者2026-10-19明确要求按照升级方案全面升级",
      "scope": "已授权进入物理结构、代码、依赖安装、隔离合成数据库验证及相应规则接线；继承三份方案，不重复请求设计批准。真实书库切换、外部发布及提交推送未请求。"
    },
    {
      "source": "作者本轮明确要求：自动定稿资格尚未启用：启用。提交并推送",
      "scope": "授权提交推送v4升级。已告知当前无目标数据库/模型配置，默认补齐有对象/期限/次数、owner-only和依据审计的author_trial能力；保留calibrated模式及全部质量闸门。启用方式和目标配置问题已异步提出，尚无回复；真实作品激活和真实校准仍不能冒称已完成。"
    },
    {
      "source": "末次暂存差异检查",
      "scope": "仅清除初始迁移docstring尾随空格，不改变DDL；核对全候选空白差异，沿用未改执行代码的功能证据。"
    }
  ],
  "spec": "docs/designs/storage/postgresql-foundation.md",
  "plan": "docs/designs/storage/implementation.md",
  "scope": [
    ".claude-plugin/marketplace.json",
    ".claude-plugin/plugin.json",
    ".gitignore",
    ".zcode-plugin/plugin.json",
    "ACKNOWLEDGMENTS.md",
    "README.md",
    "agents/pulse.md",
    "alembic.ini",
    "alembic/README",
    "alembic/env.py",
    "alembic/script.py.mako",
    "alembic/versions/070970fe2f0a_private_knowledge_temporal_history_and_.py",
    "alembic/versions/5c4c6e012a90_scoped_credentials_and_history_guards.py",
    "alembic/versions/6d30bb12e441_attachment_access.py",
    "alembic/versions/7e419c2d608b_author_trial_delegation.py",
    "apps/management-web/index.html",
    "apps/management-web/package-lock.json",
    "apps/management-web/package.json",
    "apps/management-web/src/api.ts",
    "apps/management-web/src/common.tsx",
    "apps/management-web/src/context.tsx",
    "apps/management-web/src/creative.tsx",
    "apps/management-web/src/editor.tsx",
    "apps/management-web/src/main.tsx",
    "apps/management-web/src/maintenance.tsx",
    "apps/management-web/src/management.tsx",
    "apps/management-web/src/materials.tsx",
    "apps/management-web/src/style.css",
    "apps/management-web/src/trust.tsx",
    "apps/management-web/src/visuals.tsx",
    "apps/management-web/tsconfig.json",
    "apps/management-web/vite.config.ts",
    "commands/ncc-review.md",
    "docs/README.md",
    "docs/designs/memory/memory-evolution-design.md",
    "docs/designs/storage/creation-automation.md",
    "docs/designs/storage/implementation.md",
    "docs/designs/storage/management-console.md",
    "docs/designs/storage/postgresql-foundation.md",
    "docs/engineering/documentation.md",
    "docs/guides/data-console.md",
    "docs/guides/usage.md",
    "plugin.json",
    "pyproject.toml",
    "scripts/ncc_data.py",
    "scripts/ncc_prepare.py",
    "scripts/ncclib/book.py",
    "scripts/ncclib/cli.py",
    "scripts/ncclib/cli_parsers/__init__.py",
    "scripts/ncclib/cli_parsers/book.py",
    "scripts/ncclib/cli_parsers/quality.py",
    "scripts/ncclib/core.py",
    "scripts/ncclib/database_bridge.py",
    "scripts/ncclib/deconstruction/planning.py",
    "scripts/ncclib/quality.py",
    "scripts/tests/fixtures/runtime-contract.json",
    "scripts/tests/test_architecture.py",
    "scripts/tests/test_quality.py",
    "skills/ncc-deconstruct/SKILL.md",
    "skills/ncc-eval/SKILL.md",
    "skills/ncc-new/SKILL.md",
    "skills/ncc-prepare/SKILL.md",
    "skills/ncc-review/SKILL.md",
    "skills/ncc-review/references/quality-scoring.md",
    "skills/ncc-review/references/review-domains.md",
    "skills/ncc-write/SKILL.md",
    "skills/ncc-write/references/scene-card.md",
    "skills/ncc/SKILL.md",
    "src/ncc_data/__init__.py",
    "src/ncc_data/api.py",
    "src/ncc_data/automation.py",
    "src/ncc_data/calibration.py",
    "src/ncc_data/changes.py",
    "src/ncc_data/cli.py",
    "src/ncc_data/config.py",
    "src/ncc_data/contracts.py",
    "src/ncc_data/db.py",
    "src/ncc_data/errors.py",
    "src/ncc_data/exchange.py",
    "src/ncc_data/maintenance.py",
    "src/ncc_data/models.py",
    "src/ncc_data/policy.py",
    "src/ncc_data/provider.py",
    "src/ncc_data/quality_core.py",
    "src/ncc_data/queries.py",
    "src/ncc_data/resources/policy.json",
    "src/ncc_data/scoring.py",
    "src/ncc_data/security.py",
    "src/ncc_data/seeds.py",
    "src/ncc_data/service.py",
    "src/ncc_data/utils.py",
    "src/ncc_data/validation.py",
    "src/ncc_data/workspace.py",
    "src/ncc_data/workspace_client.py",
    "tests/__init__.py",
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
    "tests/web/run_access_browser.py",
    "tests/web/run_auto_adoption_browser.py",
    "tests/web/run_browser.py",
    "tests/web/run_cli_bridge.py",
    "uv.lock",
    "workflow/architecture.md",
    "workflow/registry.json",
    "workflow/registry/roles.json",
    "workflow/registry/rules.json"
  ],
  "foreign_changes": {
    "docs/tasks/2026-10-12-readme-refresh.md": "前一轮 README 重写任务的在途记录，本轮保留，不作为本次验证证据。",
    "docs/evidence/2026-10-18-readme-project-only/validation.md": "前一轮 README 重写的在途证据，本轮保留。README 本身已纳入本次 v4 接线范围。"
  },
  "evidence_paths": [
    "docs/evidence/2026-10-18-postgresql-design/access.log",
    "docs/evidence/2026-10-18-postgresql-design/admin-review.md",
    "docs/evidence/2026-10-18-postgresql-design/auto-adoption-browser.log",
    "docs/evidence/2026-10-18-postgresql-design/auto-adoption-package.log",
    "docs/evidence/2026-10-18-postgresql-design/auto-adoption-postgres.log",
    "docs/evidence/2026-10-18-postgresql-design/auto-adoption-recovery.log",
    "docs/evidence/2026-10-18-postgresql-design/auto-adoption-web.log",
    "docs/evidence/2026-10-18-postgresql-design/automation-review.md",
    "docs/evidence/2026-10-18-postgresql-design/behavior/packets/A01-古代时代错置与称谓-r1.md",
    "docs/evidence/2026-10-18-postgresql-design/behavior/packets/A02-月相与行程-r1.md",
    "docs/evidence/2026-10-18-postgresql-design/behavior/packets/A03-待核项写了数字-r1.md",
    "docs/evidence/2026-10-18-postgresql-design/behavior/packets/A04-视角越权与超前泄密-r1.md",
    "docs/evidence/2026-10-18-postgresql-design/behavior/packets/A05-场景卡翻转没发生-r1.md",
    "docs/evidence/2026-10-18-postgresql-design/behavior/packets/A06-干净对照-r1.md",
    "docs/evidence/2026-10-18-postgresql-design/behavior/pulse-ingest.log",
    "docs/evidence/2026-10-18-postgresql-design/behavior/pulse-report.json",
    "docs/evidence/2026-10-18-postgresql-design/behavior/reports/A01-古代时代错置与称谓-r1.md",
    "docs/evidence/2026-10-18-postgresql-design/behavior/reports/A02-月相与行程-r1.md",
    "docs/evidence/2026-10-18-postgresql-design/behavior/reports/A03-待核项写了数字-r1.md",
    "docs/evidence/2026-10-18-postgresql-design/behavior/reports/A04-视角越权与超前泄密-r1.md",
    "docs/evidence/2026-10-18-postgresql-design/behavior/reports/A05-场景卡翻转没发生-r1.md",
    "docs/evidence/2026-10-18-postgresql-design/behavior/reports/A06-干净对照-r1.md",
    "docs/evidence/2026-10-18-postgresql-design/behavior/score.md",
    "docs/evidence/2026-10-18-postgresql-design/browser.log",
    "docs/evidence/2026-10-18-postgresql-design/cli-bridge.log",
    "docs/evidence/2026-10-18-postgresql-design/docs.log",
    "docs/evidence/2026-10-18-postgresql-design/format.log",
    "docs/evidence/2026-10-18-postgresql-design/implementation.md",
    "docs/evidence/2026-10-18-postgresql-design/independent-review.md",
    "docs/evidence/2026-10-18-postgresql-design/lint.log",
    "docs/evidence/2026-10-18-postgresql-design/mech.log",
    "docs/evidence/2026-10-18-postgresql-design/package.log",
    "docs/evidence/2026-10-18-postgresql-design/plugin.log",
    "docs/evidence/2026-10-18-postgresql-design/postgres.log",
    "docs/evidence/2026-10-18-postgresql-design/recovery.log",
    "docs/evidence/2026-10-18-postgresql-design/registry.log",
    "docs/evidence/2026-10-18-postgresql-design/release-browser.log",
    "docs/evidence/2026-10-18-postgresql-design/release-docs.log",
    "docs/evidence/2026-10-18-postgresql-design/release-format.log",
    "docs/evidence/2026-10-18-postgresql-design/release-lint.log",
    "docs/evidence/2026-10-18-postgresql-design/release-plugin.log",
    "docs/evidence/2026-10-18-postgresql-design/release.md",
    "docs/evidence/2026-10-18-postgresql-design/review.md",
    "docs/evidence/2026-10-18-postgresql-design/unit.log",
    "docs/evidence/2026-10-18-postgresql-design/web-build.log",
    "docs/evidence/2026-10-18-postgresql-design/web/desktop.png",
    "docs/evidence/2026-10-18-postgresql-design/web/layout.json",
    "docs/evidence/2026-10-18-postgresql-design/web/mobile.png",
    "docs/evidence/2026-10-18-postgresql-design/web/result.json"
  ],
  "candidate": {
    "base_commit": "de8d1abee1a71d169451c994a8de0c9f64242289",
    "files": [
      {
        "path": ".claude-plugin/marketplace.json",
        "type": "file",
        "sha256": "a97680b223892a070a55b8b57db41adbea1dfcd53117e82e1f75d1418dd79131",
        "executable": false
      },
      {
        "path": ".claude-plugin/plugin.json",
        "type": "file",
        "sha256": "b039f8a6343c244e0bdd1f5b5ab79b0abfab5ac4f7456f5ee990ab7844f3ab2e",
        "executable": false
      },
      {
        "path": ".gitignore",
        "type": "file",
        "sha256": "9a6fa2a90ea9a77fc35d906c9854daf34fe8997504d0dc3401a8192d7f855fcc",
        "executable": false
      },
      {
        "path": ".zcode-plugin/plugin.json",
        "type": "file",
        "sha256": "e5d1b1081fcc457fffd2f7b38e6a3d276f8bb0182a38fa7e455d4febef496f29",
        "executable": false
      },
      {
        "path": "ACKNOWLEDGMENTS.md",
        "type": "file",
        "sha256": "7b3912888a7208ac3e4a65f8a2a15b25c8e7c3dd86f43e22c3e21cf96d66da7e",
        "executable": false
      },
      {
        "path": "README.md",
        "type": "file",
        "sha256": "e8bf50210b8a4a2b2dd989be76b49c505d1562d43f384489996752a64af4cfc9",
        "executable": false
      },
      {
        "path": "agents/pulse.md",
        "type": "file",
        "sha256": "b94d7aa2f53e1d11bc0ce32a4c00ba3238805a89de50d31a32a5984ae26c9cc3",
        "executable": false
      },
      {
        "path": "alembic.ini",
        "type": "file",
        "sha256": "ff87022c0a58395668ca2bb1f50a607d91ef75ab303d680ed3df6a588871c413",
        "executable": false
      },
      {
        "path": "alembic/README",
        "type": "file",
        "sha256": "21256d00ebeabca93fe5384ce62a0913e94c92f7fd21b92715415553fbcf99ae",
        "executable": false
      },
      {
        "path": "alembic/env.py",
        "type": "file",
        "sha256": "e0b276e3b8aea2c93692d3ee4014f53b16b7f5426e97e660f3aea447d01df648",
        "executable": false
      },
      {
        "path": "alembic/script.py.mako",
        "type": "file",
        "sha256": "d38920781b4d31ae1c0a71bc09f41c2ade8feab9e5a087e3f30cb4bbf0c1c9d3",
        "executable": false
      },
      {
        "path": "alembic/versions/070970fe2f0a_private_knowledge_temporal_history_and_.py",
        "type": "file",
        "sha256": "3c692659530625a8af5145f9ae04dff5748922f44a3610dc6718eab9cb0d0a72",
        "executable": false
      },
      {
        "path": "alembic/versions/5c4c6e012a90_scoped_credentials_and_history_guards.py",
        "type": "file",
        "sha256": "e6f02cfb5299b3e8be8a2221dca52de1e28fc4c6fc61f8d4ed141d71f9d49f11",
        "executable": false
      },
      {
        "path": "alembic/versions/6d30bb12e441_attachment_access.py",
        "type": "file",
        "sha256": "920af50067773d644ad95d1575151fed6f69371a873e17162fb05eca6764666b",
        "executable": false
      },
      {
        "path": "alembic/versions/7e419c2d608b_author_trial_delegation.py",
        "type": "file",
        "sha256": "acb147a5b4de8bdda3c5a4729cdd8d2f0819723f52818b2952f3455e685dc769",
        "executable": false
      },
      {
        "path": "apps/management-web/index.html",
        "type": "file",
        "sha256": "303f4ef333d9f1f5d4b7a4a3016cb275f6e97b6bb0ae0001ac08e028666c7d50",
        "executable": false
      },
      {
        "path": "apps/management-web/package-lock.json",
        "type": "file",
        "sha256": "46f9030fe1d474900cf78bed52f0389fcdea088d40c66fb60c2cb4ab6079db1d",
        "executable": false
      },
      {
        "path": "apps/management-web/package.json",
        "type": "file",
        "sha256": "296cc502f6a369ce740b3c43b23a10bd97ed47ed4ffd86ad2808755df5f5f052",
        "executable": false
      },
      {
        "path": "apps/management-web/src/api.ts",
        "type": "file",
        "sha256": "7fbabbf22f84e8625e68ba28a84f5624488889677fc1c0f443712bee61c0b230",
        "executable": false
      },
      {
        "path": "apps/management-web/src/common.tsx",
        "type": "file",
        "sha256": "221f59ad59d4d3ba9b90c1fdc712d6ef4c7131d25f422f610a820125dd3a6da0",
        "executable": false
      },
      {
        "path": "apps/management-web/src/context.tsx",
        "type": "file",
        "sha256": "8d611dea5ea84953050418f623c813952e98f7fb14f4e493841b79264db3f9b0",
        "executable": false
      },
      {
        "path": "apps/management-web/src/creative.tsx",
        "type": "file",
        "sha256": "06ce190544443621c19576456346433a3566d45515c02a0c9b3bdfb3554e1d04",
        "executable": false
      },
      {
        "path": "apps/management-web/src/editor.tsx",
        "type": "file",
        "sha256": "b4bda0cde0b7af53a1bcb783deabd351345bd4b4563303ec5b04913cceba9dc3",
        "executable": false
      },
      {
        "path": "apps/management-web/src/main.tsx",
        "type": "file",
        "sha256": "74ab470f16db561e57bba04cb899315415d9b699a35fb389be56b15b6f289cdd",
        "executable": false
      },
      {
        "path": "apps/management-web/src/maintenance.tsx",
        "type": "file",
        "sha256": "d8bef7ee1c1165959bcb8fc8d0b3d4437b835c4dfafb5eddbf5b5fc134e5dbe4",
        "executable": false
      },
      {
        "path": "apps/management-web/src/management.tsx",
        "type": "file",
        "sha256": "a0108621cae0e6fc1b59d332ec32700a29566d6f29a1a37c02d28146887d121d",
        "executable": false
      },
      {
        "path": "apps/management-web/src/materials.tsx",
        "type": "file",
        "sha256": "6a09e6537b2f1f5ff3b55a094d5edee98a31f6aaf84bef227103382e62ffddac",
        "executable": false
      },
      {
        "path": "apps/management-web/src/style.css",
        "type": "file",
        "sha256": "a13f9ff453f39e14cb0f73eb8ba8f9526a961eea31a11f5ab5d7759f551cf0d1",
        "executable": false
      },
      {
        "path": "apps/management-web/src/trust.tsx",
        "type": "file",
        "sha256": "c9483f92bcc2b0e9b4026e6f270e68da05209ee6e9c36b3ec4504eeeff2603f5",
        "executable": false
      },
      {
        "path": "apps/management-web/src/visuals.tsx",
        "type": "file",
        "sha256": "7d4629fadc3578dbf5cdb135fe36da0b5b6341f61c4415fb65890e15f372eb39",
        "executable": false
      },
      {
        "path": "apps/management-web/tsconfig.json",
        "type": "file",
        "sha256": "540b1dcbb580e29d18bdc063e0217067c8c8c81f6b3ae17920da14bdbc564fe8",
        "executable": false
      },
      {
        "path": "apps/management-web/vite.config.ts",
        "type": "file",
        "sha256": "96388f40649d22c0c1aace29c2a0e43ecf408c087f3a73204f42c4b8425dff9f",
        "executable": false
      },
      {
        "path": "commands/ncc-review.md",
        "type": "file",
        "sha256": "6600c38a27bb1bbfabfcdc8b493e15987aa8b870c7a27a6f424317e921bda8e0",
        "executable": false
      },
      {
        "path": "docs/README.md",
        "type": "file",
        "sha256": "ef02701f6cdaafbdaef6d162b3990c8e3eba2933e832bb8a4bf7a69d8399e6be",
        "executable": false
      },
      {
        "path": "docs/designs/memory/memory-evolution-design.md",
        "type": "file",
        "sha256": "d4d4e2c22d6b08a4799454b7f38fd89aa3b48baa5251b6ed2c458a0e7074b861",
        "executable": false
      },
      {
        "path": "docs/designs/storage/creation-automation.md",
        "type": "file",
        "sha256": "37c9d9dc47ccb608dd23e20935a6e61c0420c03243a3168eb45bccd1680b820b",
        "executable": false
      },
      {
        "path": "docs/designs/storage/implementation.md",
        "type": "file",
        "sha256": "8709debecf3117bd988d5517fd58913eae2d9b5c2a08634a8f738a8c7347f28f",
        "executable": false
      },
      {
        "path": "docs/designs/storage/management-console.md",
        "type": "file",
        "sha256": "19f442b5abca298d83fad9abdf93e66ce40a52de2308082c28f8e9977fcf332b",
        "executable": false
      },
      {
        "path": "docs/designs/storage/postgresql-foundation.md",
        "type": "file",
        "sha256": "72a777937e9f7e002687bb25795e0376c0545ab390ca28e2e68fead6ff499d63",
        "executable": false
      },
      {
        "path": "docs/engineering/documentation.md",
        "type": "file",
        "sha256": "37d45fe8eb52d8e3e36a7b7a2984e96b6a9c7089ab382c2c11d6e4b810183834",
        "executable": false
      },
      {
        "path": "docs/guides/data-console.md",
        "type": "file",
        "sha256": "59c887f6f05c73d9668212e8a1cdb9c236b94fd40fa9a937bc7f5e9584e5c672",
        "executable": false
      },
      {
        "path": "docs/guides/usage.md",
        "type": "file",
        "sha256": "6cb3a4a51c4b4c0a98cccac15ae394841a0bc81c692b0804b4b08ab803b37205",
        "executable": false
      },
      {
        "path": "plugin.json",
        "type": "file",
        "sha256": "669f47162c27fd7eae5d62b9b7bd058f85705aed6d7a124d2b6544f1dcd3e619",
        "executable": false
      },
      {
        "path": "pyproject.toml",
        "type": "file",
        "sha256": "6e71bb9b0e78946c60073e5cca627947f8a692f8635535b330785870d0b41c65",
        "executable": false
      },
      {
        "path": "scripts/ncc_data.py",
        "type": "file",
        "sha256": "a89fc0ae9fe117fc4c20501f0c63013132fe7f04a53a22814429b15e9ce990c0",
        "executable": false
      },
      {
        "path": "scripts/ncc_prepare.py",
        "type": "file",
        "sha256": "6b11c3e1637d1037a418b3cb69594e6e168b5a06368547fb4082cf957cca1d87",
        "executable": false
      },
      {
        "path": "scripts/ncclib/book.py",
        "type": "file",
        "sha256": "8faeb1515745329a7737d97197ab5ea3524b88712f9f97e6eb297cfd71f8e43e",
        "executable": false
      },
      {
        "path": "scripts/ncclib/cli.py",
        "type": "file",
        "sha256": "391c1040b0a0b34c0d44a0c81c4f956bff9bde74b0d013df2b05791cf67a4437",
        "executable": false
      },
      {
        "path": "scripts/ncclib/cli_parsers/__init__.py",
        "type": "file",
        "sha256": "0a96046237ebde63ce2832b323f37a6cb44ea4fb2c5148a30df484e2b0d81662",
        "executable": false
      },
      {
        "path": "scripts/ncclib/cli_parsers/book.py",
        "type": "file",
        "sha256": "4bdc2e0d14b3664af4f152359a1c6f1ceb7e2a272effe3a3bfc292cb39e162b2",
        "executable": false
      },
      {
        "path": "scripts/ncclib/cli_parsers/quality.py",
        "type": "file",
        "sha256": "4a88fb108a8fb61145280bf6082ef8746ba36de71fd1b1ff5d607cf3e2d04616",
        "executable": false
      },
      {
        "path": "scripts/ncclib/core.py",
        "type": "file",
        "sha256": "d7a72b6da896273a0494151d6a813d4db8a06cadcbf81326d518886965d483c1",
        "executable": false
      },
      {
        "path": "scripts/ncclib/database_bridge.py",
        "type": "file",
        "sha256": "cdd406a774eabbf328ea6e76e3da910750498b3a064933c684b5df18f13be700",
        "executable": false
      },
      {
        "path": "scripts/ncclib/deconstruction/planning.py",
        "type": "file",
        "sha256": "2e0d8c41ee7a9a7ce7ec0b5cac83e4745fad5d68bf5d2eafbfa4c019e6632bc1",
        "executable": false
      },
      {
        "path": "scripts/ncclib/quality.py",
        "type": "file",
        "sha256": "b98cf98f4dca5ca4608b59f5398dcbbe66dee8b379d5a7518761c1b568cd792c",
        "executable": false
      },
      {
        "path": "scripts/tests/fixtures/runtime-contract.json",
        "type": "file",
        "sha256": "3b8492b790c46c4c1bde785d78d16f0431a9816033e357681674363ae013d825",
        "executable": false
      },
      {
        "path": "scripts/tests/test_architecture.py",
        "type": "file",
        "sha256": "d9dd29ccad46d8ba286c44278a874f96cd1206ded6c617b9b8a76f3205ed496a",
        "executable": false
      },
      {
        "path": "scripts/tests/test_quality.py",
        "type": "file",
        "sha256": "f3c50e324d6bc9831a193e4d1e4995fbaf7fd17bf8af10880ea541ff209c746f",
        "executable": false
      },
      {
        "path": "skills/ncc-deconstruct/SKILL.md",
        "type": "file",
        "sha256": "d01976b813db7d9c83f202f64b02ab2d2d5fd94d7c6f134209b446d1da388dad",
        "executable": false
      },
      {
        "path": "skills/ncc-eval/SKILL.md",
        "type": "file",
        "sha256": "0ce138fc07aba58f42796694e5e76218eca241e59fde3112fcf84b70fd81ca4f",
        "executable": false
      },
      {
        "path": "skills/ncc-new/SKILL.md",
        "type": "file",
        "sha256": "b833870a9be4038ec42617fc705deea36a3033e31825f40e5ffa20c9dbcff658",
        "executable": false
      },
      {
        "path": "skills/ncc-prepare/SKILL.md",
        "type": "file",
        "sha256": "a17e0f1de84814e589ddf741d7eba520f6d96ee66c4ca6456c1f4d4d90b4ca30",
        "executable": false
      },
      {
        "path": "skills/ncc-review/SKILL.md",
        "type": "file",
        "sha256": "79f7973b1c3da0ed32aeaed8f7c9fc13a4c7da8607715cf56d380dc5da5c34dc",
        "executable": false
      },
      {
        "path": "skills/ncc-review/references/quality-scoring.md",
        "type": "file",
        "sha256": "d3bb0f92be166864ecde71efacb5c737b8732cf73ddccd554b652b17ed431f2f",
        "executable": false
      },
      {
        "path": "skills/ncc-review/references/review-domains.md",
        "type": "file",
        "sha256": "136f5a97e38ef8947805311040d22566a8290befa035adb579ef5c8e7c7b8a43",
        "executable": false
      },
      {
        "path": "skills/ncc-write/SKILL.md",
        "type": "file",
        "sha256": "088ae93b3e846c7196258c4379398da31730b68dd9ae75dc5335d0405ecf7a94",
        "executable": false
      },
      {
        "path": "skills/ncc-write/references/scene-card.md",
        "type": "file",
        "sha256": "7a10d6efabd651bb4b18f88640fa7dc62603c3a8b8918fbc9adfb2c295c714d9",
        "executable": false
      },
      {
        "path": "skills/ncc/SKILL.md",
        "type": "file",
        "sha256": "d03f4bd938dd544a3e24928a29df0928e071572e2455b8469d1036c241055c9c",
        "executable": false
      },
      {
        "path": "src/ncc_data/__init__.py",
        "type": "file",
        "sha256": "089bb3cb5927fcac5930b8b7dbf8e54fb747da6a2e40e414514b4e4c83a30993",
        "executable": false
      },
      {
        "path": "src/ncc_data/api.py",
        "type": "file",
        "sha256": "c2180be45f4f216257d6e18b339d087f0a0c6f09ac503540d5b921098f993894",
        "executable": false
      },
      {
        "path": "src/ncc_data/automation.py",
        "type": "file",
        "sha256": "ff5b780cc263152cf907200e556c0419aa4b9c53d2750f4ae221da009ae92f70",
        "executable": false
      },
      {
        "path": "src/ncc_data/calibration.py",
        "type": "file",
        "sha256": "a20f8d6523ef5b684f3a16fac6f6871952abe02b5861c0987df0d51ca1f3fe54",
        "executable": false
      },
      {
        "path": "src/ncc_data/changes.py",
        "type": "file",
        "sha256": "75870682a50c7e21c09ef8804542c4c40c0e971b0ab13afe7222452dc7ab80ed",
        "executable": false
      },
      {
        "path": "src/ncc_data/cli.py",
        "type": "file",
        "sha256": "9a763088e51f06848efeb79cbd7d5e5135c1c6a106cf6be9e3eefaf92a591066",
        "executable": false
      },
      {
        "path": "src/ncc_data/config.py",
        "type": "file",
        "sha256": "3e70dfc3f0e128f772ce255be7c688768692a7768cc52aa968ffadd524563c1a",
        "executable": false
      },
      {
        "path": "src/ncc_data/contracts.py",
        "type": "file",
        "sha256": "10f8fedc7024ea6175f8585a938afb43c41d3f97f7ed8edfc62973aad8ef1b3f",
        "executable": false
      },
      {
        "path": "src/ncc_data/db.py",
        "type": "file",
        "sha256": "e32af53f5952b49c1b4ff2e26540dd0c0a370ba699fb4a81706559e0a0dc95bd",
        "executable": false
      },
      {
        "path": "src/ncc_data/errors.py",
        "type": "file",
        "sha256": "987a2753131846fc08482d63de1d141434336b09bd94aadea18c9646719a6ec9",
        "executable": false
      },
      {
        "path": "src/ncc_data/exchange.py",
        "type": "file",
        "sha256": "a035f353645a31fbd4eed1195d6f66ad321afffa677d1aa98d11b0e61c516364",
        "executable": false
      },
      {
        "path": "src/ncc_data/maintenance.py",
        "type": "file",
        "sha256": "7673d66caadd81acaa44bda04fafa44d9837e4ca98beab60003f71a5583a4faf",
        "executable": false
      },
      {
        "path": "src/ncc_data/models.py",
        "type": "file",
        "sha256": "8235ef8f9a5fa025fa7a90445a3539edd3acb07d6b21c5f7af678828fbd315f8",
        "executable": false
      },
      {
        "path": "src/ncc_data/policy.py",
        "type": "file",
        "sha256": "60aec42dfe078e9193a55879a4f711fe27e691502dba8b8c3e0ea1c05ab9cc95",
        "executable": false
      },
      {
        "path": "src/ncc_data/provider.py",
        "type": "file",
        "sha256": "c8693d317ffa38c66c6751f13fb63183c876164016670b6f02564935b0519618",
        "executable": false
      },
      {
        "path": "src/ncc_data/quality_core.py",
        "type": "file",
        "sha256": "2d97a55c3e24bfaa51d3bfce78d9c931b6a1385088ac33f6e72bf0059734a07d",
        "executable": false
      },
      {
        "path": "src/ncc_data/queries.py",
        "type": "file",
        "sha256": "d85905a742f761e260c6c1bfe60ea58d427f638a99dfc9abb4837a704f07b804",
        "executable": false
      },
      {
        "path": "src/ncc_data/resources/policy.json",
        "type": "file",
        "sha256": "96d46b8c9cbce6cee972a580cbf3986406ddb994ab6bcae2489999c2730272d5",
        "executable": false
      },
      {
        "path": "src/ncc_data/scoring.py",
        "type": "file",
        "sha256": "4d73c3b91ef1e8d748463236d8f61e45dddcc5304114b38618480d0b8076f0de",
        "executable": false
      },
      {
        "path": "src/ncc_data/security.py",
        "type": "file",
        "sha256": "2383543210b188613c52f6b072e6ccb76f84a3d29f03cbe6d4fd5d7afb84ef5b",
        "executable": false
      },
      {
        "path": "src/ncc_data/seeds.py",
        "type": "file",
        "sha256": "d34459e2e30f886aa8bde242e9b7c2bf90caa368bd664b959765214e10840acb",
        "executable": false
      },
      {
        "path": "src/ncc_data/service.py",
        "type": "file",
        "sha256": "35f24fe29bfc00f5adf6cee50a4105c8df2df35dadacd8fabbd808ae03ee600a",
        "executable": false
      },
      {
        "path": "src/ncc_data/utils.py",
        "type": "file",
        "sha256": "9141de40be4c4b30e1340876a2968c26e243444ad6eeaf83e7a72729d3a64cfe",
        "executable": false
      },
      {
        "path": "src/ncc_data/validation.py",
        "type": "file",
        "sha256": "d5400481641c0edad12d9c585cee984d900f0abc052209f42ddc61b6832ef7bf",
        "executable": false
      },
      {
        "path": "src/ncc_data/workspace.py",
        "type": "file",
        "sha256": "cdf0edbdca80211e72ccba4d7a3f42b4cd2bdd705897f7960382f7901961f541",
        "executable": false
      },
      {
        "path": "src/ncc_data/workspace_client.py",
        "type": "file",
        "sha256": "1447d870bb91bbd7ab95b65f4d99ced99028a58601bdfb6b2e3f528e6352f535",
        "executable": false
      },
      {
        "path": "tests/__init__.py",
        "type": "file",
        "sha256": "b5ead0172838e1ec181bf80dc17576564670ff1c7207a7a4929a6fdc792d68ce",
        "executable": false
      },
      {
        "path": "tests/data/__init__.py",
        "type": "file",
        "sha256": "94c960d65fa0871eeb40f78af44a719efd821c8d8652eefdce9c4dce21d20c75",
        "executable": false
      },
      {
        "path": "tests/data/conftest.py",
        "type": "file",
        "sha256": "5e5cb8876541d24da5e0c2b60f47668d320a5b9553a14d632e21805e7db13c3d",
        "executable": false
      },
      {
        "path": "tests/data/run_recovery.py",
        "type": "file",
        "sha256": "4ad246e7ae263f8560f6cf269a2454b9847d2561ac8acbd57199a4580f8f80cd",
        "executable": false
      },
      {
        "path": "tests/data/test_api_automation.py",
        "type": "file",
        "sha256": "14dcf13459a74ae43aa79e92f9ba2c922fcb781cf5a917f074e8451be8d0d53c",
        "executable": false
      },
      {
        "path": "tests/data/test_auto_adoption.py",
        "type": "file",
        "sha256": "7048412f243d2c71602131aa33b3a6e06645524c8fae3b9997c88d5f90811c77",
        "executable": false
      },
      {
        "path": "tests/data/test_automation_boundaries.py",
        "type": "file",
        "sha256": "8a42ecd836f2dd6b690d15f1dd639f9d3939b959495806b08d7d66f32c4e3caa",
        "executable": false
      },
      {
        "path": "tests/data/test_core.py",
        "type": "file",
        "sha256": "ed8b21531f4cba5b43ecde9467b2eaa791ee946203578018ef8f4017d68c5a34",
        "executable": false
      },
      {
        "path": "tests/data/test_exchange_maintenance.py",
        "type": "file",
        "sha256": "8cef1056fdf5160a78f4d030e4eec05ffb23f78e1ec4d2180c20fbd274ffc996",
        "executable": false
      },
      {
        "path": "tests/data/test_review_regressions.py",
        "type": "file",
        "sha256": "210fdaa0e19c35dd64ffd7c773c16cc6937d9116573af805f5ac55c05f5edd85",
        "executable": false
      },
      {
        "path": "tests/data/test_scoring.py",
        "type": "file",
        "sha256": "e4bf7a0c2c5d26cc2b65fa3af67f9db6db3095d550120363dcd857cfad0d7686",
        "executable": false
      },
      {
        "path": "tests/web/run_access_browser.py",
        "type": "file",
        "sha256": "a2aff3302bbc1a00cb38420a53abc19395c831abdc56a8e827477334fdaa6282",
        "executable": false
      },
      {
        "path": "tests/web/run_auto_adoption_browser.py",
        "type": "file",
        "sha256": "1c33e0b6b80e398de56dfe9e50ba5a9901616ca3e13bb2a2e7af5881a0623fc5",
        "executable": false
      },
      {
        "path": "tests/web/run_browser.py",
        "type": "file",
        "sha256": "10428b6277df1be1f0b2291bbd3f1f9452a1a83f73d4d259ecf48769c58e48d9",
        "executable": false
      },
      {
        "path": "tests/web/run_cli_bridge.py",
        "type": "file",
        "sha256": "f925a3863f908c660ccff283d3abc041e10b752eab7779235b4b5f721ae4dd41",
        "executable": false
      },
      {
        "path": "uv.lock",
        "type": "file",
        "sha256": "16144e359e28148e28ffa628268008622aa51a8a6fc99bfa30294ee5a5302d14",
        "executable": false
      },
      {
        "path": "workflow/architecture.md",
        "type": "file",
        "sha256": "974ecfa095cb2d228b42565e5174d1e8c8fb307e1eeb800c59e50152c8b9bec2",
        "executable": false
      },
      {
        "path": "workflow/registry.json",
        "type": "file",
        "sha256": "4560042b3332062aee0671d282c0fb7d9b4025ceaeed5f9fbfbadec683823836",
        "executable": false
      },
      {
        "path": "workflow/registry/roles.json",
        "type": "file",
        "sha256": "38bf4023449614a12a9548c66ac7c6648e9319050471d931093abe4e33e59881",
        "executable": false
      },
      {
        "path": "workflow/registry/rules.json",
        "type": "file",
        "sha256": "ad8230c28316767465dedcb0934b5f36f4a28df720cd7e021d705d8e08bd6cbf",
        "executable": false
      }
    ],
    "fingerprint": "b578894f6493f232ea39abbffd50b4bcc6563fdc0a287f10b57a03702b32907f"
  },
  "required": [
    "unit",
    "postgres",
    "web",
    "plugin",
    "docs",
    "behavior",
    "review",
    "recovery",
    "package"
  ],
  "evidence": [
    {
      "id": "legacy-unit",
      "kind": "unit",
      "candidate": "b578894f6493f232ea39abbffd50b4bcc6563fdc0a287f10b57a03702b32907f",
      "status": "passed",
      "command": "python3 -m unittest discover -s scripts/tests -t scripts -p 'test_*.py'",
      "exit_code": 0,
      "summary": "原204项通过；本轮未改CLI/评分角色标准库路径，按未改内容保留证据；本轮受影响的数据服务与前端另行重验。",
      "environment": "macOS；原CLI Python 3.9.6；数据服务Python 3.12.14；PostgreSQL 17.11临时ncc_test_*；Node 25.9；本机Chromium",
      "coverage": "标准库文件工作流、附加AI来源参数、评分接线、拆书计划与架构兼容；不证明宿主新会话。",
      "report": "docs/evidence/2026-10-18-postgresql-design/unit.log",
      "report_sha256": "60c04fa8c49d33c8b4a628143e932600ad4824142bc40e2f90c1b3255ad17072"
    },
    {
      "id": "postgres-service",
      "kind": "postgres",
      "candidate": "b578894f6493f232ea39abbffd50b4bcc6563fdc0a287f10b57a03702b32907f",
      "status": "passed",
      "command": ".venv/bin/pytest tests/data --database-url '<隔离ncc_test_upgrade连接>' -q",
      "exit_code": 0,
      "summary": "42项通过，13.30s；新增10项自动定稿边界。",
      "environment": "macOS；原CLI Python 3.9.6；数据服务Python 3.12.14；PostgreSQL 17.11临时ncc_test_*；Node 25.9；本机Chromium",
      "coverage": "事务/幂等/权限/历史/分支/类型/导入导出/评分/任务/工作副本及独立评审反例；Provider为合成替身。",
      "report": "docs/evidence/2026-10-18-postgresql-design/auto-adoption-postgres.log",
      "report_sha256": "515e3ac8489a5ce1bc41b13659e70ae97648adeea394c11625063169ba222c15"
    },
    {
      "id": "web-build",
      "kind": "web",
      "candidate": "b578894f6493f232ea39abbffd50b4bcc6563fdc0a287f10b57a03702b32907f",
      "status": "passed",
      "command": "npm --prefix apps/management-web run build",
      "exit_code": 0,
      "summary": "最终TypeScript与Vite构建通过；保留大分包提示。",
      "environment": "macOS；原CLI Python 3.9.6；数据服务Python 3.12.14；PostgreSQL 17.11临时ncc_test_*；Node 25.9；本机Chromium",
      "coverage": "前端编译与分包，不等同于性能验收；最后业务UI字节与构建一致。",
      "report": "docs/evidence/2026-10-18-postgresql-design/auto-adoption-web.log",
      "report_sha256": "f2e967a91fc9fe7b6738c462a455ee488c60fa01fa2c0839e5c909add95459da"
    },
    {
      "id": "web-browser",
      "kind": "web",
      "candidate": "b578894f6493f232ea39abbffd50b4bcc6563fdc0a287f10b57a03702b32907f",
      "status": "passed",
      "command": ".venv/bin/python tests/web/run_browser.py --output /private/tmp/ncc-browser-evidence",
      "exit_code": 0,
      "summary": "原主流程在新代码下重新通过，页面错误0；脚本等待建空间弹窗关闭。",
      "environment": "macOS；原CLI Python 3.9.6；数据服务Python 3.12.14；PostgreSQL 17.11临时ncc_test_*；Node 25.9；本机Chromium",
      "coverage": "登录、建范围、快速输入自动保存、正式采用、已保存草稿清理、历史与管理接线、桌面宽度、390px移动无横向溢出；仅合成账号文本。",
      "report": "docs/evidence/2026-10-18-postgresql-design/release-browser.log",
      "report_sha256": "4f2044f968adb6ee95eaf23472662239b00485e755df87d81f348809ecfb63e3"
    },
    {
      "id": "web-revocation",
      "kind": "web",
      "candidate": "b578894f6493f232ea39abbffd50b4bcc6563fdc0a287f10b57a03702b32907f",
      "status": "passed",
      "command": ".venv/bin/python tests/web/run_access_browser.py",
      "exit_code": 0,
      "summary": "撤权断线重连检查通过，页面错误0。",
      "environment": "macOS；原CLI Python 3.9.6；数据服务Python 3.12.14；PostgreSQL 17.11临时ncc_test_*；Node 25.9；本机Chromium",
      "coverage": "双主体，离线期间撤销secret后重连清理秘密脏表单，撤销read后移出范围。",
      "report": "docs/evidence/2026-10-18-postgresql-design/access.log",
      "report_sha256": "196d5b95ecb3bc23df6d57911340e00ffd1f012d27bfbc8c2746d9de633ed207"
    },
    {
      "id": "cli-database-bridge",
      "kind": "postgres",
      "candidate": "b578894f6493f232ea39abbffd50b4bcc6563fdc0a287f10b57a03702b32907f",
      "status": "passed",
      "command": ".venv/bin/python tests/web/run_cli_bridge.py",
      "exit_code": 0,
      "summary": "实际HTTP+CLI往返通过。",
      "environment": "macOS；原CLI Python 3.9.6；数据服务Python 3.12.14；PostgreSQL 17.11临时ncc_test_*；Node 25.9；本机Chromium",
      "coverage": "旧书初始化、影子导入、显式绑定、读写、外部编辑、typed章同步、pull与原件保留。",
      "report": "docs/evidence/2026-10-18-postgresql-design/cli-bridge.log",
      "report_sha256": "929ec30439973be326a9ca3ff76666148f21e168e3c3b03115741aee85d08526"
    },
    {
      "id": "registry-view",
      "kind": "plugin",
      "candidate": "b578894f6493f232ea39abbffd50b4bcc6563fdc0a287f10b57a03702b32907f",
      "status": "passed",
      "command": "python3 scripts/dev/build_registry.py --check",
      "exit_code": 0,
      "summary": "生成视图与分片一致。",
      "environment": "macOS；原CLI Python 3.9.6；数据服务Python 3.12.14；PostgreSQL 17.11临时ncc_test_*；Node 25.9；本机Chromium",
      "coverage": "registry源片及视图；不证明模型行为。",
      "report": "docs/evidence/2026-10-18-postgresql-design/registry.log",
      "report_sha256": "228b2b815ea0018b70c3f8c45d71c09828edf5404539a94e3c7848c7dc461975"
    },
    {
      "id": "plugin-wiring",
      "kind": "plugin",
      "candidate": "b578894f6493f232ea39abbffd50b4bcc6563fdc0a287f10b57a03702b32907f",
      "status": "passed",
      "command": "python3 scripts/dev/check_plugin.py -v",
      "exit_code": 0,
      "summary": "最终插件一致性与接线通过。",
      "environment": "macOS；原CLI Python 3.9.6；数据服务Python 3.12.14；PostgreSQL 17.11临时ncc_test_*；Node 25.9；本机Chromium",
      "coverage": "命令、技能、相对链接、引用与预算；五端新会话仍待验证。",
      "report": "docs/evidence/2026-10-18-postgresql-design/release-plugin.log",
      "report_sha256": "d52155cde6f8d38f63d2354c2073e49d3a7f379f37b4e67a41f0d8ac4b2e32b0"
    },
    {
      "id": "generated-docs",
      "kind": "docs",
      "candidate": "b578894f6493f232ea39abbffd50b4bcc6563fdc0a287f10b57a03702b32907f",
      "status": "passed",
      "command": "python3 scripts/dev/build_docs.py --check",
      "exit_code": 0,
      "summary": "最终生成文档检查通过，新增启用步骤人工核对。",
      "environment": "macOS；原CLI Python 3.9.6；数据服务Python 3.12.14；PostgreSQL 17.11临时ncc_test_*；Node 25.9；本机Chromium",
      "coverage": "生成文档新鲜度；运行指南及变更范围人工核对另见实施证据。",
      "report": "docs/evidence/2026-10-18-postgresql-design/release-docs.log",
      "report_sha256": "19a0e3bf6b510e1f141b992a7af59e17fee9c7246373fd6b5729e8be239a52fc"
    },
    {
      "id": "frontend-format",
      "kind": "docs",
      "candidate": "b578894f6493f232ea39abbffd50b4bcc6563fdc0a287f10b57a03702b32907f",
      "status": "passed",
      "command": "npm --prefix apps/management-web run format:check",
      "exit_code": 0,
      "summary": "最终前端格式通过。",
      "environment": "macOS；原CLI Python 3.9.6；数据服务Python 3.12.14；PostgreSQL 17.11临时ncc_test_*；Node 25.9；本机Chromium",
      "coverage": "前端源码与配置。",
      "report": "docs/evidence/2026-10-18-postgresql-design/release-format.log",
      "report_sha256": "456d8cc87b5f4bf86c7eccac923f217faa1d11eafc3f74defa64d9d340e57954"
    },
    {
      "id": "mechanical-anchors",
      "kind": "behavior",
      "candidate": "b578894f6493f232ea39abbffd50b4bcc6563fdc0a287f10b57a03702b32907f",
      "status": "passed",
      "command": "python3 scripts/ncc_eval.py mech",
      "exit_code": 0,
      "summary": "6个机械锚定样例通过。",
      "environment": "macOS；原CLI Python 3.9.6；数据服务Python 3.12.14；PostgreSQL 17.11临时ncc_test_*；Node 25.9；本机Chromium",
      "coverage": "机械提醒，不代替模型判据回归。",
      "report": "docs/evidence/2026-10-18-postgresql-design/mech.log",
      "report_sha256": "b5bc3935b8bbea96156e573293c74690dad4928487406b2f82d054a721a40cfe"
    },
    {
      "id": "fresh-continuity-single-run",
      "kind": "behavior",
      "candidate": "b578894f6493f232ea39abbffd50b4bcc6563fdc0a287f10b57a03702b32907f",
      "status": "passed",
      "command": "ncc_eval.py prepare /private/tmp/ncc-v4-rule-eval --runs 1；6个独立fresh continuity逐包盲审；ncc_eval.py score /private/tmp/ncc-v4-rule-eval",
      "exit_code": null,
      "summary": "8/8植入问题检出及定级到位，6/6结论正确，干净对照严重误报0。",
      "environment": "macOS；原CLI Python 3.9.6；数据服务Python 3.12.14；PostgreSQL 17.11临时ncc_test_*；Node 25.9；本机Chromium",
      "coverage": "单轮6样例；未重复、未做旧候选配对，不能据此声称稳定性与质量优越性。",
      "report": "docs/evidence/2026-10-18-postgresql-design/behavior/score.md",
      "report_sha256": "19f6027d344f8c3f7f12888f1732d1a5098afa3fd81e1b5e717c07b7c0721031"
    },
    {
      "id": "fresh-pulse-incomplete",
      "kind": "behavior",
      "candidate": "b578894f6493f232ea39abbffd50b4bcc6563fdc0a287f10b57a03702b32907f",
      "status": "passed",
      "command": "fresh pulse读取冻结P1评分包；quality ingest后运行 python3 scripts/ncc_state.py quality status /private/tmp/ncc-v4-quality-behavior --file sample.md",
      "exit_code": 0,
      "summary": "当前SHA及量表绑定有效；缺少目标/契约/前文使score=null、verdict=incomplete，正确拒绝放行。",
      "environment": "macOS；原CLI Python 3.9.6；数据服务Python 3.12.14；PostgreSQL 17.11临时ncc_test_*；Node 25.9；本机Chromium",
      "coverage": "半分、原文证据和缺依据路由；不是实网关或作者偏好校准。",
      "report": "docs/evidence/2026-10-18-postgresql-design/behavior/pulse-ingest.log",
      "report_sha256": "8e8a9a0697063998fadffa1320048eb308c13c1e7fccf32260d8eabf1f0ae579"
    },
    {
      "id": "independent-targeted-review",
      "kind": "review",
      "candidate": "b578894f6493f232ea39abbffd50b4bcc6563fdc0a287f10b57a03702b32907f",
      "status": "passed",
      "command": "独立工程会话的12类反例探针、临时ncc_test_review全量32项和最后草稿增量1项、定向代码复核",
      "exit_code": null,
      "summary": "原12类及本轮2类问题已修复复核；本轮10项独立通过，37个已读文件摘要有效。",
      "environment": "macOS；原CLI Python 3.9.6；数据服务Python 3.12.14；PostgreSQL 17.11临时ncc_test_*；Node 25.9；本机Chromium",
      "coverage": "以报告35个文件摘要与逐段边界为准；不是全部源码、全部UI或模型效果的独立认证。",
      "report": "docs/evidence/2026-10-18-postgresql-design/independent-review.md",
      "report_sha256": "64dbf6ed2f4e0fdb2575e3ab6fa535e27f1d11d88001afa06c81ada5e222b020"
    },
    {
      "id": "postgres-recovery",
      "kind": "recovery",
      "candidate": "b578894f6493f232ea39abbffd50b4bcc6563fdc0a287f10b57a03702b32907f",
      "status": "passed",
      "command": ".venv/bin/python tests/data/run_recovery.py --database-url '<隔离ncc_test_browser连接>' --target-database ncc_test_recovery_final --pg-bin /opt/homebrew/opt/postgresql@17/bin",
      "exit_code": 0,
      "summary": "含第4迁移的恢复通过；16张事实表摘要一致，恢复后所有托管撤销。",
      "environment": "macOS；原CLI Python 3.9.6；数据服务Python 3.12.14；PostgreSQL 17.11临时ncc_test_*；Node 25.9；本机Chromium",
      "coverage": "合成数据逻辑备份恢复；不证明长期WAL/RPO/RTO。",
      "report": "docs/evidence/2026-10-18-postgresql-design/auto-adoption-recovery.log",
      "report_sha256": "3fe3408e694f912a06ce9fb2c62bc8d95f92238a2c1368315cafae4b328e19bb"
    },
    {
      "id": "python-package",
      "kind": "package",
      "candidate": "b578894f6493f232ea39abbffd50b4bcc6563fdc0a287f10b57a03702b32907f",
      "status": "passed",
      "command": "uv --cache-dir /private/tmp/ncc-upgrade-uv-cache build；检查wheel清单",
      "exit_code": 0,
      "summary": "最终wheel及源码包构建通过；38项包含量表与4份迁移，无缓存。",
      "environment": "macOS；原CLI Python 3.9.6；数据服务Python 3.12.14；PostgreSQL 17.11临时ncc_test_*；Node 25.9；本机Chromium",
      "coverage": "当前Python分发包；前端单独构建。沙箱首次下载失败，获授权重跑后成功。",
      "report": "docs/evidence/2026-10-18-postgresql-design/auto-adoption-package.log",
      "report_sha256": "a361cc7647cb99608944736b760e17654791b08829e97a8dfe86ffa7ef3d4c9a"
    },
    {
      "id": "python-lint",
      "kind": "package",
      "candidate": "b578894f6493f232ea39abbffd50b4bcc6563fdc0a287f10b57a03702b32907f",
      "status": "passed",
      "command": ".venv/bin/ruff check src/ncc_data tests/data tests/web",
      "exit_code": 0,
      "summary": "最终静态检查通过。",
      "environment": "macOS；原CLI Python 3.9.6；数据服务Python 3.12.14；PostgreSQL 17.11临时ncc_test_*；Node 25.9；本机Chromium",
      "coverage": "新数据服务及测试静态检查；git diff --check另已通过。",
      "report": "docs/evidence/2026-10-18-postgresql-design/release-lint.log",
      "report_sha256": "82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18"
    },
    {
      "id": "model-calibration-pending",
      "kind": "model_quality",
      "candidate": "b578894f6493f232ea39abbffd50b4bcc6563fdc0a287f10b57a03702b32907f",
      "status": "pending",
      "command": "未配置真实模型网关或作者开发/留出样本",
      "exit_code": null,
      "summary": "真实校准/偏好尚未验证；作者试运行能力已接通，目标实例缺配置，未声称真实作品激活。",
      "environment": "macOS；原CLI Python 3.9.6；数据服务Python 3.12.14；PostgreSQL 17.11临时ncc_test_*；Node 25.9；本机Chromium",
      "coverage": "无真实网关或读者证据。",
      "report": "docs/evidence/2026-10-18-postgresql-design/implementation.md",
      "report_sha256": "ff84bfa1c05a6f0e16d6435282da07f118efa68e7f058ea6a9e4110cd7a24202"
    },
    {
      "id": "five-hosts-pending",
      "kind": "host_runtime",
      "candidate": "b578894f6493f232ea39abbffd50b4bcc6563fdc0a287f10b57a03702b32907f",
      "status": "pending",
      "command": "claude/codex/kimi/grok/zcode新会话未执行",
      "exit_code": null,
      "summary": "五端实际加载与代表调用待验证。",
      "environment": "macOS；原CLI Python 3.9.6；数据服务Python 3.12.14；PostgreSQL 17.11临时ncc_test_*；Node 25.9；本机Chromium",
      "coverage": "静态接线通过不能替代新会话。",
      "report": "docs/evidence/2026-10-18-postgresql-design/implementation.md",
      "report_sha256": "ff84bfa1c05a6f0e16d6435282da07f118efa68e7f058ea6a9e4110cd7a24202"
    },
    {
      "id": "auto-adoption-ui",
      "kind": "web",
      "candidate": "b578894f6493f232ea39abbffd50b4bcc6563fdc0a287f10b57a03702b32907f",
      "status": "passed",
      "command": ".venv/bin/python tests/web/run_auto_adoption_browser.py",
      "exit_code": 0,
      "summary": "真实界面登记合成试运行授权、标记未校准、限定对象选择及任务payload绑定均通过，页面错误0。",
      "environment": "macOS；Python3.12；本机Chromium；临时ncc_test_browser",
      "coverage": "界面与实际HTTP接线；Worker自动采用由42项数据回归验证，未接真实模型。",
      "report": "docs/evidence/2026-10-18-postgresql-design/auto-adoption-browser.log",
      "report_sha256": "07b158fceab96642e212f0905ab5429c2b9cd68bc0da6134af382a986143cf62"
    },
    {
      "id": "remote-release",
      "kind": "release",
      "candidate": "b578894f6493f232ea39abbffd50b4bcc6563fdc0a287f10b57a03702b32907f",
      "status": "passed",
      "command": "git pull; git commit; git push origin main; git ls-remote origin refs/heads/main",
      "exit_code": 0,
      "summary": "功能提交已推送，远端完整SHA与本地一致；随后仅补齐发布记录。",
      "environment": "main; core.hooksPath=.githooks; origin cloudxy/ncc-plugin",
      "coverage": "代码发布与远端提交；不是新会话加载或真实作品激活。",
      "report": "docs/evidence/2026-10-18-postgresql-design/release.md",
      "report_sha256": "cd01a18ff61c1e4927941ea91bac05e7f8ee0524cff9991c8ac5471f454aaf55"
    }
  ],
  "delivery": {
    "local": "accepted",
    "commit": "e96c1273d8e2d97064285d5fde05d47c6b24dd6d (product); record follows in metadata-only commit",
    "remote": "origin/main contains e96c1273d8e2d97064285d5fde05d47c6b24dd6d; verified by git ls-remote",
    "clone": "not_applicable_local_root_directly_registered",
    "runtime": "web_and_cli_passed;five_hosts_unverified",
    "review": "independent_scoped_passed;release_authorized_by_author"
  }
}
```
