#!/usr/bin/env python3
"""素材库治理行为测试：适配标准、全库覆盖、实际交付、过期与原地恢复。"""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

import ncc_prepare
from ncc_library import Library

SCRIPT = Path(__file__).with_name("ncc_prepare.py")


class LibraryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.work, self.source, self.target = self.root / "工作", self.root / "杂库", self.root / "整理库"
        self.write("杂库/杂记.md", "# 港口\n港口税收用于维护灯塔。港务员在涨潮前开闸。\n")
        self.write("杂库/散记.md", "# 市集\n摊位牌记录出售物品；潮城夜市实行轮换。\n")
        self.ok("init", "--title", "素材库治理", "--purpose", "形成严谨且可写作取用的库")
        self.ok("source", self.source)
        self.ok("scan")
        self.ids = {r["relative"]: r["id"] for r in self.index()["files"]}
        self.profile = {
            "name": "资料与虚构混合库",
            "organization": "条目按用途建立主归属；性质区分参考与虚构；导航引用，不重复维护内容。",
            "types": {
                "条目": {"match": ["条目/*.md"], "required": ["编号", "性质", "依据", "用途", "范围"],
                         "enum": {"性质": ["事实资料", "虚构素材"]}, "unique": ["编号"], "namespace": ["范围"]},
                "导航": {"match": ["导航.md"], "required": []}},
            "indexes": ["导航.md"]}
        self.set_profile()
        self.contents = {
            "条目/港口.md": "# 港口\n编号：A1\n性质：事实资料\n依据：杂记.md 的示例记录\n用途：港口税收与岗位描写\n范围：示例城市\n\n港口税收用于维护灯塔。港务员在涨潮前开闸。\n",
            "条目/市集.md": "# 市集\n编号：A2\n性质：虚构素材\n依据：散记.md 中的作者构思\n用途：潮城夜市情节\n范围：潮城\n\n摊位牌记录出售物品；潮城夜市实行轮换。\n",
            "导航.md": "# 导航\n- [[条目/港口]]\n- [市集](条目/市集.md#市集)\n"}

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, path, text):
        p = self.root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def json_file(self, path, value):
        return self.write(path, json.dumps(value, ensure_ascii=False))

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

    def data(self):
        return json.loads((self.work / "prepare.json").read_text())

    def index(self):
        return json.loads((self.work / ".ncc-prepare/index.json").read_text())

    def set_profile(self):
        self.ok("library-profile", "--file", self.json_file("规范.json", self.profile), "--reason", "作者授权按用途治理")

    def plan_value(self):
        return {"goal": "治理整个混合素材库", "target": str(self.target), "mode": "copy",
                "entries": [{"source": self.ids["杂记.md"], "disposition": "transformed", "reason": "整理示例资料并保留独有内容", "outputs": ["条目/港口.md"]},
                            {"source": self.ids["散记.md"], "disposition": "transformed", "reason": "虚构内容单列范围", "outputs": ["条目/市集.md"]}],
                "batches": [{"name": "港口资料", "operation": "library-refactor", "sources": [self.ids["杂记.md"]]},
                            {"name": "市集与导航", "operation": "library-curate", "sources": [self.ids["散记.md"]], "new_outputs": ["导航.md"]}],
                "queries": [{"words": ["港口", "税收"], "expected": ["条目/港口.md"]}]}

    def plan(self, value=None):
        self.ok("library-plan", "--file", self.json_file("计划.json", value or self.plan_value()), "--reason", "作者授权执行本库规范")
        return self.data()["library"]["plans"][-1]["id"]

    def batch(self, plan, batch):
        b = next(b for b in self.data()["library"]["plans"][-1]["batches"] if b["id"] == batch)
        files = {x: str(self.write("草稿/" + x, self.contents[x])) for x in b["outputs"]}
        self.ok("library-batch", "--plan", plan, "--batch", batch, "--file", self.json_file(batch + ".json", {"files": files}),
                "--report", self.write(batch + ".md", "# 逐来源检查\n读取了本批全部原文；税收、灯塔、涨潮和摊位信息按相关来源保留。范围与性质已区分，关联由导航维护。\n"),
                "--by", "当前执行者加载 curator", "--execution", "current")

    def complete(self, value=None):
        plan = self.plan(value)
        for b in self.data()["library"]["plans"][-1]["batches"]:
            self.batch(plan, b["id"])
        self.review(plan)
        return plan

    def review(self, plan):
        return self.ok("library-review", "--plan", plan, "--file", self.write("全库复核.md", "# 全库复核\n逐来源核查独有信息保留，参考与虚构范围明确，字段满足规范。导航可取用港口税收与市集岗位内容，已读全部原文及成果，当前范围无阻塞问题。\n"), "--result", "pass", "--by", "实际复核者")

    def test_full_governance_publishes_real_content_and_is_idempotent(self):
        original = {p.name: p.read_bytes() for p in self.source.glob("*.md")}
        plan = self.plan()
        packet = Path(self.ok("library-packet", "--plan", plan, "--batch", "B-0001").strip())
        self.assertIn("library-refactor", packet.read_text())
        self.assertIn(self.ids["杂记.md"], packet.read_text())
        self.assertIn("来源", packet.read_text())
        self.batch(plan, "B-0001")
        self.assertIn("未完成", self.bad("library-check", "--plan", plan))
        self.assertIn("B-0002", self.ok("status"))
        self.batch(plan, "B-0002")
        self.review(plan)
        self.ok("library-check", "--plan", plan)
        self.ok("library-apply", "--plan", plan, "--authorization", "向这个新库交付")
        self.assertEqual((self.target / "条目/港口.md").read_text(), self.contents["条目/港口.md"])
        self.assertEqual(original, {p.name: p.read_bytes() for p in self.source.glob("*.md")})
        self.ok("library-check", "--plan", plan)
        self.assertIn("条目/港口.md", self.ok("library-find", "--plan", plan, "港口", "税收"))
        self.assertIn("未重复", self.ok("library-apply", "--plan", plan, "--authorization", "沿用交付授权"))
        self.assertFalse((self.work / "book.json").exists())

    def test_in_place_restructure_archives_originals_and_checks_real_target(self):
        value = self.plan_value()
        value.update(mode="in-place", target=str(self.source))
        plan = self.complete(value)
        self.ok("library-apply", "--plan", plan, "--authorization", "按已验收清单整理源库")
        self.assertFalse((self.source / "杂记.md").exists())
        self.assertTrue((self.source / "条目/港口.md").exists())
        backup = self.work / ".ncc-prepare/library" / plan / "backup/杂记.md"
        self.assertIn("涨潮", backup.read_text())
        self.ok("library-check", "--plan", plan)
        (self.source / "条目/港口.md").write_text("作者的新版本")
        self.assertIn("变化", self.bad("library-check", "--plan", plan))

    def test_partial_coverage_and_unassigned_source_are_rejected(self):
        value = self.plan_value()
        value["entries"].pop()
        self.assertIn("覆盖", self.bad("library-plan", "--file", self.json_file("漏项.json", value), "--reason", "治理"))
        value = self.plan_value()
        value["batches"].pop()
        self.assertIn("覆盖", self.bad("library-plan", "--file", self.json_file("漏批.json", value), "--reason", "治理"))

    def test_unread_and_deferred_cannot_masquerade_as_whole_library_done(self):
        self.write("杂库/图片.bin", "未识别内容")
        self.ok("scan")
        ident = next(r["id"] for r in self.index()["files"] if r["relative"] == "图片.bin")
        value = self.plan_value()
        value["entries"].append({"source": ident, "disposition": "deferred", "reason": "等待转换", "outputs": []})
        value["batches"].append({"name": "未读格式", "operation": "library-audit", "sources": [ident]})
        plan = self.plan(value)
        for b in self.data()["library"]["plans"][-1]["batches"]:
            self.batch(plan, b["id"])
        self.assertIn("未完成来源", self.bad("library-review", "--plan", plan, "--file", self.write("检查.md", "实际仍有未读内容"), "--result", "pass", "--by", "检查者"))

    def test_source_change_addition_profile_change_and_report_change_invalidate(self):
        plan = self.complete()
        self.write("杂库/新增.md", "新增资料")
        self.assertIn("范围已变化", self.bad("library-check", "--plan", plan))
        (self.source / "新增.md").unlink()
        self.ok("library-check", "--plan", plan)
        rec = self.data()["library"]["plans"][-1]["review"]
        (self.work / rec["path"]).write_text("改动报告")
        self.assertIn("报告", self.bad("library-check", "--plan", plan))
        self.review(plan)
        self.profile["organization"] += " 新的分类决定。"
        self.set_profile()
        self.assertIn("规范已变化", self.bad("library-check", "--plan", plan))

    def test_output_change_and_incomplete_batch_do_not_pass(self):
        plan = self.complete()
        stage = self.work / ".ncc-prepare/library" / plan / "staging"
        (stage / "条目/港口.md").write_text("手改未经登记")
        self.assertIn("变化", self.bad("library-check", "--plan", plan))
        self.batch(plan, "B-0001")
        self.assertIn("检查", self.bad("library-check", "--plan", plan))
        self.review(plan)
        self.ok("library-check", "--plan", plan)

    def test_audit_reports_links_ids_fields_orphans_and_number_conflicts(self):
        self.profile = {"name": "显式规则库", "organization": "字段与单位按本库规则制定",
                        "types": {"规则": {"match": ["*.md"], "required": ["编号"], "unique": ["编号"]}},
                        "indexes": ["导航.md"], "constraints": [{"left": {"path": "规则.md", "field": "总量"}, "op": "eq", "right": {"path": "条目.md", "field": "份量"}, "factor": 4}]}
        self.set_profile()
        auditroot = self.root / "待查"
        self.write("待查/导航.md", "# 导航\n编号：N\n[[规则]] [[条目]] [[不存在]]\n")
        self.write("待查/规则.md", "# 规则\n编号：A\n总量：12\n")
        self.write("待查/条目.md", "# 条目\n编号：A\n份量：2\n[[规则#缺标题]]\n")
        self.write("待查/孤儿.md", "独有内容")
        self.ok("library-audit", "--target", auditroot)
        rec = self.data()["library"]["audits"][-1]
        report = json.loads((self.work / rec["path"]).read_text())
        codes = {r["code"] for r in report["findings"]}
        self.assertTrue({"broken-link", "broken-anchor", "duplicate-id", "required", "orphan", "numeric-conflict"} <= codes, codes)
        self.assertTrue(all(r["line"] >= 1 for r in report["findings"]))

    def test_different_libraries_worlds_and_schemas_do_not_force_shared_ids(self):
        self.profile = {"name": "多个世界", "organization": "按世界范围区分编号",
                        "types": {"词条": {"match": ["**/*.md"], "required": ["id", "world"], "unique": ["id"], "namespace": ["world"]}}}
        self.set_profile()
        self.write("杂库/杂记.md", "---\nid: A1\nworld: 东城\n---\n# 码头\n[[R-0002::码头]]\n")
        self.write("杂库/散记.md", "---\nid: A1\nworld: 西城\n---\n# 码头\n西城的同号实体\n")
        other = self.write("另一库/码头.md", "---\nid: A1\nworld: 东城\n---\n# 码头\n另一个库命名空间\n").parent
        self.ok("source", other)
        self.ok("library-audit")
        rec = self.data()["library"]["audits"][-1]
        report = json.loads((self.work / rec["path"]).read_text())
        self.assertFalse(report["findings"], report["findings"])

    def test_retrieval_failure_and_orphan_prevent_acceptance(self):
        value = self.plan_value()
        value["queries"][0]["words"] = ["找不到的词"]
        plan = self.plan(value)
        for b in self.data()["library"]["plans"][-1]["batches"]:
            self.batch(plan, b["id"])
        self.assertIn("取用未命中", self.bad("library-review", "--plan", plan, "--file", self.write("复核.md", "复核"), "--result", "pass", "--by", "检查者"))
        self.contents["导航.md"] = "# 导航\n[[条目/港口]]\n"
        self.batch(plan, "B-0002")
        self.assertIn("无法到达", self.bad("library-review", "--plan", plan, "--file", self.root / "复核.md", "--result", "pass", "--by", "检查者"))

    def test_path_escape_and_existing_destination_are_rejected(self):
        value = self.plan_value()
        value["entries"][0]["outputs"] = ["../外部.md"]
        self.assertIn("不合法", self.bad("library-plan", "--file", self.json_file("越界.json", value), "--reason", "整理"))
        plan = self.complete()
        self.target.mkdir()
        self.write("整理库/作者资料.md", "不得覆盖")
        self.assertIn("已存在", self.bad("library-apply", "--plan", plan, "--authorization", "交付新库"))
        self.assertEqual((self.target / "作者资料.md").read_text(), "不得覆盖")

    def test_false_retention_and_cross_batch_shared_output_are_rejected(self):
        value = self.plan_value()
        value["entries"][0]["disposition"] = "retained"
        plan = self.plan(value)
        b = self.data()["library"]["plans"][-1]["batches"][0]
        files = {x: str(self.write("伪保留.md", self.contents[x])) for x in b["outputs"]}
        self.assertIn("retained", self.bad("library-batch", "--plan", plan, "--batch", b["id"], "--file", self.json_file("批.json", {"files": files}), "--report", self.write("批.md", "报告"), "--by", "执行者", "--execution", "current"))
        value = self.plan_value()
        value["entries"][1]["outputs"] = ["条目/港口.md"]
        self.assertIn("一个输出", self.bad("library-plan", "--file", self.json_file("冲突.json", value), "--reason", "整理"))

    def test_interrupted_in_place_apply_restores_backups_and_preserves_external_changes(self):
        value = self.plan_value()
        value.update(mode="in-place", target=str(self.source))
        originals = {p.name: p.read_bytes() for p in self.source.glob("*.md")}
        plan = self.complete(value)
        atomic = ncc_prepare.atomic
        count = 0
        def fail_second_write(path, data):
            nonlocal count
            if path.is_relative_to(self.source):
                count += 1
                if count == 2:
                    raise OSError("合成交付中断")
            atomic(path, data)
        with patch.object(ncc_prepare, "atomic", side_effect=fail_second_write):
            with self.assertRaisesRegex(ValueError, "交付中断"):
                Library(ncc_prepare).apply(SimpleNamespace(work=self.work, plan=plan, authorization="测试中断恢复"))
        self.assertTrue(self.data()["library"]["plans"][-1]["transaction"])
        self.assertIn("先 library-restore", self.bad("library-check", "--plan", plan))
        changed = next(p for p in self.source.rglob("*.md") if p.relative_to(self.source).as_posix() in self.contents)
        saved = changed.read_bytes()
        changed.write_text("外部人工修改，应保留")
        self.assertIn("外部改动", self.bad("library-restore", "--plan", plan, "--authorization", "恢复"))
        self.assertEqual(changed.read_text(), "外部人工修改，应保留")
        changed.write_bytes(saved)
        self.ok("library-restore", "--plan", plan, "--authorization", "恢复本次中断")
        self.assertEqual(originals, {p.name: p.read_bytes() for p in self.source.glob("*.md")})
        self.assertFalse(changed.exists())
        self.ok("library-check", "--plan", plan)
        self.ok("library-apply", "--plan", plan, "--authorization", "恢复后重新执行")
        self.ok("library-check", "--plan", plan)

    def test_copy_interruption_can_be_recovered_without_losing_delivered_content(self):
        plan = self.complete()
        lib = Library(ncc_prepare)
        fingerprint = lib.fingerprint
        def fail_final_inventory(rows):
            d = self.data()["library"]["plans"][-1]
            if self.target.exists() and d["transaction"]:
                raise OSError("交付后记录中断")
            return fingerprint(rows)
        with patch.object(lib, "fingerprint", side_effect=fail_final_inventory):
            with self.assertRaises(OSError):
                lib.apply(SimpleNamespace(work=self.work, plan=plan, authorization="合成新库交付"))
        self.assertTrue((self.target / "条目/港口.md").exists())
        self.ok("library-restore", "--plan", plan, "--authorization", "恢复中断交付")
        self.assertFalse(self.target.exists())
        archive = self.work / ".ncc-prepare/library" / plan / "interrupted-copy/条目/港口.md"
        self.assertEqual(archive.read_text(), self.contents["条目/港口.md"])
        self.ok("library-apply", "--plan", plan, "--authorization", "重新交付")
        self.ok("library-check", "--plan", plan)

    def test_changed_root_and_file_directory_collision_are_rejected(self):
        value = self.plan_value()
        value.update(mode="in-place", target=str(self.source))
        value["entries"][0]["outputs"] = ["杂记.md/子条目.md"]
        value["queries"][0]["expected"] = ["杂记.md/子条目.md"]
        self.assertIn("路径冲突", self.bad("library-plan", "--file", self.json_file("冲突结构.json", value), "--reason", "整理结构"))
        plan = self.complete()
        original = self.root / "原库"
        self.source.rename(original)
        self.source.symlink_to(original, target_is_directory=True)
        self.assertIn("重定向", self.bad("library-check", "--plan", plan))
        self.assertEqual((original / "杂记.md").read_text(), "# 港口\n港口税收用于维护灯塔。港务员在涨潮前开闸。\n")


if __name__ == "__main__":
    unittest.main()
