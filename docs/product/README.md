# 产品层 · NCC 创作后台

> NCC 创作后台的产品层长期基线。小说创作方法论与流程文档仍在 `docs/guides/` 与 `docs/designs/`，此处不重复抄录。

## 文件与负责人

| 文件 | 负责人（写） | 现状 |
|---|---|---|
| `strategy.md` | pm | 已上线基线（2026-11-25 刷新） |
| `feature-map.md` | pm | 已上线基线（六大创作空间 + 分组折叠高级管理） |
| `design-system.md` | designer | 已上线基线（WCAG 对比度、最小字号与三档响应式已验收） |
| `CHANGELOG.md` | 经理 | 记录历次产品层基线升级 |

## 约定

- 只记录经实现与浏览器/集成验收确认的长期产品事实；工程架构细节见 [后台设计](../designs/storage/management-console.md) 与 [工作台重构设计](../designs/storage/novel-studio-overhaul.md)，运维与使用说明见 [数据后台指南](../guides/data-console.md)。
- 数据库只使用既定的 `ncc-pro` 与 `ncc-dev`。私有书稿、`novels/` 与本地忽略目录内容绝不进入产品层。
