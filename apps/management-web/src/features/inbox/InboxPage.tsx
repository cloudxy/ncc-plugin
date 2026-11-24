import { useQuery } from "@tanstack/react-query";
import { Alert, App, Button, Card, Skeleton } from "antd";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api, scoped, type Json } from "../../shared/api";
import { NoData, PageTitle, Status } from "../../shared/components/Feedback";
import { scopeLine } from "../../shared/scopeLabel";
import { buildJobsTaskPath, buildWorkTaskPath } from "../../shared/studioApi";
import { useWorkspace } from "../../shared/WorkspaceContext";
import { effectDetail } from "../creation/effectDetail";
import { selectedCandidate } from "../creation/jobCandidate";
import "./inbox.css";

const TASK_STATES = new Set(["qualified", "waiting", "failed"]);

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

function verdictOf(job: Json) {
  const verdict = selectedCandidate(job)?.evaluation?.verdict;
  return typeof verdict === "string" ? verdict : undefined;
}

function changeMeta(change: Json, version: number) {
  const parts = [`记录版本 ${change.base_version}`, `当前版本 ${version}`];
  if (Array.isArray(change.operations))
    parts.push(`操作数 ${change.operations.length}`);
  return parts.join(" · ");
}

export function InboxPage() {
  const { scope, refresh } = useWorkspace(),
    { message, modal } = App.useApp();
  const lock = useRef<string | null>(null);
  const announced = useRef(new Set<string>());
  const [busy, setBusy] = useState<string>();
  const [rowError, setRowError] = useState<Record<string, string>>({});
  const jobs = useQuery({
    queryKey: ["scope", scope.id, "jobs"],
    queryFn: () => api<Json[]>(scoped(scope.id, "/jobs")),
    retry: false,
    refetchInterval: (query) => (query.state.status === "error" ? false : 3000),
  });
  const changes = useQuery({
    queryKey: ["scope", scope.id, "changes"],
    queryFn: () => api<Json[]>(scoped(scope.id, "/changes")),
    retry: false,
  });
  const jobsLoading = jobs.isPending;
  const changesLoading = changes.isPending;
  const showJobsSkeleton = useDelayed(jobsLoading, 200);
  const showChangesSkeleton = useDelayed(changesLoading, 200);
  const slow = useDelayed(jobsLoading || changesLoading, 10000);
  const canAdopt = scope.actions.includes("adopt");
  const tasks = jobs.isSuccess
    ? (jobs.data ?? []).filter((job) => TASK_STATES.has(job.state))
    : [];
  const pendingChanges = changes.isSuccess
    ? (changes.data ?? []).filter(
        (change) => change.state !== "applied" && change.state !== "withdrawn",
      )
    : [];

  async function postAdopt(path: string, id: string, success: string) {
    if (!canAdopt || lock.current) return;
    lock.current = id;
    setBusy(id);
    setRowError((current) => {
      const next = { ...current };
      delete next[id];
      return next;
    });
    try {
      await api(scoped(scope.id, path), "POST");
      if (!announced.current.has(id)) {
        announced.current.add(id);
        message.success(success);
      }
      refresh();
    } catch (error) {
      setRowError((current) => ({ ...current, [id]: effectDetail(error) }));
    } finally {
      lock.current = null;
      setBusy(undefined);
    }
  }

  function adoptJob(job: Json) {
    const verdict = verdictOf(job);
    if (verdict === "blocked" || verdict === "incomplete") return;
    if (!canAdopt) return;
    const run = () => postAdopt(`/jobs/${job.id}/adopt`, job.id, "已采用");
    if (verdict !== "qualified") {
      modal.confirm({
        title: "采用你选择的版本",
        content:
          "此版本未达到自动质量线。采用会保留原评分及作者选择记录，硬伤和版本检查仍会执行。",
        okText: "仍然采用",
        cancelText: "返回修改",
        autoFocusButton: "cancel",
        onOk: run,
      });
      return;
    }
    void run();
  }

  return (
    <div aria-busy={jobsLoading || changesLoading || undefined}>
      <PageTitle
        title="我的待办"
        note="只汇总需要你选择的结果；内部成功步骤自动继续。"
      />
      <p className="scope-note" data-component="scope-line">
        {scopeLine(scope.name, scope.kind, scope.version)}
      </p>
      {slow && <p>这一页读得比较久。</p>}
      <div className="inbox-columns" data-component="inbox-columns">
        <Card title="创作与任务">
          {showJobsSkeleton && jobsLoading && (
            <Skeleton active title={false} paragraph={{ rows: 3 }} />
          )}
          {jobs.isFetching && !jobsLoading && jobs.isSuccess && (
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
          {jobs.isSuccess && tasks.length === 0 && (
            <NoData text="当前没有需要你决定的任务" />
          )}
          {tasks.map((job) => {
            const cand = selectedCandidate(job);
            const verdict = verdictOf(job);
            const blocked = verdict === "blocked" || verdict === "incomplete";
            const failed = job.state === "failed";
            const showAdopt = !failed && !blocked;
            const name =
              typeof job.payload?.name === "string" && job.payload.name
                ? job.payload.name
                : job.kind;
            const objective =
              typeof job.payload?.objective === "string" &&
              job.payload.objective
                ? job.payload.objective
                : "";
            const candidateCount = Array.isArray(job.result?.candidates)
              ? job.result.candidates.length
              : 0;
            const scoreLabel =
              cand?.evaluation?.score !== undefined &&
              cand?.evaluation?.score !== null
                ? `评分 ${cand.evaluation.score}`
                : "";
            const metaLine = [
              objective ? `目标：${objective}` : "",
              scoreLabel,
              candidateCount > 1 ? `共 ${candidateCount} 版候选` : "",
            ]
              .filter(Boolean)
              .join(" · ");
            const detail =
              (typeof job.result?.error?.detail === "string" &&
                job.result.error.detail) ||
              (typeof job.result?.auto_hold?.detail === "string" &&
                job.result.auto_hold.detail) ||
              "";
            return (
              <article key={job.id} className="todo-row">
                <div>
                  <h3>{name}</h3>
                  <Status value={job.state} />
                  {metaLine && <p>{metaLine}</p>}
                  {failed && detail && <p>{detail}</p>}
                  {blocked && <p>不能采用</p>}
                  {!failed && !blocked && !detail && (
                    <p>查看创作台中的评分、变化和候选，再决定采用或修改。</p>
                  )}
                  {!failed && !blocked && detail && <p>{detail}</p>}
                  {rowError[job.id] && <p>{rowError[job.id]}</p>}
                </div>
                <div className="row-actions">
                  {showAdopt && (
                    <Button
                      type="primary"
                      className="hit-44"
                      disabled={!canAdopt || busy === job.id}
                      onClick={() => adoptJob(job)}
                    >
                      {busy === job.id ? "正在采用" : "采用"}
                    </Button>
                  )}
                  {showAdopt && !canAdopt && (
                    <p className="perm-note">需要采用权限</p>
                  )}
                  {!failed && (
                    <Link
                      className="hit-44"
                      to={buildWorkTaskPath(scope.id, job, "inbox")}
                    >
                      到创作台查看
                    </Link>
                  )}
                  {failed && (
                    <Link
                      className="hit-44"
                      to={buildJobsTaskPath(scope.id, String(job.id), "inbox")}
                    >
                      到任务中心查看
                    </Link>
                  )}
                </div>
              </article>
            );
          })}
        </Card>
        <Card title="资料变更">
          {showChangesSkeleton && changesLoading && (
            <Skeleton active title={false} paragraph={{ rows: 3 }} />
          )}
          {changes.isFetching && !changesLoading && changes.isSuccess && (
            <p className="perm-note">正在重新读取</p>
          )}
          {changes.isError && (
            <Alert
              type="error"
              showIcon
              title={effectDetail(changes.error)}
              action={<Button onClick={() => changes.refetch()}>重试</Button>}
            />
          )}
          {changes.isSuccess && pendingChanges.length === 0 && (
            <NoData text="没有未采用的变更" />
          )}
          {pendingChanges.map((change) => {
            const invalid = change.validation?.valid === false;
            const id = String(change.id);
            return (
              <article key={id} className="todo-row">
                <div>
                  <h3>{change.title}</h3>
                  <Status value={change.state} />
                  <p>{changeMeta(change, scope.version)}</p>
                  {change.validation?.valid === true && <p>预检通过</p>}
                  {invalid && <p>预检未通过。采用已停用。</p>}
                  {rowError[id] && <p>{rowError[id]}</p>}
                </div>
                <div className="row-actions">
                  <Button
                    type="primary"
                    className="hit-44"
                    disabled={!canAdopt || invalid || busy === id}
                    onClick={() => {
                      if (!canAdopt || invalid) return;
                      void postAdopt(
                        `/changes/${change.id}/adopt`,
                        id,
                        "变更已采用",
                      );
                    }}
                  >
                    {busy === id ? "正在采用" : "采用"}
                  </Button>
                  {!canAdopt && <p className="perm-note">需要采用权限</p>}
                </div>
              </article>
            );
          })}
        </Card>
      </div>
    </div>
  );
}
