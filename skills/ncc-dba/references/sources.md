# PostgreSQL 专业来源

2026-10-19核对官方17版手册；实际服务端版本未确认时不宣称与17完全一致，执行前以连接身份和匹配版本复核。SOP/模板由NCC自写，参考不产生扩展、数据库、账号或运维依赖。

| 原页 | 核对用途 |
|---|---|
| [约束](https://www.postgresql.org/docs/17/ddl-constraints.html) | 行内约束、唯一/引用与跨行规则的适用边界。 |
| [事务隔离](https://www.postgresql.org/docs/17/transaction-iso.html) | 查询快照、并发异常与完整事务重试，区分应用版本冲突。 |
| [显式锁](https://www.postgresql.org/docs/17/explicit-locking.html) | 行/表锁、死锁及迁移影响，避免无根据的无锁承诺。 |
| [事务只读模式](https://www.postgresql.org/docs/17/sql-set-transaction.html) | MCP只读事务的作用与边界，配合最小权限/范围过滤。 |
| [EXPLAIN](https://www.postgresql.org/docs/17/using-explain.html) | 估计与执行、cost与真实时间、loops和数据规模。 |
| [pg_dump](https://www.postgresql.org/docs/17/app-pgdump.html)、[pg_restore](https://www.postgresql.org/docs/17/app-pgrestore.html) | 单库备份覆盖、格式、恢复依赖和实际执行边界。 |

具体配置来源、双库、权限与历史契约以本项目当前代码/授权为准；任何官方命令例子都不授予在正式库操作的权限。集中出处见[致谢](../../../ACKNOWLEDGMENTS.md)。
