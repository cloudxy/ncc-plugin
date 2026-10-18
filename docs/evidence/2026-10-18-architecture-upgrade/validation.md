# 架构升级验证

关联任务：[升级实施](../../tasks/2026-10-18-architecture-upgrade.md)。环境：macOS、Python 3.9.6，main，基线 `0e3faa03f05f05524442c870c0fafda134e0d8b4`。plugin_root/repo_root 均为 `/Users/xuyun/Documents/ncc-workflow`。作者已授权执行修订方案；未请求发布。

## 输入与修改边界

G0 在修改前按 Git 受管/未忽略清单保存 251 个文件/软链的原始工作树副本及 hash，位置为仓外 `/private/tmp/ncc-architecture-upgrade/baseline`。此副本包含作者原有未提交改动，不包含私有小说库或 .git。CLI 解析契约和帮助、102 个导出常量、11 组运行输出/文件状态从这个副本独立提取。后续预期没有由候选反向覆盖。

本任务精确产品范围在任务 JSON，包含移动前的删除项、移动后的文件、薄入口、注册表分片与兼容视图、生成段和现行文档。原有文档治理/入口改动保留；未清理、暂存或回退工作树，未操作真实书库。实际只改结构、读取及检查机制，不改变创作闸门/审稿判据/默认词表/角色职责，不运行无关模型回归。

## 已实现的批次

- G1：五份 JSON 按实际字段映射校验；市场名称与插件名称分开；Codex 市场无 version 合法；缺文件、错格式、重复目标、漂移与路径越界有反例。
- G2：三个开发实现移入 scripts/dev，旧顶层命令保留转发；五个既有测试模块与新增测试进入 scripts/tests；修复 ROOT、with_name、模块导入、patch 目标、子进程路径与生成标记识别。check_dev_workflow 实现与原副本字节一致，显式 --repo 语义不变。
- G5：49 个顶层命令按原顺序注册，分至七个参数模块；cli 保留 parse/handler/log/render。book/loops 的业务函数没有搬迁，日志、只读集合和自动渲染策略 AST 与原版相同。
- G3a：core、ncc_prepare、check_plugin、build_docs 共用无 core 依赖的标准库 loader；ncc_library 的准备工具依赖一并验证。
- G3b：七个分片持有原 41 键；缺片/未知片/重复键/错归属/坏格式/陈旧聚合视图拒绝启动。build_registry 通过临时文件、fsync 与原子替换构建，--check 只读。兼容 registry.json 保留旧路径和原数据。
- G4：拆书 P1 的机器契约、参考层与样例归属已写入拆书方案；该业务 P1–P6 尚未实施，不把方案接线当作新拆书功能。

## 执行检查与结果

| 检查 | 实际结果 | 退出码 |
|---|---|---:|
| 冻结原副本 `python3 -m unittest discover -s scripts -p 'test_*.py'` | 151 项，299.823 秒，通过 | 0 |
| G1 清单定向测试 | 7 项通过；真实清单与生成检查通过 | 0 |
| G2 全量 `discover -s scripts/tests -t scripts` | 158 项，252.463 秒，通过 | 0 |
| G5 全量 | 164 项，218.459 秒，通过 | 0 |
| G3a 全量 | 164 项，242.780 秒，通过 | 0 |
| registry 定向与失败注入 | 15 项通过，含替换失败保留原文件并清理临时文件 | 0 |
| 最终候选全量 | 180 项，295.687 秒，通过 | 0 |
| 新旧测试发现方式 | 当前发现集合均为 180 项，包含全部原始 151 项；导入失败项和零发现显式拒绝 | 0 |
| `python3 scripts/dev/build_registry.py --check` | REGISTRY OK，生成物新鲜 | 0 |
| `python3 scripts/dev/check_plugin.py -v` | PLUGIN OK，五份清单、链接、接线和现有读取预算通过 | 0 |
| `python3 scripts/dev/build_docs.py --check` | DOCS OK，幂等生成 | 0 |
| `python3 scripts/ncc_eval.py mech` | 六个机械锚定场景全部 PASS | 0 |
| `git diff --check` 与全部候选文本行尾检查 | 无空白错误，未跟踪新文件也检查末尾换行和行尾空白 | 0 |

