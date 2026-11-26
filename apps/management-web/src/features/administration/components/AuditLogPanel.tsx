import { Button, Card, Select, Table, Tag } from "antd";
import type { Json } from "../../../shared/api";
import {
  ErrorPanel,
  NoData,
  PageTitle,
  Permission,
} from "../../../shared/components/Feedback";
import { AUDIT_ACTION_LABELS, summarizeAuditDetail } from "../adminConstants";

export function AuditLogPanel({
  allowed,
  auditData,
  auditLoading,
  auditError,
  onRetry,
  auditAction,
  onAuditActionChange,
  auditActor,
  auditActorOptions,
  onAuditActorChange,
  onClearFilters,
}: {
  allowed: boolean;
  auditData: Json[] | undefined;
  auditLoading: boolean;
  auditError: unknown;
  onRetry: () => void;
  auditAction: string | undefined;
  onAuditActionChange: (value: string | undefined) => void;
  auditActor: string | undefined;
  auditActorOptions: { value: string; label: string }[];
  onAuditActorChange: (value: string | undefined) => void;
  onClearFilters: () => void;
}) {
  const auditActionOptions = Object.entries(AUDIT_ACTION_LABELS).map(
    ([value, label]) => ({ value, label }),
  );
  return (
    <Permission allowed={allowed}>
      <PageTitle
        title="操作审计"
        note="正式采用、成员授权、账号变更与下载均保留受保护回执；已提交审计由数据库保护，不可覆盖。"
      />
      <Card>
        <div className="audit-filters">
          <Select
            aria-label="按动作筛选"
            allowClear
            placeholder="筛选操作动作"
            style={{ width: 210 }}
            value={auditAction}
            options={auditActionOptions}
            onChange={(val) => onAuditActionChange(val)}
          />
          <Select
            aria-label="按操作者筛选"
            allowClear
            showSearch
            optionFilterProp="label"
            placeholder="筛选操作者"
            style={{ width: 190 }}
            value={auditActor}
            options={auditActorOptions}
            onChange={(val) => onAuditActorChange(val)}
          />
          {(auditAction || auditActor) && (
            <Button onClick={onClearFilters}>清除筛选</Button>
          )}
        </div>
        <ErrorPanel error={auditError} retry={onRetry} />
        <Table<Json>
          rowKey="id"
          dataSource={auditData}
          loading={auditLoading}
          locale={{
            emptyText: (
              <NoData
                text={
                  auditAction || auditActor
                    ? "没有匹配当前筛选条件的审计记录"
                    : "当前空间还没有审计记录"
                }
              />
            ),
          }}
          pagination={{ pageSize: 20 }}
          columns={[
            {
              title: "时间",
              dataIndex: "created_at",
              width: 180,
              render: (v) => new Date(v).toLocaleString(),
            },
            {
              title: "动作",
              dataIndex: "action",
              width: 160,
              render: (v: string) => <Tag>{AUDIT_ACTION_LABELS[v] || v}</Tag>,
            },
            {
              title: "操作者",
              width: 140,
              render: (_, r) =>
                r.actor_username ||
                (typeof r.actor_id === "string"
                  ? r.actor_id.slice(0, 8)
                  : "系统"),
            },
            { title: "记录版本", dataIndex: "version", width: 96 },
            {
              title: "操作摘要与回执详情",
              render: (_, r) => (
                <div>
                  <div>{summarizeAuditDetail(String(r.action), r.detail)}</div>
                  {r.detail && Object.keys(r.detail).length > 0 && (
                    <details>
                      <summary>查看原始记录 JSON</summary>
                      <pre className="json-small">
                        {JSON.stringify(r.detail, null, 2)}
                      </pre>
                    </details>
                  )}
                </div>
              ),
            },
          ]}
        />
      </Card>
    </Permission>
  );
}
