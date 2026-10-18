# 拆书功能实现与作者测试交接

关联[实施任务](../../tasks/2026-10-18-deconstruction-upgrade.md)与[统一方案](../../designs/deconstruction/upgrade.md)。作者本轮授权完成 P1–P6 的代码功能模块；继承“测试单独进行”的安排。代码已整合进本地工作树，功能回归、规则行为、独立评审、五端新会话与规则验收均未执行，不引用架构升级的180项通过作为本次证据。

## 实现落点

| 阶段 | 具体实现 |
|---|---|
| P1 | workflow/contracts/deconstruction 的9份有限结构契约；运行验证与字段表共用机器源；build_docs 生成字段表；技能拆为五份参考并登记保守读取预算 |
| P2 | index 模块处理多卷、特殊序章、标题回声、同号分章、原号跳号、短章和人工边界；结构阻塞不可 force 绕过；原文/规则变化生成影响、备份与显式重建 |
| P3 | 文件、条目、场次三级验收；包/正文/上下文/词表与契约绑定；专名别名、实体引用、状态事件、冲突、弱推断分别处理；每库写锁，原子收据为提交点，原始章备份、台账与进度可恢复且幂等 |
| P4 | structure/technique/full/transfer 目标；默认最多27个去重关键章；非连续前情缺失明确阻塞或章内独立；场次另选，基础与场次分别完成；人读稿和对标参照只留拆书库 |
| P5 | 按层覆盖、字段可用性、全书/连续范围/稀疏样本统计；缺测不当零；范围报告不覆盖全书；L3 白名单只提供已验结论投影，双独立证据、适用/代价/失效校验，源集合变化使旧包失效 |
| P6 | CLI、技能、角色、registry 分片与生成物接线；保留旧入口和 legacy 读取；公开合成样例及21个验收测试方法，另调整旧兼容用例以表达方案明确的行为变化。实际回归验收交作者执行 |

本轮47个产品路径纳入任务指纹；只从隔离副本带回相对基线的增量，合入前逐文件核对现场未变。未读私有书库，未自动迁移旧库，未暂存、提交、推送或同步其他机器。

## 本轮实际执行的静态核对

- 17个 Python 文件经过 ast.parse；13个 JSON 文件经过解析（含9份契约）；16份 Markdown 的相对链接及47个产品文件的末尾换行/行尾空白核对通过。没有导入并运行测试模块或调用功能处理器。
- 按序运行 build_registry.py、build_docs.py 生成兼容视图、字段表、命令/角色及相关规则生成段。最终 build_docs.py 输出“无改动”。生成过程不等于功能测试通过。
- 经理拆书读取集合保守上限15542个非空白字符，deconstructor 为7794，分别低于35000/20000；实际按层读取边界仍待行为验证。
- 原 CLI 冻结快照未重写。兼容测试仅排除本方案明确新增的三个 decon 子命令及已有子命令的新增参数，其他解析契约继续对照原快照；是否通过须作者运行。

## 作者测试入口与验收重点（均待执行）

先执行拆书定向用例，再按本次核心数据契约变更执行最终全量及一致性检查：

```bash
python3 -m unittest discover -s scripts/tests -t scripts -p 'test_deconstruction.py'
python3 -m unittest discover -s scripts/tests -t scripts -p 'test_*.py'
python3 scripts/dev/build_registry.py --check
python3 scripts/dev/check_plugin.py -v
python3 scripts/dev/build_docs.py --check
```

合成用例覆盖索引异常分级、稀疏上下文、文件错配、事实隔离、幂等、别名/状态冲突、基础与场次分离、原子提交前后中断、前情变更失效、重建移号、统计范围、L3 不依赖原文与写锁。测试源码与输入见 scripts/tests/test_deconstruction.py 及 fixtures/deconstruction；21是已编写的方法数，不是通过数。

规则行为需在独立合成库分别走“只看结构、稀疏技法抽样、明确全章、已有报告转化”四条路径，检查实际读取范围、缺来源时停止/降级、完成含义和作者书零写入。独立评审核对方案意图、实现、反例、兼容和回滚。五端各在新会话检查发现、参数传递、实际 plugin_root/repo_root、版本、代表调用和任务恢复；grok 另查重复发现/优先级。均保留 pending/unverified；规则回归完成后再呈作者确认，不触发无关审稿判据评测。

最小操作链（路径与数据由作者填写，以下未执行）：

```bash
python3 scripts/ncc_state.py decon index <拆书库>
python3 scripts/ncc_state.py decon plan <拆书库> --goal technique --screenplay none
python3 scripts/ncc_state.py decon packet <拆书库> 1 --framework <总纲5.0文件>
python3 scripts/ncc_state.py decon ingest <拆书库> <章JSON>
python3 scripts/ncc_state.py decon coverage <拆书库> --layer L2
python3 scripts/ncc_state.py decon ingest <拆书库> --recover
```

后续抽样章缺紧邻前情时须提供有来源的上下文，或明确 --independent；不能批量把未选章标跳过。场次用 --screenplay 选章；L3 用 packet/ingest --layer L3，只接受包内白名单证据。新层必须通过 ingest，原有旧库的手动 done 只算 legacy。

## 限制、返回与回滚

本地实现完成，尚无本次功能的通过证据；不会把 D4、P6 验收或实际加载标为完成。测试失败按复现回到对应 P 阶段修复；产品变化后重新冻结指纹、运行受影响验证，不继承旧候选的 passed。旧接口、legacy 读取和原始数据保留，但新索引的跳号/短章警告、不可 force 绕过 blocker、范围报告隔离属于明确行为变化。

回滚只撤销本任务精确产品增量，按方案的依赖逆序处理，保留此前架构与文档改动；不 reset 工作树。私有库若已试用新格式，先保存原始章/验收收据/索引备份，不用旧工具盲写新进度。发布、提交和消费端同步另需对应授权。
