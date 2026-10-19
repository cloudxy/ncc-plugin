import { DownloadOutlined, UploadOutlined } from "@ant-design/icons";
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
  List,
  Row,
  Select,
  Space,
  Statistic,
  Typography,
  Upload,
} from "antd";
import { useState } from "react";
import { api, download, scoped, type Json } from "../../shared/api";
import { NoData, PageTitle, Status } from "../../shared/components/Feedback";
import { useWorkspace } from "../../shared/WorkspaceContext";

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
