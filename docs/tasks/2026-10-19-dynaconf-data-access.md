# Dynaconf与数据接入实现

plugin_root/repo_root均为`/Users/xuyun/Documents/ncc-workflow`，main/v4.0.0；在上一轮本地候选基础上按作者纠正继续同一任务。按[配置方案](../designs/engineering/dynaconf-data-access.md)执行；[产品与工程职责方案](../designs/engineering/product-architecture.md)为待审核设计，不将其称为角色或界面已经启用。

配置及模板已统一归config，路径共用一个定义；本机私有文件已原字节迁移至config/.env，权限0600，根位置移除。MCP启动参数已同步指向新位置；MCP只读、后台/HTTP/直接CLI完整读写的业务边界保持。没有改动数据库、模型或凭据原值，也没有连接或创建数据库。

本轮验证为84项通过、38项数据库用例跳过；另10项相邻CLI检查、静态接线、SDK实际stdio、隔离wheel和配置迁移通过。覆盖及缺项见[本轮报告](../evidence/2026-10-19-dynaconf-data-access/config-ownership/validation.md)。上一候选7942e140的证据原字节保留，已退为历史输入，本轮重新冻结和绑定，不能继承旧通过状态。

主线定位为小说创作，资源管理作为可独立使用的支撑能力。职责方案给出产品经理、设计师、架构师、DBA的具体工件与验收，及卷章/续写等后续批次；本轮未修改角色注册表、开发派单或创作判据。作者审核方案与实际功能实现分开记录。

真实数据库联调继续等待既定配置来源；完整浏览器、恢复及新会话按作者专项安排。回退只还原本轮产品并按版本将唯一私有配置迁回，不同时保留两个默认文件，不操作数据库。当前未请求提交推送。

