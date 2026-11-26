# 数据服务与创作后台

NCC v4在原有文件工作流之外，提供PostgreSQL数据服务、FastAPI接口和React小说创作工作台。作者日常围绕六大创作空间开展出品把控与AI协同写作：“创作台、大纲与暗线、作品资料（万象设定与人物角色管理）、公共陈列库、市场与风向、我的待办”；定义、关系与时间、地图、历史维护、导入导出、评分、任务、审计、AI配置和运行管理默认折叠收纳于“高级管理”。

文件模式继续只需Python标准库。数据库模式需要Python 3.11以上（开发验证为3.12）、PostgreSQL 17以及Node.js 22.12以上。前后端依赖分别由`uv.lock`和`package-lock.json`锁定。界面、数据服务与独立Worker共用一套应用服务；启动服务不会自动建库或迁移真实小说。

## 安装与启动

在仓库根目录执行：

```bash
uv sync --python python3.12 --extra dev --frozen
npm --prefix apps/management-web ci
npm --prefix apps/management-web run build
```

配置使用Dynaconf统一管理，属于一次性初始化。公共默认值在`config/default/settings.toml`，可按需增加`config/<ENV>/settings.toml`；ENV由`config/.env`的`NCC_ENV`指定，默认local。覆盖顺序为默认文件 → 兼容进程值 → 环境文件 → config/.env。普通用户只维护文件，无需每次设置终端变量。保留既定PostgreSQL主机、端口、账号和正式库名，在`config/.env`保存。先执行：

```bash
.venv/bin/ncc-data init
```

初始化生成权限为600的本地`config/.env`；存在时原值不变。按`config/.env.example`填写`NCC_DB_HOST/PORT/NAME/USER/PASSWORD`和模型配置。连接串原已确定时可改用单一`NCC_DATABASE_URL`，不要同时保留非空的分项连接。程序不改数据库服务参数、不猜测账号、不自动建库。若已有NCC格式配置，可用`init --from-existing '<已有配置文件>'`初始化；仍不覆盖现有`config/.env`。真实文件已忽略，不提交Git。

旧版本把私有配置放在项目根`.env`时，再执行一次`init`即可原字节迁入`config/.env`并移除旧位置；不需要重新填写。新旧文件同时存在时会停止，请先核对并仅保留配置目录中的文件，程序不自动合并。默认加载不会回退旧位置；高级自动化仍可用`--config`明确指定隔离配置。完成迁移后执行`mcp-config --host both`更新本机宿主接线。

只使用两个库：线上正式库`ncc-pro`，以及同一服务器、端口、账号和连接选项的本地测试库`ncc-dev`。测试库名固定为`ncc-dev`，不维护第二套连接。数据库维护者只需在初始化时准备这两个库；所有作品用逻辑范围隔离，不按作品、验收、恢复操作创建库。两个命令行入口的默认目标分工如下：

- **统一启动器 `./start.py`**：面向作者日常创作，无模式参数时默认使用 `production` profile 连接正式库 `ncc-pro`（默认监听 `http://127.0.0.1:8761`）；需要本地隔离调试时显式传 `--database ncc-dev`（切换 `local` profile 与 `ncc-dev`，仍走常规端口 `8761`），自动化测试专用端口 `8788` 使用 `--test`。
- **底层 CLI `.venv/bin/ncc-data`**：未显式传模式参数时读取 `config/.env` 的 `NCC_ENV`（缺省 `"local"`），本地命令默认自动选中 `ncc-dev`，不会默认连接 `ncc-pro`。

```bash
# 推荐：跨平台启动器（macOS 使用 ./start.py；Windows 使用 py -3 start.py 或 python start.py）
# 默认连接正式库 ncc-pro（8761 端口）；若需操作测试库请显式加 --database ncc-dev
./start.py --migrate
./start.py --create-user '<账号名>'
./start.py --check
./start.py --open
```

也可以分别使用底层 `ncc-data` 命令（默认 `NCC_ENV="local"` 时选中 `ncc-dev`）：

```bash
.venv/bin/ncc-data migrate
.venv/bin/ncc-data create-user '<账号名>'
.venv/bin/ncc-data doctor
.venv/bin/ncc-data serve
```

