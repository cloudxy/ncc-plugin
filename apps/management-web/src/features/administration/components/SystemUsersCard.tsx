import { PlusOutlined } from "@ant-design/icons";
import { useQueryClient } from "@tanstack/react-query";
import {
  App,
  Button,
  Card,
  Form,
  Input,
  Modal,
  Popconfirm,
  Space,
  Table,
  Tag,
  Typography,
} from "antd";
import { useState } from "react";
import { api, type Json } from "../../../shared/api";
import { ErrorPanel } from "../../../shared/components/Feedback";
import { effectDetail } from "../../creation/effectDetail";

export function SystemUsersCard({
  isSystemAdmin,
  currentUserId,
  usersData,
  usersLoading,
  usersError,
  onRefetchUsers,
  onRefetchDirectory,
  userOpen,
  onOpenCreateUser,
  onCloseCreateUser,
  onSelectAsMember,
  onUserCreated,
}: {
  isSystemAdmin: boolean;
  currentUserId: string | undefined;
  usersData: Json[] | undefined;
  usersLoading: boolean;
  usersError: unknown;
  onRefetchUsers: () => Promise<unknown> | void;
  onRefetchDirectory: () => Promise<unknown> | void;
  userOpen: boolean;
  onOpenCreateUser: () => void;
  onCloseCreateUser: () => void;
  onSelectAsMember: (username: string, actions: string[]) => void;
  onUserCreated: (username: string) => void;
}) {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const [userForm] = Form.useForm();
  const [resetForm] = Form.useForm();
  const [resetTarget, setResetTarget] = useState<Json | null>(null);
  const [resetSaving, setResetSaving] = useState(false);

  async function toggleUserActive(row: Json) {
    try {
      await api(`/users/${row.id}`, "PATCH", { active: !row.active });
      await Promise.all([
        onRefetchUsers(),
        queryClient.invalidateQueries({ queryKey: ["users"] }),
      ]);
      message.success(
        row.active ? "账号已停用并下线活跃会话" : "账号已恢复启用",
      );
    } catch (e) {
      message.error(effectDetail(e));
    }
  }

  return (
    <>
      {isSystemAdmin && (
        <Card
          title="系统账号管理"
          extra={
            <Button
              size="small"
              type="primary"
              icon={<PlusOutlined />}
              onClick={onOpenCreateUser}
            >
              建立新账号
            </Button>
          }
        >
          <ErrorPanel error={usersError} retry={() => void onRefetchUsers()} />
          <Table<Json>
            size="small"
            rowKey="id"
            dataSource={usersData}
            loading={usersLoading}
            pagination={{ pageSize: 8 }}
            columns={[
              {
                title: "用户名",
                dataIndex: "username",
                render: (v, r) => (
                  <Space wrap size={6}>
                    <b>{v}</b>
                    {r.admin && <Tag color="processing">系统管理员</Tag>}
                    {r.must_change_credentials && (
                      <Tag color="warning">首次需改密</Tag>
                    )}
                    {r.id === currentUserId && <Tag>当前登录</Tag>}
                  </Space>
                ),
              },
              {
                title: "状态",
                dataIndex: "active",
                width: 100,
                render: (v) => (
                  <Tag color={v ? "success" : "default"}>
                    {v ? "启用中" : "已停用"}
                  </Tag>
                ),
              },
              {
                title: "操作",
                width: 210,
                render: (_, r) => (
                  <Space wrap size={4}>
                    {r.active && (
                      <Button
                        size="small"
                        type="link"
                        onClick={() => {
                          onSelectAsMember(String(r.username), [
                            "read",
                            "edit",
                          ]);
                          message.info(
                            `已填入「${r.username}」，可在下方勾选权限加入本作品`,
                          );
                        }}
                      >
                        选为成员
                      </Button>
                    )}
                    <Button
                      size="small"
                      type="link"
                      onClick={() => {
                        setResetTarget(r);
                        resetForm.resetFields();
                      }}
                    >
                      重置密码
                    </Button>
                    {r.active ? (
                      <Popconfirm
                        title={`停用账号「${r.username}」？`}
                        description="停用后该用户所有已登录会话将立即失效。"
                        okText="确认停用"
                        cancelText="取消"
                        disabled={r.id === currentUserId}
                        onConfirm={() => void toggleUserActive(r)}
                      >
                        <Button
                          size="small"
                          type="link"
                          danger
                          disabled={r.id === currentUserId}
                        >
                          停用
                        </Button>
                      </Popconfirm>
                    ) : (
                      <Button
                        size="small"
                        type="link"
                        onClick={() => void toggleUserActive(r)}
                      >
                        启用
                      </Button>
                    )}
                  </Space>
                ),
              },
            ]}
          />
        </Card>
      )}

      <Modal
        title="建立本机账号"
        open={userOpen}
        onCancel={onCloseCreateUser}
        onOk={() => userForm.submit()}
        destroyOnHidden
      >
        <Form
          name="userForm"
          form={userForm}
          layout="vertical"
          onFinish={async (values) => {
            try {
              const user = await api<Json>("/users", "POST", values);
              message.success(`账号「${user.username}」已创建`);
              onCloseCreateUser();
              onUserCreated(String(user.username));
              userForm.resetFields();
              await Promise.all([
                onRefetchUsers(),
                onRefetchDirectory(),
                queryClient.invalidateQueries({ queryKey: ["users"] }),
              ]);
            } catch (e) {
              message.error(effectDetail(e));
            }
          }}
        >
          <Form.Item
            name="username"
            label="账号名"
            rules={[{ required: true, min: 2 }]}
          >
            <Input maxLength={128} />
          </Form.Item>
          <Form.Item
            name="password"
            label="初始密码（至少 12 位）"
            rules={[{ required: true, min: 12 }]}
          >
            <Input.Password autoComplete="new-password" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={resetTarget ? `重置密码：${resetTarget.username}` : "重置密码"}
        open={resetTarget !== null}
        onCancel={() => setResetTarget(null)}
        onOk={() => resetForm.submit()}
        confirmLoading={resetSaving}
        okText="确认重置"
        destroyOnHidden
      >
        <Typography.Paragraph type="secondary">
          重置后该用户所有活跃登录会话将立即下线，下次使用新密码登录时将提示修改个人密码。
        </Typography.Paragraph>
        <Form
          name="resetPasswordForm"
          form={resetForm}
          layout="vertical"
          onFinish={async (values) => {
            if (!resetTarget) return;
            setResetSaving(true);
            try {
              await api(`/users/${resetTarget.id}`, "PATCH", {
                reset_password: values.new_password,
              });
              setResetTarget(null);
              resetForm.resetFields();
              await onRefetchUsers();
              message.success("密码已重置，该用户下次登录须更新密码");
            } catch (e) {
              message.error(effectDetail(e));
            } finally {
              setResetSaving(false);
            }
          }}
        >
          <Form.Item
            name="new_password"
            label="新临时密码（至少 12 位）"
            rules={[{ required: true, min: 12, message: "密码长度至少 12 位" }]}
          >
            <Input.Password autoComplete="new-password" maxLength={1024} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
