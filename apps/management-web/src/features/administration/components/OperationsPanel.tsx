import { Alert, Card, Col, Row, Space, Statistic, Tag, Typography } from "antd";
import type { Json } from "../../../shared/api";
import {
  ErrorPanel,
  PageTitle,
  Permission,
  Status,
} from "../../../shared/components/Feedback";

export function OperationsPanel({
  allowed,
  data,
  isPending,
  error,
  onRetry,
}: {
  allowed: boolean;
  data: Json | undefined;
  isPending: boolean;
  error: unknown;
  onRetry: () => void;
}) {
  const worker = data?.worker as
    | {
        online?: boolean;
        last_seen_at?: string | null;
        stale_seconds?: number | null;
      }
    | undefined;
  const workerLastSeen = worker?.last_seen_at
    ? `${new Date(worker.last_seen_at).toLocaleString()}${
        typeof worker.stale_seconds === "number"
          ? `（距今 ${worker.stale_seconds} 秒）`
          : ""
      }`
    : "尚无心跳记录";

  return (
    <Permission allowed={allowed}>
      <PageTitle
        title="运行管理"
        note="应用、任务、索引和恢复状态分别观察。备份与恢复通过受控维护命令执行。"
      />
      <ErrorPanel error={error} retry={onRetry} />
      <Row gutter={[16, 16]}>
        {Object.entries(data?.jobs || {}).map(([key, count]) => (
          <Col key={key} xs={12} sm={12} md={6}>
            <Card>
              <Statistic title={<Status value={key} />} value={Number(count)} />
            </Card>
          </Col>
        ))}
      </Row>
      <Card style={{ marginTop: 24 }} title="后台任务执行器（Worker）心跳">
        <Space wrap style={{ marginBottom: 8 }}>
          <Typography.Text strong>运行状态：</Typography.Text>
          {isPending ? (
            <Tag>正在检查</Tag>
          ) : worker?.online === true ? (
            <Tag color="success">在线</Tag>
          ) : worker?.online === false ? (
            <Tag color="warning">离线 / 未启动</Tag>
          ) : (
            <Tag>等待上报</Tag>
          )}
          <Typography.Text type="secondary">
            最近心跳：{workerLastSeen}
          </Typography.Text>
        </Space>
        {worker?.online === false && (
          <Alert
            type="warning"
            showIcon
            style={{ marginTop: 8, marginBottom: 0 }}
            title="后台任务执行器当前未在线"
            description={
              <span>
                排队中的创作、导入与导出任务不会自动处理。请使用{" "}
                <code>./start.py</code>（Windows 使用{" "}
                <code>python start.py</code>）一键同启 Web 与 Worker。
              </span>
            }
          />
        )}
      </Card>
      <Card style={{ marginTop: 24 }} title="环境与维护">
        <Typography.Paragraph>
          服务版本：{data?.version || "正在检查"} · 数据库：
          {data?.database || "正在检查"}
        </Typography.Paragraph>
        <Typography.Paragraph style={{ wordBreak: "break-all" }}>
          评分策略：<code>{data?.policy_hash?.slice(0, 16)}</code>
        </Typography.Paragraph>
        <Alert
          type="info"
          title="完整备份与恢复"
          description="使用 ncc-data backup / restore 维护命令，在隔离目标完成对账后切换。导出文件与完整数据库备份分别管理。"
        />
        <Typography.Paragraph style={{ marginTop: 20 }}>
          写作、修订和评价可以在「AI 配置」分别绑定不同模型或本机 CLI OAuth
          订阅通道。未配置时任务保留待处理，不生成演示正文或分数。
        </Typography.Paragraph>
        <Typography.Paragraph>
          启动服务与持久任务执行器：使用 <code>./start.py</code> 一键同启 Web 与
          Worker
        </Typography.Paragraph>
      </Card>
    </Permission>
  );
}
