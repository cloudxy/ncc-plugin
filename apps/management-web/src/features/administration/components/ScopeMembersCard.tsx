import {
  App,
  Button,
  Card,
  Checkbox,
  Form,
  type FormInstance,
  Popconfirm,
  Select,
  Space,
  Table,
  Tag,
  Typography,
} from "antd";
import { api, scoped, type Json, type Scope } from "../../../shared/api";
import { ErrorPanel } from "../../../shared/components/Feedback";
import { effectDetail } from "../../creation/effectDetail";
import { ACTION_META, ALL_ACTIONS, actionLabel } from "../adminConstants";

export function ScopeMembersCard({
  scope,
  memberForm,
  membersData,
  membersLoading,
  membersError,
  onRefetchMembers,
  userSelectOptions,
  onDirQueryChange,
}: {
  scope: Scope;
  memberForm: FormInstance;
  membersData: Json[] | undefined;
  membersLoading: boolean;
  membersError: unknown;
  onRefetchMembers: () => Promise<unknown> | void;
  userSelectOptions: { value: string; label: string }[];
  onDirQueryChange: (query: string) => void;
}) {
  const { message } = App.useApp();

  async function removeMember(row: Json) {
    const uid = row.user_id || row.id;
    if (!uid) return;
    try {
      await api(scoped(scope.id, `/members/${uid}`), "DELETE");
      await onRefetchMembers();
      message.success(`已将「${row.username}」移出本空间`);
    } catch (e) {
      message.error(effectDetail(e));
    }
  }

  return (
    <Card title="范围成员">
      <ErrorPanel error={membersError} retry={() => void onRefetchMembers()} />
      <Table<Json>
        size="small"
        rowKey={(r) => String(r.user_id || r.id)}
        dataSource={membersData}
        loading={membersLoading}
        pagination={false}
        columns={[
          {
            title: "账号",
            dataIndex: "username",
            render: (v, r) => (
              <Space wrap size={6}>
                <span>{v}</span>
                {r.owner && <Tag color="success">空间所有者</Tag>}
              </Space>
            ),
          },
          {
            title: "当前权限",
            dataIndex: "actions",
            render: (v: string[]) => (
              <Space wrap size={4}>
                {(v || []).map((x: string) => (
                  <Tag key={x}>{actionLabel(x)}</Tag>
                ))}
              </Space>
            ),
          },
          {
            title: "操作",
            width: 150,
            render: (_, r) =>
              r.owner ? (
                <Typography.Text type="secondary">默认全部权限</Typography.Text>
              ) : (
                <Space size={4}>
                  <Button
                    size="small"
                    type="link"
                    onClick={() =>
                      memberForm.setFieldsValue({
                        username: r.username,
                        actions: r.actions,
                      })
                    }
                  >
                    修改权限
                  </Button>
                  <Popconfirm
                    title={`将「${r.username}」移出当前作品范围？`}
                    description="移出后其在本作品空间的访问权限与范围凭据将立即失效。"
                    okText="确认移出"
                    cancelText="取消"
                    disabled={scope.owner === false}
                    onConfirm={() => void removeMember(r)}
                  >
                    <Button
                      size="small"
                      type="link"
                      danger
                      disabled={scope.owner === false}
                    >
                      移出范围
                    </Button>
                  </Popconfirm>
                </Space>
              ),
          },
        ]}
      />
      <Form
        name="memberForm"
        form={memberForm}
        layout="vertical"
        style={{ marginTop: 20 }}
        onFinish={async (values) => {
          try {
            await api(scoped(scope.id, "/members"), "POST", {
              username: values.username,
              actions: values.actions,
            });
            await onRefetchMembers();
            message.success("成员权限已更新");
          } catch (e) {
            message.error(effectDetail(e));
          }
        }}
      >
        <Form.Item
          name="username"
          label="协作成员用户名"
          rules={[{ required: true, message: "请选择协作成员用户名" }]}
        >
          <Select
            aria-label="协作成员用户名"
            showSearch
            placeholder="搜索并选择已建立的账号用户名"
            filterOption={false}
            onSearch={onDirQueryChange}
            options={userSelectOptions}
          />
        </Form.Item>
        <Form.Item
          name="actions"
          label="授予权限"
          initialValue={["read"]}
          rules={[
            {
              required: true,
              type: "array",
              min: 1,
              message: "至少勾选一项权限",
            },
          ]}
        >
          <Checkbox.Group style={{ width: "100%" }}>
            <div className="perm-grid">
              {ALL_ACTIONS.map((key) => (
                <Checkbox key={key} value={key}>
                  <span className="perm-option">
                    <b>{ACTION_META[key].label}</b>
                    <small>{ACTION_META[key].desc}</small>
                  </span>
                </Checkbox>
              ))}
            </div>
          </Checkbox.Group>
        </Form.Item>
        <Button type="primary" htmlType="submit">
          更新成员权限
        </Button>
      </Form>
    </Card>
  );
}
