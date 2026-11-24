import { useQuery } from "@tanstack/react-query";
import { Alert, App, Button, Card, Skeleton } from "antd";
import { Fragment, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ApiError, api, scoped, type Json } from "../../shared/api";
import { NoData, PageTitle, Status } from "../../shared/components/Feedback";
import { stages } from "../../shared/jobStages";
import { scopeLine } from "../../shared/scopeLabel";
import { buildWorkTaskPath } from "../../shared/studioApi";
import { useWorkspace } from "../../shared/WorkspaceContext";
import { effectDetail } from "../creation/effectDetail";
import "./jobs.css";

const KINDS: Record<string, string> = {
  creation: "创作任务",
  index: "索引更新",
  import: "批量导入",
  export: "数据导出",
};

function useDelayed(active: boolean, delay: number) {
  const [ready, setReady] = useState(false);
  useEffect(() => {
    if (!active) {
      setReady(false);
      return;
    }
    const timer = window.setTimeout(() => setReady(true), delay);
    return () => window.clearTimeout(timer);
  }, [active, delay]);
  return ready;
}

function kindLabel(kind: unknown) {
  if (typeof kind !== "string" || !kind) return "";
  return KINDS[kind] || kind;
}

function jobName(job: Json) {
  const name = job.payload?.name;
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
  const stage = progress?.stage;
  if (typeof stage === "string" && stage) return stages[stage] || stage;
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
    queryKey: ["scope", scope.id, "jobs"],
    queryFn: () => api<Json[]>(scoped(scope.id, "/jobs")),
    retry: false,
    refetchInterval: (query) => (query.state.status === "error" ? false : 2500),
  });
  const loading = jobs.isPending;
  const showSkeleton = useDelayed(loading, 200);
  const slow = useDelayed(loading, 10000);
  const rows = jobs.isSuccess ? (jobs.data ?? []) : [];
  const selected =
    rows.find((job) => job.id === picked) || (picked ? undefined : rows[0]);
  const canEdit = scope.actions.includes("edit");
  const canReadBody =
    scope.actions.includes("edit") || scope.actions.includes("assess");

  function shownState(job: Json) {
    return pinned && pinned.id === job.id ? pinned.state : job.state;
  }

  async function act(job: Json, action: "cancel" | "resume") {
    if (!canEdit || busy) return;
    const before = shownState(job);
    setBusy(job.id);
    setActionError(undefined);
    try {
      await api(
        scoped(
          scope.id,
          `/jobs/${job.id}/${action === "cancel" ? "cancel" : "intervene"}`,
        ),
        "POST",
        action === "cancel" ? {} : { action: "resume" },
      );
      setPinned(undefined);
      await jobs.refetch();
      if (action === "cancel")
        message.success("已提交的批次保留，取消不撤回。");
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
    const detail = job.result?.error?.detail;
    if (canReadBody && typeof detail === "string" && detail) lines.push(detail);
    if (!canReadBody) lines.push("当前权限不包含任务正文");
    return lines;
  }

  const cap =
    jobs.isSuccess && rows.length === 100
      ? "只显示最近 100 条"
      : jobs.isSuccess
        ? `当前 ${rows.length} 条。接口最多返回最近 100 条。`
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
      {cap && <p className="cap-note">{cap}</p>}
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
        <NoData text="当前范围没有任务" />
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
                  return (
                    <tr
                      key={job.id}
                      aria-current={
                        selected?.id === job.id ? "true" : undefined
                      }
                      onClick={() => selectJobRow(String(job.id))}
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
                              disabled={!canEdit || busy === job.id}
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
                          {(cancelable || resumable) && !canEdit && (
                            <p className="perm-note">需要编辑权限</p>
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
                canReadBody={canReadBody}
                busy={busy === selected.id}
                error={
                  actionError && actionError.id === selected.id
                    ? actionError.detail
                    : undefined
                }
                onCancel={() => void act(selected, "cancel")}
                onResume={() => void act(selected, "resume")}
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
  canReadBody,
  busy,
  error,
  onCancel,
  onResume,
  notes,
}: {
  scopeId: string;
  job: Json;
  state: string;
  canEdit: boolean;
  canReadBody: boolean;
  busy: boolean;
  error?: string;
  onCancel: () => void;
  onResume: () => void;
  notes: string[];
}) {
  const cancelable = state === "queued" || state === "running";
  const resumable =
    job.kind === "creation" &&
    (state === "paused" || state === "failed" || state === "waiting");
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
            disabled={!canEdit || busy}
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
        {job.kind === "creation" && (
          <Link className="hit-44" to={buildWorkTaskPath(scopeId, job, "jobs")}>
            到创作台查看
          </Link>
        )}
      </div>
      {(cancelable || resumable) && !canEdit && (
        <p className="perm-note">需要编辑权限</p>
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
