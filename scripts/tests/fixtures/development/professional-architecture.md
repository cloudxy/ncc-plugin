# 合成架构任务：引用面板与候选回写

以下是演练接口清单，并非声称已读取真实实现：
- shared/config负责既定config装配；现有host注册文件位于宿主规定位置。
- application/query(scope, filters, cursor)执行范围/隐藏信息过滤。
- application/revise(scope, entity, expected_version, request_id, patch)产生修订和审计。
- projection消费已提交事件并可重试。
新面板需要检索、提交纠错候选和查看采用结果；API、CLI、只读MCP都要读取，写入仍限授权非MCP服务。部署容量不支持新服务，既定PostgreSQL和唯一-test不重选。

团队比较三案：A在现有适配层复用服务并补业务读模型；B新开微服务复制配置、权限及章状态；C前端直读写库。有人以未来扩展为由强推B，兼容失败时直接读旧配置并把缺字段视为旧版通过；还提议把所有宿主注册文件迁进config。

请给可审核决策：现状/假设、责任与依赖、至少一条读写契约、备选及后果、迁移/兼容正反例、分批实施和回退。只做设计，当前没有真实源码或运行环境证据，不要把清单当完整源码审计。