```ncc-dev-json
{
  "schema": 1,
  "id": "2026-10-19-dynaconf-data-access",
  "goal": "采用Dynaconf并统一config目录归属，保持既定数据库参数及MCP/非MCP接入；审查以小说创作为主线的工程产品职责缺口",
  "route": "architectural",
  "risk_tags": [
    "configuration",
    "data-access",
    "product-design-candidate"
  ],
  "repo_root": "/Users/xuyun/Documents/ncc-workflow",
  "plugin_root": "/Users/xuyun/Documents/ncc-workflow",
  "branch": "main",
  "base_commit": "ac0fc44990a4f8c8e8d22a3a0a4a0540c4446393",
  "stage": "D5",
  "next": "配置归属实现及独立复核已完成；产品/架构/DBA职责方案供作者审核，后续角色接线和作品卷章路径按方案另行实施；真实PG待既定配置来源。",
  "blocked": "既定PostgreSQL连接来源未提供；config/.env原字段仍为空，38项数据库集成测试跳过，真实MCP读取和落库待验。",
  "decisions": [
    {
      "source": "作者本轮三项要求",
      "scope": "必须使用Dynaconf；MCP连接PostgreSQL读取；非MCP支持读写编辑更新；保留原PostgreSQL参数。"
    },
    {
      "source": "作者上一轮明确测试安排",
      "scope": "真实数据库、完整浏览器和恢复专项另行安排；本轮只执行受影响的实现验证，不宣称专项通过。"
    },
    {
      "source": "作者本轮关于config归属、工程角色与产品主辅线的纠正",
      "scope": "私有.env及模板归config管理；保持小说创作主线和资源管理辅线；核对四类工程职责，以具体交付和验收补足设计，不新增写作日常审批。"
    }
  ],
  "spec": "docs/designs/engineering/dynaconf-data-access.md",
  "plan": "docs/designs/engineering/dynaconf-data-access.md",
  "scope": [
    ".env.example",
    ".gitignore",
    ".zcodeignore",
    "ACKNOWLEDGMENTS.md",
    "AGENTS.md",
    "README.md",
    "config/.env.example",
    "config/default/settings.toml",
    "docs/README.md",
    "docs/designs/engineering/configuration-ownership.md",
    "docs/designs/engineering/dynaconf-data-access.md",
    "docs/designs/engineering/product-architecture.md",
    "docs/engineering/code-layout.md",
    "docs/guides/data-access.md",
    "docs/guides/data-console.md",
    "pyproject.toml",
    "scripts/ncc_data.py",
    "scripts/ncclib/database_bridge.py",
    "src/ncc_data/application/access.py",
    "src/ncc_data/cli/data.py",
    "src/ncc_data/cli/main.py",
    "src/ncc_data/cli/workspace.py",
    "src/ncc_data/domain/access.py",
    "src/ncc_data/mcp/__init__.py",
    "src/ncc_data/mcp/configuration.py",
    "src/ncc_data/mcp/server.py",
    "src/ncc_data/runtime/settings.py",
    "src/ncc_shared/configuration.py",
    "src/ncc_shared/database.py",
    "src/ncc_shared/http.py",
    "src/ncc_shared/paths.py",
    "src/ncc_shared/runtime.py",
    "tests/backend/conftest.py",
    "tests/backend/test_direct_access.py",
    "tests/unit/test_configuration.py",
    "tests/unit/test_data_access.py",
    "tests/unit/test_mcp.py",
    "uv.lock"
  ],
  "foreign_changes": {},
  "evidence_paths": [
    "docs/evidence/2026-10-19-dynaconf-data-access/architecture.log",
    "docs/evidence/2026-10-19-dynaconf-data-access/config-ownership/architecture.log",
    "docs/evidence/2026-10-19-dynaconf-data-access/config-ownership/data-cli.log",
    "docs/evidence/2026-10-19-dynaconf-data-access/config-ownership/diff.log",
    "docs/evidence/2026-10-19-dynaconf-data-access/config-ownership/docs.log",
    "docs/evidence/2026-10-19-dynaconf-data-access/config-ownership/file-cli.log",
    "docs/evidence/2026-10-19-dynaconf-data-access/config-ownership/links.log",
    "docs/evidence/2026-10-19-dynaconf-data-access/config-ownership/local-mcp.md",
    "docs/evidence/2026-10-19-dynaconf-data-access/config-ownership/migration.md",
    "docs/evidence/2026-10-19-dynaconf-data-access/config-ownership/packaging.md",
    "docs/evidence/2026-10-19-dynaconf-data-access/config-ownership/plugin.log",
    "docs/evidence/2026-10-19-dynaconf-data-access/config-ownership/quality.log",
    "docs/evidence/2026-10-19-dynaconf-data-access/config-ownership/registry.log",
    "docs/evidence/2026-10-19-dynaconf-data-access/config-ownership/review.md",
    "docs/evidence/2026-10-19-dynaconf-data-access/config-ownership/ruff.log",
    "docs/evidence/2026-10-19-dynaconf-data-access/config-ownership/tests.log",
    "docs/evidence/2026-10-19-dynaconf-data-access/config-ownership/validation.md",
    "docs/evidence/2026-10-19-dynaconf-data-access/diff.log",
    "docs/evidence/2026-10-19-dynaconf-data-access/docs.log",
    "docs/evidence/2026-10-19-dynaconf-data-access/file-cli.log",
    "docs/evidence/2026-10-19-dynaconf-data-access/links.log",
    "docs/evidence/2026-10-19-dynaconf-data-access/local-mcp.md",
    "docs/evidence/2026-10-19-dynaconf-data-access/packaging.md",
    "docs/evidence/2026-10-19-dynaconf-data-access/plugin.log",
    "docs/evidence/2026-10-19-dynaconf-data-access/quality.log",
    "docs/evidence/2026-10-19-dynaconf-data-access/registry.log",
    "docs/evidence/2026-10-19-dynaconf-data-access/review.md",
    "docs/evidence/2026-10-19-dynaconf-data-access/ruff.log",
    "docs/evidence/2026-10-19-dynaconf-data-access/tests.log",
    "docs/evidence/2026-10-19-dynaconf-data-access/validation.md"
  ],
  "candidate": {
    "base_commit": "ac0fc44990a4f8c8e8d22a3a0a4a0540c4446393",
    "files": [
      {
        "path": ".env.example",
        "type": "deleted"
      },
      {
        "path": ".gitignore",
        "type": "file",
        "sha256": "faf582ad34c78f911f336ea5111cc01d49f2850ddbfd636203a1d1acbdbdb81a",
        "executable": false
      },
      {
        "path": ".zcodeignore",
        "type": "file",
        "sha256": "20f13db5ac3ecbf6091c0f317a38b69d1b4ff394361fe08f7e2a306a7244ed5a",
        "executable": false
      },
      {
        "path": "ACKNOWLEDGMENTS.md",
        "type": "file",
        "sha256": "fa75a4796df51fd597002b01a1ae07a63e04f016b6e9efb72f68f52bb9afd998",
        "executable": false
      },
      {
        "path": "AGENTS.md",
        "type": "file",
        "sha256": "9104bed00c575d2b7fda1f8d45e4234e125ae1a53ced887cb4c4ef33abbd3dc9",
        "executable": false
      },
      {
        "path": "README.md",
        "type": "file",
        "sha256": "bc29b1c947314e36a15cd3815798a436d2ff8bd533927590acacab05d97d4f61",
        "executable": false
      },
      {
        "path": "config/.env.example",
        "type": "file",
        "sha256": "53bb1f2eb22a9ae55b50d80d8ea42b42d4c400bc5c8a03e8b30dd188d80e1c35",
        "executable": false
      },
      {
        "path": "config/default/settings.toml",
        "type": "file",
        "sha256": "3302f3313d015c686842fc095c7e9b9551314fa50a274afc3a7e5ba060325c75",
        "executable": false
      },
      {
        "path": "docs/README.md",
        "type": "file",
        "sha256": "5bdabc8d2db71191d4b46e15a15ddafe3d68eed99110dc6ba496bb8b5b49e76c",
        "executable": false
      },
      {
        "path": "docs/designs/engineering/configuration-ownership.md",
        "type": "file",
        "sha256": "222cbab2dc1c8795c64c615c5d162115dd91e0d2c036c57347b371e7f6304e69",
        "executable": false
      },
      {
        "path": "docs/designs/engineering/dynaconf-data-access.md",
        "type": "file",
        "sha256": "1f76a03fdfd2545ecb854755b24320615fe15ab6b9e3f90436bedd40d3d9314d",
        "executable": false
      },
      {
        "path": "docs/designs/engineering/product-architecture.md",
        "type": "file",
        "sha256": "f4977e90970a115abbf09338ab371dcf75d006f135c304971ea650e21aea5857",
        "executable": false
      },
      {
        "path": "docs/engineering/code-layout.md",
        "type": "file",
        "sha256": "c8f62ccfb7337b56e52c073c874140e3bdde6518e532c8d1bcfb435f94cad863",
        "executable": false
      },
      {
        "path": "docs/guides/data-access.md",
        "type": "file",
        "sha256": "6f771d57e76bab1ffd64e2600c3f1f2fe0cd94702166c615fdeafcc1ae524865",
        "executable": false
      },
      {
        "path": "docs/guides/data-console.md",
        "type": "file",
        "sha256": "0828b285321134c3d72bebc69880cc7354bdaac3209536c53aed9d03369e8bd3",
        "executable": false
      },
      {
        "path": "pyproject.toml",
        "type": "file",
        "sha256": "2442bc1b26fd44d51695affcfbe164e183a8d14f195a28d8551f3a5f4ca0d9a6",
        "executable": false
      },
      {
        "path": "scripts/ncc_data.py",
        "type": "file",
        "sha256": "732bcaa6f6f361d515766bc17a94695c33f957003205aca0084feeb7d1abbcf2",
        "executable": false
      },
      {
        "path": "scripts/ncclib/database_bridge.py",
        "type": "file",
        "sha256": "b4e1e1c896b6387f6506790a6126c47a1667c5dc66e02811c9e190e884820489",
        "executable": false
      },
      {
        "path": "src/ncc_data/application/access.py",
        "type": "file",
        "sha256": "fd6adda96259643fe59405dad8e613855373fc922187024281ebe595566aa716",
        "executable": false
      },
      {
        "path": "src/ncc_data/cli/data.py",
        "type": "file",
        "sha256": "62f53722e88b98c474c7c64d50a8ea6c770c59c98e133a6435d6247e850a1a9d",
        "executable": false
      },
      {
        "path": "src/ncc_data/cli/main.py",
        "type": "file",
        "sha256": "322bf5b364d1c1924564b7780d9a738de37998701e22e386ef022e031090e902",
        "executable": false
      },
      {
        "path": "src/ncc_data/cli/workspace.py",
        "type": "file",
        "sha256": "1decd946dce612cee4fe16b0b3cda8391e2e645334dc728c0be554100bc6283b",
        "executable": false
      },
      {
        "path": "src/ncc_data/domain/access.py",
        "type": "file",
        "sha256": "9e25fdc5bd154309a9bfb4a6a881c28b04710d970d0a50770a2cefdf7d62209f",
        "executable": false
      },
      {
        "path": "src/ncc_data/mcp/__init__.py",
        "type": "file",
        "sha256": "a161bf178ae71b80e45dae978633b5d7917f007f21eb26de083523561ea611d2",
        "executable": false
      },
      {
        "path": "src/ncc_data/mcp/configuration.py",
        "type": "file",
        "sha256": "7aace5143225989be7614efa8338fe66017ee9e53ba048c604ab1b92655acd08",
        "executable": false
      },
      {
        "path": "src/ncc_data/mcp/server.py",
        "type": "file",
        "sha256": "4f472870e4ffef463d5e283a15278ed5f98fd95ff0d0c49bd0ca961e9b489be3",
        "executable": false
      },
      {
        "path": "src/ncc_data/runtime/settings.py",
        "type": "file",
        "sha256": "0ab383e5db8b9f247d7c2f9cba2ad04e8e9aa7bfbe98e46acc907aeea3358fe4",
        "executable": false
      },
      {
        "path": "src/ncc_shared/configuration.py",
        "type": "file",
        "sha256": "73fbc3bcb35da3d46389992463f4cfa46b5c1b1c411218f72573f2d4e722f1a9",
        "executable": false
      },
      {
        "path": "src/ncc_shared/database.py",
        "type": "file",
        "sha256": "27ac281dff85fbd42423a280491f5c8f27ab57c03623eb47581eacc80f06804c",
        "executable": false
      },
      {
        "path": "src/ncc_shared/http.py",
        "type": "file",
        "sha256": "67590301f1388207b47b1a367452ca162af7af0df9dd9f4b7d7b7a94159a1d4a",
        "executable": false
      },
      {
        "path": "src/ncc_shared/paths.py",
        "type": "file",
        "sha256": "3d3b4d0a865eb80e148c895c71a4d4d6bcb9049bee0f897fd183d608fa2b3db1",
        "executable": false
      },
      {
        "path": "src/ncc_shared/runtime.py",
        "type": "file",
        "sha256": "766b0c95d4bdbcee6f800c5e38879fab77be1a01fe2b8fc86504f1d33363f80c",
        "executable": false
      },
      {
        "path": "tests/backend/conftest.py",
        "type": "file",
        "sha256": "13d793c9f824dd72cd76152f6eeccd71b392a74c1696940f7a02e6303b1a7ac6",
        "executable": false
      },
      {
        "path": "tests/backend/test_direct_access.py",
        "type": "file",
        "sha256": "fb317532b49fb1520491a7946285eb1e5c02b188936abd9c71dd079d560b3233",
        "executable": false
      },
      {
        "path": "tests/unit/test_configuration.py",
        "type": "file",
        "sha256": "fd3a032a9f2c5ef7a049444923a9a4904bf009e58517d396b118b97913dc05dd",
        "executable": false
      },
      {
        "path": "tests/unit/test_data_access.py",
        "type": "file",
        "sha256": "a94a4fd989a26eccb65c394b7454186d2e3ce8909187d8e6bd904ebb9a3b9205",
        "executable": false
      },
      {
        "path": "tests/unit/test_mcp.py",
        "type": "file",
        "sha256": "21e8f9fc550077e66721d2fcf6352b0eb840bbb38f4637731e3507f34d569345",
        "executable": false
      },
      {
        "path": "uv.lock",
        "type": "file",
        "sha256": "ee5a76662a2a2a5c647eec7d492ea7222f2e401dea146d653562704dc484ac70",
        "executable": false
      }
    ],
    "fingerprint": "af3787bbe3b355b5c6c91512049060190c8d8a73b84ee81b547153a8ff0bcb57"
  },
  "required": [
    "unit",
    "mcp",
    "postgres",
    "plugin",
    "docs",
    "package",
    "review"
  ],
  "evidence": [
    {
      "id": "revised-unit",
      "kind": "unit",
      "candidate": "af3787bbe3b355b5c6c91512049060190c8d8a73b84ee81b547153a8ff0bcb57",
      "status": "passed",
      "command": ".venv/bin/pytest tests/unit tests/backend -q；test_quality/test_architecture；Ruff",
      "exit_code": 0,
      "summary": "84通过、38项PG跳过，另10项相邻CLI通过；包含实际macOS并发文件替换/排他拒绝及TOML假入口拒绝",
      "environment": "macOS；Python3.12.14、Dynaconf3.3.5、MCP1.30.0；无真实PG或模型调用",
      "coverage": "单元和适配，非真实PG读写",
      "report": "docs/evidence/2026-10-19-dynaconf-data-access/config-ownership/validation.md",
      "report_sha256": "b98e06ae256bf49473d7f71d21fd185747e928db87153faf43846a04a8649d1f"
    },
    {
      "id": "actual-config-move",
      "kind": "configuration",
      "candidate": "af3787bbe3b355b5c6c91512049060190c8d8a73b84ee81b547153a8ff0bcb57",
      "status": "passed",
      "command": ".venv/bin/ncc-data init；原字节比对；修复后幂等init",
      "exit_code": 0,
      "summary": "本机文件归config/.env，字节不变、0600、根文件移除；首次移动发生在并发修复前，最终算法另有合成证据",
      "environment": "macOS；Python3.12.14、Dynaconf3.3.5、MCP1.30.0；无真实PG或模型调用",
      "coverage": "不以首次移动当最终算法并发证明；未改变私有原值",
      "report": "docs/evidence/2026-10-19-dynaconf-data-access/config-ownership/migration.md",
      "report_sha256": "5b619996c056f7fed987c9c81a846318a2c1e5510a08309ae966fd67962e10ee"
    },
    {
      "id": "revised-mcp",
      "kind": "mcp",
      "candidate": "af3787bbe3b355b5c6c91512049060190c8d8a73b84ee81b547153a8ff0bcb57",
      "status": "passed",
      "command": "mcp-config --host both；实际清单stdio；codex mcp get",
      "exit_code": 0,
      "summary": "实际两宿主参数已指向新路径；SDK初始化9工具及当前Codex登记通过",
      "environment": "macOS；Python3.12.14、Dynaconf3.3.5、MCP1.30.0；无真实PG或模型调用",
      "coverage": "非真实PG资料读取或宿主新会话验证；O02另经反例单元验证",
      "report": "docs/evidence/2026-10-19-dynaconf-data-access/config-ownership/local-mcp.md",
      "report_sha256": "1d762e4afa6f1f938452501e4b216a661a402f412c87c35ac761882099877679"
    },
    {
      "id": "postgres-pending",
      "kind": "postgres",
      "candidate": "af3787bbe3b355b5c6c91512049060190c8d8a73b84ee81b547153a8ff0bcb57",
      "status": "blocked",
      "command": ".venv/bin/pytest tests/unit tests/backend -q；postgresql_status",
      "exit_code": 0,
      "summary": "既定连接来源仍缺，38项PG用例跳过，实际读取和落库未验",
      "environment": "macOS；Python3.12.14、Dynaconf3.3.5、MCP1.30.0；无真实PG或模型调用",
      "coverage": "未改变连接或启动/创建数据库",
      "report": "docs/evidence/2026-10-19-dynaconf-data-access/config-ownership/validation.md",
      "report_sha256": "b98e06ae256bf49473d7f71d21fd185747e928db87153faf43846a04a8649d1f"
    },
    {
      "id": "revised-plugin",
      "kind": "plugin",
      "candidate": "af3787bbe3b355b5c6c91512049060190c8d8a73b84ee81b547153a8ff0bcb57",
      "status": "passed",
      "command": "python3 scripts/dev/check_plugin.py -v；build_registry.py --check",
      "exit_code": 0,
      "summary": "PLUGIN OK、REGISTRY OK",
      "environment": "macOS；Python3.12.14、Dynaconf3.3.5、MCP1.30.0；无真实PG或模型调用",
      "coverage": "未改创作角色或判据，不启用工程代理",
      "report": "docs/evidence/2026-10-19-dynaconf-data-access/config-ownership/validation.md",
      "report_sha256": "b98e06ae256bf49473d7f71d21fd185747e928db87153faf43846a04a8649d1f"
    },
    {
      "id": "revised-docs",
      "kind": "docs",
      "candidate": "af3787bbe3b355b5c6c91512049060190c8d8a73b84ee81b547153a8ff0bcb57",
      "status": "passed",
      "command": "python3 scripts/dev/build_docs.py --check；Markdown相对目标检查；git diff --check",
      "exit_code": 0,
      "summary": "生成及87个相对目标通过，产品方案的候选与后续边界明确",
      "environment": "macOS；Python3.12.14、Dynaconf3.3.5、MCP1.30.0；无真实PG或模型调用",
      "coverage": "当前指南和设计；无外部链接或锚点验证",
      "report": "docs/evidence/2026-10-19-dynaconf-data-access/config-ownership/validation.md",
      "report_sha256": "b98e06ae256bf49473d7f71d21fd185747e928db87153faf43846a04a8649d1f"
    },
    {
      "id": "revised-wheel",
      "kind": "package",
      "candidate": "af3787bbe3b355b5c6c91512049060190c8d8a73b84ee81b547153a8ff0bcb57",
      "status": "passed",
      "command": "uv build --wheel；仓外隔离探针",
      "exit_code": 0,
      "summary": "77成员、4历史迁移字节不变；包内macOS原子迁移、默认新配置位置、MCP和CLI通过",
      "environment": "macOS；Python3.12.14、Dynaconf3.3.5、MCP1.30.0；无真实PG或模型调用",
      "coverage": "Mac实际文件系统，无真实配置/数据库；Linux实际系统未验",
      "report": "docs/evidence/2026-10-19-dynaconf-data-access/config-ownership/packaging.md",
      "report_sha256": "9a1de76f6cabf9d8276dd3daad8c51eeedac8425a2a5fe7fcdfff658ddccfe35"
    },
    {
      "id": "revised-review",
      "kind": "review",
      "candidate": "af3787bbe3b355b5c6c91512049060190c8d8a73b84ee81b547153a8ff0bcb57",
      "status": "passed",
      "command": "独立会话/root/upgrade_review修复复核及候选绑定",
      "exit_code": 0,
      "summary": "O01/O02修复独立复核通过，40项定向单元通过、1项stdio排除；受检增量无已复现P1/P2遗留",
      "environment": "macOS；Python3.12.14、Dynaconf3.3.5、MCP1.30.0；无真实PG或模型调用",
      "coverage": "Mac原生排他迁移/并发合成、MCP语义拒绝及产品职责候选；Linux原生/真实PG/UI未验",
      "report": "docs/evidence/2026-10-19-dynaconf-data-access/config-ownership/review.md",
      "report_sha256": "69153cc221a337310252eb6c77e34a483e98b0d0063f954a0c9dee0d3672e179"
    }
  ],
  "delivery": {
    "local": "implemented_pending_integration",
    "commit": "not_requested",
    "remote": "not_requested",
    "clone": "not_requested",
    "runtime": "config归属及MCP接线已迁移；实际stdio通过；真实PG及五宿主新会话未验",
    "review": "passed_scoped_no_database",
    "product_design": "candidate_for_author_review; engineering roles not activated"
  },
  "prior_candidates": [
    {
      "fingerprint": "7942e140baafb9418d09c5afd5952480b9fd4024ed41f161ba06c91b3ae4a372",
      "scope": "上一轮Dynaconf/双通道实现，配置仍在根.env；被本轮配置归属修订替代，原证据保留不改写",
      "evidence_paths": [
        "docs/evidence/2026-10-19-dynaconf-data-access/architecture.log",
        "docs/evidence/2026-10-19-dynaconf-data-access/diff.log",
        "docs/evidence/2026-10-19-dynaconf-data-access/docs.log",
        "docs/evidence/2026-10-19-dynaconf-data-access/file-cli.log",
        "docs/evidence/2026-10-19-dynaconf-data-access/links.log",
        "docs/evidence/2026-10-19-dynaconf-data-access/local-mcp.md",
        "docs/evidence/2026-10-19-dynaconf-data-access/packaging.md",
        "docs/evidence/2026-10-19-dynaconf-data-access/plugin.log",
        "docs/evidence/2026-10-19-dynaconf-data-access/quality.log",
        "docs/evidence/2026-10-19-dynaconf-data-access/registry.log",
        "docs/evidence/2026-10-19-dynaconf-data-access/review.md",
        "docs/evidence/2026-10-19-dynaconf-data-access/ruff.log",
        "docs/evidence/2026-10-19-dynaconf-data-access/tests.log",
        "docs/evidence/2026-10-19-dynaconf-data-access/validation.md"
      ],
      "status": "superseded_pending_revalidation"
    },
    {
      "fingerprint": "1d65b717f90bafca919ca433cd1aeb3764330cef65ba94fc27f4302dcd0f7424",
      "status": "rejected_by_independent_review",
      "scope": "配置归属初审发现O01/P1并发迁移删除及O02/P2 TOML误改；现已修复重验，旧80项结果不继承为新候选证据"
    }
  ]
}
```