`./start.py --check` 与 `.venv/bin/ncc-data doctor` 都会输出实际选中的 `profile`、`database`、`default_admin_active` 与 `origin`（`./start.py --check` 默认输出 `production` 与 `ncc-pro`，加 `--database ncc-dev` 输出 `local` 与 `ncc-dev`；`ncc-data doctor` 在默认 `NCC_ENV="local"` 下输出 `local` 与 `ncc-dev`）。没有匿名管理入口：当目标库 `ncc_user` 为空时，`migrate` 会自动建立初始默认系统管理员 `admin` / `123456`（标记 `must_change_credentials=true`，绝不覆盖已有账号），第一次使用时必须进入后台同时修改默认账号名和密码（新密码至少12字符）；也可随时通过 `create-user` 在终端两次输入至少12字符密码新建账号（空库下通过 `create-user` 建立的首个账号同样为系统管理员且无需强改）。主机差异化策略：通过回环地址（`127.0.0.1` / `localhost` / `::1`）监听和访问时，默认管理员账号仅在顶栏展示醒目安全提醒与快捷修改入口，不阻断日常操作；一旦监听或访问非回环真实地址（如局域网/公网 IP、`0.0.0.0` / `::`、或非回环 `NCC_PUBLIC_ORIGIN` / `Host` 头），后端将在默认管理员完成改名改密前强制拒绝全部业务接口与事件流（返回 `403 credential_change_required`），前端锁定在不可关闭的修改凭据对话框。打开`http://127.0.0.1:8761`登录。若使用 `ncc-data serve` 分离启动，可在另一个终端启动任务执行器，自动读取同一份`config/.env`并保持同一目标库（直接运行 `./start.py` 时已自动同启 Web 与 Worker）：

```bash
.venv/bin/ncc-data worker
```

直接通过底层 `ncc-data` 维护或部署正式环境时，可在服务器`config/.env`设置`NCC_ENV="production"`，或在单次命令显式传`--production` / `--profile production`，同一组`migrate / create-user / doctor / serve / worker`即选中线上库`ncc-pro`（`./start.py` 无需额外参数即默认选中 `ncc-pro`）。

API和前端同源运行，采用HttpOnly会话与CSRF令牌。远程部署需要HTTPS同源反向代理，并在`config/.env`中将`NCC_PUBLIC_ORIGIN`设为实际地址；代理需支持SSE、限制请求大小、关闭事件流缓冲。CLI与Worker不接收任意SQL或脚本。`serve`默认仅监听本机，不暴露数据库端口。

源码安装会使用`apps/management-web/dist`。单独安装Python wheel时，迁移与定义包随wheel分发；前端单独构建并在`config/.env`通过`NCC_WEB_DIST`指向构建目录。未经构建的前端返回明确的未就绪信息。

## 创作与审核

1. 建立书项目、作者资料库、系列、宇宙、拆书研究或固定基线的IF分支。
2. 在创作台选择已有内容或开始新稿，直接写入会自动保存私人草稿；“保存修订”才采用为正式内容。另一窗口修改正式内容后，旧基线不能直接覆盖。
3. 输入目标，可选参考资料，选择正文、纲要、设定、资料整理或修改任务，点击“开始处理”。选中文本后可改写选段；“仅评分”检查现有内容并保留正文。
4. 系统准备上下文、规划、评价、生成和有限返修。进度、分数、依据、问题、版本和实际用量保存在数据库。作者可暂停、改目标、编辑或选版本；人工草稿保存会暂停同对象的后台任务。
5. 达标成果默认等待作者采用。采用前重查范围版本、候选hash、当前权限、评分和故事审；正文与可确认的台账变化在同一事务提交，未解析的事实进入待处理记录。后续索引任务可恢复。

正文/纲要/设定/抽取分别使用P1–P4；修改结果仍按其内容类型评分，并另外展示P5执行质量。85分为初始质量线、70分以下建议重构、任一维低于3分转修改；严重硬伤和缺证据会阻断采用。最多两次总修订，包含场景计划返修，不能靠重试无限重写。分数属于当前量表下的模型评价，不是读者实测。详细量表唯一见[评分说明](../../skills/ncc-review/references/quality-scoring.md)。

## 配置创作模型

管理后台「AI 配置」（`/admin/models`）将「模型与连接」置于第一页签，第二页签为「本机 CLI OAuth 订阅」，支持兼容 OpenAI Chat JSON 的 HTTP API Key 网关（`transport="http"`）与本机 CLI OAuth 订阅通道（`transport="cli_subscription"`，覆盖 `grok`、`codex`、`agy`）混合路由：

