import { LogoutOutlined } from "@ant-design/icons";
import { Alert, Button, Form, Input, Modal, Space } from "antd";
import { useEffect, useState } from "react";
import { api, setCSRF, type Json } from "../../shared/api";
import { ErrorPanel } from "../../shared/components/Feedback";

export type CredentialChangeModalProps = {
  open: boolean;
  enforced?: boolean;
  currentUsername?: string;
  mustChangeDefault?: boolean;
  mustChangePassword?: boolean;
  onClose?: () => void;
  onSuccess: (updatedMe: Json) => void;
  onLogout?: () => void | Promise<void>;
};

type CredentialFormValues = {
  current_password: string;
  new_username: string;
  new_password: string;
  confirm_password: string;
};

export function CredentialChangeModal({
  open,
  enforced = false,
  currentUsername = "",
  mustChangeDefault = false,
  mustChangePassword = false,
  onClose,
  onSuccess,
  onLogout,
}: CredentialChangeModalProps) {
  const [form] = Form.useForm<CredentialFormValues>();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<unknown>();

  const requirePasswordUpdate =
    enforced || mustChangeDefault || mustChangePassword;

  useEffect(() => {
    if (!open) return;
    setError(undefined);
    form.resetFields();
    form.setFieldsValue({
      current_password: "",
      new_username: mustChangeDefault ? "" : currentUsername,
      new_password: "",
      confirm_password: "",
    });
  }, [open, currentUsername, mustChangeDefault, form]);

  const canDismiss = !enforced && !submitting;

  const modalTitle = enforced
    ? mustChangeDefault
      ? "首次登录安全要求：修改默认管理员账号与密码"
      : `首次登录安全要求：修改账号（${currentUsername}）的临时密码`
    : mustChangeDefault
      ? "修改默认管理员账号与密码"
      : mustChangePassword
        ? `请修改临时密码（${currentUsername}）`
        : "修改账号与密码";

  return (
    <Modal
      title={modalTitle}
      open={open}
      closable={canDismiss}
      keyboard={canDismiss}
      mask={{ closable: canDismiss }}
      onCancel={canDismiss ? () => onClose?.() : undefined}
      footer={
        <Space
          style={{
            width: "100%",
            justifyContent: enforced && onLogout ? "space-between" : "flex-end",
          }}
        >
          {enforced && onLogout ? (
            <Button
              icon={<LogoutOutlined />}
              disabled={submitting}
              onClick={() => void onLogout()}
            >
              退出登录
            </Button>
          ) : null}
          <Space>
            {!enforced ? (
              <Button disabled={submitting} onClick={() => onClose?.()}>
                取消
              </Button>
            ) : null}
            <Button
              type="primary"
              loading={submitting}
              onClick={() => form.submit()}
            >
              确认修改
            </Button>
          </Space>
        </Space>
      }
      destroyOnHidden
    >
      {enforced ? (
        <Alert
          type="warning"
          showIcon
          title={
            mustChangeDefault
              ? "当前通过真实地址访问且正在使用默认管理员账号，必须先修改账号名和密码后才能继续使用工作台。"
              : `当前监听或访问非回环地址，账号（${currentUsername}）正在使用初始或已重置临时密码，必须先设置至少 12 位的新密码后才能继续使用。`
          }
        />
      ) : mustChangeDefault ? (
        <Alert
          type="info"
          showIcon
          title="首次使用默认管理员账号（admin），请修改为专属账号名并设置至少 12 位的新密码。"
        />
      ) : mustChangePassword ? (
        <Alert
          type="info"
          showIcon
          title={`当前账号（${currentUsername}）使用的是初始或已重置临时密码，请设置至少 12 位的新密码（账号名可保持不变，也可一并修改）。`}
        />
      ) : null}
      <ErrorPanel error={error} />
      <Form<CredentialFormValues>
        name="credentialChangeForm"
        form={form}
        layout="vertical"
        onFinish={async (values) => {
          if (submitting) return;
          setSubmitting(true);
          setError(undefined);
          try {
            const updated = await api<Json>("/auth/credentials", "POST", {
              current_password: values.current_password,
              new_username: values.new_username.trim(),
              new_password: values.new_password,
            });
            if (typeof updated?.csrf === "string") {
              setCSRF(updated.csrf);
            }
            form.resetFields();
            onSuccess(updated);
          } catch (e) {
            setError(e);
          } finally {
            setSubmitting(false);
          }
        }}
      >
        <Form.Item
          name="current_password"
          label="当前密码"
          rules={[
            { required: true, message: "请输入当前密码" },
            { max: 1024, message: "密码长度不能超过 1024 个字符" },
          ]}
        >
          <Input.Password
            autoComplete="current-password"
            placeholder="请输入当前登录密码"
          />
        </Form.Item>
        <Form.Item
          name="new_username"
          label="新账号名"
          rules={[
            {
              validator: async (_, value) => {
                const trimmed = typeof value === "string" ? value.trim() : "";
                if (!trimmed) {
                  throw new Error("请输入新账号名");
                }
                if (trimmed.length < 2 || trimmed.length > 128) {
                  throw new Error("账号名长度须在 2 到 128 个字符之间");
                }
                if (/[\s\u0000-\u001f\u007f]/.test(trimmed)) {
                  throw new Error("账号名不能包含空格或控制字符");
                }
                if (mustChangeDefault && trimmed.toLowerCase() === "admin") {
                  throw new Error("请修改默认管理员账号名，不能继续使用 admin");
                }
              },
            },
          ]}
        >
          <Input
            autoComplete="username"
            maxLength={128}
            placeholder={
              mustChangeDefault
                ? "请输入新账号名（不能继续使用 admin）"
                : "可保持原账号名或修改（2–128 个字符）"
            }
          />
        </Form.Item>
        <Form.Item
          name="new_password"
          label="新密码"
          dependencies={["current_password"]}
          rules={[
            { required: true, message: "请输入新密码" },
            { min: 12, message: "新密码至少需要 12 个字符" },
            { max: 1024, message: "密码长度不能超过 1024 个字符" },
            ({ getFieldValue }) => ({
              validator: async (_, value) => {
                if (
                  requirePasswordUpdate &&
                  value &&
                  value === getFieldValue("current_password")
                ) {
                  throw new Error("新密码不能与当前密码相同");
                }
              },
            }),
          ]}
        >
          <Input.Password
            autoComplete="new-password"
            placeholder="至少 12 个字符"
          />
        </Form.Item>
        <Form.Item
          name="confirm_password"
          label="确认新密码"
          dependencies={["new_password"]}
          rules={[
            { required: true, message: "请再次输入新密码" },
            ({ getFieldValue }) => ({
              validator: async (_, value) => {
                if (value && value !== getFieldValue("new_password")) {
                  throw new Error("两次输入的新密码不一致");
                }
              },
            }),
          ]}
        >
          <Input.Password
            autoComplete="new-password"
            placeholder="再次输入新密码以确认一致"
          />
        </Form.Item>
        <button
          type="submit"
          style={{ display: "none" }}
          aria-hidden="true"
          tabIndex={-1}
        />
      </Form>
    </Modal>
  );
}
