# 设计出处与致谢

感谢下列项目及作者公开分享设计、方法与实践。本文集中记录 NCC 的设计参考、相关自有项目和具体材料借用，说明参考了什么、怎样转化、落在何处。项目名与来源链接保留原作者归属。

## 参考关系与项目边界

NCC 自己维护规则、技能、脚本和工作状态。外部项目提供设计参考，使用者无需下载或安装它们，就能使用 NCC 的现有能力。参考项目不进入 NCC 的受管依赖、插件打包、运行时必需项或 CI 安装要求，也不为它们建立 vendor 原件库、锁文件、更新监控或自动采用流程。

| 参考方式 | 应说明的内容 | NCC 中的成果 |
|---|---|---|
| 核心思想与架构 | 解决什么问题、为何适合 NCC、保留和舍弃什么 | 本项目自行设计的协议、模块与职责 |
| Skill 的设计能力 | 参考哪项技能、输入输出与推理步骤、怎样适配小说或开发领域 | 由 NCC 维护的本地方法与验证依据 |
| 设计时实际调用外部能力 | 使用的项目/技能、可识别版本或内容指纹、调用目的、影响的决定与工件 | 当次方案中的使用记录；不成为后续使用者的必装项 |
| 引用或改编具体文字、模板、词表等材料 | 原作者、原件位置、版本、借用范围、改写位置及适用许可 | 如实标注材料借用，不能概称为“只借思想” |

开发者可以按当次任务授权使用自己已安装的外部技能辅助设计；外部项目的全局规则不因被参考而成为 NCC 的管控规则。讨论和设计结果回到 NCC 自己的文档与接口，后续执行不要求再次调用同一外部技能。是否安装、启用或更新第三方项目由使用者自行决定。

本文是来源与致谢的唯一集中记录，具体方案补充当次参考范围、取舍、落点及验证结果，并链接本文对应条目。不为尚未采用的来源宣称“已借鉴”或“已验证”，也不以项目名气和星数代替设计证据。

引用记录应能回查“项目/作者 → 具体组件与版本 → 学到的机制 → NCC 的转化 → 落点与验证”。只知道本地内容指纹时就记录指纹，不冒充上游 commit；上游出现新版本也不自动改变 NCC 的已定规则。

致谢与许可分别处理：Skill 正文、模板、词表和代码的实际复制或改编，都应按相应材料的许可保留必要声明。没有明确许可不能仅凭公开可见推定可自由复制；参见 [GitHub 的仓库许可说明](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository)。本文末尾已明确记录 oh-story 词表清单的借用，不再用“全部仅为思想借鉴”概括所有来源。

## 使用者自行获取参考项目

本文本身就是可保存、下载的 Markdown 说明。以下各条提供上游项目链接：打开其仓库，使用 Code → Download ZIP，或将仓库克隆到自己选择的**NCC 仓库以外**的目录；下载供阅读与对照，不会自动安装技能。

通用命令模板（替换 URL 和目标路径后自行运行）：

```bash
git clone <上游仓库URL> <仓库外的目标目录>
git -C <目标目录> rev-parse HEAD
```

例如，选择自己本机的学习资料目录后，可分别获取开发设计参考：

```bash
git clone https://github.com/obra/superpowers.git /path/to/reference-projects/superpowers
git clone https://github.com/mattpocock/skills.git /path/to/reference-projects/mattpocock-skills
```

这些命令仅为使用者按需执行的下载文本，本项目不执行批量下载。克隆当前默认分支获得的是下载时的版本，不等于 NCC 曾参考的版本；要复现某次设计，应依其记录选择对应 commit/tag，或核对记录中的文件指纹。若需要启用上游技能，再按上游自己的安装文档和本机宿主选择办理，下载说明不替使用者进行安装或改变项目配置。

## 开发设计参考（2026-10-12）

以下参考用于开发工作流的设计，已转化为 ncc-dev 开发入口、[本地流程规范](docs/engineering/workflow.md)与候选证据检查器；本次状态见[升级任务](docs/evidence/2026-10-12-ncc-dev/task.md)。参考范围与取舍见[开发工作流设计](docs/designs/engineering/workflow.md)；本机所读技能的内容指纹见[方案审查记录](docs/designs/engineering/source-audit.md)。后者只记录来源阅读，未调用这些外部技能执行任务。

