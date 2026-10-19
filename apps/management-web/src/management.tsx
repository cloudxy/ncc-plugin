import { useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Alert,
  App,
  Button,
  Card,
  Checkbox,
  Col,
  Drawer,
  Form,
  Input,
  List,
  Modal,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  Typography,
  Upload,
} from "antd";
import {
  DownloadOutlined,
  PlusOutlined,
  UploadOutlined,
} from "@ant-design/icons";
import { api, download, scoped, type Json } from "./api";
import { useWorkspace } from "./context";
import { ErrorPanel, NoData, PageTitle, Permission, Status } from "./common";
import { EntityDrawer } from "./materials";
import { TrustControls } from "./trust";

export function ExchangePage() {
  const { scope } = useWorkspace(),
    { message } = App.useApp(),
    [attachment, setAttachment] = useState<Json>(),
    [preview, setPreview] = useState<Json>(),
    [accepted, setAccepted] = useState(false),
    [busy, setBusy] = useState(false),
    [format, setFormat] = useState("json"),
    [form] = Form.useForm();
  const jobs = useQuery({
    queryKey: ["scope", scope.id, "jobs"],
    queryFn: () => api<Json[]>(scoped(scope.id, "/jobs")),
    refetchInterval: 3000,
  });
  async function upload(file: File) {
    setBusy(true);
    setPreview(undefined);
    try {
      const body = new FormData();
      body.append("file", file);
      setAttachment(await api(scoped(scope.id, "/attachments"), "POST", body));
      message.success("原件已受管保存");
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setBusy(false);
    }
    return false;
  }
  async function preflight(values: Json) {
    if (!attachment) return;
    setBusy(true);
    try {
      setPreview(
        await api(scoped(scope.id, "/imports/preflight"), "POST", {
          attachment_id: attachment.id,
          mapping: values,
        }),
      );
      setAccepted(false);
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <PageTitle
        title="导入与导出"
        note="原件、映射、预检与回执分开保存。导出只生成私有文件，不自动发送到外部。"
      />
      <Row gutter={24}>
        <Col xs={24} lg={14}>
          <Card
            title="批量导入"
            extra={
              <Upload
                beforeUpload={upload}
                showUploadList={false}
                accept=".json,.jsonl,.csv,.md,.txt"
              >
                <Button
                  icon={<UploadOutlined />}
                  loading={busy}
                  disabled={!scope.actions.includes("edit")}
                >
                  选择文件
                </Button>
              </Upload>
            }
          >
            {attachment ? (
              <>
                <Alert
                  type="success"
                  title={`${attachment.name} · ${attachment.size}字节`}
                  description={`原件摘要 ${attachment.digest.slice(0, 16)}…`}
                />
                <Form
                  style={{ marginTop: 20 }}
                  form={form}
                  layout="vertical"
                  initialValues={{ kind: "source", name: "name", text: "text" }}
                  onFinish={preflight}
                >
                  <Space wrap align="start">
                    <Form.Item name="kind" label="缺省类型">
                      <Input placeholder="如 character / source / 人物" />
                    </Form.Item>
                    <Form.Item name="name" label="名称所在列">
                      <Input />
                    </Form.Item>
                    <Form.Item name="text" label="正文所在列">
                      <Input />
                    </Form.Item>
                  </Space>
                  <Button htmlType="submit" loading={busy}>
                    执行预检与映射
                  </Button>
                </Form>
              </>
            ) : (
              <NoData text="选择JSON、JSONL、CSV或文本，原件会先进入私有暂存区" />
            )}
            {preview && (
              <div style={{ marginTop: 24 }}>
                <Space>
                  <Statistic title="映射条目" value={preview.count} />
                  <Statistic title="阻断问题" value={preview.errors.length} />
                  <Statistic title="需确认项" value={preview.warnings.length} />
                </Space>
                {preview.errors.length > 0 && (
                  <Alert
                    style={{ marginTop: 16 }}
                    type="error"
                    title="预检尚未通过"
                    description={
                      <pre className="json-small">
                        {JSON.stringify(preview.errors.slice(0, 20), null, 2)}
                      </pre>
                    }
                  />
                )}
                <List
                  size="small"
                  dataSource={preview.warnings}
                  renderItem={(w: Json) => (
                    <List.Item>
                      <Typography.Text type="secondary">
                        {w.detail}
                        {w.unknown_fields
                          ? `：${w.unknown_fields.join("、")}`
                          : ""}
                      </Typography.Text>
                    </List.Item>
                  )}
                />
                {preview.warnings.length > 0 && (
                  <Checkbox
                    checked={accepted}
                    onChange={(e) => setAccepted(e.target.checked)}
                  >
                    我确认上述未映射信息保留在原件与报告中
                  </Checkbox>
                )}
                <div style={{ marginTop: 20 }}>
                  <Button
                    type="primary"
                    disabled={
                      preview.errors.length > 0 ||
                      (!accepted && preview.warnings.length > 0) ||
                      !scope.actions.includes("adopt")
                    }
                    onClick={async () => {
                      try {
                        await api(
                          scoped(scope.id, `/imports/${preview.id}/apply`),
                          "POST",
                          { acknowledge_unmapped: accepted },
                        );
                        message.success("已排入分批导入任务");
                        jobs.refetch();
                      } catch (e) {
                        message.error((e as Error).message);
                      }
                    }}
                  >
                    确认清单并导入
                  </Button>
                </div>
              </div>
            )}
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card title="创建导出">
            <Typography.Paragraph type="secondary">
              固定当前版本及可访问范围。JSON保留结构，CSV用于电子表格查看，Markdown用于阅读。
            </Typography.Paragraph>
            <Space wrap>
              <Select
                value={format}
                onChange={setFormat}
                style={{ width: 160 }}
                options={[
                  { value: "json", label: "JSON 交换包" },
                  { value: "csv", label: "CSV 安全查看" },
                  { value: "markdown", label: "Markdown" },
                ]}
              />
              <Button
                type="primary"
                icon={<DownloadOutlined />}
                disabled={!scope.actions.includes("export")}
                onClick={async () => {
                  try {
                    await api(scoped(scope.id, "/exports"), "POST", { format });
                    message.success("导出任务已建立");
                    jobs.refetch();
                  } catch (e) {
                    message.error((e as Error).message);
                  }
                }}
              >
                生成导出文件
              </Button>
            </Space>
          </Card>
          <Card title="交换任务" style={{ marginTop: 24 }}>
            <List
              dataSource={jobs.data?.filter((x) =>
                ["import", "export"].includes(x.kind),
              )}
              locale={{ emptyText: "暂无交换任务" }}
              renderItem={(job) => (
                <List.Item
                  actions={[
                    job.kind === "export" && job.state === "succeeded" ? (
                      <Button
                        type="link"
                        onClick={() =>
                          download(
                            scope.id,
                            job.result.id,
                            job.result.name,
                          ).catch((e) => message.error(e.message))
                        }
                      >
                        下载
                      </Button>
                    ) : null,
                  ]}
                >
                  <List.Item.Meta
                    title={
                      <Space>
                        {job.kind === "export" ? "导出" : "导入"}
                        <Status value={job.state} />
                      </Space>
                    }
                    description={
                      job.result?.error?.detail ||
                      (job.progress?.total &&
                        `${job.progress.committed} / ${job.progress.total}`) ||
                      "查看任务中心了解阶段与回执"
                    }
                  />
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>
    </>
  );
}

export function QualityPage() {
  const { message } = App.useApp();
  const { scope } = useWorkspace(),
    [detail, setDetail] = useState<string>(),
    [report, setReport] = useState<Json>();
  const quality = useQuery({
    queryKey: ["scope", scope.id, "quality"],
    queryFn: () => api<Json>(scoped(scope.id, "/quality")),
  });
  const scores = useQuery({
    queryKey: ["scope", scope.id, "assessments"],
    queryFn: () => api<Json[]>(scoped(scope.id, "/assessments")),
  });
  return (
    <>
      <PageTitle
        title="质量与评分"
        note="每份报告绑定内容与规则版本。作者偏好独立记录，历史分数不会被改成当前新稿的结论。"
      />
      <Row gutter={24}>
        <Col xs={24} xl={9}>
          <Card title="数据问题与待核实">
            <ErrorPanel error={quality.error} />
            <List
              dataSource={quality.data?.items}
              locale={{
                emptyText: <NoData text="本次检查范围内没有待处理问题" />,
              }}
              renderItem={(issue: Json) => (
                <List.Item
                  actions={[
                    <Button
                      type="link"
                      onClick={() => setDetail(issue.entity_id)}
                    >
                      定位
                    </Button>,
                  ]}
                >
                  <List.Item.Meta
                    title={issue.detail}
                    description={<Tag>{issue.kind}</Tag>}
                  />
                </List.Item>
              )}
            />
            <p className="muted">
              覆盖口径：{quality.data?.coverage || "等待检查"}
              。覆盖不足时不会直接判定伏笔遗忘。
            </p>
          </Card>
        </Col>
        <Col xs={24} xl={15}>
          <Card title="AI内容评分">
            <ErrorPanel error={scores.error} />
            <Table
              rowKey="id"
              dataSource={scores.data}
              loading={scores.isPending}
              pagination={{ pageSize: 12 }}
              columns={[
                { title: "类型", dataIndex: "scheme" },
                {
                  title: "总分",
                  dataIndex: "score",
                  render: (v) => (
                    <b className="score-number">{v ?? "待评分"}</b>
                  ),
                },
                {
                  title: "结论",
                  dataIndex: "verdict",
                  render: (v) => (
                    <Tag color={v === "qualified" ? "green" : "orange"}>
                      {(
                        {
                          qualified: "达标",
                          revise: "需修改",
                          restructure: "需重构",
                          blocked: "硬伤阻断",
                          incomplete: "依据不足",
                        } as Json
                      )[v] || v}
                    </Tag>
                  ),
                },
                {
                  title: "有效性",
                  dataIndex: "fresh",
                  render: (v) => <Tag>{v ? "当前依据" : "历史 / 待复评"}</Tag>,
                },
                {
                  title: "操作",
                  render: (_, r) => (
                    <Button type="link" onClick={() => setReport(r)}>
                      分项与证据
                    </Button>
                  ),
                },
              ]}
            />
          </Card>
        </Col>
      </Row>
      <EntityDrawer id={detail} onClose={() => setDetail(undefined)} />
      <Drawer
        width={760}
        open={!!report}
        title="评分、依据与反馈"
        onClose={() => setReport(undefined)}
      >
        <Typography.Paragraph>
          {report?.report?.report?.summary}
        </Typography.Paragraph>
        <Space wrap>
          {[
            ["satisfied", "满意"],
            ["usable", "可用"],
            ["dislike", "不喜欢"],
            ["prefer_other", "更喜欢其他版本"],
          ].map(([choice, label]) => (
            <Button
              key={choice}
              onClick={async () => {
                try {
                  await api(
                    scoped(scope.id, `/assessments/${report?.id}/feedback`),
                    "POST",
                    { choice, note: "" },
                  );
                  message.success("偏好已单独记录，原分数保留");
                } catch (e) {
                  message.error((e as Error).message);
                }
              }}
            >
              {label}
            </Button>
          ))}
        </Space>
        <pre className="json-block">{JSON.stringify(report, null, 2)}</pre>
      </Drawer>
    </>
  );
}

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
