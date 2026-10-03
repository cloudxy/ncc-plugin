# 书项目的目录契约与词表

<!-- 整份由 scripts/build_docs.py 从 workflow/registry.json 的 layout 与 vocab 生成，勿手改；要改就改注册表再运行 build_docs.py。 -->

信息的源头、写者与视图见 [book-state.md](book-state.md) 的"信息地图"。

## 目录契约

每一项标了类别：源头（权威数据，只经脚本或指定写者）、历史（只追加）、视图（生成，勿手改）、作者（作者本人的材料）、角色（角色产出的文档）、工作件（机器写）。

```
{book_root}/{书名}/
  book.json    # [源头] 阶段、闸门、章节状态、写作模式、档位、时代背景｜只经 ncc_state.py（gate、chapter、mode、level、era…）
  author-intent.md    # [视图] 书魂、类型契约、目标读者、签约点、作者雷点｜render 生成，勿手改
  current-focus.md    # [视图] 续写状态卡：上一章结束在何时何地、下一章要接什么、近三章的翻转、读者此刻｜render 生成，勿手改
  00-策划/
    作者种子.md    # [作者] 作者种子（原话）｜经理按作者原话记
    briefing.md    # [角色] 选题一页纸：题材、对标、差异点、目标读者、爽点承诺｜scout
    对标分析.md    # [角色] 对标书分析｜scout
    变更提议.md    # [历史] 冻结后的变更提议与作者决定（只追加）｜经理
    技艺库摘录.md    # [视图] 别的书里与本书相关的经验｜craft read 生成
    复盘/    # [角色] 单元、卷、全书复盘：生成区块是台账数据，区块外是作者与角色的判断｜report --write；作者与角色｜如 单元-U1.md、卷1.md、全书.md
    收束清单.md    # [角色] 收束清单：生成区块是数据，区块外是清算方案｜report finale --write；outliner 与作者
  01-设定/
    世界观圣经.md    # [角色] 世界的规则与关系、社会洞察（不写具体数据，写知识台账的键）｜worldbuilder；冻结后走变更提议
    力量体系.md    # [角色] 境界阶梯、量纲定义、越级例外｜worldbuilder；冻结后走变更提议
    设定词典.md    # [角色] 专名：首现章计划、读者已知、完整真相、计划揭示章｜worldbuilder；写手修正首现章实值
    规则表.md    # [角色] 克制链、兑换率（只对本书有效）｜worldbuilder
    类目/    # [角色] 设定类目卡：门派、种族、血脉、企业……本书用哪些类目由 worldbuilder 研判、作者在 G1 确认（类目表在注册表，本书的选择在 book.json）｜setting add 建卡，worldbuilder 填｜如 门派/青云宗.md
    时代错置词.md    # [角色] 本书特有的时代错置词（可选）｜worldbuilder
    人物卡/    # [角色] 人物卡与角色采访；秘密是什么写这里，谁知道记知情台账｜worldbuilder｜如 <名字>.md、<名字>-采访.md
  02-大纲/
    总纲.md    # [角色] 主线、分卷目录、结局方向；名场面与母题只引用编号｜outliner
    卷纲/    # [角色] 卷纲｜outliner｜如 卷1.md
    章纲/    # [角色] 章纲（建筑师模式）｜outliner｜如 ch-0001.md
    场景卡/    # [源头] 每章要发生的事：视角、目标、翻转、两难、情感（关键章十项）｜outliner 起草，过故事审｜如 ch-0001.md
    知识点/    # [角色] 本章知识点清单：知识点、学科、写成什么、来源、状态｜scholar｜如 ch-0001.md
  03-文风/
    文风基准.md    # [角色] 语感、本书校准段、负面清单（进写手包）｜worldbuilder（task: style），作者确认
    文风指纹.json    # [源头] 文风的数字指纹（只给审稿与脚本）｜style 生成
    放行清单.md    # [作者] 作者认定有意为之的原句（附章号与理由）｜作者
  04-正文/    # [角色] 正文｜writer；修订由 editor｜如 第0001章-标题.md
    _versions/    # [角色] 关键节拍的多版，作者比选｜writer｜如 ch-0001-<节拍>-A.md
  05-审稿/    # [角色] 故事审、审稿报告、盲评｜经理落盘角色的报告｜如 story-ch-0001.md、ch-0001-review.md、blind-ch-0001-0003-<画像>.md
    读者数据.json    # [源头] 读者反馈（真实与模拟，标画像）｜feedback add
  06-台账/
    承诺台账.json    # [源头] 承诺：读者在等的事与作者的待定项（类型见词表）｜promise add/touch/resolve/reschedule/drop
    知情台账.json    # [源头] 谁知道什么（读者与各角色）｜know add/learn
    知识台账.json    # [源头] 数据：距离、物价、历法、称谓、数值｜fact set（同键改值要 --override）
    状态事件.json    # [历史] 人物与世界的变化（只追加；指纹记在 book.json）｜event add
    承诺台账.md    # [视图] 承诺台账，含名场面清单、核心意象｜render 生成，勿手改
    知情台账.md    # [视图] 知情台账｜render 生成，勿手改
    知识台账.md    # [视图] 知识台账｜render 生成，勿手改
  07-导出/    # [工作件] 合稿与电子书（只收已定稿的章）｜export｜如 <书名>-第M-N章.md|txt|epub
  素材/    # [作者] 本书素材卡（按八域分目录）｜material add｜如 <八域>/M-0001-短名.md，未分的放 未分/
  memory/    # [源头] 各角色的本书记忆：约定、教训、手感、校准（<角色>.json 是源头，<角色>.md 是生成的视图；不记作者偏好）｜memory add/reinforce/edit/merge/archive/restore/promote（经理按角色交回的记忆提议执行）｜如 writer.json、writer.md、reader.json…（每个角色一份）
  .ncc/    # [工作件] 机器工作件：写手包、审稿快照、横评、操作日志、迁移备份｜只由脚本写
    写手包/    # [工作件] 写手包（脚本组装、留档）｜pack｜如 ch-0001.md
    快照/    # [工作件] 审稿前的正文快照（复审只看改动）｜review plan/delta｜如 ch-0001.md
    横评/    # [工作件] 模型横评：同一写手包的各模型草稿、盲稿与结果｜ncc_eval.py bench｜如 ch-0001/
    操作日志.jsonl    # [历史] 写操作日志（团队交接）｜脚本自动追加
    记忆日志.jsonl    # [历史] 记忆的每次新增、强化、合并、归档、晋升、撤回｜memory 命令自动追加
    交接/
      会话.jsonl    # [历史] 会话交接卡：作者在会话里的原话、决定、情绪、待办（只追加，关掉也是追加一条）｜handoff add/close
    派单/    # [工作件] 派单头（脚本组装、留档）：本角色记忆、作者刚说的话、技法参考｜brief｜如 outliner-ch-0012.md
    迁移备份/    # [工作件] 迁移时移走的旧版手写视图｜migrate｜如 author-intent.旧.md

{book_root}/
  _作者/    # [作者] 关于作者本人的跨书资产
    偏好.json    # [源头] 偏好、雷点、否决过的推荐（权重随时间衰减）｜pref like/confirm/reject/dislike
    素材/    # [作者] 跨书共用的素材卡｜material add --shared｜如 <八域>/MS-0001-短名.md
    技艺库/    # [作者] 跨书技艺库：每本书一份｜完本后 craft init 再填｜如 <书名>.md
    记忆/    # [源头] 跨书记忆：换一本书也成立的角色经验（<角色>.json 源头＋.md 视图）｜memory promote；edit/reinforce/merge/archive/restore/consolidate --shared｜如 writer.json、writer.md
    技法库/    # [作者] 跨书技法库：拆书学来的写法卡，每张带证据、适用条件、代价｜technique add（deconstructor 学法时）｜如 <类别>/T-0001-短名.md
      使用记录.jsonl    # [历史] 技法卡用在哪本书哪一章、结果如何；停用与恢复｜unit close 自动结算；technique result/retire/restore
    进化/
      覆盖.json    # [源头] 作者覆盖层：通过闸门的规则改动（阈值、词表增删、新类目、新技法类别）；插件默认 < 书库配置 < 作者覆盖 < 本书配置｜evolve apply/revert
      提议.jsonl    # [历史] 进化提议：提出、评测、作者确认、生效、撤回｜evolve propose/eval/apply/reject/revert
  _拆书库/    # [角色] 拆书库：每本对标书一个目录（原文、索引、实体、台账、报告，进度在 _progress.json）｜deconstructor；decon index/mark/stats｜如 <书名>/索引/chapter_index.json、<书名>/台账/伏笔.jsonl、<书名>/报告/基线.json
```