| 项目与作者 | 具体参考 | NCC 的转化与取舍 | 来源依据 |
|---|---|---|---|
| [superpowers — Jesse Vincent / obra](https://github.com/obra/superpowers) | brainstorming 的意图澄清与任务分流，writing-plans 的可验收计划，verification 的证据纪律 | 分为探索、局部、结构三条路径；保留已有授权，按变更性质验证；不移植全部审批仪式 | 本机 brainstorming 内容指纹见审查记录；[上游 MIT 许可](https://github.com/obra/superpowers/blob/main/LICENSE) 于 2026-10-12 核对 |
| [skills — Matt Pocock](https://github.com/mattpocock/skills) | codebase-design 的深模块与删除测试；grilling 的决定依赖；grill-with-docs 的讨论落档；to-spec 的上下文综合 | 按调用者所需知识评估接口，关键决定有依据，设计取舍留档；质询只进开发分支，不要求运行上游技能 | 本机相关文件指纹见审查记录；[上游 MIT 许可](https://github.com/mattpocock/skills/blob/main/LICENSE) 于 2026-10-12 核对 |

这次设计未复制上述技能正文，也未建立对它们的运行调用。下面的创作机制出处保留原有来源说明；历史版本标签只表示当时参照范围，不表示上游当前版本或兼容承诺。

## [chinese-novelist-skill](https://github.com/PenglongHuang/chinese-novelist-skill)（MIT）

| 借鉴 | 落点 |
|---|---|
| 单一 JSON 状态机（进度/恢复/校验四合一） | book.json ＋ ncc_state.py |
| 三层递进问答（L1必答/L2可选/L3书名）＋偏好记忆＋🎲 | skills/ncc-new/references/qa-layers.md |
| 文风锚点：「动笔前最后读的必须是正文语态」＋第1章校准回填 | 上下文包契约、golden-three.md |
| 设定词典四栏（首现/读者已知/完整真相/计划揭示） | worldbuilding.md |
| 章节工艺（字数带/张力波峰/对话占比/钩子十三式思路） | chapter-loop.md |
| 确定性字数脚本（只数汉字、剔 Markdown） | check_chapter.py |
| 自动化边界：决策点人确认、执行段禁停顿 | 各 SKILL 的边界节 |

NCC 按自己的执行方式补充了单章串行回写、偏好滚动裁剪和统一的章节长度口径；具体阈值与现行规则以本项目注册表和技能为准。

## [Openwrite / dsh-Openwrite](https://github.com/LiPu-jpg/Openwrite)（Apache-2.0）

| 借鉴 | 落点 |
|---|---|
| 审稿以正文证据为锚，缺陷、严重度与覆盖分别表达 | review-domains.md；NCC 当前采用三层评价，不移植原累加分制 |
| 评审 SHA 绑定正文：正文一变评审即 stale，修订后强制复评 | book-state.md、ncc-review |
| 写前上下文包预检（可审计、可留档） | context-pack.md ＋ .ncc/写手包/ |
| 伏笔义务清单（due/overdue/to_plant）进工作简报 | v0.2 扩为承诺台账（ncc_state.py promise）、情节承诺域 |
| 50 章滚动规划窗 | outline.md |
| 写→审→修→复评→收尾的交付 DAG | 每章流水线 |

按其经验做了减法：47 节点物化 DAG 与六域并行（约 7 次模型调用）收敛为两次派单（continuity＋pulse），适配 CLI 插件成本。v0.2 按 D11 扩为八域，派单次数不变。

## [InkOS](https://github.com/Narcooo/inkos)（AGPL-3.0）

**仅借鉴架构思想，零代码引用。**

| 借鉴 | 落点 |
|---|---|
| 权威 JSON 状态 ＋ MD 投影分离，MD 永不作为事实源 | book-state.md 铁律 |
| 写-审-改分离：审计只产 observation，修订是显式独立动作 | continuity/editor 角色切分 |
| 上下文 protected/compressible 分层 | context-pack.md（永不裁的 protected 五件） |
| author_intent / current_focus 双控制文档 | 书项目根的两个意图文件 |
| 章节级留痕（intent/context 可追溯） | .ncc/写手包/ 留档 |
| 创作方法外置 SKILL、代码只管协议 | 本插件的 skills/ 结构 |

未移植：Studio/TUI 产品面、pi-agent 运行时、SQLite 检索内核（CLI 场景用 grep＋文件即数据库）、多模型路由。

## 本人既有资产

| 资产 | 落点 |
|---|---|
| 《小说拆分总纲 5.0》（~/Documents/word_wx/ai-skills/） | ncc-deconstruct 的字段口径；事件溯源台账；量纲定义；设定词典与底卡分级 |
| [sdlc-workflow](https://github.com/cloudxy/sdlc-plugins)（作者自有相关项目） | 目录骨架、经理窗口＋角色帽、registry 唯一事实源、闸门与铁律文体、G-fresh 思想（→ reader/continuity 的 fresh 上下文）；2026-10-12 进一步参照其来源声明、原件与本地实现分离的组织方式，不引入其 vendor 安装与依赖管理 |
| [VSC / video_wk](https://github.com/cloudxy/vsc-plugin)（作者自有相关项目） | 项目级接线、扁平开发现场；2026-10-12 参照其区分阅读参考与实际依赖、记录来源及使用方式的思想；NCC 采用文档引用，不引入其本地组件、锁文件与更新器 |
| 主流网文工业流（黄金三章/存稿/日更/爽点节奏的大众共识） | 阶段主线、golden-three.md、连载节奏 |
| novel_guide（~/Documents/Obsidian_files/novel_guide/） | 爽点通用结构（压迫→误判→吃亏→破口→反打→善后→新责任）是欠·挣·超·证的来源；卡文五问进卡文协议；v0.6：「12 代入感」「13 规避点」整理成判据（review-domains.md 的"代入感与规避点"、check_chapter.py 规避点告警、故事审的主角在场与章尾落点、人物卡标志细节、新手档推荐偏稳） |
| novel_sources/小说底盘（~/Documents/Obsidian_files/novel_sources/） | v0.6：玄幻、仙侠类力量体系与资源设定的底料（`setting_base_candidates`）；底盘自己的铁律（数值可回查、不跳境界上限、突破有代价、称号不冒充境界）与本插件的量纲、越级例外一致 |

### novel_guide 未采纳的条目（v0.6）

| 原话大意 | 为什么不采纳 |
|---|---|
| 不会写转折，就用"突然、居然、没想到"过渡 | 以词代事，正是 AI 味判据要拦的写法；转折要靠事件与两难，不靠连接词 |
| 读者评论都是浮云 | 部分采纳：评论原文不推给作者（噪音隔离），但真实读者数据要回流，用来校准模拟读者 |
| 文学靠灵感不靠修改，修改会把书改死 | 部分采纳：连载中已发布内容只修硬伤与基础错误、不大改（与五层可逆度一致）；发布前的场景卡故事审、关键章比选和硬伤修订照常 |
| 主角只要"泛性格"就够了 | 部分采纳：性格底色可以泛，欲望、恐惧、处境必须具体（人物引擎）；写进 character.md |

## v3.0 记忆与自进化的参照

只借设计思想，未复制任何代码；实现为本插件自写的标准库脚本。

| 来源 | 许可 | 借鉴 | 落点 |
|---|---|---|---|
| [openclaw/openclaw](https://github.com/openclaw/openclaw) 的记忆机制 | MIT | 身份文件与长期记忆分开；长期记忆小而常驻、每日笔记可搜不常驻；上下文压缩前先把要紧的落盘 | 记忆分层（身份、本书记忆、跨书记忆、记忆日志）；单元整理；交接卡"上下文快满时先补记" |
| [NousResearch/hermes-agent](https://github.com/nousresearch/hermes-agent) | MIT | 智能体自管记忆并定期整理；从做成的事里沉淀可复用的技能、用的时候再改进；跨会话全文检索 | 角色的记忆提议与 `memory consolidate`；技法卡按使用结果升降；`recall` |
| Practice Makes Unsafe: Skill Misevolution in Self-Improving LLM Agents（2026 预印本） | — | 会给自己沉淀技能的智能体，容易把一次侥幸成功的坏做法固化下来；持续自适应要同时管住写进去什么、以后复用什么 | 自进化四档：两处证据才生效、会衰减、规则改动过锚定章回归再由作者确认、可撤回；铁律与可见范围永不自动 |

## v1.1 借鉴 oh-story（第一组）

| 来源 | 许可 | 借鉴 | 落点 |
|---|---|---|---|
| [zenstory-ai/oh-story-claudecode](https://github.com/zenstory-ai/oh-story-claudecode) v0.8.4 的写章流程与 storyctl 字数收口 | MIT | 欠字不补、超字只删一次、分组写作与中途一次字数检查、收下长度的下限（不到一半不轻易收） | `check_chapter.py` 的 needs_decision、`ncc_state.py chapter length` 与 `words`、chapter-loop.md |
| 同上，`check-degeneration.js` | MIT | 退化指纹的分类：复读、截断、占位与拒绝语、工程词泄漏；台词豁免 | `check_chapter.py` 退化与元信息（正则与判定为本插件自写） |
| 同上，`demo/craft-stock-reaction-eval` | MIT | 实验结论：把身体微动作设为情绪默认译法会产出套路反应；改为只写有后果的反应 | 写作简报、chapter-loop.md、writing-brief.md、身体小动作告警 |
| 同上，SKILL.md「面向作者的汇报」 | MIT | 只讲写了什么、要作者定什么、下一步；编号带故事标签；技术备注放最后一行 | `skills/ncc/SKILL.md` 面向作者的汇报 |

## v1.0 格式参照

| 来源 | 用在哪 |
|---|---|
| W3C EPUB 3.3（容器、包文档、导航文档规范） | `ncc_state.py export --format epub`：mimetype 首项且不压缩、`META-INF/container.xml`、`content.opf`（EPUB 3）、`nav.xhtml`；另附 EPUB 2 的 `toc.ncx` 以兼容老阅读器。按规范自写，未用第三方库 |

## v0.2 引导层参照

只借做法，未复制任何代码。

| 项目 | 许可 | 借鉴 | 落点 |
|---|---|---|---|
| [superpowers](#开发设计参考2026-10-12) | MIT | brainstorming：一次一问、尽量给选择题、2–3 种方案且推荐在前 | guidance.md 第 3 步 |
| [github/spec-kit](https://github.com/github/spec-kit) | MIT | clarify：按影响排序、最多 5 问、"为什么要紧"、推荐项置顶、回答立即写回 | guidance.md 第 1–3、5 步 |
| [bmad-code-org/BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) | 许可按所参考版本的原件核对 | 高级启发：选一种推理方法（事前复盘等）二次审视已有方案 | guidance.md 第 7 步 |
| [zenstory-ai/oh-story-claudecode](https://github.com/zenstory-ai/oh-story-claudecode) | MIT | 候选真相带最晚可改章；作者真相与读者已知分开记录；一句话路由 | 暂定决策的 deadline、知情台账、一句话入口 |
| [ExplosiveCoderflome/AI-Novel-Writing-Assistant](https://github.com/ExplosiveCoderflome/AI-Novel-Writing-Assistant) | AGPL-3.0（据其 README；只借思想） | 面向新手：一句灵感生成多套整本方向与书名组、附推荐理由、可只重做某一套；简易/专业两种模式 | scout 的整本方向候选、定向重做、引导档位 |

## v0.3 上限引擎的依据（研究与创作理论）

| 来源 | 结论 | 落点 |
|---|---|---|
| Russell et al., StoryScope（2026 预印本） | AI 小说爱把主题说破、情节整齐单线、主角选择缺少道德两难、事件升级平淡、从外部描写人物 | 书魂不进写手提示；场景卡的两难与风险升级；写作简报要求从视角人物的身体写起 |
| Chakrabarty et al., Art or Artifice?（CHI 2024） | 大模型给创意写作打分与专家相关性接近零 | 三层评价：不打绝对分 |
| Chakrabarty et al., Can AI writing be salvaged?（LAMP，CHI 2025） | AI 文本的七类毛病（陈词滥调、不必要的说明等） | 写手的"先写后删"；硬伤层的文风检查 |
| Doshi & Hauser（Science Advances 2024） | AI 创意帮个人变好，但让作品彼此变像 | 作者种子：挖掘在前、推荐在后，推荐标来源 |
| Nakayashiki & Watanabe（2026 预印本） | 多个模型彼此一致，却不与读者一致 | 品质层用读者记忆测试，真实读者数据回流校准（M3） |
| oh-story 章纲到正文指南 | 细纲写"本章必须发生什么变化"，过结构验收才写正文 | 场景卡与故事审 |
| 麦基《故事》；Swain；Maass；Weiland；埃格里；李渔《闲情偶寄》；恩格斯致哈克奈斯 | 价值翻转、场景与续场、情感旅程、人物弧光与"信错的那句话"、前提、立主脑密针线减头绪脱窠臼、典型人物 | mind-frame.md 的"小说家的生成模型"；scene-card.md；character.md |

## v0.4 借用的清单

| 来源 | 许可 | 借用 | 落点 |
|---|---|---|---|
| [zenstory-ai/oh-story-claudecode](https://github.com/zenstory-ai/oh-story-claudecode) 的 story-deslop（`banned-words.md`） | MIT，Copyright (c) 2025-2026 oh-story-claudecode | 一级禁用词、二级密度词、高危句式与五星句式分级、作者白名单的做法 | `scripts/check_chapter.py`（清单为整理后的子集；正则与判定逻辑为本插件自写） |

