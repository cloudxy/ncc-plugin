#!/usr/bin/env python3
"""ncc_eval.py 匿名盲审派单、多源锚定集、断章钩机检、反例防御与单轮/多轮评分自测。"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TEST_ROOT = Path(__file__).resolve().parent
SCRIPTS_ROOT = TEST_ROOT.parent
REPO_ROOT = SCRIPTS_ROOT.parent
sys.path.insert(0, str(SCRIPTS_ROOT))
import ncc_eval as ne  # noqa: E402
from tests.test_ncc_state import EVAL, run  # noqa: E402


class TestNccEvalBlindAndPlatinum(unittest.TestCase):
    def test_blind_packets_isolate_manifest_strip_headings_and_support_multi_anchor_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            extra = root / "platinum-suite"
            p01 = extra / "P01"
            p03 = extra / "P03"
            p01.mkdir(parents=True)
            p03.mkdir(parents=True)

            # 即使源文件标题误带题号或多级标题，prepare 也须在入包时剥离，不向评审暴露提示。
            (p01 / "台账.md").write_text("#### P01\n- 时代背景：古代\n- 视角：沈砚（第三人称限知）\n", "utf-8")
            (p01 / "场景卡.md").write_text("# P01 场景卡\n## 场景 1\n- 视角：沈砚\n- 翻转：绝处脱身\n- 两难：弃图还是受剑\n", "utf-8")
            (p01 / "正文.md").write_text(
                "# 第八章 晨粥\n\n次日清晨，外门膳堂的木桶刚揭开盖，热气混着米糠味扑面而来。"
                + "沈砚排在队伍末尾，听前面两个杂役念叨昨夜柴房漏雨。" * 14
                + "\n\n至于昨晚石室里那场虚惊，早已被他抛在脑后。\n",
                "utf-8",
            )
            (p01 / "answers.json").write_text(json.dumps({
                "id": "P01",
                "suite": "承诺",
                "era": "古代",
                "seq": 8,
                "prev_hook": {
                    "type": "悬剑钩",
                    "intensity": 5,
                    "line": "玄铁闸门轰然砸落，周烈剑尖已抵住咽喉",
                    "next": "石室剑下脱身保住残图",
                },
                "verdict": "fail",
                "mech": ["跨章断章承接"],
                "expected": [{
                    "id": "d1",
                    "category": "情节承诺",
                    "severity": "critical",
                    "quotes": ["次日清晨，外门膳堂的木桶刚揭开盖"],
                    "desc": "未正面承接上章高强断章钩",
                }],
            }, ensure_ascii=False), "utf-8")

            (p03 / "台账.md").write_text("- 时代背景：古代\n- 视角：沈砚（第三人称限知）\n", "utf-8")
            (p03 / "场景卡.md").write_text("## 场景 1\n- 视角：沈砚\n- 翻转：扣牌放行\n- 两难：损参还是被押\n", "utf-8")
            (p03 / "正文.md").write_text(
                "# 第十章 宵禁\n\n巷口火把噼啪作响，黑衣捕头的刀锋已抵在药箱铜扣上：“搜他药箱！”\n\n"
                "沈砚稳住脚步，将药箱横在身前。\n",
                "utf-8",
            )
            (p03 / "answers.json").write_text(json.dumps({
                "id": "P03",
                "suite": "对照",
                "era": "古代",
                "seq": 10,
                "prev_hook": {
                    "type": "悬剑钩",
                    "intensity": 4,
                    "line": "巷口火把齐亮，黑衣捕头刀锋一指：“搜他药箱！”",
                    "next": "沈砚应对捕头搜箱",
                },
                "verdict": "pass",
                "mech": [],
                "mech_clean": True,
                "expected": [],
            }, ensure_ascii=False), "utf-8")

            code, out = run("mech", "--anchors-dir", REPO_ROOT / "eval/anchors", "--anchors-dir", extra, script=EVAL)
            self.assertEqual(code, 0, out)
            self.assertIn("PASS P01", out)
            self.assertIn("PASS P03", out)

            admin_dir = root / "admin-audit-secret-name"
            isolated_packets = root / "isolated-packets"
            code, out = run(
                "prepare", admin_dir, "--runs", 2,
                "--anchors-dir", REPO_ROOT / "eval/anchors",
                "--anchors-dir", extra,
                "--packets-dir", isolated_packets,
                script=EVAL,
            )
            self.assertEqual(code, 0, out)
            self.assertFalse((isolated_packets / "manifest.json").exists())
            pkts = sorted(isolated_packets.glob("*.md"))
            self.assertEqual(len(pkts), 16)  # (6 + 2) * 2
            man = json.loads((admin_dir / "manifest.json").read_text("utf-8"))
            self.assertEqual(man["anchor_dirs"][0], "eval/anchors")
            for pkt in pkts:
                content = pkt.read_text("utf-8")
                self.assertNotIn("admin-audit-secret-name", content)
                self.assertNotIn("干净对照", content)
                self.assertNotIn("P01", content)
                self.assertNotIn("P03", content)

            # 故意漏交一份 P01 r2 报告，并在另一份报告中使用加粗判决与转义竖线，核实鲁棒性。
            for code_id, meta in man["blind"].items():
                if meta["anchor"] == "P01" and meta["run"] == 2:
                    continue
                if meta["anchor"] in ("A06-干净对照", "P03"):
                    rep = "**硬伤层**: 通过\n\n| # | 类别 | 严重度 | 正文引用 | 问题 | 推荐处置与理由 |\n|---|---|---|---|---|---|\n| 1 | 无 | | | 无 | |\n"
                else:
                    rep = "**硬伤层**：不通过\n\n| # | 类别 | 严重度 | 正文引用 | 问题 | 推荐处置与理由 |\n|---|---|---|---|---|---|\n| 1 | 情节承诺 | critical | 「次日清晨，外门膳堂的木桶刚揭开盖」 | 切镜头\\|未接断章 | 改 |\n"
                (admin_dir / "reports" / f"{code_id}.md").write_text(rep, "utf-8")

            # 从仓库外任意工作目录调用 score，验证相对路径可移植解析。
            sp = subprocess.run([sys.executable, EVAL, "score", str(admin_dir)], cwd=root, capture_output=True, text=True)
            self.assertEqual(sp.returncode, 0, sp.stdout + sp.stderr)
            self.assertIn("缺报告（1 份）", sp.stdout)
            self.assertIn("（P01 r2）", sp.stdout)
            self.assertIn("单轮基线（r1，收回 8/8 份）", sp.stdout)

    def test_story_noun_in_anchor_suffix_does_not_false_block_while_invalid_runs_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            suite_dir = root / "custom"
            a07 = suite_dir / "A07-手表"
            a07.mkdir(parents=True)
            (a07 / "台账.md").write_text("- 时代背景：古代\n- 视角：陆言\n", "utf-8")
            (a07 / "场景卡.md").write_text("# A07-手表 场景卡\n## 场景 1\n- 视角：陆言\n", "utf-8")
            (a07 / "正文.md").write_text("# A07-手表\n\n掌柜低头看了看手表。\n", "utf-8")
            (a07 / "answers.json").write_text(json.dumps({
                "id": "A07-手表",
                "suite": "底蕴",
                "era": "古代",
                "verdict": "fail",
                "mech": ["时代错置词"],
                "expected": [{"id": "d1", "category": "底蕴", "severity": "major",
                              "quotes": ["看了看手表"], "desc": "古代背景出现现代手表"}],
            }, ensure_ascii=False), "utf-8")

            self.assertEqual(run("prepare", root / "bad0", "--runs", 0, "--anchors-dir", suite_dir, script=EVAL)[0], 1)
            self.assertEqual(run("prepare", root / "badneg", "--runs", -2, "--anchors-dir", suite_dir, script=EVAL)[0], 1)

            rd = root / "good"
            code, out = run("prepare", rd, "--runs", 1, "--anchors-dir", suite_dir, script=EVAL)
            self.assertEqual(code, 0, out)
            pkt = (rd / "packets" / "M01.md").read_text("utf-8")
            self.assertIn("掌柜低头看了看手表。", pkt)
            self.assertNotIn("A07-手表", pkt)
            self.assertNotIn("古代背景出现现代手表", pkt)

            verdict, obs = ne.parse_report("**硬伤层: 不通过**\n\n| # | 类别 | 严重度 | 正文引用 | 问题 | 推荐处置与理由 |\n|---|---|---|---|---|---|\n| 1 | 底蕴 | major | 「看了看\\|手表」 | 错置 | 改 |\n")
            self.assertEqual(verdict, "fail")
            self.assertEqual(obs[0]["cite"], "「看了看|手表」")

    def test_legacy_unblinded_manifest_remains_scorable(self):
        with tempfile.TemporaryDirectory() as tmp:
            rd = Path(tmp) / "legacy"
            (rd / "reports").mkdir(parents=True)
            (rd / "manifest.json").write_text(json.dumps({
                "anchors": ["A06-干净对照"],
                "runs": 1,
                "suite": "对照",
                "created": "2026-10-12T00:00:00",
            }, ensure_ascii=False), "utf-8")
            (rd / "reports" / "A06-干净对照-r1.md").write_text(
                "硬伤层: 通过\n\n| # | 类别 | 严重度 | 正文引用 | 问题 | 推荐处置与理由 |\n|---|---|---|---|---|---|\n| 1 | 无 | | | 无 | |\n",
                "utf-8",
            )
            code, out = run("score", rd, script=EVAL)
            self.assertEqual(code, 0, out)
            self.assertIn("结论准确率（通过／不通过判对）：1/1（100%）", out)
            self.assertIn("干净章误报（critical／major）：0 条", out)


if __name__ == "__main__":
    unittest.main()