- **模型与连接（第一页签）**：可登记多套 HTTP 网关配置或 CLI 订阅配置，并将场景计划（`plan`）、正文与设定（`write`）、修订（`revise`）、独立评价（`judge`）、第二评价（`judge_secondary`）分别绑定到不同已启用条目。HTTP 通道仅保存网关地址、模型标识和环境变量名，绝不接收或回传明文 API Key；支持按需触发轻量在线探测（`GET /api/v1/operations/models?live=true`，仅校验连通性或本机 CLI 登录态，不消耗生成额度）。
- **本机 CLI OAuth 订阅（第二页签）**：支持在网页端发起无 `osascript` 弹窗的受管 Device-Auth 授权会话（`grok` / `codex` 自动提取授权链接与一次性设备码并轮询落盘状态，`agy` 返回安全终端手动指引，会话 180 秒自动过期清理），授权就绪后可一键「绑定为写作/审评模型」。订阅凭据始终留在本机，绝不回传浏览器，调用子进程时自动剥离外部按量计费环境变量以防串路扣费。

`ncc-data doctor` 与 `./start.py --check` 同步识别网页已保存的 HTTP 与 CLI 订阅路由状态。已启动的任务固定使用开始时快照的模型路由。某一用途未在网页绑定且无匹配已启用条目时，回退读取下列环境变量（修改环境变量后需重启服务和 Worker）：

| 配置项 | 用途 |
|---|---|
| `NCC_MODEL_URL` | 兼容Chat JSON接口的网关基础地址，最终请求路径为`/chat/completions` |
| `NCC_MODEL_KEY` | 网关凭据，可用于本机无密钥网关；不发送给浏览器 |
| `NCC_WRITER_MODEL` | 规划、生成及修订模型 |
| `NCC_JUDGE_MODEL` | 独立评价任务使用的模型，未设置时使用写作模型的新调用 |
| `NCC_SECOND_JUDGE_MODEL` | 可选第二评价器，启用后分歧超阈值转人工复核 |

没有配置时任务保留待处理，界面不会生成演示正文或分数。单次调用不持有数据库事务；续执行需要有效租约和当前权限。外部模型请求不保证天然恰好一次；已知用量入账，响应不明的成本须按网关记录对账。错误响应不进入普通日志。

自动定稿支持两种授权模式。“作者授权试运行”由作品所有者明确启用，记录授权依据、对象、方案、期限和次数；可以在尚无真实校准数据时自动采用达标稿，但始终标记“校准未验证”。“仅使用已校准策略”仍需要真实人工标注的开发/留出样本，并针对固定量表、方案和评价器启用校准。接口拒绝同源泄漏、重复计数及不足样本；候选门槛为20个留出来源组、20组至少三次重复评分、20组偏好比较、10组严重缺陷样本，同时满足80%偏好一致、分差90分位不超过5分、植入严重缺陷误放为0。附加评价器和P5也需分别校准。有限样本不保证未知缺陷零误放。

两种模式都必须通过85分质量线、维度底线、硬伤/证据、二评/P5、版本与当前权限检查。开篇前三章与关键章仍保留作者选择；授权不包含对外发布。授权、校准和范围令牌可以撤销；评分策略改变须重新授权，迁移遗留的未绑定策略授权也须续授权。

启用步骤：在“成员与设置 → 自动定稿授权”选择模式、明确对象及方案，填写授权依据，设置期限与次数并登记；随后回到创作台选择同一对象，在“成果采用方式”选中该授权，再点击“开始处理”。初始建议为24小时、最多3次，可自行调整；未选择授权的任务仍交作者审核。P5修订同时需要其内容方案（正文P1、纲要P2、设定P3、资料P4）和P5授权。被阻断的自动采用显示原因，保留候选，不消耗成功采用次数。

试运行功能已接通并完成合成流程验证；本地工作区尚未配置真实数据库、模型网关或目标作品，因此没有声称任何真实作品已经开始自动定稿。部署后须通过上述步骤将授权写入目标范围；没有用测试样本伪造校准资格。

## 资料与高级管理

类型/属性/关系是版本化定义，领域名词是种子内容；新类型不要求新增表。内置16领域目录覆盖人物、种族、组织、力量、地理、器物、经济、思想语录、叙事等273项。通用维护支持精确数值字符串、分子分母、数量单位、坐标系、引用、多值、秘密属性和附件。未注册属性会报错，未知输入不会静默丢弃。

