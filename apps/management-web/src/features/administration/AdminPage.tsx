import { PlusOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import {
  Alert,
  App,
  Button,
  Card,
  Checkbox,
  Col,
  Form,
  Input,
  Modal,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  Typography,
} from "antd";
import { useState } from "react";
import { useParams } from "react-router-dom";
import { api, scoped, type Json } from "../../shared/api";
import {
  ErrorPanel,
  PageTitle,
  Permission,
  Status,
} from "../../shared/components/Feedback";
import { useWorkspace } from "../../shared/WorkspaceContext";
import { TrustControls } from "./components/TrustControls";

export function AdminPage() {
  const { page } = useParams(),
    { scope } = useWorkspace(),
    { message } = App.useApp(),
    [userOpen, setUserOpen] = useState(false),
    [token, setToken] = useState("");
  const [memberForm] = Form.useForm(),
    [userForm] = Form.useForm(),
    [tokenForm] = Form.useForm();
  const me = useQuery({ queryKey: ["me"], queryFn: () => api<Json>("/me") });
  const audit = useQuery({
    queryKey: ["scope", scope.id, "audit"],
    queryFn: () => api<Json[]>(scoped(scope.id, "/audit")),
    enabled: page === "audit" && scope.actions.includes("admin"),
  });
  const members = useQuery({
    queryKey: ["scope", scope.id, "members"],
    queryFn: () => api<Json[]>(scoped(scope.id, "/members")),
    enabled: page === "settings" && scope.actions.includes("admin"),
  });
  const operations = useQuery({
    queryKey: ["scope", scope.id, "operations"],
    queryFn: () => api<Json>(scoped(scope.id, "/operations")),
    enabled: page === "operations" && scope.actions.includes("operate"),
    refetchInterval: 10000,
  });
  if (page === "audit")
    return (
      <Permission allowed={scope.actions.includes("admin")}>
        <PageTitle
          title="操作审计"
          note="正式采用、成员授权与下载保留回执；已提交审计由数据库保护，不可普通覆盖。"
        />
        <Card>
          <ErrorPanel error={audit.error} />
          <Table
            rowKey="id"
            dataSource={audit.data}
            loading={audit.isPending}
            pagination={{ pageSize: 20 }}
            columns={[
              {
                title: "时间",
                dataIndex: "created_at",
                render: (v) => new Date(v).toLocaleString(),
              },
              { title: "动作", dataIndex: "action" },
              { title: "记录版本", dataIndex: "version" },
              {
                title: "操作者",
                dataIndex: "actor_id",
                render: (v) => v.slice(0, 8),
              },
              {
                title: "范围与摘要",
                dataIndex: "detail",
                render: (v) => <code>{JSON.stringify(v)}</code>,
              },
            ]}
          />
        </Card>
      </Permission>
    );
  if (page === "operations")
    return (
      <Permission allowed={scope.actions.includes("operate")}>
        <PageTitle
          title="运行管理"
          note="应用、任务、索引和恢复状态分别观察。备份与恢复通过受控维护命令执行。"
        />
        <ErrorPanel error={operations.error} />
        <Row gutter={20}>
          {Object.entries(operations.data?.jobs || {}).map(([key, count]) => (
            <Col key={key} span={6}>
              <Card>
                <Statistic
                  title={<Status value={key} />}
                  value={Number(count)}
                />
              </Card>
            </Col>
          ))}
        </Row>
        <Card style={{ marginTop: 24 }} title="环境与维护">
          <Typography.Paragraph>
            服务版本：{operations.data?.version || "正在检查"} · 数据库：
            {operations.data?.database || "正在检查"}
          </Typography.Paragraph>
          <Typography.Paragraph>
            评分策略：<code>{operations.data?.policy_hash?.slice(0, 16)}</code>
          </Typography.Paragraph>
          <Alert
            type="info"
            title="完整备份与恢复"
            description="使用 ncc-data backup / restore 维护命令，在隔离目标完成对账后切换。导出文件与完整数据库备份分别管理。"
          />
          <Typography.Paragraph style={{ marginTop: 20 }}>
            模型配置由服务端私有环境管理：NCC_MODEL_URL、NCC_MODEL_KEY、NCC_WRITER_MODEL、NCC_JUDGE_MODEL。未配置时任务保留待处理状态，不生成演示正文或分数。
          </Typography.Paragraph>
          <Typography.Paragraph>
            启动持久任务执行器：<code>ncc-data worker</code>
          </Typography.Paragraph>
        </Card>
      </Permission>
    );
  return (
    <Permission allowed={scope.actions.includes("admin")}>
      <PageTitle
        title="成员与设置"
        note="真实用户权限与小说人物认知分别管理，范围凭据不能扩大账号现有权限。"
        actions={
          me.data?.admin && (
            <Button icon={<PlusOutlined />} onClick={() => setUserOpen(true)}>
              建立账号
            </Button>
          )
        }
      />
      <Row gutter={24}>
        <Col xs={24} lg={14}>
          <Card title="范围成员">
            <ErrorPanel error={members.error} />
            <Table
              rowKey="id"
              dataSource={members.data}
              pagination={false}
              columns={[
                { title: "账号", dataIndex: "username" },
                {
                  title: "权限",
                  dataIndex: "actions",
                  render: (v) => (
                    <Space wrap>
                      {v.map((x: string) => (
                        <Tag key={x}>{x}</Tag>
                      ))}
                    </Space>
                  ),
                },
              ]}
            />
            <Form
              form={memberForm}
              layout="vertical"
              style={{ marginTop: 24 }}
              onFinish={async (values) => {
                try {
                  await api(scoped(scope.id, "/members"), "POST", values);
                  members.refetch();
                  message.success("成员权限已更新");
                } catch (e) {
                  message.error((e as Error).message);
                }
              }}
            >
              <Form.Item
                name="user_id"
                label="账号ID"
                rules={[{ required: true }]}
              >
                <Input />
              </Form.Item>
              <Form.Item
                name="actions"
                label="授权动作"
                initialValue={["read"]}
              >
                <Checkbox.Group
                  options={[
                    "read",
                    "edit",
                    "adopt",
                    "assess",
                    "export",
                    "secret",
                    "admin",
                    "operate",
                  ]}
                />
              </Form.Item>
              <Button type="primary" htmlType="submit">
                更新权限
              </Button>
            </Form>
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card title="本范围自动化凭据">
            <Typography.Paragraph type="secondary">
              令牌仅显示一次，保存到私有环境变量。不要放入小说、Git或浏览器持久存储。
            </Typography.Paragraph>
            <Form
              form={tokenForm}
              layout="vertical"
              initialValues={{ actions: ["read"], hours: 24 }}
              onFinish={async (values) => {
                try {
                  const result = await api<Json>(
                    scoped(scope.id, "/tokens"),
                    "POST",
                    values,
                  );
                  setToken(result.token);
                } catch (e) {
                  message.error((e as Error).message);
                }
              }}
            >
              <Form.Item name="actions" label="动作">
                <Checkbox.Group options={scope.actions} />
              </Form.Item>
              <Form.Item name="hours" label="有效小时">
                <Select
                  options={[1, 8, 24, 72, 168].map((value) => ({
                    value,
                    label: String(value),
                  }))}
                />
              </Form.Item>
              <Button htmlType="submit">生成范围凭据</Button>
            </Form>
            {token && (
              <Input.Password
                style={{ marginTop: 16 }}
                value={token}
                readOnly
                addonAfter={
                  <Button
                    type="link"
                    onClick={() => navigator.clipboard.writeText(token)}
                  >
                    复制
                  </Button>
                }
              />
            )}
          </Card>
          <Card style={{ marginTop: 24 }} title="自动定稿策略">
            <Typography.Paragraph>
              普通创作默认集中审核。托管需明确对象、时间与次数，并完成对应评分策略的留出校准；授权可随时撤销。
            </Typography.Paragraph>
            <Tag>质量线 85 · 最多修订 2 次</Tag>
          </Card>
          <TrustControls />
        </Col>
      </Row>
      <Modal
        title="建立本机账号"
        open={userOpen}
        onCancel={() => setUserOpen(false)}
        onOk={() => userForm.submit()}
        destroyOnHidden
      >
        <Form
          form={userForm}
          layout="vertical"
          onFinish={async (values) => {
            try {
              const user = await api<Json>("/users", "POST", values);
              message.success("账号已创建，ID：" + user.id);
              setUserOpen(false);
              memberForm.setFieldsValue({ user_id: user.id });
              userForm.resetFields();
            } catch (e) {
              message.error((e as Error).message);
            }
          }}
        >
          <Form.Item
            name="username"
            label="账号名"
            rules={[{ required: true }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="password"
            label="初始密码"
            rules={[{ required: true, min: 12 }]}
          >
            <Input.Password autoComplete="new-password" />
          </Form.Item>
        </Form>
      </Modal>
    </Permission>
  );
}
