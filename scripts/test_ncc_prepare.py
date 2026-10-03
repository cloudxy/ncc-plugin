#!/usr/bin/env python3
"""独立创作准备的行为测试：空白创建、只读来源、版本失效与范围交接。"""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from ncc_prepare import TASKS


SCRIPT = Path(__file__).with_name("ncc_prepare.py")


class PreparationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.work = self.root / "准备"
        self.ok("init", "--title", "通用准备", "--purpose", "创建可复用资料与独立世界设定", "--scope", "当前主题")

    def tearDown(self):
        self.tmp.cleanup()

    def call(self, command, *args):
        return subprocess.run([sys.executable, "-B", str(SCRIPT), command, str(self.work), *map(str, args)],
                              capture_output=True, text=True)

    def ok(self, command, *args):
        r = self.call(command, *args)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout

    def bad(self, command, *args):
        r = self.call(command, *args)
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout + r.stderr

    def write(self, name, text):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def data(self):
        return json.loads((self.work / "prepare.json").read_text("utf-8"))

    def item(self, task="setting-create", scope=None, extra=()):
        p = self.write("草稿.md", "# 潮城\n港口由市民与航运行会共管。行会缴纳维修费，遇到停航仍需支付维护成本。\n")
        args = ["--file", p, "--title", "潮城港口", "--task", task, "--nature", "fiction", "--basis", "按作者给定的共治方向创建"]
        if scope:
            args += ["--scope", scope]
        self.ok("item", *args, *extra)
        return self.data()["items"][-1]["id"]

    def accept(self, ident):
        self.ok("decide", ident, "--state", "accepted", "--reason", "作者授权按共治目标创建，本范围收下")

    def review(self, scope=None):
        p = self.write("检查.md", "# 范围检查\n已读港口设定及费用关系，行会权限与承担的成本一致；停航有维护费约束。无当前范围阻塞。外海航路留待后续主题处理。\n")
        args = ["--file", p, "--result", "pass", "--by", "设定核对"]
        if scope:
            args += ["--scope", scope]
        return self.ok("review", *args)

    def source(self):
        p = self.write("资料/港口.md", "# 港口记录\n| 机构 | 职责 |\n|---|---|\n| 市民会 | 批准费用 |\n| 航运行会 | 维护码头 |\n")
        self.ok("source", p.parent)
        self.ok("scan")
        idx = json.loads((self.work / ".ncc-prepare/index.json").read_text("utf-8"))
        return p, next(r["id"] for r in idx["files"] if r["status"] == "readable")

    def test_blank_start_all_six_tasks_and_handoff(self):
        for task in TASKS:
            self.accept(self.item(task))
        self.assertFalse((self.work / "book.json").exists())
        self.assertFalse((self.work / "01-设定").exists())
        self.assertIn("语义检查", self.bad("check"))
        self.review()
        self.assertIn("PASS", self.ok("check"))
        output = Path(self.ok("export").strip()).read_text("utf-8")
        for label in TASKS.values():
            self.assertIn(label, output)
        self.assertIn("市民与航运行会", output)
        self.assertIn("不是写手包", output)

    def test_empty_scope_cannot_pass(self):
        self.assertIn("没有成果", self.bad("check"))
        p = self.write("报告.md", "已检查目录。")
        self.assertIn("没有成果", self.bad("review", "--file", p, "--result", "pass", "--by", "作者"))
        self.assertIn("暂不能交接", self.bad("export"))

    def test_scan_is_read_only_reports_duplicates_and_unsupported(self):
        a = self.write("资料/a.md", "# 名录\n共同条目\n")
        b = self.write("资料/b.md", a.read_text())
        pdf = self.root / "资料/图谱.pdf"; pdf.write_bytes(b"%PDF-test")
        bad = self.root / "资料/旧编码.txt"; bad.write_bytes(b"\xff\xfe\x00")
        (a.parent / "循环").symlink_to(a.parent, target_is_directory=True)
        initial = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in (a, b, pdf, bad)}
        self.ok("source", a.parent)
        r = json.loads(self.ok("scan"))
        self.assertEqual(r["coverage"], {"readable": 2, "unsupported": 1, "unreadable": 1, "link": 1})
        self.assertEqual(len(r["duplicate_groups"]), 1)
        self.assertEqual(initial, {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in (a, b, pdf, bad)})
        a.unlink()
        r = json.loads(self.ok("scan"))
        self.assertEqual(r["coverage"]["missing"], 1)
        self.assertEqual(r["changes"]["missing"], 1)

    def test_scan_excludes_own_state_and_outputs(self):
        self.write("准备/原始.md", "# 原始资料\n城市\n")
        self.item()
        self.ok("source", self.work)
        r = json.loads(self.ok("scan"))
        self.assertEqual(r["coverage"], {"readable": 1})
        second = json.loads(self.ok("scan"))
        self.assertEqual(second["changes"], {"unchanged": 1})

    def test_source_references_and_freshness_without_rescan(self):
        p, sid = self.source()
        draft = self.write("整理稿.md", "# 港口职责编排\n市民会审批，航运行会维护。\n")
        args = ["--file", draft, "--title", "机构职责", "--task", "material-organize", "--nature", "fact", "--basis", "按记录整理"]
        self.assertIn("必须带来源", self.bad("item", *args))
        self.assertIn("范围无效", self.bad("item", *args, "--ref", f"{sid}:2-100"))
        self.ok("item", *args, "--ref", f"{sid}:2-5")
        self.accept("P-0001"); self.review()
        self.assertIn("PASS", self.ok("check"))
        p.write_text(p.read_text() + "后来由商会接管。\n", encoding="utf-8")
        self.assertIn("来源", self.bad("check"))
        self.assertIn("来源", self.bad("export"))
        self.assertIn("来源已改变", self.bad("show", sid))
        self.ok("scan")
        self.assertIn("来源", self.bad("check"))

    def test_search_and_show_preserve_table_rows(self):
        p, sid = self.source()
        self.assertIn(sid, self.ok("search", "批准", "费用"))
        out = self.ok("show", sid, "--start", "2", "--end", "5")
        self.assertIn("| 机构 | 职责 |", out)
        self.assertIn("| 市民会 | 批准费用 |", out)
        self.assertNotIn("# 港口记录", out)
        self.assertIn("范围无效", self.bad("show", sid, "--start", "0"))

    def test_blocker_cannot_be_hidden_by_deferral(self):
        ident = self.item(); self.accept(ident)
        self.ok("issue", "--kind", "gap", "--text", "缺维修费用", "--evidence", "当前设定未给费用安排", "--next", "补费用机制", "--item", ident, "--blocking")
        self.assertIn("阻塞", self.bad("check"))
        self.assertIn("触发点", self.bad("resolve", "Q-0001", "--state", "deferred", "--reason", "以后补"))
        self.ok("resolve", "Q-0001", "--state", "deferred", "--reason", "以后补", "--until", "进入港口时")
        self.assertIn("阻塞", self.bad("check"))
        self.ok("resolve", "Q-0001", "--state", "resolved", "--reason", "维护费关系已补全")
        self.review(); self.ok("check")

    def test_creation_issue_can_bind_new_output(self):
        self.ok("issue", "--kind", "creation", "--text", "还没有城市制度", "--evidence", "从空白开始", "--next", "创建共治制度", "--blocking")
        ident = self.item(); self.accept(ident)
        self.ok("resolve", "Q-0001", "--state", "resolved", "--reason", "完整制度已创建", "--item", ident)
        self.assertEqual(self.data()["issues"][0]["items"], [ident])
        self.review(); self.ok("check")
        changed = self.write("修改稿.md", "# 港口制度修订\n市民会仅提案，最终费用由轮值会议决定。\n")
        self.item(extra=("--id", ident, "--file", changed))
        self.accept(ident)
        self.assertIn("关闭依据已变", self.bad("check"))

    def test_revision_archives_content_and_invalidates_acceptance(self):
        ident = self.item(); self.accept(ident); self.review()
        p = self.work / self.data()["items"][0]["path"]
        original = p.read_bytes()
        p.write_text("# 修改的共治制度\n改由轮值理事会管理。\n", encoding="utf-8")
        self.assertIn("成果已修改", self.bad("check"))
        self.ok("item", "--id", ident, "--file", p, "--title", "潮城", "--task", "setting-improve", "--nature", "fiction", "--basis", "作者要求完善治理结构")
        self.assertEqual(self.data()["items"][0]["state"], "candidate")
        history = list((self.work / ".ncc-prepare/history").glob("*.md"))
        self.assertIn(original, [p.read_bytes() for p in history])
        self.assertIn("尚未采用", self.bad("check"))
        self.accept(ident)
        self.assertIn("已过期", self.bad("check"))
        self.review(); self.ok("check")

    def test_unrelated_future_blocker_does_not_block_current_scope(self):
        self.accept(self.item())
        self.ok("issue", "--kind", "gap", "--text", "外海航路未定", "--evidence", "后续主题", "--next", "进入外海时创建", "--scope", "远海", "--blocking")
        self.review(); self.ok("check")
        self.assertIn("没有成果", self.bad("check", "--scope", "远海"))

    def test_dependencies_propagate_across_scopes(self):
        base = self.item(scope="通用世界"); self.accept(base)
        self.accept(self.item(extra=("--depends", base)))
        self.review(); self.ok("check")
        self.ok("decide", base, "--state", "rejected", "--reason", "基础规则需要重做")
        self.assertIn("尚未采用", self.bad("check"))
        self.assertIn("暂不能交接", self.bad("export"))

    def test_inference_and_empty_evidence_cannot_be_accepted(self):
        p = self.write("推演.md", "# 推演\n本地区可能由三个组织共同管理。\n")
        args = ["--file", p, "--title", "待核治理", "--task", "material-create", "--nature", "inference", "--basis", "未经核实的分析"]
        self.ok("item", *args)
        self.assertIn("推演仍未核实", self.bad("decide", "P-0001", "--state", "accepted", "--reason", "收下"))
        self.assertIn("不能为空", self.bad("decide", "P-0001", "--state", "shelved", "--reason", " "))
        empty = self.write("空.md", " \n")
        self.assertIn("正文", self.bad("item", *args, "--file", empty))
        self.assertEqual(len(self.data()["items"]), 1)

    def test_review_report_tampering_invalidates_handoff(self):
        self.accept(self.item()); self.review(); self.ok("check")
        report = self.work / self.data()["reviews"]["当前主题"]["report"]
        report.write_text("已经改过检查结论", encoding="utf-8")
        self.assertIn("报告被修改", self.bad("check"))

    def test_symlink_output_cannot_write_outside_workspace(self):
        outside = self.root / "外部目录"; outside.mkdir()
        (self.work / "成果").symlink_to(outside, target_is_directory=True)
        self.assertIn("越出", self.bad("item", "--file", self.write("新稿.md", "原创设定"), "--title", "新稿", "--task", "setting-create", "--nature", "fiction", "--basis", "用户要求"))
        self.assertEqual(list(outside.iterdir()), [])
        self.assertEqual(self.data()["items"], [])

    def test_replaced_source_root_is_not_followed(self):
        p, sid = self.source()
        base = p.parent
        moved = self.root / "移走的原资料"
        base.rename(moved)
        base.symlink_to(moved, target_is_directory=True)
        self.assertIn("来源变成了链接", self.bad("show", sid))
        result = json.loads(self.ok("scan"))
        self.assertEqual(result["coverage"], {"missing": 1})
        self.assertIn("来源根已变成符号链接", result["errors"][0])


if __name__ == "__main__":
    unittest.main()
