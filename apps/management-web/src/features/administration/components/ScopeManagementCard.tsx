import { useQueryClient } from "@tanstack/react-query";
import { App, Button, Card, Popconfirm, Space, Table, Typography } from "antd";
import { api, type Scope } from "../../../shared/api";
import { queryKeys } from "../../../shared/queryKeys";
import { kindLabel } from "../../../shared/scopeLabel";
import { effectDetail } from "../../creation/effectDetail";

export function ScopeManagementCard({
  scope,
  archivedScopes,
  onRefetchAllScopes,
}: {
  scope: Scope;
  archivedScopes: Scope[];
  onRefetchAllScopes: () => Promise<unknown> | void;
}) {
  const { message } = App.useApp();
  const queryClient = useQueryClient();

  async function archiveOrRestoreScope(targetId: string, archived: boolean) {
    try {
      await api(`/scopes/${targetId}`, "PATCH", { archived });
      await queryClient.invalidateQueries({ queryKey: queryKeys.scopesRoot() });
      await onRefetchAllScopes();
      message.success(
        archived ? "空间已归档，可随时在本页恢复" : "空间已恢复至工作台列表",
      );
    } catch (e) {
      message.error(effectDetail(e));
    }
  }

  async function deleteEmptyScope(targetId: string) {
    try {
      await api(`/scopes/${targetId}`, "DELETE");
      await queryClient.invalidateQueries({ queryKey: queryKeys.scopesRoot() });
      await onRefetchAllScopes();
      message.success("空空间已彻底删除");
    } catch (e) {
      message.error(effectDetail(e));
    }
  }

  return (
    <Card title="作品空间管理">
      <Typography.Paragraph type="secondary">
        当前空间：<b>{scope.name}</b>（{kindLabel(scope.kind)} · v
        {scope.version}）
      </Typography.Paragraph>
      <Space wrap>
        <Popconfirm
          title={`归档当前空间「${scope.name}」？`}
          description="归档后将从顶栏日常下拉列表中隐藏，全部章节、设定与修订历史原样保留，随时可在此恢复。"
          okText="确认归档"
          cancelText="取消"
          disabled={scope.owner === false}
          onConfirm={() => void archiveOrRestoreScope(scope.id, true)}
        >
          <Button disabled={scope.owner === false}>归档当前空间</Button>
        </Popconfirm>
        {scope.version === 0 ? (
          <Popconfirm
            title={`彻底删除空空间「${scope.name}」？`}
            description="该空间尚无正式修订（v0），彻底删除后不可恢复。"
            okText="彻底删除"
            cancelText="取消"
            disabled={scope.owner === false}
            onConfirm={() => void deleteEmptyScope(scope.id)}
          >
            <Button danger disabled={scope.owner === false}>
              删除空空间
            </Button>
          </Popconfirm>
        ) : (
          <Typography.Text type="secondary">
            已有正式修订（v{scope.version}
            ）的空间受保护不可彻底删除，可使用归档隐藏。
          </Typography.Text>
        )}
      </Space>
      {archivedScopes.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <Typography.Text strong>
            已归档空间（{archivedScopes.length}）
          </Typography.Text>
          <Table<Scope>
            size="small"
            style={{ marginTop: 8 }}
            rowKey="id"
            pagination={false}
            dataSource={archivedScopes}
            columns={[
              {
                title: "名称",
                dataIndex: "name",
                render: (v, r) => (
                  <span>
                    {v} · {kindLabel(r.kind)} · v{r.version}
                  </span>
                ),
              },
              {
                title: "操作",
                width: 170,
                render: (_, r) => (
                  <Space size={6}>
                    <Button
                      size="small"
                      type="link"
                      disabled={r.owner === false}
                      onClick={() => void archiveOrRestoreScope(r.id, false)}
                    >
                      恢复使用
                    </Button>
                    {r.version === 0 && r.owner !== false && (
                      <Popconfirm
                        title={`彻底删除空空间「${r.name}」？`}
                        okText="彻底删除"
                        cancelText="取消"
                        onConfirm={() => void deleteEmptyScope(r.id)}
                      >
                        <Button size="small" type="link" danger>
                          删除
                        </Button>
                      </Popconfirm>
                    )}
                  </Space>
                ),
              },
            ]}
          />
        </div>
      )}
    </Card>
  );
}