迁移时首次全量发现两个测试模块的导入顺序错误（131 项、2 errors），已修复；后续集合核查拒绝 _FailedTest 并逐项对照原始 151 项，G2 的 158 项全量通过后才进入后续步骤。中途 179 项集成运行曾通过，但其中没有最终补充的换行反例，不作为最终候选的完整验收。

最终自查在修复前公共副本复现：非 UTF-8 损坏聚合文件会使构建器读旧视图失败，即使分片有效。已改为直接比较规范 UTF-8 字节，构建不解码旧视图；坏编码、坏 JSON、缺视图均可从分片恢复；CRLF 被识别为陈旧并修复为 LF。补充反例后重新运行最终全量，不沿用上一候选的通过结论。

## 等价与兼容证据

- registry.json 与原始副本逐字节一致，SHA-256：`7892f62f261264d01cfa33b553bfc67c6fef7121ec5c5ca5f37c5f5985a3c4be`。因此顶层/嵌套键、数值类型、数组和字典顺序均保持；registry schema 仍为 2，书项目 SCHEMA 仍为 4，layout_legacy 保留。
- 102 个可序列化导出常量逐项、逐类型/顺序与原版一致；路径只把两个插件根归一成同一占位符。
- 140 个解析路径（含根路径）及所有帮助文本对照一致；包含位置参数、options、dest、类型、choices、默认值、required、nargs、const、help 与 handler 模块/名称。冻结契约持久化在 `scripts/tests/fixtures/cli-contract.json`；摘要 hash 为 `c9d1fb1aefd65256a90ead00eec9c574d6c4d366924348b0d26fca549e0ccb18`。
- 11 组运行行为：init/status、chapter add、promise add/list、gate check、错误枚举/缺参、空拆书库 coverage、prepare init/status。比较退出码、标准输出/错误和完整文件状态；只归一时间与插件/合成工作路径。只读操作另外核对原始字节、mtime 与 inode。冻结预期在 `scripts/tests/fixtures/runtime-contract.json`，探针与测试代码在 tests 内。
- 12 个规则生成区块正文与原版完全相同；book-layout 除来源标记外相同，agents/commands 文件逐字节相同。仅更新源定位/构建说明，不扩展角色读取权限。
- 新/旧开发命令在仓外含中文与空格的 cwd 下结果一致；合成 Git 仓的 snapshot/check 与候选变化失败均保持，--repo 不误用工具自身根。
- 无 .git、无私有内容的公开文件副本启动五个运行模块并检查五个新/旧开发入口，全部符合原退出码。check_chapter 的 --help/用法仍为 2；ncc_library 是扩展模块，运行启动不代表新建了独立 CLI。
- 60 条宿主相对软链目标核实到仓内源；五份清单字段静态通过。claude/codex/kimi/grok/zcode 的实际新会话均为 unverified，没有用当前会话读文件冒充加载成功。

## 自查、限制与交付

当前会话逐项复核设计意图、实现、失败反例、兼容边界、依赖与私有范围；自查完成，独立评审待办，未派小说角色或冒称另有独立代理评审。宿主新会话与其他机器消费克隆未核验，旧薄入口继续保留。没有用户级安装、网络发布、提交/推送或数据迁移。

最终 scope、候选指纹、报告 hash 和每类证据由任务 JSON 持有；snapshot 与 check --delivery 结果由任务 JSON 的候选和交付字段登记。规则键值与业务标准等价，未触发实质创作规则确认。回滚按方案依赖和本任务增量处理，保留实施前的有效脏改动。

最终候选测试摘要见 [unit.log](unit.log)，冻结原副本的基线摘要见 [baseline.log](baseline.log)；其中陈旧视图/临时修复输出来自故障注入，套件最终退出 0。

实施前已存在且不在本任务范围的文件与软链逐项 hash/目标对照未变，所有新增文件均已归属。最终精确产品候选为 64 个路径，记录不包含私有书库。