## 词表

脚本认的取值都在这里；别的文档要列取值，就引用"词表"，不再抄一份。

| 词表 | 取值 | 用在哪 |
|---|---|---|
| 引导档位（`levels`） | 新手、熟手、老手 | init --level、level |
| 主角弧光（`arcs`） | 正向、负向、平弧 | soul --arc |
| 承诺类型（`promise_types`） | 伏笔、悬念、爽点欠账、人物弧、感情线、卷目标、名场面、母题、期权、暂定决策 | promise add --type |
| 承诺编号前缀（* 为其余类型）（`promise_id_prefix`） | 伏笔→FS、暂定决策→TD、名场面→SC、母题→MT、*→P | promise add 自动编号 |
| 不面向读者的承诺类型（不计水章判定、不进"读者在等什么"）（`non_reader_types`） | 期权、暂定决策、母题 | water、读者此刻 |
| 承诺的开放状态（`open_states`） | 开放、推进中 | 逾期与水章判定 |
| 章节状态（另有 done）（`chapter_states`） | pending、drafting、drafted、checking、reviewing、revising、failed | chapter mark |
| 张力（`tension`） | 压、放、平 | chapter mood |
| 旧版张力名的换算（`legacy_mood`） | 压抑→压、释放→放 | 读旧书时自动换算 |
| 情绪色（`colors`） | 爽、燃、虐、甜、怕、笑、悲、敬、叹 | chapter mood --colors |
| 签约点（`signing_points`） | 主角与欲望、世界的不公、主角的机会、第一次小兑现、长线钩子 | sign |
| 场景卡必填项（`scene_required`） | 视角、目标、翻转、两难、情感 | scene check |
| 关键章场景卡另须填（`scene_key_required`） | 盲区、阻碍、画面、风险、默认写法 | scene check |
| 每批场景卡的章数（按写作模式）（`scene_batch`） | 建筑师 5、混合 3、园丁 2 | scene next |
| 完整人物卡必含（`character_required`） | 欲望、需要、恐惧、声音 | gate settings |
| 单元复盘区块外必填节（`unit_review_required`） | 暂定决策、故事审、下一单元 | unit close |
| 卷复盘区块外必填节（`volume_review_required`） | 承诺盘点、书魂检验、数据归因、变更提议 | gate volume |
| 收束清单区块外必填节（`finale_required`） | 承诺清算、暗线收拢、书魂回答 | gate finale |
| 时代背景（`eras`） | 古代、架空古代、近代、现代、架空现代、未来 | era；古代与架空古代启用时代错置词提醒 |
| 二十四门学科（底蕴卡）（`domains`） | 爽文、人情冷暖、社会、心理、历史与朝代更替、政治、经济、军事、天文、地理、生物、自然、物理、化学、数学、工程、建造、工艺、语言、文学、艺术、视频、想象力、宗教神话民俗 | knowledge、material --domain、study |
| 学科别名（`domain_alias`） | 人情→人情冷暖、历史→历史与朝代更替、朝代→历史与朝代更替、宗教→宗教神话民俗、神话→宗教神话民俗、民俗→宗教神话民俗、影视→视频、建筑→建造、医学→生物、医药→生物、气象→自然、历法→天文、称谓→语言、礼仪→语言、诗词→文学、音乐→艺术、书画→艺术 | --domain 自动归一 |
| 八域（学科分组；素材卡按此分目录）（`regions`） | 甲-爽感：爽文；乙-人间：人情冷暖、社会、心理；丙-天下：历史与朝代更替、政治、经济、军事；丁-天地：天文、地理、生物、自然；戊-物数：物理、化学、数学；己-造物：工程、建造、工艺；庚-表达：语言、文学、艺术、视频；辛-想象：想象力、宗教神话民俗 | material add |
| 素材卡必填项（`material_required`） | 来源、内容、可用处 | material check |
| 素材可信级（`material_trust`） | 亲历、转述、文献、传闻、拆书 | material add --trust |
| 进写手包的作者种子编号（`writer_seeds`） | 1、3、6 | pack |
| 团队岗位（`team_positions`） | 主编、主笔、设定、考据、发展编辑、审稿、试读、拆书 | team set |
| 读者数据来源（`feedback_sources`） | 真实、模拟 | feedback add --source |
| 读者数据种类（`feedback_kinds`） | 追读、弃读、略读、划线、评论、出戏 | feedback add --kind |
| 记忆种类（`memory_kinds`） | 约定、教训、手感、校准 | memory add --kind |
| 会话交接种类（`handoff_kinds`） | 原话、决定、情绪、待办 | handoff add --kind |
| 交接作用层（`handoff_layers`） | L0、L1、L2、L3、L4、拆书 | handoff add --layer（L0 书魂 … L4 文字；拆书单列） |
| 技法类别（`technique_kinds`） | 大局设计、剧情规划、爽点规划、暗线伏笔、情绪调用、人物塑造、设定构造、文笔参考 | technique add --kind；场景卡「技法：」 |
| 技法卡状态（由证据与使用结果推出）（`technique_states`） | 样本、手法、已验证、停用 | technique list |
| 技法适用阶段（`technique_stages`） | 开篇、连载、卷末、收束 | technique add --applies 阶段=… |
| 置信级（`confidence`） | 原文明说、强推断、弱推断 | technique add --confidence；拆书抽取 |
| 写作模式（`writing_modes`） | 建筑师、园丁、混合 | init --mode、mode |
