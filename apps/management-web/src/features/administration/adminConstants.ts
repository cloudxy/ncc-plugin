import type { Json } from "../../shared/api";

export const ALL_ACTIONS = [
  "read",
  "edit",
  "adopt",
  "assess",
  "export",
  "secret",
  "admin",
  "operate",
] as const;

export const ACTION_META: Record<string, { label: string; desc: string }> = {
  read: { label: "只读浏览", desc: "查看公开正文、设定、大纲与地图" },
  edit: { label: "编辑起草", desc: "编写草稿、发起 AI 协同与提交变更" },
  adopt: { label: "正式采用", desc: "将修订或候选稿正式落库为新版本" },
  assess: { label: "质量审评", desc: "发起质量评分并查看审评依据" },
  export: { label: "导出下载", desc: "导出作品成稿与数据包文件" },
  secret: { label: "作者秘密", desc: "读写隐藏设定、暗线与作者秘密" },
  admin: { label: "空间管理", desc: "管理本空间成员、凭据与操作审计" },
  operate: { label: "运行监控", desc: "查看队列指标与后台 Worker 心跳" },
};

export const AUDIT_ACTION_LABELS: Record<string, string> = {
  adopt: "正式采用变更",
  "change.adopt": "正式采用变更",
  "change.create": "提交变更集",
  "scope.create": "创建作品空间",
  "scope.rename": "修改空间名称",
  "scope.archive": "归档 / 恢复空间",
  "scope.delete": "彻底删除空空间",
  "user.create": "新建系统账号",
  "user.update": "变更系统账号",
  "auth.credentials_change": "修改账号与密码",
  "member.set": "设置协作成员权限",
  "member.remove": "移出协作成员",
  "token.create": "签发范围凭据",
  "token.revoke": "吊销范围凭据",
  "delegation.create": "登记自动定稿授权",
  "delegation.revoke": "撤销自动定稿授权",
  "studio.founding": "保存立书档案",
  "studio.market_config": "保存赛道母本配置",
  "studio.map_config": "保存地图默认底图",
  "attachment.download": "下载导出附件",
  "export.create": "创建导出任务",
  "import.apply": "执行批量导入",
  "workspace.commit": "CLI 工作副本回写",
};

export function actionLabel(action: string): string {
  return ACTION_META[action]?.label || action;
}

export function summarizeAuditDetail(
  action: string,
  detail: Json | undefined,
): string {
  if (!detail || typeof detail !== "object") return "已记录受保护回执";
  const parts: string[] = [];
  if (typeof detail.title === "string" && detail.title) {
    parts.push(`变更「${detail.title}」`);
  }
  if (typeof detail.name === "string" && detail.name) {
    parts.push(`名称「${detail.name}」`);
  }
  if (typeof detail.username === "string" && detail.username) {
    parts.push(`账号：${detail.username}`);
  }
  if (typeof detail.target_username === "string" && detail.target_username) {
    parts.push(`目标账号：${detail.target_username}`);
  }
  if (
    typeof detail.old_username === "string" &&
    typeof detail.new_username === "string"
  ) {
    parts.push(`${detail.old_username} → ${detail.new_username}`);
  }
  if (Array.isArray(detail.actions) && detail.actions.length > 0) {
    parts.push(
      `权限：${detail.actions.map((a: string) => actionLabel(String(a))).join("、")}`,
    );
  }
  if (typeof detail.hours === "number") {
    parts.push(`有效期 ${detail.hours} 小时`);
  }
  if (typeof detail.archived === "boolean") {
    parts.push(detail.archived ? "状态：已归档" : "状态：已恢复使用");
  }
  if (Array.isArray(detail.fields) && detail.fields.length > 0) {
    parts.push(`更新项：${detail.fields.join("、")}`);
  }
  if (typeof detail.playbook_id === "string" && detail.playbook_id) {
    parts.push(`母本：${detail.playbook_id}`);
  }
  if (typeof detail.custom_track === "string" && detail.custom_track) {
    parts.push(`赛道：${detail.custom_track}`);
  }
  if (typeof detail.basemap_attachment_id === "string") {
    parts.push(
      detail.basemap_attachment_id
        ? `底图附件：${detail.basemap_attachment_id.slice(0, 8)}…`
        : "已清除默认底图",
    );
  }
  if (typeof detail.count === "number") {
    parts.push(`共 ${detail.count} 项操作`);
  }
  if (parts.length > 0) return parts.join(" · ");
  const label = AUDIT_ACTION_LABELS[action];
  return label ? `已完成${label}` : "查看下方详情";
}
