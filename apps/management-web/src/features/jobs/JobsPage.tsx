import { useQuery } from "@tanstack/react-query";
import { Alert, App, Button, Card, Select, Skeleton, Space } from "antd";
import { Fragment, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ApiError, api, scoped, type Json } from "../../shared/api";
import { NoData, PageTitle, Status } from "../../shared/components/Feedback";
import { stages } from "../../shared/jobStages";
import { queryKeys } from "../../shared/queryKeys";
import { scopeLine } from "../../shared/scopeLabel";
import { buildWorkTaskPath } from "../../shared/studioApi";
import { useDelayed } from "../../shared/useDelayed";
import { useWorkspace } from "../../shared/WorkspaceContext";
import { effectDetail } from "../creation/effectDetail";
import "./jobs.css";

const KINDS: Record<string, string> = {
  creation: "创作任务",
  index: "索引更新",
  import: "批量导入",
  export: "数据导出",
};

const KIND_OPTIONS = [
  { value: "", label: "全部类型" },
  { value: "creation", label: "创作任务" },
  { value: "import", label: "批量导入" },
  { value: "export", label: "数据导出" },
];

const STATE_OPTIONS = [
  { value: "", label: "全部状态" },
  { value: "queued", label: "排队中" },
  { value: "running", label: "处理中" },
  { value: "qualified", label: "达标待采用" },
  { value: "waiting", label: "需要你决定" },
  { value: "paused", label: "已暂停" },
  { value: "succeeded", label: "已完成" },
  { value: "applied", label: "已采用" },
  { value: "failed", label: "执行失败" },
  { value: "cancelled", label: "已取消" },
];

function kindLabel(kind: unknown) {
  if (typeof kind !== "string" || !kind) return "";
  return KINDS[kind] || kind;
}

function jobName(job: Json) {
  const name = job.payload?.name || job.result?.target_name;
  if (typeof name === "string" && name) return name;
  return kindLabel(job.kind) || "任务";
}

function progressText(job: Json) {
  const progress = job.progress;
  if (progress && progress.total != null) {
    const committed =
      progress.committed != null ? String(progress.committed) : "";
    return committed
      ? `${committed} / ${progress.total}`
      : String(progress.total);
  }
  const stage = progress?.stage || job.stage || job.result?.stage;
  if (typeof stage === "string" && stage) return stages[stage] || stage;
  return "";
}

function extractJobError(job: Json): string {
  if (typeof job?.error === "string" && job.error) return job.error;
  if (typeof job?.error?.detail === "string" && job.error.detail)
    return job.error.detail;
  if (typeof job?.result?.error === "string" && job.result.error)
    return job.result.error;
  if (
    typeof job?.result?.error?.detail === "string" &&
    job.result.error.detail
  ) {
    return job.result.error.detail;
  }
  return "";
}

function localTime(value: unknown) {
  if (typeof value !== "string" || !value) return "";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return `${parsed.toLocaleString()} · 本机时区`;
}

