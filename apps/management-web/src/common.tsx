import { Alert, Button, Empty, Result, Space, Tag, Typography } from "antd";
import type { ReactNode } from "react";
import { ApiError } from "./api";
export function ErrorPanel({
  error,
  retry,
}: {
  error: unknown;
  retry?: () => void;
}) {
  if (!error) return null;
  const e = error as ApiError;
  return (
    <Alert
      type="error"
      showIcon
      title={e.message || "加载失败"}
      description={
        <Space orientation="vertical">
          <span>{e.problem?.code && `错误代码：${e.problem.code}`}</span>
          {e.problem?.errors && (
            <pre className="json-small">
              {JSON.stringify(e.problem.errors, null, 2)}
            </pre>
          )}
          {retry && <Button onClick={retry}>重试</Button>}
        </Space>
      }
    />
  );
}
export function PageTitle({
  title,
  note,
  actions,
}: {
  title: string;
  note?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="page-title">
      <div>
        <Typography.Title level={3}>{title}</Typography.Title>
        {note && <Typography.Text type="secondary">{note}</Typography.Text>}
      </div>
      {actions}
    </div>
  );
}
const statuses: Record<string, [string, string]> = {
  queued: ["default", "排队中"],
  running: ["processing", "处理中"],
  qualified: ["success", "达标待采用"],
  waiting: ["warning", "需要你决定"],
  paused: ["default", "已暂停"],
  cancelled: ["default", "已取消"],
  failed: ["error", "执行失败"],
  succeeded: ["success", "已完成"],
  applied: ["success", "已采用"],
  draft: ["default", "草稿"],
  validated: ["processing", "预检通过"],
  approved: ["success", "已批准"],
};
export function Status({ value }: { value: string }) {
  const [color, label] = statuses[value] || ["default", value];
  return <Tag color={color}>{label}</Tag>;
}
export function NoData({
  text = "这里还没有内容",
  action,
}: {
  text?: string;
  action?: ReactNode;
}) {
  return <Empty description={text}>{action}</Empty>;
}
export function Permission({
  children,
  allowed,
}: {
  children: ReactNode;
  allowed: boolean;
}) {
  return allowed ? (
    <>{children}</>
  ) : (
    <Result
      status="403"
      title="当前账号没有此操作权限"
      subTitle="可以联系此资料范围的所有者调整授权"
    />
  );
}
