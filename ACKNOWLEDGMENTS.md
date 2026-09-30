# 设计出处与致谢

本插件的方法论融合自三个开源项目与本人既有资产。**未复制任何源代码**；所有借鉴停留在设计思想、流程结构与规则层面（InkOS 为 AGPL-3.0，代码级借鉴会传染许可证，故严格只读思想）。

## [chinese-novelist-skill](https://github.com/PenglongHuang/chinese-novelist-skill)（MIT，⭐3.2k）

| 借鉴 | 落点 |
|---|---|
| 单一 JSON 状态机（进度/恢复/校验四合一） | book.json ＋ ncc_state.py |
| 三层递进问答（L1必答/L2可选/L3书名）＋偏好记忆＋🎲 | skills/ncc-new/references/qa-layers.md |
| 文风锚点：「动笔前最后读的必须是正文语态」＋第1章校准回填 | 上下文包契约、golden-three.md |
| 设定词典四栏（首现/读者已知/完整真相/计划揭示） | worldbuilding.md |
| 章节工艺（字数带/张力波峰/对话占比/钩子十三式思路） | chapter-loop.md |
| 确定性字数脚本（只数汉字、剔 Markdown） | check_chapter.py |
| 自动化边界：决策点人确认、执行段禁停顿 | 各 SKILL 的边界节 |

并修正了它的已知薄弱点：共享词典并发写冲突（本插件单章串行回写）、偏好无限增长（50 条滚动裁剪）、章节下限口径矛盾（统一 3000）。

## [Openwrite / dsh-Openwrite](https://github.com/LiPu-jpg/Openwrite)（Apache-2.0，⭐765）

| 借鉴 | 落点 |
|---|---|
| 审稿累加分制：只有带正文证据的准则计分、问题不扣分、覆盖率独立、critical 只 block | review-domains.md |
| 评审 SHA 绑定正文：正文一变评审即 stale，修订后强制复评 | book-state.md、ncc-review |
| 写前上下文包预检（可审计、可留档） | context-pack.md ＋ _packs/ |
| 伏笔义务清单（due/overdue/to_plant）进工作简报 | v0.2 扩为承诺台账（ncc_state.py promise）、情节承诺域 |
| 50 章滚动规划窗 | outline.md |
| 写→审→修→复评→收尾的交付 DAG | 每章流水线 |

按其经验做了减法：47 节点物化 DAG 与六域并行（约 7 次模型调用）收敛为两次派单（continuity＋pulse），适配 CLI 插件成本。v0.2 按 D11 扩为八域，派单次数不变。

## [InkOS](https://github.com/Narcooo/inkos)（AGPL-3.0，⭐10k）

**仅借鉴架构思想，零代码引用。**

| 借鉴 | 落点 |
|---|---|
| 权威 JSON 状态 ＋ MD 投影分离，MD 永不作为事实源 | book-state.md 铁律 |
| 写-审-改分离：审计只产 observation，修订是显式独立动作 | continuity/editor 角色切分 |
| 上下文 protected/compressible 分层 | context-pack.md（永不裁的 protected 五件） |
| author_intent / current_focus 双控制文档 | 书项目根的两个意图文件 |
| 章节级留痕（intent/context 可追溯） | _packs/ 留档 |
| 创作方法外置 SKILL、代码只管协议 | 本插件的 skills/ 结构 |

未移植：Studio/TUI 产品面、pi-agent 运行时、SQLite 检索内核（CLI 场景用 grep＋文件即数据库）、多模型路由。

## 本人既有资产

| 资产 | 落点 |
|---|---|
| 《小说拆分总纲 5.0》（~/Documents/word_wx/ai-skills/） | ncc-deconstruct 的字段口径；事件溯源台账；量纲定义；设定词典与底卡分级 |
| sdlc-workflow 插件 | 目录骨架、经理窗口＋角色帽、registry 唯一事实源、闸门与铁律文体、G-fresh 思想（→ reader/continuity 的 fresh 上下文） |
| 主流网文工业流（黄金三章/存稿/日更/爽点节奏的大众共识） | 阶段主线、golden-three.md、连载节奏 |
| novel_guide（~/Documents/Obsidian_files/novel_guide/） | 爽点通用结构（压迫→误判→吃亏→破口→反打→善后→新责任）是欠·挣·超·证的来源；卡文五问进卡文协议 |

## v0.2 引导层参照（GitHub 高星项目，星数为 2026-09-30 数据）

只借做法，未复制任何代码。

| 项目 | 许可 | 借鉴 | 落点 |
|---|---|---|---|
| [obra/superpowers](https://github.com/obra/superpowers)（约 29.3 万星） | MIT | brainstorming：一次一问、尽量给选择题、2–3 种方案且推荐在前 | guidance.md 第 3 步 |
| [github/spec-kit](https://github.com/github/spec-kit)（约 13.9 万星） | MIT | clarify：按影响排序、最多 5 问、"为什么要紧"、推荐项置顶、回答立即写回 | guidance.md 第 1–3、5 步 |
| [bmad-code-org/BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD)（约 5.4 万星） | 见其仓库（GitHub 未识别为标准许可） | 高级启发：选一种推理方法（事前复盘等）二次审视已有方案 | guidance.md 第 7 步 |
| [zenstory-ai/oh-story-claudecode](https://github.com/zenstory-ai/oh-story-claudecode)（约 7200 星） | MIT | 候选真相带最晚可改章；作者真相与读者已知分开记录；一句话路由 | 暂定决策的 deadline、知情台账、一句话入口 |
| [ExplosiveCoderflome/AI-Novel-Writing-Assistant](https://github.com/ExplosiveCoderflome/AI-Novel-Writing-Assistant)（约 3000 星） | AGPL-3.0（据其 README；只借思想） | 面向新手：一句灵感生成多套整本方向与书名组、附推荐理由、可只重做某一套；简易/专业两种模式 | scout 的整本方向候选、定向重做、引导档位 |
