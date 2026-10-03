# 素材库治理接口

所有命令使用 `python3 <PLUGIN_ROOT>/scripts/ncc_prepare.py <命令> <准备目录>`。脚本负责确定性检查与记录，执行者负责阅读、实际编写和语义判断。prepare.json 的 library 保存规范、计划与批次状态，`.ncc-prepare/library/` 保存任务包、内容、报告和备份。可以接续已有准备工作区，无需书项目。

全库治理的准备目录放在来源根之外，避免新写的草稿、规范和清单被当成下一批原始资料。来源范围和最终成果位置分别登记。

## 本库规范

先 init、source、scan。按实际内容制定 JSON 规范，再登记：

```bash
python3 <PLUGIN_ROOT>/scripts/ncc_prepare.py library-profile <准备目录> --file <规范.json> --reason "沿用已有分类并按作者目标整理"
python3 <PLUGIN_ROOT>/scripts/ncc_prepare.py library-audit <准备目录>
```

下面只展示接口，目录、类型和字段由本库决定：

```json
{
  "name": "生活参考与虚构城市素材",
  "organization": "现实参考和虚构城市各有主归属；定义维护一次；导航引用条目；新增内容按类型入库。",
  "types": {
    "reference": {"match": ["参考/*.md"], "required": ["编号", "来源", "用途"], "unique": ["编号"]},
    "setting": {"match": ["设定/*.md"], "required": ["编号", "范围", "条件"], "unique": ["编号"], "namespace": ["范围"]},
    "index": {"match": ["导航.md"], "required": []}
  },
  "indexes": ["导航.md"],
  "links": true
}
```

类型 match 使用路径 glob，文件需恰好匹配一种类型。required 声明必要字段；enum 为字段到允许值数组的映射；unique 在“来源根＋类型＋namespace 字段值”内检查。字段支持扁平 frontmatter、独立 `字段：值` 行或两列属性表，复杂 YAML/嵌套表先转换成可解析表达并保留关联。

indexes 声明导航文件，检查能否从这些入口到达条目；links 支持 Markdown 路径、Obsidian 链接、标题和块引用。跨登记来源可用 `[[R-0002::路径/条目]]`。图片等未读文件仍可作为链接目标，内容覆盖单独报告。terms 声明术语候选映射，结果只作待查警告。

constraints 支持跨文件标量对账，例如 `{"name":"总量对账","left":{"path":"规则.md","field":"总量"},"op":"eq","right":{"path":"条目.md","field":"份量"},"factor":4,"offset":0,"tolerance":0}`。支持 eq/le/ge，执行者先确认量纲、参照与公式。复杂矩阵、区间、单位换算和因果关系由语义复核完成，不凭数字相同认定自洽。

## 全库计划

```bash
python3 <PLUGIN_ROOT>/scripts/ncc_prepare.py library-plan <准备目录> --file <计划.json> --reason "作者授权按已定规范治理全库"
```

计划包含 goal、target（绝对路径）、mode（copy/in-place）、entries、batches、queries。entries 覆盖 scan 的全部当前来源，每项恰好一次。来源编号从 index.json 或 search/show 获取。每项有 source、disposition、reason、outputs，处置取值在注册表 preparation.library.dispositions。保留、转换、合并、拆分指向实际文件；排除说明依据；延期明确待办并阻塞全库通过。未读取格式先转换并登记。

每批包含 name、operation、sources，可选 new_outputs（新增导航或必要内容）。operation 使用注册表五类库工程任务。每个来源恰好属于一批，同一输出由一批维护；合并到同一文件的来源安排在同批。按规则、内容、索引依赖执行。queries 每项有 words（检索词数组）、expected（预期文件数组），至少一个代表性取用用例。

```json
{
  "goal": "全库整理为可取用的城市素材",
  "target": "/tmp/示例/整理库",
  "mode": "copy",
  "entries": [{"source":"S-实际编号","disposition":"transformed","reason":"整合主题并保留出处","outputs":["参考/港口.md"]}],
  "batches": [{"name":"港口与导航","operation":"library-refactor","sources":["S-实际编号"],"new_outputs":["导航.md"]}],
  "queries": [{"words":["港口","税收"],"expected":["参考/港口.md"]}]
}
```

copy 交付到与来源分开的新路径；in-place 对应唯一登记目录根，多库分别规划。来源新增、变化、缺失或规范版本变化会使旧计划失效，重新诊断并规划，旧成果仍保留供复用。默认扫描忽略隐藏文件，向作者说明覆盖边界。

## 批次与任务包

```bash
python3 <PLUGIN_ROOT>/scripts/ncc_prepare.py library-packet <准备目录> --plan L-0001 --batch B-0001
python3 <PLUGIN_ROOT>/scripts/ncc_prepare.py library-batch <准备目录> --plan L-0001 --batch B-0001 --file <交付清单.json> --report <逐来源检查.md> --by "curator" --execution current
python3 <PLUGIN_ROOT>/scripts/ncc_prepare.py status <准备目录>
```

任务包给出目标、规范、操作方法、来源路径和版本、逐来源处置、输出与角色协议，执行者按定位读取全文再写草稿。脚本不调用模型或派代理。execution 为 current/native/fallback，属于执行者声明；状态保留协议哈希、报告及实际内容版本。

交付清单形如 `{"files":{"参考/港口.md":"/tmp/港口完整稿.md","导航.md":"/tmp/导航完整稿.md"}}`，恰好覆盖本批输出。报告逐来源说明独有信息怎样保留、拆合与改编依据、规则及关联检查和剩余疑点，排除项也要回传。登记后内容保存到本计划 staging，更新批次会撤销旧验收。

## 全库验收与交付

```bash
python3 <PLUGIN_ROOT>/scripts/ncc_prepare.py library-find <准备目录> --plan L-0001 港口 税收
python3 <PLUGIN_ROOT>/scripts/ncc_prepare.py library-audit <准备目录> --target <计划的staging目录>
python3 <PLUGIN_ROOT>/scripts/ncc_prepare.py library-review <准备目录> --plan L-0001 --file <全库语义检查.md> --result pass --by "实际复核者"
python3 <PLUGIN_ROOT>/scripts/ncc_prepare.py library-check <准备目录> --plan L-0001
python3 <PLUGIN_ROOT>/scripts/ncc_prepare.py library-apply <准备目录> --plan L-0001 --authorization "作者已授权向该具体目标交付验收结果"
```

模型报告复核保真、权威、范围、完整性、结构、未定问题及真实取用结果。没完成全部批次、有延期、文件/来源/规范/报告变化、结构错误或用例未命中均不能通过。机械通过不证明语义正确，警告在报告中解释。

新库目标须尚不存在。原地应用备份原文，更新内容并移除已归档旧位置；沿用具体授权并遵守宿主权限。中断后通过 `library-restore <准备目录> --plan L-0001 --authorization "恢复中断改动"` 恢复，检测到外部修改停止覆盖。交付后 check/find 对实际目标工作，重复 apply 不重复写入。

完成后交付实际库、规范、导航、覆盖与处置记录、报告和待办。新内容或规范变化开启新计划，普通六类准备仍可单独运行。
