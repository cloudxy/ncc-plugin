import { DownloadOutlined, UploadOutlined } from "@ant-design/icons";
import { useQuery, useQueryClient } from "@tanstack/react-query";
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
import { useMemo, useState } from "react";
import { api, download, scoped, type Json } from "../../shared/api";
import { normalizeChapterStatus } from "../../shared/chapterStatus";
import { NoData, PageTitle, Status } from "../../shared/components/Feedback";
import { queryKeys } from "../../shared/queryKeys";
import { fetchStudioOverview } from "../../shared/studioApi";
import { useWorkspace } from "../../shared/WorkspaceContext";
import { effectDetail } from "../creation/effectDetail";

const FORMAT_LABELS: Record<string, string> = {
  epub: "EPUB 成稿",
  txt: "TXT 成稿",
  manuscript_md: "合稿 Markdown",
  json: "JSON 交换包",
  csv: "CSV 表格",
  markdown: "资料 Markdown",
};

export function ExchangePage() {
  const { scope } = useWorkspace(),
    { message } = App.useApp(),
    client = useQueryClient(),
    [attachment, setAttachment] = useState<Json>(),
    [preview, setPreview] = useState<Json>(),
    [accepted, setAccepted] = useState(false),
    [busy, setBusy] = useState(false),
    [manuscriptFormat, setManuscriptFormat] = useState("epub"),
    [volumeId, setVolumeId] = useState<string>(),
    [onlyDone, setOnlyDone] = useState(false),
    [author, setAuthor] = useState(""),
    [exportingManuscript, setExportingManuscript] = useState(false),
    [format, setFormat] = useState("json"),
    [exportingArchive, setExportingArchive] = useState(false),
    [form] = Form.useForm();

  const canExport = scope.actions.includes("export");
  const canCheckOperations = scope.actions.some((a) =>
    ["operate", "edit", "assess", "export"].includes(a),
  );

  const overview = useQuery({
    queryKey: queryKeys.studioOverview(scope.id),
    queryFn: () => fetchStudioOverview(scope.id),
  });

  const jobs = useQuery({
    queryKey: queryKeys.jobs(scope.id, { summary: true }),
    queryFn: () => api<Json[]>(scoped(scope.id, "/jobs?summary=true")),
    refetchInterval: 3000,
  });

  const exchangeJobs = useMemo(
    () =>
      (jobs.data || []).filter((x) => ["import", "export"].includes(x.kind)),
    [jobs.data],
  );
  const hasQueuedExchange = exchangeJobs.some((job) => job.state === "queued");

  const operations = useQuery({
    queryKey: queryKeys.operations(scope.id),
    queryFn: () => api<Json>(scoped(scope.id, "/operations")),
    enabled: canCheckOperations && hasQueuedExchange,
    refetchInterval: 10000,
  });
  const workerOffline =
    hasQueuedExchange && operations.data?.worker?.online === false;

  const volumes = overview.data?.volumes || [];
  const chapters = overview.data?.chapters || [];
  const chapterStats = useMemo(() => {
    const scopedChapters = volumeId
      ? chapters.filter((ch) => ch.parent_id === volumeId)
      : chapters;
    const done = scopedChapters.filter(
      (ch) => normalizeChapterStatus(ch.status) === "done",
    );
    return {
      total: scopedChapters.length,
      done: done.length,
      matched: onlyDone ? done.length : scopedChapters.length,
    };
  }, [chapters, volumeId, onlyDone]);

  async function invalidateJobs() {
    await client.invalidateQueries({ queryKey: queryKeys.jobsRoot(scope.id) });
  }

  async function upload(file: File) {
    setBusy(true);
    setPreview(undefined);
    try {
      const body = new FormData();
      body.append("file", file);
      setAttachment(await api(scoped(scope.id, "/attachments"), "POST", body));
      message.success("原件已受管保存");
    } catch (e) {
      message.error(effectDetail(e));
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
      message.error(effectDetail(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageTitle
        title="导入与导出"
        note="原件、映射、预检与回执分开保存。成稿导出仅输出公开正文，数据交换包保留完整结构。"
      />
      {workerOffline && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          title="检测到排队的导入/导出任务，但后台任务 Worker 当前离线"
          description={
            <span>
              队列中的任务暂不会自动执行。请在终端运行 <code>./start.py</code>
              （Windows 运行 <code>python start.py</code>）一键同启 Web 服务与
              Worker。
            </span>
          }
        />
      )}
      <Row gutter={[24, 24]}>
        <Col xs={24} lg={13}>
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
                        await invalidateJobs();
                      } catch (e) {
                        message.error(effectDetail(e));
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
        <Col xs={24} lg={11}>
          <Card title="作品成稿导出">
            <Typography.Paragraph type="secondary" style={{ marginBottom: 12 }}>
              按卷章顺序输出阅读与发布用成稿（EPUB 3 / 纯净 TXT / 合稿
              Markdown），自动剔除修订注记、细纲与全部作者秘密。
            </Typography.Paragraph>
            <Space orientation="vertical" style={{ width: "100%" }} size={10}>
              <Space wrap>
                <Select
                  aria-label="成稿格式"
                  value={manuscriptFormat}
                  onChange={setManuscriptFormat}
                  style={{ width: 220 }}
                  options={[
                    { value: "epub", label: "EPUB 电子书（.epub）" },
                    { value: "txt", label: "纯净排版 TXT（首行缩进）" },
                    { value: "manuscript_md", label: "合稿 Markdown（.md）" },
                  ]}
                />
                <Select
                  aria-label="导出分卷"
                  allowClear
                  placeholder="全书所有章节"
                  value={volumeId}
                  onChange={(value) => setVolumeId(value)}
                  style={{ width: 200 }}
                  options={volumes.map((vol) => ({
                    value: vol.id,
                    label: vol.name,
                  }))}
                />
              </Space>
              <Input
                aria-label="作者署名"
                maxLength={128}
                placeholder="作者署名（可选，写入 EPUB 元数据）"
                value={author}
                onChange={(event) => setAuthor(event.target.value)}
              />
              <div>
                <Checkbox
                  checked={onlyDone}
                  onChange={(event) => setOnlyDone(event.target.checked)}
                >
                  仅导出「已定稿」章节
                </Checkbox>
                <div>
                  <Typography.Text type="secondary">
                    {`当前匹配 ${chapterStats.matched} 章（范围内共 ${chapterStats.total} 章，已定稿 ${chapterStats.done} 章）`}
                  </Typography.Text>
                </div>
              </div>
              <Button
                type="primary"
                icon={<DownloadOutlined />}
                loading={exportingManuscript}
                disabled={!canExport || chapterStats.matched === 0}
                onClick={async () => {
                  setExportingManuscript(true);
                  try {
                    await api(scoped(scope.id, "/exports"), "POST", {
                      format: manuscriptFormat,
                      volume_id: volumeId || null,
                      only_done: onlyDone,
                      author: author.trim(),
                    });
                    message.success("作品成稿导出任务已建立");
                    await invalidateJobs();
                  } catch (e) {
                    message.error(effectDetail(e));
                  } finally {
                    setExportingManuscript(false);
                  }
                }}
              >
                导出作品成稿
              </Button>
            </Space>
          </Card>

          <Card title="数据交换包导出" style={{ marginTop: 16 }}>
            <Typography.Paragraph type="secondary">
              固定当前版本及可访问范围导出结构化资料备份。JSON 保留完整结构，CSV
              便于电子表格查看，Markdown 用于全库资料归档。
            </Typography.Paragraph>
            <Space wrap>
              <Select
                aria-label="交换包格式"
                value={format}
                onChange={setFormat}
                style={{ width: 190 }}
                options={[
                  { value: "json", label: "JSON 交换包" },
                  { value: "csv", label: "CSV 安全查看" },
                  { value: "markdown", label: "资料归档 Markdown" },
                ]}
              />
              <Button
                icon={<DownloadOutlined />}
                loading={exportingArchive}
                disabled={!canExport}
                onClick={async () => {
                  setExportingArchive(true);
                  try {
                    await api(scoped(scope.id, "/exports"), "POST", { format });
                    message.success("导出任务已建立");
                    await invalidateJobs();
                  } catch (e) {
                    message.error(effectDetail(e));
                  } finally {
                    setExportingArchive(false);
                  }
                }}
              >
                生成导出文件
              </Button>
            </Space>
          </Card>

          <Card title="交换任务" style={{ marginTop: 16 }}>
            {exchangeJobs.length === 0 ? (
              <NoData text="当前范围还没有导入或导出任务" />
            ) : (
              <List
                dataSource={exchangeJobs}
                renderItem={(job) => {
                  const fmtKey = String(job.payload?.format || "");
                  const fmtLabel = FORMAT_LABELS[fmtKey] || fmtKey;
                  const errDetail =
                    job.error?.detail || job.result?.error?.detail;
                  return (
                    <List.Item
                      actions={[
                        job.kind === "export" &&
                        job.state === "succeeded" &&
                        job.result?.id ? (
                          <Button
                            type="link"
                            onClick={() =>
                              download(
                                scope.id,
                                job.result.id,
                                job.result.name,
                              ).catch((e) =>
                                message.error((e as Error).message),
                              )
                            }
                          >
                            下载
                          </Button>
                        ) : null,
                      ]}
                    >
                      <List.Item.Meta
                        title={
                          <Space wrap>
                            <span>
                              {job.kind === "export"
                                ? fmtLabel
                                  ? `导出 · ${fmtLabel}`
                                  : "导出"
                                : "导入"}
                            </span>
                            <Status value={job.state} />
                          </Space>
                        }
                        description={
                          errDetail ||
                          job.result?.name ||
                          (job.progress?.total &&
                            `${job.progress.committed ?? 0} / ${job.progress.total}`) ||
                          "查看任务中心了解阶段与回执"
                        }
                      />
                    </List.Item>
                  );
                }}
              />
            )}
          </Card>
        </Col>
      </Row>
    </>
  );
}
