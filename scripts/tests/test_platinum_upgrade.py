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

    def test_w01_w07_dropped_promise_truth_isolation_and_template_placeholder_guard(self):
        # W01: 暗线在第 2 章作废并补偿，第 2 章写手包只出公开补偿、绝不泄露真义；第 3 章场景卡照抄真义必须拦截
        self.ok(
            "promise", "add", self.book,
            "--type", "伏笔", "--line", "暗线", "--strength", "4",
            "--content", "残镜背面血印", "--ch", "1",
            "--cover", "铜镜背面的朱砂旧印",
            "--truth", "太上长老夺舍血契真名",
        )
        self.ok("promise", "drop", self.book, "FS-0001", "--ch", "2", "--compensation", "铜镜在斗法中碎裂化为凡铁")
        for seq in (1, 2, 3):
            self.ok("chapter", "add", self.book, seq, "--file", f"04-正文/第{seq:04d}章.md")
        # W07: 官方模板说明、占位符与否定描述均不授权揭晓
        self.ok(
            "promise", "add", self.book,
            "--type", "伏笔", "--line", "暗线", "--strength", "5",
            "--content", "矿底寒铁锁链", "--ch", "1",
            "--cover", "拴在废井口的冷铁链",
            "--truth", "仙界贬谪罪龙锁魂链",
        )
        ch2_card = PLATINUM_CARD.format(
            seq=2,
            must=(
                "铜镜碎裂\n"
                "- 伏笔回收：<本场显式揭晓兑现的承诺编号，如 FS-0001；仅擦碰推进不揭晓时勿填>\n"
                "- 备注：本场暂不揭晓 FS-0002，留到卷末回收"
            ),
        )
        self.write("02-大纲/场景卡/ch-0002.md", ch2_card)
        self.ok("scene", "check", self.book, 2)
        self.ok("scene", "review", self.book, 2, "--result", "pass", "--by", "author")
        self.ok("pack", self.book, 2)
        pack2 = (self.book / ".ncc/写手包/ch-0002.md").read_text("utf-8")
        self.assertIn("承诺作废补偿交代", pack2)
        self.assertIn("铜镜在斗法中碎裂化为凡铁", pack2)
        self.assertNotIn("太上长老夺舍血契真名", pack2)
        self.assertNotIn("伏笔回收揭晓", pack2)
        self.assertNotIn("仙界贬谪罪龙锁魂链", pack2)

        # 第 3 章场景卡照抄已作废伏笔真义：scene check 与 pack 均须拦截
        self.write("02-大纲/场景卡/ch-0003.md", PLATINUM_CARD.format(seq=3, must="识破太上长老夺舍血契真名"))
        bad_check = self.bad("scene", "check", self.book, 3)
        self.assertIn("已作废", bad_check)
        # 显式把已作废编号填入伏笔回收同样拦截
        self.write("02-大纲/场景卡/ch-0003.md", PLATINUM_CARD.format(seq=3, must="强行揭晓\n- 伏笔回收：FS-0001"))
        bad_drop_rev = self.bad("scene", "check", self.book, 3)
        self.assertIn("已作废承诺: FS-0001", bad_drop_rev)

    def test_w02_w03_sandbox_missing_or_corrupt_signature_and_persistent_stale_review(self):
        self.ok("plight", self.book, "--overhead", "三日清退令", "--leverage", "火耗真账")
        self.ok("unit", "open", self.book, "--start", "1", "--title", "破冰", "--countdown", "三天")
        self.ok("chapter", "add", self.book, 1, "--file", "04-正文/第0001章.md")
        self.write("02-大纲/场景卡/ch-0001.md", PLATINUM_CARD.format(seq=1, must="亮出账册"))
        self.ok("sandbox", self.book, "--from", "1", "--to", "3", "--write")
        sb_file = self.book / "00-策划/沙盘/单元-U1.md"
        orig = sb_file.read_text("utf-8")

        # W02a: 移除签名并手改段落 -> 普通 --write 必须拒绝覆盖并保留原件
        no_sig = orig.split("<!-- ncc:sandbox-sha")[0] + "手改补充备注\n<!-- ncc:生成区块 结束 -->\n\n## 出品人战前调优拍板\n- 拍板A\n"
        sb_file.write_text(no_sig, "utf-8")
        err_missing = self.bad("sandbox", self.book, "--from", "1", "--to", "3", "--write")
        self.assertIn("缺少生成区块签名", err_missing)
        self.assertEqual(sb_file.read_text("utf-8"), no_sig)

        # W02b: 损坏签名 -> 普通 --write 必须拒绝覆盖并保留原件
        corrupt_sig = orig.replace("<!-- ncc:sandbox-sha ", "<!-- ncc:sandbox-sha BROKEN_")
        sb_file.write_text(corrupt_sig, "utf-8")
        err_corrupt = self.bad("sandbox", self.book, "--from", "1", "--to", "3", "--write")
        self.assertIn("签名已损坏", err_corrupt)
        self.assertEqual(sb_file.read_text("utf-8"), corrupt_sig)

        # W03: 恢复正常沙盘，作者拍板后改台账，连续重刷两次，待复核告警必须保留，直到作者更新拍板或 --ack-review
        signed_off = orig.replace("确认开战／调整后开战（待填）", "第一版拍板：同意开战")
        sb_file.write_text(signed_off, "utf-8")
        self.ok("plight", self.book, "--overhead", "清退令提前到今夜")
        self.ok("sandbox", self.book, "--from", "1", "--to", "3", "--write")
        first_refresh = sb_file.read_text("utf-8")
        self.assertIn("底层台账或场景卡已变更", first_refresh)
        # 原样再刷新一次，告警绝不能消失！
        self.ok("sandbox", self.book, "--from", "1", "--to", "3", "--write")
        second_refresh = sb_file.read_text("utf-8")
        self.assertIn("底层台账或场景卡已变更", second_refresh)
        self.assertIn("第一版拍板：同意开战", second_refresh)

        # R06/W03: 沙盘之外随手补普通备忘再刷新，绝不能清除待复核状态；只有明确复核当前沙盘摘要或对当前摘要执行 --ack-review 才解除
        import re as _re
        cur_sha = _re.search(r"<!-- ncc:sandbox-sha ([0-9a-f]{16})", second_refresh).group(1)
        casual_memo = second_refresh + "\n- 随手备忘：明晚补一条茶馆闲笔\n"
        sb_file.write_text(casual_memo, "utf-8")
        self.ok("sandbox", self.book, "--from", "1", "--to", "3", "--write")
        after_casual = sb_file.read_text("utf-8")
        self.assertIn("底层台账或场景卡已变更", after_casual)
        self.assertIn("随手备忘：明晚补一条茶馆闲笔", after_casual)

        # 作者在拍板区明确写入「已复核：<当前沙盘摘要>」后刷新 -> 告警解除
        reviewed = after_casual.replace(
            "第一版拍板：同意开战",
            f"第二版复核拍板：按今夜死限开战（已复核：{cur_sha}）",
        )
        sb_file.write_text(reviewed, "utf-8")
        self.ok("sandbox", self.book, "--from", "1", "--to", "3", "--write")
        cleared = sb_file.read_text("utf-8")
        self.assertNotIn("底层台账或场景卡已变更", cleared)
        self.assertIn(f"已复核：{cur_sha}", cleared)

        # 再次改台账后，未先刷新直接带 --ack-review 必须拒绝；先刷新看到新快照后再 --ack-review 方可解除
        self.ok("plight", self.book, "--overhead", "清退令再次升级为立斩")
        blind_ack = self.bad("sandbox", self.book, "--from", "1", "--to", "3", "--write", "--ack-review")
        self.assertIn("请先不带 --ack-review 刷新查看新沙盘", blind_ack)
        self.ok("sandbox", self.book, "--from", "1", "--to", "3", "--write")
        self.assertIn("底层台账或场景卡已变更", sb_file.read_text("utf-8"))
        self.ok("sandbox", self.book, "--from", "1", "--to", "3", "--write", "--ack-review")
        self.assertNotIn("底层台账或场景卡已变更", sb_file.read_text("utf-8"))

    def test_w04_w05_w06_w08_chapter_scoped_unit_window_converge_and_complete_gate(self):
        # 准备第 1–5 章已定稿
        import re as _re
        for seq in range(1, 6):
            rel = f"04-正文/第{seq:04d}章.md"
            self.ok("chapter", "add", self.book, seq, "--file", rel, "--origin", "author")
            self.write(rel, "陆言执铁尺破局斩敌，火光映照寒潭。" * 210)
            self.write(f"02-大纲/场景卡/ch-{seq:04d}.md", PLATINUM_CARD.format(seq=seq, must=f"第{seq}章推进"))
            self.ok("scene", "review", self.book, seq, "--result", "pass", "--by", "author")
            if seq <= 3:
                self.ok("chapter", "pick", self.book, seq, "--version", "A")
            len_out = self.ok("chapter", "length", self.book, seq, "--accept")
            actual_words = int(_re.search(r"(\d+)\s*字", len_out).group(1))
            self.ok("complete", self.book, seq, "--words", actual_words, "--hard", "pass", "--decidable", "0.95")

        # W04: 第 6 章开启新单元并登记新处境，重新生成第 2 章写手包不能读出第 6 章的倒计时与新处境
        self.ok("unit", "open", self.book, "--start", "6", "--title", "内门风云", "--countdown", "内门大比倒计时10天")
        self.ok("plight", self.book, "--overhead", "第6章才出现的内门刑堂追杀令")
        self.ok("pack", self.book, 2)
        pack2 = (self.book / ".ncc/写手包/ch-0002.md").read_text("utf-8")
        self.assertNotIn("内门大比倒计时10天", pack2)
        self.assertNotIn("第6章才出现的内门刑堂追杀令", pack2)
        self.assertIn("隔离", pack2)

        # W05: 预登记第 90 章时，默认沙盘保持 10 章单元窗口（第6–15章），显式 --to 90 时允许扩展
        self.ok("chapter", "add", self.book, 90, "--file", "04-正文/第0090章.md")
        default_sb = self.ok("sandbox", self.book)
        self.assertIn("（第6–15章）", default_sb)
        self.assertNotIn("| 第90章 |", default_sb)
        explicit_sb = self.ok("sandbox", self.book, "--from", "6", "--to", "90")
        self.assertIn("| 第90章 |", explicit_sb)

        # W06: 单场景写入两个不存在的回收编号 -> scene check 拒绝，沙盘不报合拢达标并定位错号
        self.ok("chapter", "add", self.book, 6, "--file", "04-正文/第0006章.md", "--origin", "author")
        self.write("02-大纲/场景卡/ch-0006.md", PLATINUM_CARD.format(seq=6, must="决战\n- 伏笔回收：FS-9998、FS-9999"))
        bad_sc = self.bad("scene", "check", self.book, 6)
        self.assertIn("FS-9998", bad_sc)
        sb_w06 = self.ok("sandbox", self.book)
        self.assertNotIn("多线雪崩合拢达标", sb_w06)
        self.assertIn("错号定位告警", sb_w06)
        self.assertIn("FS-9998", sb_w06)

        # W08: 正文缺失或空白、低可判定率（0.1）均不能 complete，且失败后章节保持原状态
        self.write("02-大纲/场景卡/ch-0006.md", PLATINUM_CARD.format(seq=6, must="决战内门"))
        self.ok("scene", "review", self.book, 6, "--result", "pass", "--by", "author")
        missing_err = self.bad("complete", self.book, 6, "--words", "3200", "--hard", "pass", "--decidable", "0.1")
        self.assertIn("找不到第 6 章正文文件", missing_err)
        d_after = json.loads((self.book / "book.json").read_text("utf-8"))
        ch6 = next(c for c in d_after["chapters"] if c["seq"] == 6)
        self.assertNotEqual(ch6["status"], "done")
        self.assertEqual(ch6["sha"], "")

        self.write("04-正文/第0006章.md", "   \n\n  ")
        blank_err = self.bad("complete", self.book, 6, "--words", "3200", "--hard", "pass", "--decidable", "0.9")
        self.assertIn("空白", blank_err)

        self.write("04-正文/第0006章.md", "陆言踏入内门演武场，剑气冲霄。" * 230)
        len6_out = self.ok("chapter", "length", self.book, 6, "--accept")
        w6 = int(_re.search(r"(\d+)\s*字", len6_out).group(1))
        dec_err = self.bad("complete", self.book, 6, "--words", w6, "--hard", "pass", "--decidable", "0.1")
        self.assertIn("低于下限 0.8", dec_err)
        self.ok("complete", self.book, 6, "--words", w6, "--hard", "pass", "--decidable", "0.9")
        d_done = json.loads((self.book / "book.json").read_text("utf-8"))
        ch6_done = next(c for c in d_done["chapters"] if c["seq"] == 6)
        self.assertEqual(ch6_done["status"], "done")
        self.assertEqual(len(ch6_done["sha"]), 16)

    def test_r06_r07_r08_rework_verifications(self):
        import hashlib as _hashlib

        # --- R06: 第 1 章保存处境并开启 U1 -> 第 5 章关 U1 -> 第 6 章开 U2 并清空当前处境 -> 重打第 2 章写手包与历史沙盘均取 U1 及历史处境快照 ---
        self.ok("plight", self.book, "--overhead", "第1章外门寒铁枷锁", "--leverage", "旧账残页")
        self.ok("unit", "open", self.book, "--start", "1", "--title", "寒门立脚", "--countdown", "三日外门小考", "--milestone", "站稳外门脚跟")
        for seq in range(1, 6):
            rel = f"04-正文/第{seq:04d}章.md"
            self.ok("chapter", "add", self.book, seq, "--file", rel, "--origin", "author")
            self.write(rel, "风雪寒鸦渡，孤灯照旧剑。" * 324)  # 10 汉字/句 × 324 = 3240 汉字（正常区间 3000–5000）
            self.write(f"02-大纲/场景卡/ch-{seq:04d}.md", PLATINUM_CARD.format(seq=seq, must=f"第{seq}章破局"))
            self.ok("scene", "review", self.book, seq, "--result", "pass", "--by", "author")
            if seq <= 3:
                self.ok("chapter", "pick", self.book, seq, "--version", "A")
            self.ok("complete", self.book, seq, "--words", 3240, "--hard", "pass", "--decidable", "0.95")

        rep_out = self.ok("report", self.book, "unit", "--write")
        import re as _re
        rel_rev = _re.search(r"写进\s+(\S+)\s+的生成区块", rep_out).group(1)
        u1_rev_path = self.book / rel_rev
        u1_rev_path.write_text(u1_rev_path.read_text("utf-8").replace("（待填）", "已确认复盘结论"), "utf-8")
        self.ok("unit", "close", self.book, "--end", "5")

        self.ok("unit", "open", self.book, "--start", "6", "--title", "京城暗流", "--countdown", "第6章才开启的七日秋闱死限", "--milestone", "金榜入仕")
        self.ok("plight", self.book, "--clear")

        self.ok("pack", self.book, 2)
        pack2 = (self.book / ".ncc/写手包/ch-0002.md").read_text("utf-8")
        self.assertIn("第1章外门寒铁枷锁", pack2)
        self.assertIn("三日外门小考", pack2)
        self.assertNotIn("七日秋闱死限", pack2)

        hist_sb = self.ok("sandbox", self.book, "--from", "1", "--to", "5")
        self.assertIn("单元 U1《寒门立脚》", hist_sb)
        self.assertIn("三日外门小考", hist_sb)
        self.assertIn("站稳外门脚跟", hist_sb)
        self.assertNotIn("七日秋闱死限", hist_sb)
        self.assertIn("第1章外门寒铁枷锁", hist_sb)

        cur_sb = self.ok("sandbox", self.book, "--from", "6", "--to", "10")
        self.assertIn("单元 U2《京城暗流》", cur_sb)
        self.assertIn("第6章才开启的七日秋闱死限", cur_sb)
        self.assertNotIn("三日外门小考", cur_sb)
        self.assertNotIn("第1章外门寒铁枷锁", cur_sb)

        # --- R07: 同章兑现无场景卡（及跨两场分开回收）不误报同场合拢；延后/批注/否定不授权揭晓，明确本场回收才揭晓 ---
        self.ok("promise", "add", self.book, "--type", "伏笔", "--line", "暗线", "--strength", "5",
                "--content", "青铜罗盘裂纹", "--ch", "1", "--cover", "铜盘裂痕", "--truth", "钦天监星门坐标")
        self.ok("promise", "add", self.book, "--type", "伏笔", "--line", "暗线", "--strength", "4",
                "--content", "旧驿卒断指", "--ch", "2", "--cover", "缺指老卒", "--truth", "前朝影卫统领")
        # 1) 第 7 章两条真实伏笔同章 resolve，但没有任何场景卡 -> 沙盘只报同章多线兑现（未证同场），绝不报同场合拢
        self.ok("promise", "resolve", self.book, "FS-0001", "--ch", "7", "--note", "揭开星门")
        self.ok("promise", "resolve", self.book, "FS-0002", "--ch", "7", "--note", "认出统领")
        sb_no_card = self.ok("sandbox", self.book, "--from", "6", "--to", "10")
        self.assertNotIn("多线雪崩合拢达标", sb_no_card)
        self.assertIn("同章多线兑现（未证同场）", sb_no_card)

        # 2) 第 7 章若有两场分别各收一条（不同场），仍属于同章非同场；排入同一场景才报多线雪崩合拢达标
        split_scenes_card = (
            "# ch-0007 场景卡\n\n## 场景 1\n- 翻转：罗盘裂开\n- 伏笔回收：FS-0001\n\n"
            "## 场景 2\n- 翻转：老卒亮刀\n- 伏笔回收：FS-0002\n"
        )
        self.write("02-大纲/场景卡/ch-0007.md", split_scenes_card)
        sb_split = self.ok("sandbox", self.book, "--from", "6", "--to", "10")
        self.assertNotIn("多线雪崩合拢达标", sb_split)
        self.assertIn("同章多线兑现（未证同场）", sb_split)

        same_scene_card = "# ch-0007 场景卡\n\n## 场景 1\n- 翻转：星门与影卫同场引爆\n- 伏笔回收：FS-0001、FS-0002\n"
        self.write("02-大纲/场景卡/ch-0007.md", same_scene_card)
        sb_same_scene = self.ok("sandbox", self.book, "--from", "6", "--to", "10")
        self.assertIn("**多线雪崩合拢达标**：第 7 章", sb_same_scene)

        # 3) 新增 FS-0003 / FS-0004 测试延后（含括号内带逗号与并列局部延后）、批注、否定 vs 明确本场有效回收（含禁地/不得不等正常叙事词）
        self.ok("promise", "add", self.book, "--type", "伏笔", "--line", "暗线", "--strength", "5",
                "--content", "井底红绳木牌", "--ch", "1", "--cover", "系红绳的榆木腰牌", "--truth", "皇后私印密令")
        self.ok("promise", "add", self.book, "--type", "伏笔", "--line", "暗线", "--strength", "4",
                "--content", "破庙残碑拓片", "--ch", "2", "--cover", "磨损青石拓片", "--truth", "太祖遗诏藏宝图")
        self.ok("chapter", "add", self.book, 6, "--file", "04-正文/第0006章.md", "--origin", "author")
        deferred_card = PLATINUM_CARD.format(
            seq=6,
            must=(
                "井口试探\n"
                "- 伏笔回收：FS-0003（下章再揭晓）\n"
                "- 揭晓伏笔：FS-0003（表面写腰牌，实留到卷末再揭晓）\n"
                "- 兑现承诺：（批注：FS-0003 本场仅擦碰明面伪装）；【注】FS-0004\n"
                "- 本场兑现：暂不回收 FS-0003"
            ),
        )
        self.write("02-大纲/场景卡/ch-0006.md", deferred_card)
        self.ok("scene", "review", self.book, 6, "--result", "pass", "--by", "author")
        self.ok("pack", self.book, 6)
        pack6_def = (self.book / ".ncc/写手包/ch-0006.md").read_text("utf-8")
        self.assertNotIn("皇后私印密令", pack6_def)
        self.assertNotIn("太祖遗诏藏宝图", pack6_def)
        self.assertNotIn("伏笔回收揭晓", pack6_def)
        self.assertIn("系红绳的榆木腰牌", pack6_def)

        # 第 6 章当前章不带真义的同时，核对第 2 章旧章写手包同样不含 FS-0003 / FS-0004 未揭晓真义
        self.ok("pack", self.book, 2)
        pack2_re = (self.book / ".ncc/写手包/ch-0002.md").read_text("utf-8")
        self.assertNotIn("皇后私印密令", pack2_re)
        self.assertNotIn("太祖遗诏藏宝图", pack2_re)

        # 并列声明中 FS-0003 为本场有效回收，FS-0004 带括号延后 -> 仅披露 FS-0003 真义，仍严防泄露 FS-0004 真义
        valid_card = PLATINUM_CARD.format(
            seq=6,
            must="井底翻牌\n- 伏笔回收：FS-0003（禁地前不得不当众识别并揭开密令）、FS-0004（下章再揭晓）",
        )
        self.write("02-大纲/场景卡/ch-0006.md", valid_card)
        self.ok("scene", "review", self.book, 6, "--result", "pass", "--by", "author")
        self.ok("pack", self.book, 6)
        pack6_ok = (self.book / ".ncc/写手包/ch-0006.md").read_text("utf-8")
        self.assertIn("伏笔回收揭晓：皇后私印密令", pack6_ok)
        self.assertNotIn("太祖遗诏藏宝图", pack6_ok)

        # --- R08: 传入不通过或 SHA 过期的报告拒绝定稿；旧无 SHA 通过报告及复审更新 SHA 报告兼容；正常字数免重批旧例外 ---
        # 1) 先写 1800 字短稿并授权接收篇幅例外
        self.write("04-正文/第0006章.md", "夜雪入京城，铁衣踏寒街。" * 180)  # 1800 汉字 < 3000
        self.ok("chapter", "length", self.book, 6, "--accept", "--force", "--note", "初稿偏短先收")
        # 若改为 2100 字（仍低于 3000 下限且 SHA 已变），定稿闸仍须拒绝并要求重核字数
        self.write("04-正文/第0006章.md", "夜雪入京城，铁衣踏寒街。" * 210)  # 2100 汉字 < 3000
        err_still_short = self.bad("complete", self.book, 6, "--words", 2100, "--hard", "pass")
        self.assertIn("篇幅确认后已改动", err_still_short)

        # 随后扩写回 3200 字正常范围（区间 3000–5000）
        body6_path = self.write("04-正文/第0006章.md", "夜雪入京城，铁衣踏寒街。" * 320)  # 3200 汉字
        real_sha = _hashlib.sha256(body6_path.read_bytes()).hexdigest()[:16]

        # 2) 传入明确“不通过”且摘要过期的报告（含 Markdown 加粗及未填模板占位）+ hard=pass -> 必须拒绝
        self.write("05-审稿/ch-0006-bad.md", "# ch-0006 审稿\n- **正文 SHA**: `0000deadbeef0000`\n- **硬伤层**: **不通过**｜**可判定率**: 0.90\n")
        err_fail_rep = self.bad("complete", self.book, 6, "--words", 3200, "--hard", "pass", "--report", "05-审稿/ch-0006-bad.md")
        self.assertIn("不通过", err_fail_rep)

        self.write("05-审稿/ch-0006-tpl.md", f"# ch-0006 审稿\n- 正文 SHA: {real_sha}\n- 硬伤层: 通过 | 不通过｜可判定率: 0.90\n")
        err_tpl_rep = self.bad("complete", self.book, 6, "--words", 3200, "--hard", "pass", "--report", "05-审稿/ch-0006-tpl.md")
        self.assertIn("不通过", err_tpl_rep)

        # 3) 传入结论“通过”但正文 SHA 过期的报告 -> 必须拒绝
        self.write("05-审稿/ch-0006-stale.md", "# ch-0006 审稿\n- 正文 SHA: 0000deadbeef0000\n- 硬伤层: 通过｜可判定率: 0.92\n")
        err_stale_rep = self.bad("complete", self.book, 6, "--words", 3200, "--hard", "pass", "--report", "05-审稿/ch-0006-stale.md")
        self.assertIn("不一致", err_stale_rep)

        # 4) 传入含复审记录更新到当前 SHA 且通过的有效报告（且 3200 字已在正常范围，无需再次跑 chapter length --accept！） -> 成功定稿
        self.write(
            "05-审稿/ch-0006-ok.md",
            f"# ch-0006 审稿\n- 正文 SHA: 0000deadbeef0000\n- 硬伤层: 不通过｜可判定率: 0.85\n\n"
            f"## 复审记录\n- rev 1（SHA 0000deadbeef0000→{real_sha}）: 重跑硬伤层，结论：通过｜可判定率: 0.95\n",
        )
        out_ok = self.ok("complete", self.book, 6, "--words", 3200, "--hard", "pass", "--report", "05-审稿/ch-0006-ok.md")
        self.assertIn(f"sha={real_sha}", out_ok)
        ch6_after = next(c for c in json.loads((self.book / "book.json").read_text("utf-8"))["chapters"] if c["seq"] == 6)
        self.assertEqual(ch6_after["status"], "done")
        self.assertNotIn("length", ch6_after)

        # 5) 旧报告兼容：无 SHA 元数据的传统简版审稿通过记录仍可定稿
        self.ok("chapter", "add", self.book, 8, "--file", "04-正文/第0008章.md")
        self.write("04-正文/第0008章.md", "长街灯火明灭，刀锋映雪。" * 300)
        self.write("02-大纲/场景卡/ch-0008.md", PLATINUM_CARD.format(seq=8, must="夜探旧宅"))
        self.ok("scene", "review", self.book, 8, "--result", "pass", "--by", "author")
        self.write("05-审稿/ch-0008-legacy.md", "# 第8章审稿纪要\n全文连贯无硬伤，准予定稿。\n")
        self.ok("complete", self.book, 8, "--words", 3000, "--hard", "pass", "--report", "05-审稿/ch-0008-legacy.md")


if __name__ == "__main__":
    unittest.main()
