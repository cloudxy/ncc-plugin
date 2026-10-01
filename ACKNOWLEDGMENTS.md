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
| novel_guide（~/Documents/Obsidian_files/novel_guide/） | 爽点通用结构（压迫→误判→吃亏→破口→反打→善后→新责任）是欠·挣·超·证的来源；卡文五问进卡文协议；v0.6：「12 代入感」「13 规避点」整理成判据（review-domains.md 第四节、check_chapter.py 规避点告警、故事审的主角在场与章尾落点、人物卡标志细节、新手档推荐偏稳） |
| novel_sources/小说底盘（~/Documents/Obsidian_files/novel_sources/） | v0.6：玄幻、仙侠类力量体系与资源设定的底料（`setting_base_candidates`）；底盘自己的铁律（数值可回查、不跳境界上限、突破有代价、称号不冒充境界）与本插件的量纲、越级例外一致 |

### novel_guide 未采纳的条目（v0.6）

| 原话大意 | 为什么不采纳 |
|---|---|
| 不会写转折，就用"突然、居然、没想到"过渡 | 以词代事，正是 AI 味判据要拦的写法；转折要靠事件与两难，不靠连接词 |
| 读者评论都是浮云 | 部分采纳：评论原文不推给作者（噪音隔离），但真实读者数据要回流，用来校准模拟读者 |
| 文学靠灵感不靠修改，修改会把书改死 | 部分采纳：连载中已发布内容只修硬伤与基础错误、不大改（与五层可逆度一致）；发布前的场景卡故事审、关键章比选和硬伤修订照常 |
| 主角只要"泛性格"就够了 | 部分采纳：性格底色可以泛，欲望、恐惧、处境必须具体（人物引擎）；写进 character.md |

## v0.2 引导层参照（GitHub 高星项目，星数为 2026-09-30 数据）

只借做法，未复制任何代码。

| 项目 | 许可 | 借鉴 | 落点 |
|---|---|---|---|
| [obra/superpowers](https://github.com/obra/superpowers)（约 29.3 万星） | MIT | brainstorming：一次一问、尽量给选择题、2–3 种方案且推荐在前 | guidance.md 第 3 步 |
| [github/spec-kit](https://github.com/github/spec-kit)（约 13.9 万星） | MIT | clarify：按影响排序、最多 5 问、"为什么要紧"、推荐项置顶、回答立即写回 | guidance.md 第 1–3、5 步 |
| [bmad-code-org/BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD)（约 5.4 万星） | 见其仓库（GitHub 未识别为标准许可） | 高级启发：选一种推理方法（事前复盘等）二次审视已有方案 | guidance.md 第 7 步 |
| [zenstory-ai/oh-story-claudecode](https://github.com/zenstory-ai/oh-story-claudecode)（约 7200 星） | MIT | 候选真相带最晚可改章；作者真相与读者已知分开记录；一句话路由 | 暂定决策的 deadline、知情台账、一句话入口 |
| [ExplosiveCoderflome/AI-Novel-Writing-Assistant](https://github.com/ExplosiveCoderflome/AI-Novel-Writing-Assistant)（约 3000 星） | AGPL-3.0（据其 README；只借思想） | 面向新手：一句灵感生成多套整本方向与书名组、附推荐理由、可只重做某一套；简易/专业两种模式 | scout 的整本方向候选、定向重做、引导档位 |

## v0.3 上限引擎的依据（研究与创作理论）

| 来源 | 结论 | 落点 |
|---|---|---|
| Russell et al., StoryScope（2026 预印本） | AI 小说爱把主题说破、情节整齐单线、主角选择缺少道德两难、事件升级平淡、从外部描写人物 | 书魂不进写手提示；场景卡的两难与风险升级；写作简报要求从视角人物的身体写起 |
| Chakrabarty et al., Art or Artifice?（CHI 2024） | 大模型给创意写作打分与专家相关性接近零 | 三层评价：不打绝对分 |
| Chakrabarty et al., Can AI writing be salvaged?（LAMP，CHI 2025） | AI 文本的七类毛病（陈词滥调、不必要的说明等） | 写手的"先写后删"；硬伤层的文风检查 |
| Doshi & Hauser（Science Advances 2024） | AI 创意帮个人变好，但让作品彼此变像 | 作者种子：挖掘在前、推荐在后，推荐标来源 |
| Nakayashiki & Watanabe（2026 预印本） | 多个模型彼此一致，却不与读者一致 | 品质层用读者记忆测试，真实读者数据回流校准（M3） |
| oh-story 章纲到正文指南 | 细纲写"本章必须发生什么变化"，过结构验收才写正文 | 场景卡与故事审 |
| 麦基《故事》；Swain；Maass；Weiland；埃格里；李渔《闲情偶寄》；恩格斯致哈克奈斯 | 价值翻转、场景与续场、情感旅程、人物弧光与"信错的那句话"、前提、立主脑密针线减头绪脱窠臼、典型人物 | mind-frame.md 第二节；scene-card.md；character.md |

## v0.4 借用的清单

| 来源 | 许可 | 借用 | 落点 |
|---|---|---|---|
| [zenstory-ai/oh-story-claudecode](https://github.com/zenstory-ai/oh-story-claudecode) 的 story-deslop（`banned-words.md`） | MIT，Copyright (c) 2025-2026 oh-story-claudecode | 一级禁用词、二级密度词、高危句式与五星句式分级、作者白名单的做法 | `scripts/check_chapter.py`（清单为整理后的子集；正则与判定逻辑为本插件自写） |

