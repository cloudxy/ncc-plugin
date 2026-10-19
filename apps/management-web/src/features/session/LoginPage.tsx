import { Button, Form, Input, Typography } from "antd";
import { useState } from "react";
import { api, setCSRF, type Json } from "../../shared/api";
import { ErrorPanel } from "../../shared/components/Feedback";

export function LoginPage({ done }: { done: () => void }) {
  const [busy, setBusy] = useState(false),
    [error, setError] = useState<unknown>();
  return (
    <div className="login-shell">
      <div className="login-intro">
        <div className="brand-mark">N</div>
        <h1>
          让故事生长。
          <br />
          把复杂留给流程。
        </h1>
        <p>Novel Create Center · 私有创作与知识工作台</p>
        <div className="login-lines">
          <span>创作与修改</span>
          <span>世界与人物</span>
          <span>质量与连续性</span>
        </div>
      </div>
      <div className="login-form">
        <Typography.Title level={2}>进入创作空间</Typography.Title>
        <Typography.Paragraph type="secondary">
          使用本机管理员建立的账号登录。
        </Typography.Paragraph>
        <ErrorPanel error={error} />
        <Form
          layout="vertical"
          onFinish={async (values) => {
            setBusy(true);
            setError(undefined);
            try {
              const user = await api<Json>("/auth/login", "POST", values);
              setCSRF(user.csrf);
              done();
            } catch (e) {
              setError(e);
            } finally {
              setBusy(false);
            }
          }}
        >
          <Form.Item name="username" label="账号" rules={[{ required: true }]}>
            <Input autoComplete="username" size="large" />
          </Form.Item>
          <Form.Item name="password" label="密码" rules={[{ required: true }]}>
            <Input.Password autoComplete="current-password" size="large" />
          </Form.Item>
          <Button
            type="primary"
            htmlType="submit"
            loading={busy}
            block
            size="large"
          >
            登录
          </Button>
        </Form>
        <p className="muted">
          首次使用请在终端执行 ncc-data create-user。服务没有默认密码。
        </p>
      </div>
    </div>
  );
}
