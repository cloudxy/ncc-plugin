import {
  Button,
  Card,
  Checkbox,
  Skeleton,
  Space,
  Table,
  Tag,
  Typography,
} from "antd";
import type { Key, ReactNode } from "react";
import type { Definition, Entity } from "../../../shared/api";
import type { CodexGroup } from "../../../shared/studioApi";
import {
  fieldText,
  resolveFieldLabel,
  resolveKindLabel,
} from "../materialHelpers";

export function MaterialCardGrid({
  view,
  showSkeleton,
  loading,
  rows,
  groups,
  defs,
  canEdit,
  selected,
  emptyNode,
  offset,
  totalCount,
  hasServerTotal,
  hasNextPage,
  nextOffset,
  onSelectedChange,
  onOpenDetail,
  onHandoff,
  onPrevPage,
  onNextPage,
}: {
  view: "表格" | "卡片";
  showSkeleton: boolean;
  loading: boolean;
  rows: Entity[];
  groups: CodexGroup[];
  defs: Definition[] | undefined;
  canEdit: boolean;
  selected: Key[];
  emptyNode: ReactNode;
  offset: number;
  totalCount: number;
  hasServerTotal: boolean;
  hasNextPage: boolean;
  nextOffset: number;
  onSelectedChange: (next: Key[]) => void;
  onOpenDetail: (id: string) => void;
  onHandoff: (row: Entity) => void;
  onPrevPage: () => void;
  onNextPage: () => void;
}) {
  return (
    <>
      {showSkeleton ? (
        <Skeleton active paragraph={{ rows: 8 }} />
      ) : view === "表格" ? (
        <Table
          rowKey="id"
          loading={loading}
          dataSource={rows}
          pagination={false}
          scroll={{ x: 1000 }}
          locale={{ emptyText: emptyNode }}
          rowSelection={
            canEdit
              ? { selectedRowKeys: selected, onChange: onSelectedChange }
              : undefined
          }
          columns={[
            {
              title: "名称",
              dataIndex: "name",
              width: 220,
              onCell: (row: Entity) => ({
                onClick: () => onOpenDetail(row.id),
                style: { cursor: "pointer" },
              }),
              render: (name: string, row: Entity) => (
                <Button
                  type="link"
                  onClick={(event) => {
                    event.stopPropagation();
                    onOpenDetail(row.id);
                  }}
                >
                  {name}
                </Button>
              ),
            },
            {
              title: "类型",
              dataIndex: "kind",
              width: 160,
              render: (value: string) => (
                <Tag>{resolveKindLabel(defs, value)}</Tag>
              ),
            },
            {
              title: "摘要",
              render: (_value, row: Entity) =>
                row.data?.description || row.text_preview || "—",
            },
            {
              title: "标签",
              render: (_value, row: Entity) => (
                <Space wrap>
                  {row.data?.tags?.map((value: string) => (
                    <Tag key={value}>{value}</Tag>
                  ))}
                </Space>
              ),
            },
            {
              title: "排序号",
              width: 90,
              render: (_value, row: Entity) =>
                typeof row.data?.position === "number"
                  ? row.data.position
                  : "—",
            },
            {
              title: "版本",
              dataIndex: "version",
              width: 100,
              render: (value: string) => value.split(":").pop(),
            },
            {
              title: "范围",
              dataIndex: "secret",
              width: 100,
              render: (value: boolean) => (
                <Tag color={value ? "orange" : "default"}>
                  {value ? "作者秘密" : "普通资料"}
                </Tag>
              ),
            },
          ]}
        />
      ) : (
        <>
          {rows.length === 0 ? (
            emptyNode
          ) : (
            <div className="mat-card-grid">
              {rows.map((row) => {
                const owner = groups.find((item) =>
                  item.kinds.includes(row.kind),
                );
                const keys = owner?.recommended_fields || [];
                return (
                  <article key={row.id} className="mat-card">
                    <Card
                      title={
                        <h3 className="mat-card-name" title={row.name}>
                          {row.name}
                        </h3>
                      }
                      extra={
                        canEdit ? (
                          <Checkbox
                            aria-label={`选择 ${row.name}`}
                            checked={selected.includes(row.id)}
                            onChange={(event) =>
                              onSelectedChange(
                                event.target.checked
                                  ? [...selected, row.id]
                                  : selected.filter((id) => id !== row.id),
                              )
                            }
                          />
                        ) : null
                      }
                    >
                      <Tag>{resolveKindLabel(defs, row.kind)}</Tag>
                      <p>
                        {row.data?.description ||
                          row.text_preview ||
                          "还没有摘要"}
                      </p>
                      <div className="mat-highlight">
                        {keys.map((key) => {
                          const text = fieldText(row.data?.[key]);
                          if (!text) return null;
                          return (
                            <div key={key}>
                              <strong>{resolveFieldLabel(defs, key)}：</strong>
                              {text}
                            </div>
                          );
                        })}
                      </div>
                      <Space wrap>
                        <Button onClick={() => onOpenDetail(row.id)}>
                          详情编辑
                        </Button>
                        <Button onClick={() => onHandoff(row)}>
                          带入创作台
                        </Button>
                      </Space>
                    </Card>
                  </article>
                );
              })}
            </div>
          )}
        </>
      )}
      <div className="pager">
        <Typography.Text type="secondary">
          {loading
            ? "正在载入"
            : hasServerTotal
              ? `本页 ${rows.length} 条 · 共 ${totalCount} 条`
              : `当前 ${rows.length} 条 · 服务端分页`}
        </Typography.Text>
        <Space>
          <Button disabled={offset === 0} onClick={onPrevPage}>
            上一页
          </Button>
          <Button disabled={!hasNextPage} onClick={onNextPage}>
            下一页
          </Button>
        </Space>
      </div>
    </>
  );
}
