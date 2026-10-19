# 工程角色行为验证

范围：四工程职责的开发调度、方案审查和报告拒绝路径。输入为仓内三个合成案例，未使用书稿或真实私有配置，未访问数据库。执行由实际独立会话完成，脚本仅生成包、登记和检查，不调用模型。七个会话独立启动，不共享其他角色报告。

| 输入 | 实际执行 | 预期与观察 |
|---|---|---|
| configuration.md | /root/configuration_architect、/root/configuration_dba | 只选架构师/DBA；两者均changes_required。具体指出按cwd各自读配置、未知键被丢弃、源/目标并发替换、静默双源、随机数据库和跨项目账号，并给单一来源、保留原值、版本/身份校验、唯一-test及缺资料阻断等修法。 |
| feature.md | /root/feature_product_manager、/root/feature_product_designer、/root/feature_architect、/root/feature_dba | 四职责均changes_required。经理退回资源维护前置和无价值扩域；设计师指出卷章定位、人工新稿/旧基线、失败恢复状态；架构师指出规则复制、入口越权、读写链分裂；DBA指出覆盖写无历史、重复事实及多库越界。各报告含定位、证据和具体修法。 |
| documentation.md | /root/documentation_routing | 实际运行plan和check --delivery，effects=documentation；四职责均not_applicable，无额外角色调用，退出0。只代表该文案案例的工程职责契约通过。 |

六个错误方案报告经实际record登记为failed，configuration/feature的check --delivery均退出1并列出必要职责未通过。这是预期拒绝，不是产品测试失败。原始派单、实际报告与拒绝日志均在behavior/。

六报告的产品运行验证全部诚实标pending；报告有设计修法不代表它们实施了配置迁移或UI改造。当前任务另有三份current_session设计自查，不称独立专家，独立代码复核见review.md。

私有配置/数据库未进入包；角色没有执行SQL或修改产品。字段、输入摘要及报告新鲜度由登记器检查，问题语义由协调者逐份阅读和独立评审复核，不以关键词命中率或字段存在证明能力。

确定性反例覆盖超预算、私有/越界输入、错误角色/摘要、缺交付字段、major伪装ready、缺报告、篡改报告/状态、改来源/协议、漏计划字段、历史兼容及旧任务采用契约后反删除字段。新任务不能借历史兼容免验收。

限制：这是三类合成开发场景的单次真实行为验证；未证明所有未来任务或模型稳定性。五宿主静态挂载和实际新会话是不同证据，新会话仍待验。真实PostgreSQL读写、浏览器作者任务和C–E功能未执行。