稳定身份与名称记录分开。实体修订、事实的世界时间与记录版本、来源和审计可追溯；关系可带区间、公开性和证据。排他归属及组织循环在正式采用前校验。角色认知区分知道、怀疑、误信、不知和否认。计划事实与正式事实分别记录；未解析对象可登记`soft_reference`的`ncc://`引用，不能冒充已确认关系端点。

定义发布、变更预检/批准/采用、三方分支合并、重复身份合并、信息拆分与历史恢复都形成可审查变更。恢复会创建新修订，原记录保留。大于500项的单次维护需分批明确处理；冲突不会按先到先得覆盖。

中文名称和正文支持字面搜索，图谱最多两跳并显示截断提示；地图使用虚构坐标系和可选底图，坐标资料可通过表格替代。当前未接入向量提供方，语义相似召回不是已启用能力。质量扫描和可视化是有界查询，覆盖范围在界面显示；正式大书库的性能需要按实际规模压测。

## 导入、导出与旧CLI接入

导入支持CSV、JSON/JSONL、Markdown和纯文本。先上传保留原件，选择映射并预检；未知字段明确列出。交换包会重建定义、实体、关系及附件，身份重新映射。前向引用依赖在同一批处理，超预算依赖组会报错；整个预检在回滚事务中执行，正式内容不变。采用后按批次留回执，中途取消不撤销已经提交的批次。

JSON导出固定版本，包含当前对象、可访问事实、定义以及有权限的历史和附件，不截断为首200条。CSV和Markdown用于查看；CSV对公式开头字段作安全处理。除此之外，创作台顶栏「导出成稿」与「导入与导出」（`/admin/exchange`）均提供面向作者交付的干净**成稿导出**（共用纯标准库 `src/ncc_shared/manuscript.py`，支持标准 EPUB 3 `.epub`、纯文本 `.txt` 与合稿 Markdown `.md`，可按分卷或「仅已定稿章节」过滤，严格按全书卷章顺序 `ordered_book_chapters` 排版、自动清理段落行尾注记，并强制剔除已停用与 `secret=true` 秘密对象）。导入产生新的身份及本地真实审计，原历史/原时间戳在原件中保留；完整保真灾难恢复使用PostgreSQL备份。

旧文件范围保持原工作路径。数据库权威范围仅通过显式工作副本绑定启用，不自动接管现有书库：

```bash
.venv/bin/ncc-data workspace import '<私有工作副本目录>' --scope '<范围ID>'
.venv/bin/ncc-data workspace bind '<私有工作副本目录>' --scope '<范围ID>'
python3 scripts/cli/ncc_state.py status '<私有工作副本目录>'
.venv/bin/ncc-data workspace pull '<私有工作副本目录>' --scope '<范围ID>'
```

在`config/.env`中填写`NCC_API_URL`与`NCC_API_TOKEN`。范围凭据在“成员与设置”生成，至少需要`read/edit/adopt/export/secret`完成完整CLI工作副本往返；令牌只显示一次，不存入工作副本标记。导入前先备份并审核差异；import与bind是两个明确动作。工作副本在保留未知原件的同时，已完成核心创作资产的确定性双向幂等映射（`snapshot -> commit` 无修改时零冗余修订）：章节顺序/标题/正文/关键章/追读钩及章节状态（`planned / draft / review / done`）、章节场景卡与章纲（`02-大纲/场景卡/` 与 `02-大纲/章纲/` ↔ `beat_outline`）、全书总纲（`02-大纲/总纲.md`）、立书档案（书魂四问/弧光/主副契约/毒点/写作模式 ↔ `book.json`，文风基准 ↔ `03-文风/文风基准.md`）、作品设定与人物卡（`01-设定/人物卡/`、`01-设定/类目/*` 及核心设定文档 ↔ `/materials` 实体，保留 `*-采访.md` 原件独立）、以及承诺伏笔（`06-台账/承诺台账.json` ↔ 工作台伏笔实体，里层真义入私有字段 `secret_note`）。其余专用台账以受管原件兼容保留。

绑定后，CLI先从数据库一致版本构造隔离工作区，再经应用服务回写；命令运行时发生作者编辑或数据库变化会拒绝覆盖。一次命令最多200文件和18MiB传输预算。直接调用程序内部文件写函数不能绕过数据库标记。外部编辑器的本地变化要先对账；冲突原稿保留，不静默切回文件双主模式。新型数据库语义不能无损降级时，只回退应用或保留只读库。

