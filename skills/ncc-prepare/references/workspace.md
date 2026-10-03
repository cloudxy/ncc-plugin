# 准备工作区与命令

唯一入口脚本为 `scripts/ncc_prepare.py`，以下命令的 `<准备目录>` 是独立工作区，不要求 book.json。使用 `--help` 查看完整参数。任务代码、状态与格式支持只在 `workflow/registry.json` 的 preparation 中定义。

## 保存位置

```text
准备目录/
  prepare.json                  目标、范围、来源根、成果元数据、采用决定、问题与检查记录
  成果/P-NNNN.md                整理、完善或创建的实际内容
  .ncc-prepare/
    index.json                  原资料的生成索引，含 SHA、标题、行数和读取状态
    events.jsonl                操作历史，只追加
    history/                    更新成果前的内容版本
    reviews/                    语义检查报告
    exports/                    按范围生成的交接文档
```

prepare.json 由脚本写；成果 Markdown 是内容源，允许作者编辑，编辑后通过 item --id 重新登记并复核；导出和索引是生成视图，不回写原资料。索引没有复制原文，来源移动或修改会提示复核。

## 建立与读取

```bash
python3 <PLUGIN_ROOT>/scripts/ncc_prepare.py init <准备目录> --title "港城创作准备" --purpose "建立可复用的港口资料与城市设定" --scope "港口体系"
python3 <PLUGIN_ROOT>/scripts/ncc_prepare.py source <准备目录> <资料目录或单文件> --kind material
python3 <PLUGIN_ROOT>/scripts/ncc_prepare.py scan <准备目录>
python3 <PLUGIN_ROOT>/scripts/ncc_prepare.py search <准备目录> 港口 税收
python3 <PLUGIN_ROOT>/scripts/ncc_prepare.py show <准备目录> <来源编号> --start 12 --end 40
python3 <PLUGIN_ROOT>/scripts/ncc_prepare.py status <准备目录>
```

init 可用重复的 `--task` 选本轮任务；不指定时六类都可用。没有资料时直接创建成果，source 与 scan 可跳过。来源角色只是初步分类，不替代条目级采用。

scan 支持 UTF-8 Markdown/文本。其他格式、编码错误、超大文件、读取失败和消失文件在覆盖报告里明示。需要时用宿主可用的转换工具产生文本再登记转换稿，并在成果来源保留原件定位。不要声称未转换的文件已读。

目录符号链接只记录，不递归跟随；需要读目标时把真实目录登记为另一来源根。扫描跳过隐藏文件、隐藏目录和自身状态/成果目录，不是全盘搜集。完全重复组只报告，不删除。来源变化后先重新扫描，再复核受影响的成果。

## 登记实际成果

先把实际内容写成 UTF-8 文档，再用 item 接收；它复制到准备目录，保留输入文件。任务代码：

| 工作 | --task |
|---|---|
| 资料整理 | material-organize |
| 资料完善 | material-improve |
| 资料创建 | material-create |
| 设定整理 | setting-organize |
| 设定完善 | setting-improve |
| 设定创建 | setting-create |

```bash
python3 <PLUGIN_ROOT>/scripts/ncc_prepare.py item <准备目录> --file <成果稿.md> --title "港口运作资料" --task material-organize --nature fact --basis "整合已登记资料中关于港口的内容" --ref <来源编号>:12-40
python3 <PLUGIN_ROOT>/scripts/ncc_prepare.py item <准备目录> --file <新设定.md> --title "潮汐城港务会" --task setting-create --nature fiction --basis "作者要求：商会与市民共同治理，海潮影响运输" --depends P-0001
```

- `--nature fact` 是有来源的现实资料，必须给 `--ref` 或 `--citation`。外部出处用重复的 `--citation "标题｜作者/机构｜URL或书目｜定位｜查询日期"` 登记；脚本不联网验证，模型须实际查证。
- `fiction` 明确虚构；`inference` 为未核推演，不可直接采用。混合文档按不同性质拆开引用。
- 本地引用用 search 返回的 S 编号与完整行段，登记时校验当前 SHA 和行数；可重复 `--ref`。
- `--depends` 关联其他成果，后续检查会连带检查这些成果，不要求依赖与当前范围相同。
- `--scope` 覆盖默认范围；`*` 表示所有范围都依赖的公共成果。单个工作区面向一个采用语境，多作品复用同一素材时分别建立准备工作区并登记同一来源，避免把 A 书的决定当成 B 书的决定。
- 更新使用同样的完整参数加 `--id P-0001`；旧内容留档，来源和依赖需完整重给，状态回到 candidate。不能只改文本后沿用旧检查。

## 采用与问题处理

```bash
python3 <PLUGIN_ROOT>/scripts/ncc_prepare.py decide <准备目录> P-0001 --state accepted --reason "作者要求创建这份专题资料；已核实来源，作为本轮资料成果收下"
python3 <PLUGIN_ROOT>/scripts/ncc_prepare.py issue <准备目录> --kind gap --text "港务会缺税收分配规则" --evidence "P-0002 的议事规则未说明资金来源" --next "补充收入来源、分配及监督关系" --item P-0002 --blocking
python3 <PLUGIN_ROOT>/scripts/ncc_prepare.py resolve <准备目录> Q-0001 --state resolved --reason "已补全并检查税收流向，见 P-0002"
```

decide 的 accepted 表示在指定范围里收下当前成果；资料被收下不等于它已成为某书设定。候选可以 shelved 或 rejected，说明理由。设定采用依据应引用作者授权或已有裁定；命令不会替作者做创作选择。

缺项、冲突、待研究或待创建分别用 gap、conflict、research、creation。未形成成果时可以不挂 item，完成后 resolve 用 `--item` 关联新成果。修订成果先 item、再 decide，然后 resolve，问题关闭会绑定修订后的内容与依据。

非当前必需的问题可 deferred，须 `--until "进入远海场景时"` 说明触发点。阻塞项延期仍阻塞该范围；不同范围的问题用 `--scope` 明确归属。解决依据关联的成果再改动，问题需要重新复核。

## 检查与交接

模型先写有实质内容的语义检查报告，检查范围与尚未读到的部分须说清楚。登记和交接：

```bash
python3 <PLUGIN_ROOT>/scripts/ncc_prepare.py review <准备目录> --scope "港口体系" --file <检查报告.md> --result pass --by "执行本轮语义核对的角色"
python3 <PLUGIN_ROOT>/scripts/ncc_prepare.py check <准备目录> --scope "港口体系"
python3 <PLUGIN_ROOT>/scripts/ncc_prepare.py export <准备目录> --scope "港口体系"
```

没有成果、未定候选、未解决阻塞、失效来源、缺少有效检查报告都会拒绝交接。无法通过语义检查时登记 needs_work，继续处理具体问题。检查和交接按范围计算，不证明未纳入范围的资料已完成。

交接文档只供作者及规划、设定工作使用，保留来源、创作依据、采用理由、依赖与待办；不是正文，也不是写手包。进入 NCC 书项目时由经理按现有设定/素材/词典/台账分工接入，不覆盖外部工程的追踪状态。
