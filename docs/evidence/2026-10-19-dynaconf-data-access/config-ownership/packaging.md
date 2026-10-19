# 配置归属最终安装包验证

uv build --wheel成功（exit 0）；仓外以-I优先加载包内模块，用合成旧根.env验证实际macOS原子迁移、默认新位置加载及资源。未使用真实配置，不连数据库。新模板只从config/.env.example构建资源。

```text
usage: ncc-data data [-h]
                     {status,scopes,scope,definitions,search,get,history,revision,facts,create,update,edit,retire,apply}
                     ...

positional arguments:
  {status,scopes,scope,definitions,search,get,history,revision,facts,create,update,edit,retire,apply}
    status              只读连接与schema状态，不返回凭据
    scopes              读取范围凭据可访问的作品/资料范围

options:
  -h, --help            show this help message and exit
wheel-only imports, packaged defaults, config/.env default priority, atomic exclusive legacy migration, immutable init 0600, isolated environment, single -test derivation, 9 read-only structured MCP tools, direct CLI parser: passed; no database connection attempted

{"wheel_sha256": "3fc95f1af91fa43705cdfad40958d264aaec4d23006ce4e6b3038d9f6123e920", "package_members": 77, "historical_migrations_unchanged": 4, "private_configs_packaged": false}
exit_code=0
```

完整探针：

```python
import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

root = Path('/Users/xuyun/Documents/ncc-workflow')
wheel = root / 'dist/ncc_data-4.0.0-py3-none-any.whl'
base = 'ac0fc44990a4f8c8e8d22a3a0a4a0540c4446393'
with tempfile.TemporaryDirectory(prefix='ncc-dynaconf-wheel-') as temporary:
    work = Path(temporary).resolve()
    package = work / 'wheel'
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        archive.extractall(package)
        assert names.count('ncc_shared/resources/settings.toml') == 1
        assert archive.read('ncc_shared/resources/settings.toml') == (root / 'config/default/settings.toml').read_bytes()
        assert archive.read('ncc_shared/resources/dotenv.example') == (root / 'config/.env.example').read_bytes()
        assert not any(name.endswith('/.env') or '.mcp.json' in name or '.codex/' in name for name in names)
        versions = [name for name in names if '/migrations/versions/' in name and name.endswith('.py')]
        assert len(versions) == 4
        for name in versions:
            old = subprocess.check_output(['git', 'show', base + ':src/' + name], cwd=root)
            assert old == archive.read(name) == (root / 'src' / name).read_bytes()
    code = r'''
import asyncio
import importlib
import os
import stat
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from dynaconf import Dynaconf
from ncc_shared.configuration import initialize, load_settings, template
from ncc_data.runtime.settings import Settings
from ncc_data.mcp.server import create_server
from ncc_data.cli.main import main
import ncc_shared
assert Path(ncc_shared.__file__).resolve().is_relative_to(Path(sys.argv[1]).resolve())
config = Path.cwd() / 'config/.env'
values = template()
values.update({'NCC_DATABASE_URL': 'postgresql://synthetic:secret@db.invalid:5432/synthetic', 'NCC_SESSION_HOURS': '12', 'NCC_API_TOKEN': 'synthetic-cli', 'NCC_MCP_TOKEN': 'synthetic-mcp'})
before = dict(os.environ)
legacy = Path.cwd() / ".env"
assert initialize(legacy, values=values)
legacy_bytes = legacy.read_bytes()
assert initialize(values=values)
assert not legacy.exists()
assert config.read_bytes() == legacy_bytes
original = config.read_bytes()
assert not initialize(config, values={'NCC_DATABASE_URL': 'ignored'})
assert config.read_bytes() == original
assert stat.S_IMODE(config.stat().st_mode) == 0o600
manager = load_settings(environ={})
assert isinstance(manager, Dynaconf)
assert manager.SESSION_HOURS == 12 and manager.PUBLIC_ORIGIN == 'http://127.0.0.1:8787'
settings = Settings.load(environ={})
assert settings.api_token == 'synthetic-cli' and settings.mcp_token == 'synthetic-mcp'
assert Settings.load(profile='test', environ={}).database_url.endswith('/synthetic-test')
assert dict(os.environ) == before
async def discover():
    tools = await create_server(config).list_tools()
    assert len(tools) == 9
    assert all(tool.outputSchema and tool.annotations.readOnlyHint for tool in tools)
asyncio.run(discover())
try:
    main(['data', '--help'])
except SystemExit as result:
    assert result.code == 0
else:
    raise AssertionError('help should exit')
print('wheel-only imports, packaged defaults, config/.env default priority, atomic exclusive legacy migration, immutable init 0600, isolated environment, single -test derivation, 9 read-only structured MCP tools, direct CLI parser: passed; no database connection attempted')
'''
    result = subprocess.run([str(root / '.venv/bin/python'), '-I', '-c', code, str(package)], cwd=work, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print(result.stdout)
    if result.returncode:
        raise SystemExit(result.returncode)
    print(json.dumps({'wheel_sha256': hashlib.sha256(wheel.read_bytes()).hexdigest(), 'package_members': len(names), 'historical_migrations_unchanged': len(versions), 'private_configs_packaged': False}, ensure_ascii=False))

```