export function JobsPage() {
  const { scope } = useWorkspace(),
    { message } = App.useApp(),
    navigate = useNavigate(),
    [searchParams, setSearchParams] = useSearchParams();
  const paramScope = searchParams.get("scope");
  const validParamScope = !paramScope || paramScope === scope.id;
  const targetJobId = validParamScope
    ? searchParams.get("job") || undefined
    : undefined;
  const fromOrigin = validParamScope ? searchParams.get("from") : null;
  const [picked, setPicked] = useState<string | undefined>(targetJobId);
  const [kindFilter, setKindFilter] = useState("");
  const [stateFilter, setStateFilter] = useState("");
  const [busy, setBusy] = useState<string>();
  const [pinned, setPinned] = useState<{ id: string; state: string }>();
  const [actionError, setActionError] = useState<{
    id: string;
    detail: string;
  }>();
  const scopeSeen = useRef(scope.id);
  if (scopeSeen.current !== scope.id) {
    scopeSeen.current = scope.id;
    setPicked(targetJobId);
    setKindFilter("");
    setStateFilter("");
    setPinned(undefined);
    setActionError(undefined);
  }
  useEffect(() => {
    if (targetJobId) setPicked(targetJobId);
  }, [scope.id, targetJobId]);
  function selectJobRow(id: string) {
    setPicked(id);
    const next = new URLSearchParams(searchParams);
    next.set("scope", scope.id);
    next.set("job", id);
    setSearchParams(next, { replace: true });
  }
  const returnAction =
    fromOrigin === "inbox" ? (
      <Button onClick={() => navigate("/inbox")}>返回我的待办</Button>
    ) : fromOrigin === "work" ? (
      <Button onClick={() => navigate(-1)}>返回创作台</Button>
    ) : undefined;
  const jobs = useQuery({
    queryKey: queryKeys.jobs(scope.id, {
      kind: kindFilter || undefined,
      state: stateFilter || undefined,
      summary: true,
    }),
    queryFn: () => {
      const qs = new URLSearchParams({ summary: "true" });
      if (kindFilter) qs.set("kind", kindFilter);
      if (stateFilter) qs.set("state", stateFilter);
      return api<Json[]>(scoped(scope.id, `/jobs?${qs.toString()}`));
    },
    retry: false,
    refetchInterval: (query) => (query.state.status === "error" ? false : 2500),
  });
  const canCheckOperations = scope.actions.some((a) =>
    ["operate", "edit", "assess", "export"].includes(a),
  );
  const operations = useQuery({
    queryKey: queryKeys.operations(scope.id),
    queryFn: () => api<Json>(scoped(scope.id, "/operations")),
    enabled: canCheckOperations,
    refetchInterval: 10000,
  });
  const loading = jobs.isPending;
  const showSkeleton = useDelayed(loading, 200);
  const slow = useDelayed(loading, 10000);
  const rows = jobs.isSuccess ? (jobs.data ?? []) : [];
  const selected =
    rows.find((job) => job.id === picked) || (picked ? undefined : rows[0]);
  const canEdit = scope.actions.includes("edit");
  const canAssess = scope.actions.includes("assess");
  const canExport = scope.actions.includes("export");

  function canReadJobBody(job: Json) {
    return canEdit || canAssess || (job.kind === "export" && canExport);
  }

  function shownState(job: Json) {
    return pinned && pinned.id === job.id ? pinned.state : job.state;
  }

  function canCancelJob(job: Json) {
    if (job.kind === "export") return canExport;
    if (job.kind === "creation") return canEdit || canAssess;
    return canEdit;
  }

  function canRetryJob(job: Json) {
    if (job.kind === "export") return canExport;
    return canEdit;
  }

  async function act(job: Json, action: "cancel" | "resume" | "retry") {
    const allowed =
      action === "cancel"
        ? canCancelJob(job)
        : action === "retry"
          ? canRetryJob(job)
          : canEdit;
    if (!allowed || busy) return;
    const before = shownState(job);
    setBusy(job.id);
    setActionError(undefined);
    try {
      const endpoint =
        action === "cancel"
          ? "cancel"
          : action === "retry"
            ? "retry"
            : "intervene";
      await api(
        scoped(scope.id, `/jobs/${job.id}/${endpoint}`),
        "POST",
        action === "resume" ? { action: "resume" } : {},
      );
      setPinned(undefined);
      await jobs.refetch();
      if (action === "cancel") {
        message.success("已提交的批次保留，取消不撤回。");
      } else if (action === "retry") {
        message.success("任务已重新排入队列");
      }
    } catch (error) {
      if (error instanceof ApiError && error.status === 409)
        setPinned({ id: job.id, state: before });
      setActionError({ id: job.id, detail: effectDetail(error) });
    } finally {
      setBusy(undefined);
    }
  }

  function notes(job: Json, state: string) {
    const lines: string[] = [];
    if (state === "cancelled") lines.push("已提交的批次保留，取消不撤回。");
    const detail = extractJobError(job);
    const readable = canReadJobBody(job);
    if (readable && detail) lines.push(detail);
    if (!readable) lines.push("当前权限不包含任务正文");
    return lines;
  }

  const hasQueuedJobs =
    rows.some((job) => shownState(job) === "queued") ||
    Number(operations.data?.jobs?.queued || 0) > 0;
  const workerOffline = operations.data?.worker?.online === false;
  const hasFilters = Boolean(kindFilter || stateFilter);

  const cap =
    jobs.isSuccess && rows.length === 100
      ? "只显示最近 100 条"
      : jobs.isSuccess
        ? `当前 ${rows.length} 条 · 轻量摘要轮询`
        : "";

  return (
    <div aria-busy={loading || undefined}>
      <PageTitle
        title="任务中心"
        note="进度与回执持久保存。取消会停止后续处理，已提交批次保留记录。"
        actions={returnAction}
      />
      <p className="scope-note" data-component="scope-line">
        {scopeLine(scope.name, scope.kind, scope.version)}
      </p>
      {hasQueuedJobs && workerOffline && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          title="检测到排队任务，但后台任务 Worker 当前离线"
          description={
            <span>
              队列中的任务暂不会自动执行。请在终端运行 <code>./start.py</code>
              （Windows 运行 <code>python start.py</code>）一键同启 Web
              服务与后台 Worker。
            </span>
          }
        />
      )}
      <Space wrap style={{ marginBottom: 12 }}>
        <Select
          aria-label="任务类型"
          value={kindFilter}
          style={{ width: 150 }}
          options={KIND_OPTIONS}
          onChange={setKindFilter}
        />
        <Select
          aria-label="任务状态"
          value={stateFilter}
          style={{ width: 160 }}
          options={STATE_OPTIONS}
          onChange={setStateFilter}
        />
        {hasFilters && (
          <Button
            onClick={() => {
              setKindFilter("");
              setStateFilter("");
            }}
          >
            清除筛选
          </Button>
        )}
        {cap && <span className="cap-note">{cap}</span>}
      </Space>
      {slow && <p>这一页读得比较久。</p>}
      {showSkeleton && loading && (
        <Skeleton active title={false} paragraph={{ rows: 4 }} />
      )}
      {jobs.isFetching && !loading && jobs.isSuccess && (
        <p className="perm-note">正在重新读取</p>
      )}
      {jobs.isError && (
        <Alert
          type="error"
          showIcon
          title={effectDetail(jobs.error)}
          action={<Button onClick={() => jobs.refetch()}>重试</Button>}
        />
      )}
      {jobs.isSuccess && rows.length === 0 && (
        <NoData
          text={hasFilters ? "没有符合筛选条件的任务" : "当前范围没有任务"}
          action={
            hasFilters ? (
              <Button
                onClick={() => {
                  setKindFilter("");
                  setStateFilter("");
                }}
              >
                清除筛选
              </Button>
            ) : undefined
          }
        />
      )}
      {rows.length > 0 && (
        <div className="job-split">
          <Card>
            <table className="plain-table">
              <thead>
                <tr>
                  <th>名称</th>
                  <th>类型</th>
                  <th>状态</th>
                  <th>进度</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((job) => {
                  const state = shownState(job);
                  const cancelable = state === "queued" || state === "running";
                  const resumable =
                    job.kind === "creation" &&
                    (state === "paused" ||
                      state === "failed" ||
                      state === "waiting");
                  const retryable =
                    (job.kind === "export" || job.kind === "import") &&
                    (state === "failed" ||
                      state === "paused" ||
                      state === "waiting" ||
                      state === "cancelled");
                  const allowCancel = canCancelJob(job);
                  const allowRetry = canRetryJob(job);
                  return (
                    <tr
                      key={job.id}
                      tabIndex={0}
                      aria-current={
                        selected?.id === job.id ? "true" : undefined
                      }
                      onClick={() => selectJobRow(String(job.id))}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === " ") {
                          event.preventDefault();
                          selectJobRow(String(job.id));
                        }
                      }}
                    >
                      <td>{jobName(job)}</td>
                      <td>{kindLabel(job.kind)}</td>
                      <td>
                        <Status value={state} />
                      </td>
                      <td>{progressText(job)}</td>
                      <td>
                        <div className="row-actions">
                          {cancelable && (
                            <Button
                              className="hit-44"
                              disabled={!allowCancel || busy === job.id}
                              onClick={(event) => {
                                event.stopPropagation();
                                void act(job, "cancel");
                              }}
                            >
                              取消
                            </Button>
                          )}
                          {resumable && (
                            <Button
                              className="hit-44"
                              disabled={!canEdit || busy === job.id}
                              onClick={(event) => {
                                event.stopPropagation();
                                void act(job, "resume");
                              }}
                            >
                              恢复
                            </Button>
                          )}
                          {retryable && (
                            <Button
                              className="hit-44"
                              disabled={!allowRetry || busy === job.id}
                              onClick={(event) => {
                                event.stopPropagation();
                                void act(job, "retry");
                              }}
                            >
                              重试
                            </Button>
                          )}
                          {((cancelable && !allowCancel) ||
                            (resumable && !canEdit) ||
                            (retryable && !allowRetry)) && (
                            <p className="perm-note">需要对应操作权限</p>
                          )}
                          {job.kind === "creation" && (
                            <Link
                              to={buildWorkTaskPath(scope.id, job, "jobs")}
                              onClick={(event) => event.stopPropagation()}
                            >
                              到创作台查看
                            </Link>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </Card>
          {selected && (
            <Card>
              <JobDetail
                scopeId={scope.id}
                job={selected}
                state={shownState(selected)}
                canEdit={canEdit}
                canCancel={canCancelJob(selected)}
                canRetry={canRetryJob(selected)}
                canReadBody={canReadJobBody(selected)}
                busy={busy === selected.id}
                error={
                  actionError && actionError.id === selected.id
                    ? actionError.detail
                    : undefined
                }
                onCancel={() => void act(selected, "cancel")}
                onResume={() => void act(selected, "resume")}
                onRetry={() => void act(selected, "retry")}
                notes={notes(selected, shownState(selected))}
              />
            </Card>
          )}
        </div>
      )}
    </div>
  );
}

function JobDetail({
  scopeId,
  job,
  state,
  canEdit,
  canCancel,
  canRetry,
  canReadBody,
  busy,
  error,
  onCancel,
  onResume,
  onRetry,
  notes,
}: {
  scopeId: string;
  job: Json;
  state: string;
  canEdit: boolean;
  canCancel: boolean;
  canRetry: boolean;
  canReadBody: boolean;
  busy: boolean;
  error?: string;
  onCancel: () => void;
  onResume: () => void;
  onRetry: () => void;
  notes: string[];
}) {
  const cancelable = state === "queued" || state === "running";
  const resumable =
    job.kind === "creation" &&
    (state === "paused" || state === "failed" || state === "waiting");
  const retryable =
    (job.kind === "export" || job.kind === "import") &&
    (state === "failed" ||
      state === "paused" ||
      state === "waiting" ||
      state === "cancelled");
  const created = localTime(job.created_at);
  const updated = localTime(job.updated_at);
  const progress = progressText(job);
  const objective =
    canReadBody &&
    typeof job.payload?.objective === "string" &&
    job.payload.objective
      ? job.payload.objective
      : "";
  return (
    <div>
      <h2>{jobName(job)}</h2>
      <div data-component="labeled-fields">
        <dl className="labeled-fields">
          <dt>名称</dt>
          <dd>{jobName(job)}</dd>
          {objective && (
            <>
              <dt>目标</dt>
              <dd>{objective}</dd>
            </>
          )}
          <dt>类型</dt>
          <dd>{kindLabel(job.kind)}</dd>
          <dt>状态</dt>
          <dd>
            <Status value={state} />
          </dd>
          {progress && (
            <>
              <dt>进度</dt>
              <dd>{progress}</dd>
            </>
          )}
          {typeof job.attempts === "number" && (
            <>
              <dt>尝试次数</dt>
              <dd>{job.attempts}</dd>
            </>
          )}
          {created && (
            <>
              <dt>建立时间</dt>
              <dd>{created}</dd>
            </>
          )}
          {updated && (
            <>
              <dt>更新时间</dt>
              <dd>{updated}</dd>
            </>
          )}
          {notes.map((line, index) => (
            <Fragment key={`${index}-${line}`}>
              <dt>说明</dt>
              <dd>{line}</dd>
            </Fragment>
          ))}
        </dl>
      </div>
      <div className="row-actions">
        {cancelable && (
          <Button
            className="hit-44"
            disabled={!canCancel || busy}
            onClick={onCancel}
          >
            取消
          </Button>
        )}
        {resumable && (
          <Button
            className="hit-44"
            disabled={!canEdit || busy}
            onClick={onResume}
          >
            恢复
          </Button>
        )}
        {retryable && (
          <Button
            className="hit-44"
            disabled={!canRetry || busy}
            onClick={onRetry}
          >
            重试
          </Button>
        )}
        {job.kind === "creation" && (
          <Link className="hit-44" to={buildWorkTaskPath(scopeId, job, "jobs")}>
            到创作台查看
          </Link>
        )}
      </div>
      {((cancelable && !canCancel) ||
        (resumable && !canEdit) ||
        (retryable && !canRetry)) && (
        <p className="perm-note">需要对应操作权限</p>
      )}
      {!canReadBody && <p>当前权限不包含任务正文</p>}
      {error && <p>{error}</p>}
      <details>
        <summary className="hit-44">原始回执</summary>
        <pre className="json-block">{JSON.stringify(job, null, 2)}</pre>
      </details>
    </div>
  );
}
