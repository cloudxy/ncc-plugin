# NCC 开发工作流

本文件是开发路径、阶段、返回规则与证据契约的唯一规范。适用于 NCC 插件维护和升级；小说创作沿用原七技能与十二角色。设计依据见[升级设计](../designs/engineering/workflow.md)，方法出处见[致谢](../../ACKNOWLEDGMENTS.md#开发设计参考2026-10-12)。不要求安装或调用外部技能。

工程角色通过ncc-dev单独调度，注册表development与[执行协议](../../skills/ncc-dev/references/roles.md)定义产品经理、产品设计师、项目架构师和DBA的触发、读取和交付。它们不加入小说每章流程。

## 定位与授权

开始时显示 plugin_root（实际加载技能/脚本所在根）、repo_root（作者指定的活动 Git 工作树）、分支、基线与脏改动。不能因插件加载于独立克隆，就在该克隆中执行项目的 Git 操作。五端保持项目级接入，同任务只有一个活动工作树；zcode 独立克隆也可开发，通过 GitHub main 汇合。

先查代码与环境，继承已有指令和有效决定；常规可逆选择由开发者处理。只询问会改变目标、公开接口、创作标准或风险承诺且未授权的关键选择，每轮优先一至三项，给推荐、理由、代价与备选。目标与设计合并评审，计划只有引入新关键取舍时才另行确认。确认记录来源、范围和对应工件，编辑性修订不重置全部决定。

不清理他人脏改动，不自动 stash/reset，不安装用户级技能；不自动发送消息或发布。开发记录、评测和报告不含真实书稿、素材或完整私人会话。规则候选优先在临时隔离副本实现，完成回归后由作者确认，再整合到项目级规则源。隔离不是新的长期开发仓库。

## 任务路径

按未知性、影响面与可逆性选择，不能按行数规避证据。规则变更是可叠加的风险标签。

| 路径 | 工件与执行 | 终点 |
|---|---|---|
| spike 探索 | 任务记录写问题、探针、观察、推荐；临时产物隔离，不保留生产实现 | 有证据的结论；转实现时重新定范围和计划 |
| bounded 局部 | 一个任务记录包含短书面计划、验收、验证和交付状态；接口/数据契约稳定 | 本地候选验收或按授权发布 |
| architectural 结构 | 任务记录链接书面 spec 和分阶段计划，包含接口、数据、验收、风险与回滚 | 分阶段验收、按授权发布 |

隐藏复杂度出现时升路径并返回最早受影响阶段，保留有效事实与决定。独立新任务说明拆分理由和承接关系。文案无需伪造失败测试；代码缺陷先复现，规则调整先定义样例和预期。

## 开发阶段与返回规则

结构路径完整执行下表；局部路径把 D1/D2 合并到任务记录；探索只完成 D0、探针与结论。阶段不是逐关询问作者的命令。

| 阶段 | 完成依据 | 失败或变化的返回点 |
|---|---|---|
| D0 定位 | 请求、活动仓库、已有决定、路径、必要基线与既有失败归属 | 先查目录/目标歧义，保留脏改动 |
| D1 方案 | 问题、目标/非目标、备选、理由、接口/数据影响、验收、风险与回滚；关键选择有决定 | 补事实/关键选择 |
| D2 计划 | 每步范围、前置条件、验证、回滚和交付范围；需确认之处标明 | 拆小不可验收步骤，不先铺不可执行文档 |
| D3 实现 | 按计划小批改动，复现缺陷或冻结规则样例 | 范围变化回 D1/D2；实现缺陷留 D3 |
| D4 验证 | 对确定候选运行全量自测、一致性及适用行为/宿主检查，绑定指纹 | 失败回 D3；环境受限保留待验 |
| D5 评审 | 核查意图、实现、反例、边界、覆盖与私有内容，报告绑定候选 | 修复后重验；无独立能力写“自查完成，独立评审待办” |
| D6 发布 | 最终候选、同步、质量证据、发布授权；提交/推送、远端提交、消费克隆状态 | 合并改变内容回 D4/D5；不覆盖脏克隆 |
| D7 观察 | 新会话核验实际加载根/版本与代表操作，记录回滚条件和结果 | 缓存未刷新保持运行待验；缺陷进修复/回滚任务 |

关键缺陷必须修；非关键延期记录理由、决定人和后续项。私有泄露、缺必要验证、陈旧证据不能豁免。小说角色不承担代码评审。独立会话、作者人工或宿主评审均可；遵守当次代理授权，多代理不是运行依赖。

## 工程职责与执行接口

新开发任务及实质范围变化在D1声明实际影响并选用职责，D2完成相应设计交付，D3处理major问题后实现，D4/D5复核行为和实现。纯文档明确使用documentation，无交互或数据影响时不调用相关角色。当前会话可按职责顺序执行，execution标为current_session；支持代理且已有授权时按角色派单，标为subagent。标识只是执行声明，是否实际执行仍需证据与独立核对。

工程状态直接放在原任务的engineering字段，不另建状态库。脚本只做确定性计划、派单和报告验证，不调用模型：

```bash
python3 scripts/dev/development.py --repo "$REPO_ROOT" --task "$TASK" plan --effects architecture --input docs/engineering/code-layout.md
python3 scripts/dev/development.py --repo "$REPO_ROOT" --task "$TASK" packet --role project-architect --output docs/evidence/任务号/architect-packet.json
# 按派单实际执行角色，产生约定JSON报告；报告由代理或当前会话写入指定证据路径。
python3 scripts/dev/development.py --repo "$REPO_ROOT" --task "$TASK" record --packet docs/evidence/任务号/architect-packet.json --report docs/evidence/任务号/architect-report.json
python3 scripts/dev/development.py --repo "$REPO_ROOT" --task "$TASK" check --delivery
```

REPO_ROOT/TASK使用当前已定位值；影响类型可以组合，具体职责由注册表决定。输入限定已授权源码/设计/合成案例，真实私有.env、书稿和忽略文件不能进入派单。派单绑定目标、决定、角色定义、协议、入口及输入字节；变更后旧报告不能通过，需重新执行角色。计划改变会清空当前登记但保留旧报告文件。

record检查职责字段、来源、问题证据、执行方式与结论。major未解决不能ready；changes_required和blocked分别登记失败/受阻，不能靠字段齐全放行。ready仅指该角色的本次设计/评审结论，真实数据库、UI和产品采用仍按各自证据判断。check --delivery要求选中角色全部通过，原check_dev_workflow的交付检查同步执行此约束；历史无engineering_contract的冻结任务不强制补角色报告。

进入实现前由协调者处理角色提出的具体问题，已有授权内的修正不反复询问作者。新增关键取舍沿既有确认边界。产品经理维持小说创作主线，设计师减少作者操作，架构师统一归属和契约，DBA保护既定数据库及历史；不因角色增加作者审批或额外数据库。

## 任务记录与检查接口

每任务唯一进度记录位于 docs/tasks/，正文保存短计划、决定来源、边界、基线、阶段、下一步、受阻原因、风险、环境、结果摘要与回滚。结构任务只链接 spec/计划，不复制其正文；两者可在同一方案内分节维护并引用同一文件。文档归属见[文档组织规范](documentation.md)。生成物也属于候选。记录一个标记为 ncc-dev-json 的 JSON 代码块；只用标准库检查，不建第二份状态库。

```ncc-dev-json
{
  "schema": 1,
  "id": "example",
  "goal": "修正现有参数提示",
  "route": "bounded",
  "risk_tags": [],
  "repo_root": "/absolute/active/repository",
  "plugin_root": "/absolute/loaded/plugin",
  "branch": "main",
  "base_commit": "替换为 git rev-parse HEAD 的完整提交号",
  "stage": "D3",
  "next": "实现后冻结候选并验证",
  "blocked": "",
  "decisions": [{"source": "作者当前请求", "scope": "修正提示，未授权发布"}],
  "spec": "",
  "plan": "",
  "scope": ["commands/example.md"],
  "foreign_changes": {},
  "evidence_paths": [],
  "candidate": {},
  "required": ["unit", "plugin", "docs"],
  "evidence": [],
  "delivery": {"local": "pending", "commit": "not_requested", "remote": "not_requested", "clone": "not_requested", "runtime": "unverified"}
}
```

此示例不是已验收记录。实际任务替换路径、基线和范围。scope 为精确产品路径列表（含删除项、新文件与仓内软链源），不支持通配符。foreign_changes 为本次不交付的在途路径 → 归属/理由，不能把本任务规则放进去绕过验证。evidence_paths 只能列 docs/tasks/ 下当前任务记录或 docs/evidence/ 下日志，不能排除产品文件；日志须人工检查无私有内容。记录本身自动排除自身指纹，其他任务记录若修改需显式归属。结构路径 spec/plan 必须存在并在 scope 中。repo_root 与当前活动工作树必须相符，plugin_root 可不同，但须核验加载来源。

在活动仓库运行（PLUGIN_ROOT、REPO_ROOT、TASK 为调用者已定位的值）：

```bash
python3 "$PLUGIN_ROOT/scripts/dev/check_dev_workflow.py" snapshot "$TASK" --repo "$REPO_ROOT"
python3 "$PLUGIN_ROOT/scripts/dev/check_dev_workflow.py" check "$TASK" --repo "$REPO_ROOT"
python3 "$PLUGIN_ROOT/scripts/dev/check_dev_workflow.py" check "$TASK" --repo "$REPO_ROOT" --delivery
```

snapshot 只更新该 JSON 块内的 candidate；不自动添加通过证据，不覆盖旧证据，不扫描私有小说目录。按路径排序计算 SHA-256，纳入相对路径、文件内容或软链目标、执行位、删除项与 base commit；仓内软链所指源文件同样纳入。拒绝绝对/上跳/私有/忽略/越界路径、断链和未归属 Git 差异。实际差异同时核查工作树、暂存区与未跟踪文件，暂存后从工作树删除的新文件也须报告归属。缺文件只有在基线确有该文件且现已删除时才可作为删除项。切换基线或分支必须显式更新任务并重验。

check 核验记录、候选与已登记证据；--delivery 再检查 required 中每类都有当前候选的 passed 证据，并要求 local 为 accepted。普通 check 允许尚未完成的证据，但会打印 pending/blocked/failed；不把记录有效当验收通过。陈旧/缺报告、失败或受阻的必需证据不能通过交付检查。已暂存的任务产品须与候选的字节、软链目标、删除项和执行位一致；本地验收不要求提前暂存，D6 精确暂存后必须再检查，避免提交未经验证的 index 内容。

每份证据包含 id、kind、candidate（冻结指纹）、status（passed/failed/blocked/pending）、command（含实际命令或会话操作）、exit_code（模型/人工可 null）、summary、environment、coverage、report（仓内日志路径）和 report_sha256。报告须列输入、观察、实际结果与缺项；修改报告也会使其校验失败。检查器只证明结构、边界和内容新鲜度，不能证明报告真实或语义质量。宿主证据需实际新会话，不能手填 passed 消除待办。

## 恢复与证据失效

先读任务记录，再核对 repo/plugin 根、分支、基线、实际 Git 差异和 check 结果。无变化接 next，沿用有效决定；候选变化列出陈旧证据，至少回 D4 重跑适用确定性检查，语义变化补相应行为验证和独立评审。影响目标、接口或标准则回 D1/D2 并重新处理相关决定。只补证据元数据/日志不使产品指纹递归变化，但日志自有哈希仍核查。

不能通过重做 snapshot 继承旧 passed。测试失败回 D3；缺报告保留 pending；目标 CLI 不可用记 blocked 或 unverified。远端变化合并后重新冻结/验证；消费克隆脏则报告冲突，不能强制覆盖。检查器不做自动 Git 同步、发布或任务调度。

## 分层验证与规则确认

测试范围由实际影响决定，不按修改文件数量或所在目录决定。作者于 2026-10-16 明确：纯文档或无功能影响的调整不跑全量；局部修改和新增功能只测试受影响部分；大范围改造才跑全量。

| 影响范围 | 必要验证 |
|---|---|
| 文案、注释、排版 | 内容与引用核对；没有功能影响时不跑功能测试 |
| 文档搬迁、入口查找路径 | 链接、接线和直接受影响的路径用例；不跑无关创作回归 |
| 局部修复、新增功能 | 缺陷/新功能用例、边界、相邻接口和兼容性；不用无关全量测试 |
| 大范围重构、跨模块行为、核心数据契约 | 全量自测，加受影响的行为和集成验证 |
| 创作标准、闸门、角色职责或判据变更 | 对应规则行为样例；审稿判据变化时追加锚定章模型回归 |

大范围改造的全量检查入口如下，局部任务按适用项选择：

```bash
python3 -m unittest discover -s scripts/tests -t scripts -p 'test_*.py'
python3 scripts/dev/build_registry.py --check
python3 scripts/dev/check_plugin.py -v
python3 scripts/dev/build_docs.py --check
python3 scripts/ncc_eval.py mech
```

任务记录先说明影响范围和检查选择，再记录实际测试数、退出码、环境与候选指纹；无功能影响时可不设功能测试项。改变开发路由、恢复或交付行为时，用真实代理执行的场景验证受影响行为，不能用词句扫描代替；不改变这些行为的文档编辑无需重跑全部场景。开发流程大改的代表场景包括：探索不保留生产实现；局部有短计划且继承授权；跨端入口走结构路径；D3 后换会话恢复；验证后改规则使证据失效；失败/缺报告/CLI 不可用分别表达；同步改变候选重验且脏克隆不覆盖；“接着写第十章”回创作入口。

registry 分片与生成视图、skills/agents 改动按 AGENTS.md 判断语义影响；文字、链接和目录定位不自动触发模型回归。涉及审稿判据时按 ncc-eval：prepare → 每包独立 fresh continuity 盲审 → score。基线/候选冻结相同锚定输入与可观测模型配置，重复次数按稳定性要求确定；答案不进入审稿上下文。事前写允许差异和异常处置，核查报告完整性、检出/定级/结论准确率、干净章误报和稳定性。score 退出 0 不证明报告齐全；mech 与 gate 仅覆盖机械层。开发路由变化另用开发场景验证，不靠无关锚定回归证明。不能完成必要验证时保留待验，不伪造报告。实质规则候选完成对应验证后呈作者确认，才能整合发布。

## 宿主与交付

check_plugin 只核查命令登记、三个项目级相对软链与可定位的仓内源文件。参数提示等命令 frontmatter 由 registry.commands 持有、build_docs 生成；应修改元数据源再生成，不能只改生成的命令文件。claude、codex、kimi、grok、zcode 各记录静态与新会话运行结果：passed/failed/unverified/blocked。每端运行核验发现入口、参数转入、plugin_root/repo_root、加载来源/版本、代表调用与恢复；grok 另查重复发现/优先级。完整失败场景可仅在主宿主执行，不假设五端相同斜杠语法。当前会话修改后读文件不等于新会话加载成功。

交付分开记录本地验收、提交、远端发布、消费克隆同步与运行加载。无发布授权停在候选。发布时检查 core.hooksPath=.githooks、暂存范围与私有内容；先拉合并，最终内容重验，精确暂存提交，推送并核对远端具体提交。钩子只保护同步/暂存路径，不做质量或全文隐私审查；不绕过钩子。消费克隆仅在干净且目标提交明确时更新，新会话核验加载。回滚按任务范围保留未提交候选或对已发布提交做授权 revert，不用 reset 覆盖他人工作。


## 注册表构建与兼容入口

现行规则值只编辑 workflow/registry 下对应分片；顶层归属与兼容顺序见 `scripts/ncclib/registry.py` 的 SHARD_KEYS 与 KEY_ORDER。新增顶层键时同批更新归属、顺序和用例；不在多个片里复制同一业务值。`workflow/registry.json` 为只读生成视图，保留给原始文件读者使用。core 与准备工具、开发检查器和生成器都调用同一纯标准库 loader；视图陈旧、缺片或契约错误会在运行命令前失败。

修改后按序执行：

```bash
python3 scripts/dev/build_registry.py
python3 scripts/dev/build_docs.py
python3 scripts/dev/build_registry.py --check
python3 scripts/dev/check_plugin.py -v
python3 scripts/dev/build_docs.py --check
```

build_registry 从分片合并后以临时文件原子替换视图，构建阶段无需旧视图有效；--check 不写文件，陈旧退出 1。只修视图不改变书数据，也不运行书项目 migrate。生成物与源片一起进入候选指纹，必须一起分发。

scripts/dev 是开发实现，scripts/tests 是测试与合成样例；运行入口与 ncclib 保持独立。旧顶层开发脚本仅转发，原 `unittest discover -s scripts` 仍支持；当前任务与新文档使用上面的新路径。冻结证据和历史设计中的旧命令不重写。五端新会话完成兼容验证之前保留薄入口，删除入口另立明确的兼容变更。
