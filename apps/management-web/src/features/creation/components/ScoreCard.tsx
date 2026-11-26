import { EditOutlined, PauseOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import { Alert, Button, Card, Tag } from "antd";
import { Fragment, useState } from "react";
import { api, scoped, type Json } from "../../../shared/api";
import { Status } from "../../../shared/components/Feedback";
import { stages } from "../../../shared/jobStages";
import { queryKeys } from "../../../shared/queryKeys";
import { useCreationPolicy } from "../../../shared/useCreationPolicy";
import { useWorkspace } from "../../../shared/WorkspaceContext";
import { effectDetail } from "../effectDetail";
import {
  isFiniteNumber,
  selectedCandidate,
  usageSource,
} from "../jobCandidate";

function dimensionText(value: unknown): string {
  if (!value || typeof value !== "object") return "";
  const dim = value as Json;
  const parts: string[] = [];
  if (dim.score !== undefined && dim.score !== null)
    parts.push(String(dim.score));
  if (typeof dim.reason === "string" && dim.reason)
    parts.push("依据：" + dim.reason);
  if (Array.isArray(dim.evidence)) {
    const quotes = dim.evidence.filter(
      (quote) => typeof quote === "string" && quote,
    );
    if (quotes.length) parts.push("原文：" + quotes.join(" / "));
  }
  return parts.join(" · ");
}

export function ScoreCard({
  job,
  relatedJobs,
  loading,
  loadError,
  offline,
  pending,
  adopted,
  adopting,
  adoptError,
  returnLabel,
  onReturn,
  onSelectJob,
  onAdopt,
  onEdit,
  onChoose,
  onRefresh,
}: {
  job?: Json;
  relatedJobs?: Json[];
  loading: boolean;
  loadError?: string;
  offline: boolean;
  pending: boolean;
  adopted: boolean;
  adopting: boolean;
  adoptError?: string;
  returnLabel?: string;
  onReturn?: () => void;
  onSelectJob?: (jobId: string) => void;
  onAdopt: () => void;
  onEdit: (text: string, artifact: "plan" | "draft") => void;
  onChoose: (index: number) => void;
  onRefresh: () => void;
}) {
  const { scope } = useWorkspace();
  const policy = useCreationPolicy();
  const [pausing, setPausing] = useState(false);
  const [pauseError, setPauseError] = useState<string>();
  const candidate = selectedCandidate(job);
  const report = candidate?.evaluation?.report;
  const secondEval = candidate?.second_evaluation;
  const revisionEval = candidate?.revision_evaluation;
  const running = job?.state === "running" || job?.state === "queued";
  const jobQueued = job?.state === "queued";
  const operations = useQuery({
    queryKey: queryKeys.operations(scope.id),
    queryFn: () => api<Json>(scoped(scope.id, "/operations")),
    enabled:
      jobQueued &&
      scope.actions.some((a) =>
        ["operate", "edit", "assess", "export"].includes(a),
      ),
    refetchInterval: 10000,
  });
  const workerOffline = jobQueued && operations.data?.worker?.online === false;
  const assess = job?.payload?.mode === "assess";
  const verdict = candidate?.evaluation?.verdict;
  const secondVerdict = secondEval?.verdict;
  const revisionVerdict = revisionEval?.verdict;
  const disputed = candidate?.disputed === true;
  const blocked =
    verdict === "blocked" ||
    verdict === "incomplete" ||
    secondVerdict === "blocked" ||
    secondVerdict === "incomplete" ||
    revisionVerdict === "blocked" ||
    revisionVerdict === "incomplete" ||
    disputed;
  const canAdopt = scope.actions.includes("adopt");
  const canPause =
    scope.actions.includes("edit") || scope.actions.includes("assess");
  const hard =
    typeof report?.hard === "string"
      ? report.hard === "pass"
        ? "没有硬伤"
        : "有硬伤"
      : undefined;
  const candidates = Array.isArray(job?.result?.candidates)
    ? job.result.candidates
    : [];
  const selectedIndex =
    typeof job?.result?.selected === "number"
      ? job.result.selected
      : Math.max(candidates.length - 1, 0);
  const revisions =
    isFiniteNumber(job?.progress?.revisions) &&
    isFiniteNumber(job?.payload?.max_revisions)
      ? job.progress.revisions + " / " + job.payload.max_revisions
      : undefined;
  const tokens = isFiniteNumber(job?.progress?.tokens)
    ? job.progress.tokens
    : undefined;
  const source = usageSource(job?.progress?.usage_kind);
  const suggestionSource: unknown[] = Array.isArray(report?.suggestions)
    ? report.suggestions
    : [];
  const suggestions = suggestionSource
    .filter((item): item is string => typeof item === "string" && item !== "")
    .slice(0, 3);
  const scheme = candidate?.scheme || job?.payload?.scheme;
  const profiles = Array.isArray(policy.data?.profiles?.[scheme])
    ? policy.data.profiles[scheme]
    : [];
  const p5Profiles = Array.isArray(policy.data?.profiles?.P5)
    ? policy.data.profiles.P5
    : [];
  const dimensions = Object.entries(report?.dimensions || {});
  const revisionDimensions = Object.entries(
    revisionEval?.report?.dimensions || {},
  );
  const excerpt = typeof candidate?.text === "string" ? candidate.text : "";
  const planCandidate = candidate?.artifact === "plan";
  const showAdopt = !!candidate && !running && !assess && !blocked && !adopted;
  const taskName =
    typeof job?.payload?.name === "string" && job.payload.name
      ? job.payload.name
      : "";
  const taskObjective =
    typeof job?.payload?.objective === "string" && job.payload.objective
      ? job.payload.objective
      : "";
  const siblingTasks = Array.isArray(relatedJobs) ? relatedJobs : [];
  async function pause() {
    if (!job || !canPause || pausing) return;
    setPausing(true);
    setPauseError(undefined);
    try {
      await api(scoped(scope.id, `/jobs/${job.id}/intervene`), "POST", {
        action: "pause",
      });
      onRefresh();
    } catch (error) {
      setPauseError(effectDetail(error));
    } finally {
      setPausing(false);
    }
  }
  return (
    <section
      className="creation-verdict"
      data-component="verdict"
      aria-label="这一版留不留"
    >
      <Card
        className="score-card"
        title="这一版留不留"
        extra={job ? <Status value={job.state} /> : undefined}
      >
        {returnLabel && onReturn ? (
          <div className="creation-actions" style={{ marginBottom: 8 }}>
            <Button size="small" onClick={onReturn}>
              {returnLabel}
            </Button>
          </div>
        ) : null}
        {siblingTasks.length > 1 && onSelectJob ? (
          <div
            className="creation-actions"
            role="group"
            aria-label="同章候选任务"
            style={{ marginBottom: 10, flexWrap: "wrap" }}
          >
            {siblingTasks.map((item, idx) => {
              const itemObjective =
                typeof item.payload?.objective === "string" &&
                item.payload.objective
                  ? item.payload.objective
                  : typeof item.payload?.name === "string" && item.payload.name
                    ? item.payload.name
                    : `任务 ${idx + 1}`;
              const shortLabel =
                itemObjective.length > 12
                  ? `${itemObjective.slice(0, 12)}…`
                  : itemObjective;
              return (
                <Button
                  key={String(item.id)}
                  size="small"
                  title={itemObjective}
                  style={{ maxWidth: "100%" }}
                  type={item.id === job?.id ? "primary" : "default"}
                  onClick={() => onSelectJob(String(item.id))}
                >
                  {`任务 ${idx + 1} · ${shortLabel}`}
                </Button>
              );
            })}
          </div>
        ) : null}
        {loading ? (
          <p>正在读取创作台。还没返回的结果不会写成没有内容。</p>
        ) : loadError ? (
          <div data-component="error-panel">
            <Alert
              type="error"
              showIcon
              title={offline ? "网络连接失败。恢复连接后可重试。" : loadError}
              description={
                offline
                  ? "未提交的正文还在。不会显示草稿已自动保存。"
                  : undefined
              }
              action={
                <Button onClick={onRefresh} type="link">
                  重试
                </Button>
              }
            />
            {!offline && <p className="creation-note">编辑器里的字还在。</p>}
          </div>
        ) : !job && !pending ? (
          <div data-component="empty-state">
            <p>生成后会在这里显示评分与依据</p>
          </div>
        ) : running && job ? (
          <div data-component="labeled-fields">
            {workerOffline && (
              <Alert
                type="warning"
                showIcon
                style={{ marginBottom: 12 }}
                title="当前任务处于排队中，但后台 Worker 离线"
                description="请使用 ./start.py 一键同启 Web 与后台 Worker，否则排队任务不会开始执行。"
              />
            )}
            <dl className="creation-fields">
              {taskName && (
                <>
                  <dt>任务名称</dt>
                  <dd>{taskName}</dd>
                </>
              )}
              {taskObjective && (
                <>
                  <dt>创作目标</dt>
                  <dd>{taskObjective}</dd>
                </>
              )}
              {typeof job.progress?.stage === "string" &&
                job.progress.stage && (
                  <>
                    <dt>阶段</dt>
                    <dd>{stages[job.progress.stage] || job.progress.stage}</dd>
                  </>
                )}
              <dt>对象</dt>
              <dd>这一栏还不是新的候选。左边的草稿不会被盖掉。</dd>
            </dl>
            <div className="creation-actions">
              <Button
                icon={<PauseOutlined />}
                disabled={!canPause || pausing}
                onClick={pause}
              >
                {pausing ? "正在暂停" : "暂停并接管"}
              </Button>
            </div>
            {!canPause && <p className="creation-note">需要编辑权限</p>}
            {pauseError && <p className="creation-note">{pauseError}</p>}
          </div>
        ) : !candidate ? (
          <div data-component="labeled-fields">
            {(taskName || taskObjective) && (
              <dl className="creation-fields">
                {taskName && (
                  <>
                    <dt>任务名称</dt>
                    <dd>{taskName}</dd>
                  </>
                )}
                {taskObjective && (
                  <>
                    <dt>创作目标</dt>
                    <dd>{taskObjective}</dd>
                  </>
                )}
              </dl>
            )}
            {job?.result?.error?.detail ? (
              <Alert type="error" showIcon title={job.result.error.detail} />
            ) : (
              <p>检查与评分完成后显示结果</p>
            )}
          </div>
        ) : (
          <div data-component="labeled-fields">
            <dl className="creation-fields">
              {taskName && (
                <>
                  <dt>任务名称</dt>
                  <dd>{taskName}</dd>
                </>
              )}
              {taskObjective && (
                <>
                  <dt>创作目标</dt>
                  <dd>{taskObjective}</dd>
                </>
              )}
              {candidates.length > 1 && (
                <>
                  <dt>候选版本</dt>
                  <dd>{`第 ${selectedIndex + 1} / ${candidates.length} 版`}</dd>
                </>
              )}
              <dt>对象</dt>
              <dd>当前候选，不是左边的草稿，也不是已采用历史</dd>
              {candidate.evaluation?.score !== undefined &&
                candidate.evaluation?.score !== null && (
                  <>
                    <dt>内容总分</dt>
                    <dd>{String(candidate.evaluation.score)}</dd>
                  </>
                )}
              {secondEval?.score !== undefined &&
                secondEval?.score !== null && (
                  <>
                    <dt>第二评价</dt>
                    <dd>
                      {String(secondEval.score)}
                      {disputed ? " · 分歧待复核" : ""}
                    </dd>
                  </>
                )}
              {revisionEval?.score !== undefined &&
                revisionEval?.score !== null && (
                  <>
                    <dt>P5 修订质量</dt>
                    <dd>{String(revisionEval.score)}</dd>
                  </>
                )}
              {hard && (
                <>
                  <dt>硬伤</dt>
                  <dd>
                    <Tag color={hard === "没有硬伤" ? "green" : "orange"}>
                      {hard}
                    </Tag>
                  </dd>
                </>
              )}
              {revisions && (
                <>
                  <dt>自动修订</dt>
                  <dd>{revisions}</dd>
                </>
              )}
              {tokens !== undefined && (
                <>
                  <dt>用量</dt>
                  <dd>
                    {tokens}
                    {source ? " · " + source : ""}
                  </dd>
                </>
              )}
            </dl>
            {suggestions.map((suggestion, index) => (
              <p className="creation-suggest" key={index}>
                <b>{index + 1}</b>
                <span>{suggestion}</span>
              </p>
            ))}
            {(dimensions.length > 0 ||
              revisionDimensions.length > 0 ||
              excerpt) && (
              <dl className="creation-fields">
                {dimensions.map(([key, value]) => {
                  const label =
                    profiles.find((item: Json) => item.key === key)?.label ||
                    key;
                  return (
                    <Fragment key={key}>
                      <dt>{label}</dt>
                      <dd>{dimensionText(value)}</dd>
                    </Fragment>
                  );
                })}
                {revisionDimensions.map(([key, value]) => {
                  const label =
                    p5Profiles.find((item: Json) => item.key === key)?.label ||
                    key;
                  return (
                    <Fragment key={`p5-${key}`}>
                      <dt>P5 · {label}</dt>
                      <dd>{dimensionText(value)}</dd>
                    </Fragment>
                  );
                })}
                {excerpt && (
                  <>
                    <dt>候选摘录</dt>
                    <dd className="creation-excerpt">{excerpt}</dd>
                  </>
                )}
              </dl>
            )}
            {planCandidate ? (
              <p>细纲候选 · 采用后写入本章细纲，不覆盖现有正文</p>
            ) : null}
            {job?.result?.error?.detail && (
              <Alert type="warning" showIcon title={job.result.error.detail} />
            )}
            <div className="creation-actions">
              <Button
                disabled={candidates.length < 2 || selectedIndex <= 0}
                onClick={() => onChoose(selectedIndex - 1)}
              >
                上一候选
              </Button>
              <Button
                disabled={
                  candidates.length < 2 ||
                  selectedIndex >= candidates.length - 1
                }
                onClick={() => onChoose(selectedIndex + 1)}
              >
                下一候选
              </Button>
            </div>
            <div className="creation-actions">
              {adopted ? (
                <Button type="primary" disabled>
                  已采用
                </Button>
              ) : (
                showAdopt && (
                  <Button
                    type="primary"
                    disabled={!canAdopt || adopting}
                    onClick={onAdopt}
                  >
                    {adopting ? "正在采用" : "采用当前候选"}
                  </Button>
                )
              )}
              <Button
                icon={<EditOutlined />}
                disabled={!excerpt}
                onClick={() =>
                  onEdit(excerpt, planCandidate ? "plan" : "draft")
                }
              >
                放入编辑器继续修改
              </Button>
            </div>
            {adopted && <p className="creation-note">已采用</p>}
            {blocked && <p className="creation-note">不能采用</p>}
            {showAdopt && !canAdopt && (
              <p className="creation-note">需要采用权限</p>
            )}
            {adoptError && <p className="creation-note">{adoptError}</p>}
          </div>
        )}
      </Card>
    </section>
  );
}
