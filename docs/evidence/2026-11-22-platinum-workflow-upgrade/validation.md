# 白金连载引擎与出品人工作流升级验证报告

## 一、输入与环境

- 仓库与插件根：`/Users/xuyun/Documents/ncc-workflow`（`main`，基线提交 `f3f6bc1af80967b15b4fc575e3ccb273bd8e8e1a`）
- 冻结候选指纹：`9934821e365215222c70b8d9e4a579221f39de84a5d912260acf6091e2f6bc74`（45 个产品文件）
- 关联方案：`docs/designs/writing/platinum-upgrade.md` 与 `ACKNOWLEDGMENTS.md`（白金连载引擎与全网创作框架吸收）
- 环境：macOS 本地沙盒，Python 3 标准库运行态，全合成测试数据（未触碰 `novels/`、`config/.env` 或 PostgreSQL 数据库）

## 二、实际执行的确定性验证与观察

1. **专项行为与架构兼容自测（`behavior.log`）**
   - 命令：`python3 -m unittest scripts/tests/test_platinum_upgrade.py scripts/tests/test_architecture.py -v`
   - 结果：12 项全部通过（退出码 0）。
   - 观察：
     - 三线伏笔 `--line 暗线 --cover ... --truth ...` 在未揭晓章（含兑现后回打更早章节）仅将明面伪装送入写手包，对 ≥2 字 `true_meaning` 执行严密泄漏拦截，并在 `reader-now` 的 `mask_truth` 模式下屏蔽秘密伏笔；真实正序写章通过场景卡显式标记 `伏笔回收：FS-NNNN` 无死锁放行并注入回收真相与呼应点。
     - 暗线沉底达 8 章时，`reader-now`、`brief --role outliner` 与 `sandbox` 准确发出暗香断档预警；已在当前沙盘窗口排入时自动消警。
     - 真实连载正序（先 `unit open --arc-ch` 后 `chapter add`）自动将弧光章标为 `key=True`；`plight` 四维高压处境、人物卡标志细节与关系、主角专属 `arc_stage` 行为反差提示与场景卡 `配角速写` 均准确进入写手包与生成视图。
     - 跨章断章钩秒接提醒自动剥离章节标题行，在开头切镜头时准确告警、正面承接时消除。
     - `sandbox` 只读运行不污染操作日志；`--write` 含 `sandbox-sha` 脏检查与无标记手写文件防丢稿保护，底层变动重刷时自动提示复核已有拍板；10 章单元准确输出**单元五拍中点锚（中点反守为攻）**、**活跃暗线封顶 5 条超载预警**、**十章一响提醒**与高潮单场兑现 ≥2 条线索时的**多线雪崩合拢达标**识别。
     - 原 CLI 参数快照与运行时输出快照（`runtime-contract.json`）在未传入新可选参数时逐字节保持兼容。
2. **全量单元测试（`unit.log`）**
   - 命令：`python3 -m unittest discover -s scripts/tests -t scripts -p 'test_*.py'`
   - 结果：231 项测试全部通过（退出码 0）。
3. **注册表与文档生成一致性（`registry.log`、`docs.log`）**
   - 命令：`python3 scripts/dev/build_registry.py --check`、`python3 scripts/dev/build_docs.py --check`
   - 结果：`REGISTRY OK`、`DOCS OK`（退出码 0）。
4. **插件契约与角色读取预算检查（`plugin.log`）**
   - 命令：`python3 scripts/dev/check_plugin.py -v`
   - 结果：`PLUGIN OK`（退出码 0）。全部角色与经理意图均在预算内（`worldbuilder 19575/20000`、`outliner 17161/20000`、`story-editor 16725/20000`、`scout 6348/20000`、`writer 6475/20000`、`manager:new 34550/35000`、`manager:write 30751/35000`）。
5. **机械评测锚定章回归（`mech.log`）**
   - 命令：`python3 scripts/ncc_eval.py mech`
   - 结果：A01–A06 六章全部 `PASS`（退出码 0）。

## 三、未验证边界与后续安排

- 按作者明确授权，本轮暂不开书，完成全网小说创作框架吸收与本地全量验证后，执行 `git pull` → 提交 → 推送 `origin/main`。
- 真实多章大模型连载回归、审稿模型锚定盲审与五套宿主 CLI 新会话冒烟尚未执行，保持 `runtime: unverified`。
