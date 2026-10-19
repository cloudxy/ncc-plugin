"""Exercise real HTTP working-copy cutover with a synthetic legacy book only."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import httpx


def main():
    root = Path(__file__).resolve().parents[2]
    origin = "http://127.0.0.1:8787"
    with httpx.Client(base_url=origin, timeout=120) as client:
        user = (
            client.post(
                "/api/v1/auth/login",
                headers={"x-ncc-client": "console"},
                json={"username": "browser-author", "password": "synthetic-browser-password"},
            )
            .raise_for_status()
            .json()
        )
        headers = {"x-csrf-token": user["csrf"]}
        sid = (
            client.post("/api/v1/scopes", headers=headers, json={"name": "CLI合成验收"})
            .raise_for_status()
            .json()["id"]
        )
        token = (
            client.post(
                f"/api/v1/scopes/{sid}/tokens",
                headers=headers,
                json={"actions": ["read", "edit", "adopt", "export", "secret"], "hours": 1},
            )
            .raise_for_status()
            .json()["token"]
        )
        env = dict(os.environ, NCC_API_URL=origin, NCC_API_TOKEN=token)
        with tempfile.TemporaryDirectory(prefix="ncc-cli-private-") as tmp:
            original = Path(tmp) / "original"
            work = Path(tmp) / "checkout"

            def run(args, private=False):
                result = subprocess.run(args, cwd=root, env=env, text=True, capture_output=True)
                assert result.returncode == 0, (args[-2:], result.stdout, result.stderr)
                return result.stdout

            cli = [sys.executable, str(root / "scripts/ncc_state.py")]
            run([*cli, "init", str(original), "--title", "合成CLI书"])
            body = original / "04-正文/ch-0001.md"
            body.write_text("# 第一章 合成测试\n\n少年走到渡口。\n")
            run([*cli, "chapter", "add", str(original), "1", "--file", "04-正文/ch-0001.md"])
            data = [sys.executable, "-m", "ncc_data.cli", "workspace"]
            run([*data, "import", str(original), "--scope", sid])
            run([*data, "bind", str(work), "--scope", sid])
            assert (work / ".ncc-database.json").exists()
            run([*cli, "status", str(work)])
            run(
                [
                    *cli,
                    "promise",
                    "add",
                    str(work),
                    "--type",
                    "悬念",
                    "--content",
                    "谁留下了这把剑",
                    "--ch",
                    "1",
                ]
            )
            (work / "04-正文/ch-0001.md").write_text("# 第一章 合成测试\n\n作者主动改写了这一段。\n")
            run([*cli, "status", str(work)])
            page = (
                client.post(
                    f"/api/v1/scopes/{sid}/entities/search", headers=headers, json={"kind": "chapter"}
                )
                .raise_for_status()
                .json()
            )
            assert len(page["items"]) == 1
            eid = page["items"][0]["id"]
            entity = client.get(f"/api/v1/scopes/{sid}/entities/{eid}").raise_for_status().json()
            assert "作者主动改写" in entity["text"]
            run([*data, "pull", str(work), "--scope", sid])
            assert "作者主动改写" in (work / "04-正文/ch-0001.md").read_text()
            assert "少年走到渡口" in body.read_text()
        print(
            json.dumps(
                {
                    "synthetic_only": True,
                    "checks": [
                        "legacy init",
                        "shadow import",
                        "explicit bind",
                        "CLI read",
                        "promise write",
                        "external author edit",
                        "typed chapter sync",
                        "safe pull",
                        "original preserved",
                    ],
                },
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