文件模式的AI成果可运行`ncc_state.py quality plan/ingest/status/accept`。评分报告绑定正文SHA及量表hash，脚本重算总分；AI章节定稿时检查评分新鲜度。作者手写与旧资料不会被追溯标成AI。

## 权限与维护

PostgreSQL只读MCP和不依赖API启动的直接CLI读写，见[数据接入指南](data-access.md)。它们共用后台Service，不能绕过当前权限、修订、审计或变更采用检查。

系统管理员可在「成员与设置」（`/admin/settings`）查看与管理全局账号（建立新账号、启用/停用账号、授予或撤销系统管理员、重置临时密码并自动吊销旧会话，内置防自禁与保留至少一名活跃管理员保护），但系统管理身份不会自动获得其他作者的私有作品权限。范围所有者通过活跃账号下拉目录（无需手工复制 UUID）添加、调整或移除协作成员，签发或吊销范围 CLI 令牌，执行空间改名、归档/恢复显示（默认顶栏隐藏已归档空间），以及彻底删除尚无正式修订（`version == 0`）且无子分支的空空间。`read/edit/adopt/assess/export/secret/admin/operate`分别控制范围行为，范围令牌再收窄权限。秘密正文、属性、变更、任务、评分和导出附件在读取时重新校验；安全栅格底图（PNG/JPEG/WebP/GIF）支持受控内联预览，SVG/HTML 等高风险格式强制作为附件下载；撤权不能仅隐藏导航。

数据库账号和权限沿用已经确定的配置。不要把数据库凭据交给浏览器或模型。当前保护由应用授权、事务约束和数据库历史不可变触发器共同执行，没有宣称已实现数据库RLS隔离。

备份恢复共用当前选定连接及其TLS、证书、超时等参数，不再维护额外维护连接。工具不在PATH时，在`config/.env`填写`NCC_PG_BIN`。

```bash
.venv/bin/ncc-data backup '<仓外私有备份文件.dump>'
# 仅当既定目标已为空库时恢复；不为每次操作创建新库
.venv/bin/ncc-data restore '<仓外私有备份文件.dump>' --confirm-database '<既定正式库名>'
```

备份为完整custom格式转储，拒绝覆盖文件，权限为600并给出摘要。恢复只允许明确确认的空库，不隐式清理正式数据。恢复后撤销会话与托管，暂停未完成任务；核对对象、历史、事实、附件、正文、权限与摘要后再恢复服务。恢复演练仅在`ncc-dev`进行，使用合成数据备份重放，需显式确认，失败时保留转储。定时备份、异地副本、WAL归档由部署环境配置。

## 验证入口

```bash
python3 -m unittest discover -s scripts/tests -t scripts -p 'test_*.py'
python3 scripts/dev/checkers/check_plugin.py -v
.venv/bin/pytest tests/unit tests/backend -q
npm --prefix apps/management-web run build
.venv/bin/python scripts/dev/run_browser_suite.py --include-cli-bridge --output '<仓外验收截图目录>'
.venv/bin/python tests/backend/operations/run_recovery.py --confirm-reset-test 'ncc-dev'
```

后台集成、浏览器、CLI往返和恢复演练共用`tests/support/`环境，串行使用`ncc-dev`；已占用时停止，不创建更多库。普通定向与集成测试仅操作当次新建的合成范围与合成账号，不执行整库TRUNCATE，保护`ncc-dev`中已有的日常作品、身份与历史记录；恢复演练与显式重置在检测到非空共用库或未知表、其他业务schema时拒绝清库。连接尚未配置时，数据库用例明确跳过，不视为联调通过。

浏览器验收自动启动并关闭本机测试服务，默认`http://127.0.0.1:8788`，不复用已有端口服务。合成账号由公共环境在-test库准备。`ncc-data --test serve/worker/migrate/doctor`选择同一测试库和测试服务地址；`--test request/workspace`也选择测试地址，并在发送凭据前核对服务profile。普通正式与本地服务默认8761；测试地址可在`config/.env`的`NCC_TEST_PUBLIC_ORIGIN`填写。高级自动化可显式使用`--config '<config/.env>'`，普通操作无需此参数。

代码目录、复用边界和测试归属见[代码归属规范](../engineering/code-layout.md)。
