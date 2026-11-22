#!/usr/bin/env python3
"""起点白金连载引擎与战前沙盘升级自测。"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TEST_ROOT = Path(__file__).resolve().parent
SCRIPTS_ROOT = TEST_ROOT.parent
REPO_ROOT = SCRIPTS_ROOT.parent
STATE = str(SCRIPTS_ROOT / "ncc_state.py")
CHECK = str(SCRIPTS_ROOT / "check_chapter.py")

PLATINUM_CARD = """# ch-{seq:04d} 场景卡

## 场景 1
- 视角：陆言　盲区：不知王管事已暗中勾结外门执事
- 切入点：王管事把催命账册拍在石桌上后三秒
- 目标：保住三号矿洞管事权　阻碍：王管事握有清退令，陆言手握火耗假账铁证
- 第一手受挫：陆言搬出矿规申诉，王管事直接亮出执事堂手令封嘴
- 翻转：从「被迫交印」到「反拿王管事贪墨死穴」
- 两难：当场掀翻假账（代价：彻底得罪执事堂）还是忍气吞声（代价：三日后被清退惨死）
- 情感：先憋后燃，爽
- 画面：染血算盘砸碎在火盆里
- 风险：赌上内门晋升资格；二阶后果：执事堂连夜派护法下场彻查
- 配角速写：王老五｜私货小算盘：想顺手昧下两钱碎银给儿子抓药｜盲区：以为陆言必倒台｜口癖：爱捻袖口铜扣
- 默认写法：主角爆发灵气一拳打飞管事，全场震惊
- 关键节拍：掀出假账暗记的瞬间
- 章尾断章：绝境悬刀钩——矿洞外忽然亮起执事堂血色警戒灯
- 本场必须发生：{must}
"""

CHAR_CARD = """# 陆言
## 一句话
寒门矿奴出身的阵纹学徒
## 欲望
攒够百枚灵石赎回妹妹
## 需要
学会信任真正并肩的同伴
## 恐惧
重回任人宰割的底层矿坑
## 伤口
父亲因顶替矿难黑锅惨死
## 信错的那句话
所有同伴在利益面前都会背叛
## 内在矛盾
极度谨慎惜命 vs 见到底层受难忍不住出手
## 声音
「账算不清，今天谁也别出这个门。」
## 标志细节
左手拇指总摩挲父亲留下的半截铁尺
## 关系
| 对象 | 他欠对方什么 | 他怕对方什么 | 他想从对方那里得到什么 |
|---|---|---|---|
| 王老五 | 曾受一饭之恩 | 怕他嘴碎泄密 | 套出库房值守排班 |
## 弧光
正向：从谁也不信的矿奴到敢把后背交给同伴的破局者
"""


def run(*args, script=STATE):
    r = subprocess.run([sys.executable, script, *map(str, args)], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


class TestPlatinumUpgrade(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.book = Path(self.tmp.name) / "白金测试书"
        code, out = run("init", self.book, "--title", "白金测试书", "--genre", "仙侠,悬疑", "--mode", "混合")
        self.assertEqual(code, 0, out)

    def tearDown(self):
        self.tmp.cleanup()

    def ok(self, *args, script=STATE):
        code, out = run(*args, script=script)
        self.assertEqual(code, 0, out)
        return out

    def bad(self, *args, code=1, script=STATE):
        c, out = run(*args, script=script)
        self.assertEqual(c, code, out)
        return out

    def write(self, rel: str, text: str) -> Path:
        p = self.book / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, "utf-8")
        return p

    def test_three_line_foreshadowing_cover_mask_and_truth_leak_guard(self):
        out = self.ok(
            "promise", "add", self.book,
            "--type", "伏笔", "--line", "暗线", "--strength", "5",
            "--content", "青铜残片的来历", "--ch", "1", "--window", "5-12",
            "--cover", "矿洞捡到的生锈青铜垫片，用来垫瘸腿石桌",
            "--truth", "上古坠仙殿阵眼核心钥匙碎片",
        )
        self.assertIn("FS-0001", out)
        self.assertIn("暗线", out)

        lst = self.ok("promise", "list", self.book, "--line", "暗线")
        self.assertIn("FS-0001 [伏笔·暗线]", lst)
        self.assertIn("伪装:矿洞捡到的生锈青铜垫片", lst)

        # 第 2 章擦碰该暗线（未揭晓）：写手包必须带明面伪装，且绝不能含里层真相
        self.ok("chapter", "add", self.book, 1, "--file", "04-正文/第0001章-起局.md")
        self.write("04-正文/第0001章-起局.md", "夜雨滂沱，矿洞深处寒气刺骨。" * 220)
        self.write("02-大纲/场景卡/ch-0001.md", PLATINUM_CARD.format(seq=1, must="捡起垫片"))
        self.ok("scene", "review", self.book, 1, "--result", "pass", "--by", "author")
        self.ok("chapter", "pick", self.book, 1, "--version", "A")
        self.ok("complete", self.book, 1, "--words", 3000, "--hard", "pass")

        self.ok("chapter", "add", self.book, 2, "--file", "04-正文/第0002章-暗涌.md")
        self.ok("promise", "touch", self.book, "FS-0001", "--ch", "2", "--note", "石桌垫片在火光下微热")
        self.write("02-大纲/场景卡/ch-0002.md", PLATINUM_CARD.format(seq=2, must="顺手扶正石桌下的垫片"))
        self.ok("scene", "review", self.book, 2, "--result", "pass", "--by", "author")
        self.ok("pack", self.book, 2)
        pack2 = (self.book / ".ncc/写手包/ch-0002.md").read_text("utf-8")
        self.assertIn("明面细节埋设", pack2)
        self.assertIn("矿洞捡到的生锈青铜垫片", pack2)
        self.assertNotIn("上古坠仙殿阵眼核心钥匙碎片", pack2)

        # 若场景卡误写入未揭晓的里层真相（含短词），pack 必须拦截
        self.write("02-大纲/场景卡/ch-0002.md", PLATINUM_CARD.format(seq=2, must="露出上古坠仙殿阵眼核心钥匙碎片"))
        self.ok("scene", "review", self.book, 2, "--result", "pass", "--by", "author")
        err = self.bad("pack", self.book, 2)
        self.assertIn("未揭晓伏笔真相", err)

        # 真实写章正序：在 Step 3 跑 pack 时尚未 promise resolve，通过场景卡显式标「伏笔回收：FS-0001」即可无死锁注入真相
        self.write("02-大纲/场景卡/ch-0002.md", PLATINUM_CARD.format(seq=2, must="阵眼共鸣\n- 伏笔回收：FS-0001"))
        self.ok("scene", "review", self.book, 2, "--result", "pass", "--by", "author")
        self.ok("pack", self.book, 2)
        pack2_reveal = (self.book / ".ncc/写手包/ch-0002.md").read_text("utf-8")
        self.assertIn("伏笔回收揭晓：上古坠仙殿阵眼核心钥匙碎片", pack2_reveal)

        # 第 3 章完成 resolve 后，若回头重打第 1 章（早于揭晓章）且混入真相，仍须拦截
        self.ok("promise", "resolve", self.book, "FS-0001", "--ch", "2", "--note", "阵眼共鸣揭开真相")
        self.write("02-大纲/场景卡/ch-0001.md", PLATINUM_CARD.format(seq=1, must="捡到上古坠仙殿阵眼核心钥匙碎片"))
        self.ok("scene", "review", self.book, 1, "--result", "pass", "--by", "author")
        err_hist = self.bad("pack", self.book, 1)
        self.assertIn("未揭晓伏笔真相", err_hist)

    def test_dark_line_cooling_alert_in_reader_now_and_brief(self):
        self.ok("promise", "add", self.book, "--type", "伏笔", "--line", "暗线",
                "--content", "血衣老祖失踪之谜", "--ch", "1", "--cover", "残破血色袖标")
        rn_early = self.ok("reader-now", self.book, 5)
        self.assertNotIn("暗线暗香提醒", rn_early)

        rn_cool = self.ok("reader-now", self.book, 10)
        self.assertIn("暗线暗香提醒", rn_cool)
        self.assertIn("FS-0001", rn_cool)
        self.assertIn("已沉底 9 章", rn_cool)

        self.ok("brief", self.book, "--role", "outliner", "--seq", "10")
        brief_txt = (self.book / ".ncc/派单/outliner-ch-0010.md").read_text("utf-8")
        self.assertIn("暗线冷却预警", brief_txt)
        self.assertIn("FS-0001", brief_txt)

    def test_plight_unit_locks_character_living_details_and_arc_pack(self):
        self.write("01-设定/人物卡/陆言.md", CHAR_CARD)
        self.ok("soul", self.book, "--arc", "正向", "--arc-stage", "裂痕初现")
        self.ok("plight", self.book,
                "--overhead", "外门清退死规压顶",
                "--peers", "王管事暗中做假账嫁祸",
                "--shortfall", "距赎回妹妹还差八十灵石",
                "--leverage", "独掌矿脉火耗真账本")
        # 真实连载正序：Step 0 先 unit open 指定 --arc-ch 4，Step 1 再 chapter add 4，仍自动标为关键章
        self.ok("unit", "open", self.book, "--start", "4", "--title", "矿脉死局",
                "--countdown", "距离外门清退大考仅剩7天",
                "--milestone", "夺下三号矿洞主事印并晋升凝气四层",
                "--arc-ch", "4")
        self.ok("chapter", "add", self.book, 4, "--file", "04-正文/第0004章-破局.md")

        # arc-ch 自动标记为关键章
        d = json.loads((self.book / "book.json").read_text("utf-8"))
        ch4 = next(c for c in d["chapters"] if c["seq"] == 4)
        self.assertTrue(ch4["key"])

        self.write("02-大纲/场景卡/ch-0004.md", PLATINUM_CARD.format(seq=4, must="逼王老五当众作证"))
        self.ok("scene", "review", self.book, 4, "--result", "pass", "--by", "author")
        self.ok("pack", self.book, 4)
        pack = (self.book / ".ncc/写手包/ch-0004.md").read_text("utf-8")

        # 验证标志细节、人物关系、弧光反差提示、配角活人算盘、单元推进锁、四维处境全部进入写手包
        self.assertIn("标志细节：左手拇指总摩挲父亲留下的半截铁尺", pack)
        self.assertIn("关系：", pack)
        self.assertIn("行为反差张力", pack)
        self.assertIn("裂痕初现", pack)
        self.assertIn("场内配角活人算盘", pack)
        self.assertIn("王老五｜私货小算盘", pack)
        self.assertIn("悬顶倒计时：距离外门清退大考仅剩7天", pack)
        self.assertIn("头顶恶规／大山：外门清退死规压顶", pack)
        self.assertIn("唯一生门／支点：独掌矿脉火耗真账本", pack)

        # render 同步更新续写状态卡与 author-intent.md
        focus = (self.book / "current-focus.md").read_text("utf-8")
        intent = (self.book / "author-intent.md").read_text("utf-8")
        self.assertIn("外门清退死规压顶", focus)
        self.assertIn("当前刻度：裂痕初现", intent)

    def test_cross_chapter_hook_handoff_pack_and_warning(self):
        self.ok("chapter", "add", self.book, 1, "--file", "04-正文/第0001章-悬刀.md")
        self.write("04-正文/第0001章-悬刀.md", "风雪交加，陆言握紧铁尺退到崖边。" * 210)
        self.write("02-大纲/场景卡/ch-0001.md", PLATINUM_CARD.format(seq=1, must="退到断魂崖边"))
        self.ok("scene", "review", self.book, 1, "--result", "pass", "--by", "author")
        self.ok("chapter", "hook", self.book, 1, "--type", "绝境悬刀钩", "--intensity", "5", "--line", "玄铁重剑裹着寒光当头劈落")
        self.ok("chapter", "end", self.book, 1, "--time", "子夜", "--place", "断魂崖", "--next", "正面招架玄铁重剑绝杀")
        self.ok("chapter", "pick", self.book, 1, "--version", "A")
        self.ok("complete", self.book, 1, "--words", 3150, "--hard", "pass")

        self.ok("chapter", "add", self.book, 2, "--file", "04-正文/第0002章-反杀.md")
        self.write("02-大纲/场景卡/ch-0002.md", PLATINUM_CARD.format(seq=2, must="借崖边冰棱卸力反刺"))
        self.ok("scene", "review", self.book, 2, "--result", "pass", "--by", "author")
        self.ok("pack", self.book, 2)
        pack2 = (self.book / ".ncc/写手包/ch-0002.md").read_text("utf-8")
        self.assertIn("章首 300 字秒接", pack2)
        self.assertIn("绝境悬刀钩", pack2)
        self.assertIn("玄铁重剑裹着寒光当头劈落", pack2)

        # 若第 2 章开头完全切镜头写无关日常，check_chapter 给出跨章断章承接告警
        self.ok("promise", "add", self.book, "--type", "悬念", "--content", "神秘黑衣人身份", "--ch", "2")
        self.ok("chapter", "hook", self.book, 2, "--type", "半步揭晓钩", "--intensity", "4")
        filler = "".join(f"清晨集市热闹第{i}摊开张卖热汤面。" for i in range(1, 240))
        self.write("04-正文/第0002章-反杀.md", filler)
        code, res_raw = run(self.book, 2, script=CHECK)
        self.assertEqual(code, 0, res_raw)
        res = json.loads(res_raw)
        self.assertTrue(any("跨章断章承接" in w for w in res["warnings"]), res["warnings"])

        # 开头正面承接玄铁重剑，告警消失
        connected = "玄铁重剑贴着眉骨劈落，陆言横起半截铁尺硬生生架开锋刃。" + "".join(f"山风呼啸碎石滚落第{i}道崖缝。" for i in range(1, 280))
        self.write("04-正文/第0002章-反杀.md", connected)
        code2, res_raw2 = run(self.book, 2, script=CHECK)
        self.assertEqual(code2, 0, res_raw2)
        res2 = json.loads(res_raw2)
        self.assertFalse(any("跨章断章承接" in w for w in res2["warnings"]), res2["warnings"])

    def test_pre_battle_sandbox_preview_and_diagnostics(self):
        self.write("00-策划/赛道白金母本.md", "# 仙侠悬疑苟道母本\n- 核心杠杆：账本死穴反杀\n")
        self.ok("plight", self.book, "--overhead", "清退令", "--leverage", "真账本")
        self.ok("unit", "open", self.book, "--start", "1", "--title", "开局三章破冰",
                "--countdown", "3日交账", "--milestone", "站稳矿洞")
        self.ok("promise", "add", self.book, "--type", "爽点欠账", "--line", "明线",
                "--content", "当众反拿王管事", "--ch", "1", "--desire", "1")
        self.ok("promise", "add", self.book, "--type", "伏笔", "--line", "暗线",
                "--content", "矿底古阵异动", "--ch", "1", "--cover", "矿镐震麻虎口的寒铁声", "--truth", "镇魔封界松动")

        for seq in (1, 2, 3):
            self.ok("chapter", "add", self.book, seq, "--file", f"04-正文/第{seq:04d}章-试炼.md")
            self.ok("chapter", "mood", self.book, seq, "压", "--colors", "虐")
            ref = "P-0001 与 FS-0001 交汇" if seq == 2 else "推进矿洞排查"
            self.write(f"02-大纲/场景卡/ch-{seq:04d}.md", PLATINUM_CARD.format(seq=seq, must=ref))

        # 只读运行 sandbox 不产生操作日志写入，且准确输出三线交织、连压预警与赛道母本挂载
        oplog = self.book / ".ncc/操作日志.jsonl"
        before_lines = oplog.read_text("utf-8").splitlines() if oplog.exists() else []
        preview = self.ok("sandbox", self.book, "--from", "1", "--to", "3")
        after_lines = oplog.read_text("utf-8").splitlines() if oplog.exists() else []
        self.assertEqual(len(before_lines), len(after_lines))
        self.assertIn("已挂载专属 `00-策划/赛道白金母本.md`", preview)
        self.assertIn("明·暗·灰三线交织进度表", preview)
        self.assertIn("镇魔封界松动", preview)
        self.assertIn("连压憋屈预警", preview)
        self.assertIn("**明暗交织达标**：第 1、2 章", preview)
        self.assertIn("钩型「绝境悬刀钩」", preview)

        # --write 写入生成区块并保留出品人战前调优拍板手写内容
        self.ok("sandbox", self.book, "--from", "1", "--to", "3", "--write")
        sb_file = self.book / "00-策划/沙盘/单元-U1.md"
        self.assertTrue(sb_file.is_file())
        edited = sb_file.read_text("utf-8").replace("确认开战／调整后开战（待填）", "出品人拍板：第 2 章提前给一次反击小爽！")
        sb_file.write_text(edited, "utf-8")
        self.ok("sandbox", self.book, "--from", "1", "--to", "3", "--write")
        refreshed = sb_file.read_text("utf-8")
        self.assertIn("出品人拍板：第 2 章提前给一次反击小爽！", refreshed)

        # 防丢稿脏检查：若误改了生成区块内部表格，不带 --force 拒绝覆盖；底层台账变动重刷则提示复核
        tampered = refreshed.replace("清退令", "手工误改区块内文字")
        sb_file.write_text(tampered, "utf-8")
        dirty_err = self.bad("sandbox", self.book, "--from", "1", "--to", "3", "--write")
        self.assertIn("生成区块被手工修改过", dirty_err)
        self.ok("plight", self.book, "--overhead", "清退死令升级")
        self.ok("sandbox", self.book, "--from", "1", "--to", "3", "--write", "--force")
        stale_warned = sb_file.read_text("utf-8")
        self.assertIn("底层台账或场景卡已变更", stale_warned)
        self.assertIn("出品人拍板：第 2 章提前给一次反击小爽！", stale_warned)

        # Grill-Me 铁律与全网框架校验：活跃暗线封顶 5 条超载报警 ＋ 10 章单元中点攻守锚与「十章一响」检查
        for k in range(2, 7):
            self.ok("promise", "add", self.book, "--type", "伏笔", "--line", "暗线",
                    "--content", f"第{k}条暗线谜团", "--ch", "1", "--cover", f"旧物{k}")
        ten_ch_preview = self.ok("sandbox", self.book, "--from", "4", "--to", "13")
        self.assertIn("单元五拍中点锚：第 8 章", ten_ch_preview)
        self.assertIn("中点反守为攻", ten_ch_preview)
        self.assertIn("暗线池超载预警", ten_ch_preview)
        self.assertIn("十章一响提醒", ten_ch_preview)

        # 验证高潮章单场兑现 ≥2 条线索时触发「多线雪崩合拢达标」识别
        self.write("02-大纲/场景卡/ch-0012.md", PLATINUM_CARD.format(seq=12, must="终局掀桌\n- 伏笔回收：FS-0001、P-0001"))
        converge_preview = self.ok("sandbox", self.book, "--from", "4", "--to", "13")
        self.assertIn("**多线雪崩合拢达标**：第 12 章", converge_preview)
        self.assertNotIn("十章一响提醒", converge_preview)


if __name__ == "__main__":
    unittest.main()
