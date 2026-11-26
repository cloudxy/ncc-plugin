import { DownloadOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import {
  Alert,
  App,
  Button,
  Checkbox,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Typography,
} from "antd";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, download, scoped, type Json } from "../../shared/api";
import { normalizeChapterStatus } from "../../shared/chapterStatus";
import { Status } from "../../shared/components/Feedback";
import { queryKeys } from "../../shared/queryKeys";
import {
  buildJobsTaskPath,
  type StudioChapter,
  type StudioVolume,
} from "../../shared/studioApi";
import { useWorkspace } from "../../shared/WorkspaceContext";
import { effectDetail } from "../creation/effectDetail";

const MANUSCRIPT_FORMATS = [
  { value: "epub", label: "EPUB 电子书（.epub）" },
  { value: "txt", label: "纯净排版 TXT（首行全角缩进）" },
  { value: "manuscript_md", label: "合稿 Markdown（纯净正文 .md）" },
];

export function QuickExportModal({
  open,
  onClose,
  volumes = [],
  chapters = [],
  origin = "work",
}: {
  open: boolean;
  onClose: () => void;
  volumes?: StudioVolume[];
  chapters?: StudioChapter[];
  origin?: "work" | "blueprint";
}) {
  const { scope } = useWorkspace();
  const { message } = App.useApp();
  const navigate = useNavigate();
  const [format, setFormat] = useState("epub");
  const [volumeId, setVolumeId] = useState<string>();
  const [onlyDone, setOnlyDone] = useState(false);
  const [author, setAuthor] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [createdJobId, setCreatedJobId] = useState<string>();
  const [submitError, setSubmitError] = useState("");

  const canExport = scope.actions.includes("export");
  const canCheckOps = scope.actions.some((a) =>
    ["operate", "edit", "assess", "export"].includes(a),
  );

  const chapterStats = useMemo(() => {
    const inVolume = volumeId
      ? chapters.filter((ch) => ch.parent_id === volumeId)
      : chapters;
    const done = inVolume.filter(
      (ch) => normalizeChapterStatus(ch.status) === "done",
    );
    return {
      total: inVolume.length,
      done: done.length,
      matched: onlyDone ? done.length : inVolume.length,
    };
  }, [chapters, volumeId, onlyDone]);

  const trackedJob = useQuery({
    queryKey: ["scope", scope.id, "jobs", "quick-export", createdJobId],
    enabled: open && Boolean(createdJobId),
    queryFn: () => api<Json>(scoped(scope.id, `/jobs/${createdJobId}`)),
    refetchInterval: (query) => {
      const state = query.state.data?.state;
      return state === "queued" || state === "running" ? 1500 : false;
    },
  });

  const jobQueued = trackedJob.data?.state === "queued";
  const operations = useQuery({
    queryKey: queryKeys.operations(scope.id),
    enabled: open && jobQueued && canCheckOps,
    queryFn: () => api<Json>(scoped(scope.id, "/operations")),
    refetchInterval: 8000,
  });
  const workerOffline = jobQueued && operations.data?.worker?.online === false;

  async function handleExport() {
    if (!canExport) return;
    setSubmitting(true);
    setSubmitError("");
    try {
      const created = await api<Json>(scoped(scope.id, "/exports"), "POST", {
        format,
        volume_id: volumeId || null,
        only_done: onlyDone,
        author: author.trim(),
      });
      setCreatedJobId(String(created.id));
      message.success("成稿导出任务已建立");
    } catch (error) {
      setSubmitError(effectDetail(error));
    } finally {
      setSubmitting(false);
    }
  }

  const jobData = trackedJob.data;
  const result = jobData?.result || {};

  return (
    <Modal
      title="导出作品成稿"
      open={open}
      onCancel={() => {
        setSubmitError("");
        onClose();
      }}
      footer={
        <Space wrap>
          <Button onClick={onClose}>关闭</Button>
          {createdJobId && (
            <Button
              onClick={() => {
                onClose();
                navigate(buildJobsTaskPath(scope.id, createdJobId, origin));
              }}
            >
              前往任务中心
            </Button>
          )}
          <Button
            type="primary"
            icon={<DownloadOutlined />}
            disabled={!canExport || chapterStats.matched === 0}
            loading={submitting}
            onClick={() => void handleExport()}
          >
            立即生成成稿
          </Button>
        </Space>
      }
      destroyOnHidden
    >
      <Typography.Paragraph type="secondary" style={{ marginBottom: 12 }}>
        按全书卷章顺序排版纯净正文，自动剔除修订注记、细纲与一切作者秘密设定。
      </Typography.Paragraph>
      {!canExport && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 12 }}
          title="当前账号在此作品范围没有导出权限"
        />
      )}
      {submitError && (
        <Alert
          type="error"
          showIcon
          style={{ marginBottom: 12 }}
          title={submitError}
        />
      )}
      <Form layout="vertical">
        <Form.Item label="导出格式" style={{ marginBottom: 12 }}>
          <Select
            aria-label="成稿导出格式"
            value={format}
            options={MANUSCRIPT_FORMATS}
            onChange={setFormat}
          />
        </Form.Item>
        <Form.Item label="分卷范围" style={{ marginBottom: 12 }}>
          <Select
            aria-label="导出分卷范围"
            allowClear
            placeholder="全书所有分卷与章节"
            value={volumeId}
            options={volumes.map((vol) => ({
              value: vol.id,
              label: vol.name,
            }))}
            onChange={(value) => setVolumeId(value)}
          />
        </Form.Item>
        <Form.Item label="作者署名（可选）" style={{ marginBottom: 12 }}>
          <Input
            aria-label="作者署名"
            maxLength={128}
            placeholder="留空则默认使用作品名署名"
            value={author}
            onChange={(event) => setAuthor(event.target.value)}
          />
        </Form.Item>
        <Form.Item style={{ marginBottom: 8 }}>
          <Checkbox
            checked={onlyDone}
            onChange={(event) => setOnlyDone(event.target.checked)}
          >
            仅导出状态为「已定稿」的章节
          </Checkbox>
          <div style={{ marginTop: 4 }}>
            <Typography.Text type="secondary">
              {`当前范围共 ${chapterStats.total} 章，已定稿 ${chapterStats.done} 章；本次预计导出 ${chapterStats.matched} 章。`}
            </Typography.Text>
          </div>
        </Form.Item>
      </Form>
      {chapterStats.matched === 0 && (
        <Alert
          type="info"
          showIcon
          style={{ marginTop: 8 }}
          title={
            onlyDone
              ? "当前筛选范围内还没有标为「已定稿」的章节，可取消勾选导出草稿或先将章节设为「已定稿」。"
              : "当前筛选范围内还没有可导出的公开章节。"
          }
        />
      )}
      {jobData && (
        <Alert
          style={{ marginTop: 12 }}
          type={
            jobData.state === "succeeded"
              ? "success"
              : jobData.state === "failed"
                ? "error"
                : "info"
          }
          showIcon
          title={
            <Space wrap>
              <span>最近导出任务</span>
              <Status value={jobData.state} />
              {typeof result.chapter_count === "number" && (
                <span>{`共 ${result.chapter_count} 章`}</span>
              )}
              {typeof result.words === "number" && (
                <span>{`汉字 ${result.words}`}</span>
              )}
            </Space>
          }
          description={
            <div>
              {jobData.state === "failed" && (
                <p style={{ margin: "4px 0" }}>
                  {result.error?.detail || "成稿生成失败，请检查任务中心详情。"}
                </p>
              )}
              {workerOffline && (
                <p style={{ margin: "4px 0" }}>
                  检测到后台任务 Worker 当前离线，请在终端运行{" "}
                  <code>./start.py</code> 一键同启 Web 与 Worker。
                </p>
              )}
              {jobData.state === "succeeded" && result.id && (
                <Button
                  type="primary"
                  size="small"
                  icon={<DownloadOutlined />}
                  style={{ marginTop: 6 }}
                  onClick={() =>
                    download(scope.id, result.id, result.name).catch((err) =>
                      message.error((err as Error).message),
                    )
                  }
                >
                  下载 {result.name || "成稿文件"}
                </Button>
              )}
            </div>
          }
        />
      )}
    </Modal>
  );
}
