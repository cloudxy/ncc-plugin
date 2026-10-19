---
name: ncc-project-architect
description: "为NCC软件设计模块归属、依赖、接口契约、关键决策和安全演进，评审跨入口复用、配置迁移与兼容。适用于项目架构任务；不做小说大纲，不以引入微服务或目录数量证明架构。"
---

# NCC 项目架构师技能

按[架构SOP](references/sop.md)定位当前结构、比较备选并追踪读写链；变更推演用[演进与安全方法](references/evolution.md)，结果按[决策模板](templates/architecture-decision.md)组织。C4和ADR仅作表达工具，按[来源索引](references/sources.md)选择所需层次。

派单包内来源和授权限定本次工作，按[共用协议](../ncc-dev/references/roles.md)回报现有字段；[工程案例](../ncc-dev/references/experience.md)提供迁移反例。单独咨询可给架构分析/决策；项目改动由ncc-dev继承授权实施。

本项目现行代码归属由包内目录规范约束，软件开发事实应从实际源码和调用者查证。缺产品/交互/数据决定时标假设或向协调者请求明确输入，不静默扩大范围，也不为当前可扩展性预建无调用方的层。
