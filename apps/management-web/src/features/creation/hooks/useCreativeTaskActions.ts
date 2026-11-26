import { useQuery } from "@tanstack/react-query";
import { App } from "antd";
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type MutableRefObject,
} from "react";
import {
  api,
  scoped,
  type Entity,
  type Json,
  type Scope,
} from "../../../shared/api";
import { queryKeys } from "../../../shared/queryKeys";
import {
  setLastEditedChapter,
  validateStudioStages,
  type BuiltinCommonsAttachment,
  type CrossScopeAttachment,
  type PipelineStage,
  type StudioReturnOrigin,
} from "../../../shared/studioApi";
import { effectDetail } from "../effectDetail";
import {
  chapterCreationJobs,
  currentCreationJob,
  selectedCandidate,
} from "../jobCandidate";

export function useCreativeTaskActions({
  scope,
  entityId,
  entityData,
  baseline,
  currentEntityKind,
  creationPolicyData,
  refetchCreationPolicy,
  marketPlaybookId,
  dirty,
  text,
  name,
  scheme,
  stages,
  objective,
  guidance,
  beatOutline,
  selectionOnly,
  selection,
  sourceIds,
  commonsRefs,
  builtins,
  jobId,
  setJobId,
  returnOrigin,
  phaseRef,
  setPhase,
  setCockpitTab,
  setRightOpen,
  setBeatOpen,
  setDraftStatus,
  syncUrlTarget,
  save,
  resetEditorForTarget,
  refresh,
  refetchEntity,
  refetchOverview,
}: {
  scope: Scope;
  entityId: string | undefined;
  entityData: Entity | undefined;
  baseline: Entity | undefined;
  currentEntityKind: string | undefined;
  creationPolicyData: Json | undefined;
  refetchCreationPolicy: () => void;
  marketPlaybookId: string | undefined;
  dirty: boolean;
  text: string;
  name: string;
  scheme: string;
  stages: PipelineStage[] | null;
  objective: string;
  guidance: string;
  beatOutline: string;
  selectionOnly: boolean;
  selection: [number, number];
  sourceIds: string[];
  commonsRefs: CrossScopeAttachment[];
  builtins: BuiltinCommonsAttachment[];
  jobId: string | undefined;
  setJobId: (id: string | undefined) => void;
  returnOrigin: StudioReturnOrigin | undefined;
  phaseRef: MutableRefObject<"idle" | "save" | "start">;
  setPhase: (phase: "idle" | "save" | "start") => void;
  setCockpitTab: (tab: string) => void;
  setRightOpen: (open: boolean) => void;
  setBeatOpen: (open: boolean) => void;
  setDraftStatus: (status: string) => void;
  syncUrlTarget: (
    nextEntityId: string | undefined,
    nextJobId: string | undefined,
    nextFrom: StudioReturnOrigin | undefined,
  ) => void;
  save: (overrideExpectedVersion?: string) => Promise<string | undefined>;
  resetEditorForTarget: (value?: string, initialName?: string) => void;
  refresh: () => void;
  refetchEntity: () => void;
  refetchOverview: () => void;
}) {
  const { message, modal } = App.useApp();
  const announced = useRef<string | undefined>(undefined);
  const [delegationId, setDelegationId] = useState<string>();
  const [adoptedId, setAdoptedId] = useState<string>();
  const [adopting, setAdopting] = useState(false);
  const [adoptError, setAdoptError] = useState<string>();

  const delegations = useQuery({
    queryKey: queryKeys.delegations(scope.id),
    queryFn: () => api<Json[]>(scoped(scope.id, "/delegations")),
    enabled: scope.actions.includes("adopt"),
    refetchInterval: 10000,
  });

  useEffect(() => {
    setDelegationId(undefined);
  }, [entityId, scheme]);

  const revisionScheme =
    creationPolicyData?.revision_schemes?.[currentEntityKind || "chapter"] ||
    "P3";
  const availableDelegations = (delegations.data || []).filter(
    (item) =>
      !item.revoked &&
      item.remaining > 0 &&
      new Date(item.expires_at).getTime() > Date.now() &&
      item.target_ids.includes(entityId) &&
      item.schemes.includes(scheme) &&
      (scheme !== "P5" || item.schemes.includes(revisionScheme)),
  );

  const jobs = useQuery({
    queryKey: queryKeys.jobsRoot(scope.id),
    queryFn: () => api<Json[]>(scoped(scope.id, "/jobs")),
    refetchInterval: 2500,
  });
  const job = currentCreationJob(jobs.data, jobId, entityId);
  const relatedJobs = useMemo(() => {
    const base = chapterCreationJobs(jobs.data, entityId);
    if (job && !base.some((item) => item.id === job.id)) {
      return [job, ...base];
    }
    return base;
  }, [jobs.data, entityId, job]);
  const candidate = selectedCandidate(job);
  const jobsLoading = jobs.isPending && jobs.data === undefined;
  const jobsOffline = jobs.error instanceof TypeError;

  const hasOutlineForStages = Boolean(
    beatOutline.trim() ||
    text.trim() ||
    (entityId &&
      entityData?.id === entityId &&
      (String(entityData.data?.beat_outline || "").trim() ||
        String(entityData.text || "").trim())),
  );
  const hasCurrentForStages =
    Boolean(entityId) || Boolean(dirty && text.trim());
  const stageError = validateStudioStages(stages, {
    hasOutline: hasOutlineForStages,
    hasCurrent: hasCurrentForStages,
    hasSavedTarget: Boolean(entityId),
    hasDelegation: Boolean(delegationId),
  });

  async function generate() {
    if (!creationPolicyData) {
      message.error("评分方案尚未载入，请稍后重试");
      refetchCreationPolicy();
      return;
    }
    const chosen = delegationId ? null : stages;
    const isJudgeOnly = Boolean(
      chosen && chosen.length === 1 && chosen[0] === "judge",
    );
    const effectiveObjective =
      objective.trim() ||
      (isJudgeOnly
        ? `对「${name.trim() || baseline?.name || "当前章节"}」执行独立质量审评并给出硬伤与维度诊断`
        : "");
    if (!effectiveObjective) {
      message.info("写下一句话，告诉AI这次要完成什么");
      return;
    }
    if (stageError) {
      message.warning(stageError);
      return;
    }
    if (
      delegationId &&
      !availableDelegations.some((item) => item.id === delegationId)
    ) {
      message.error("自动定稿授权已变化，请重新选择或改为人工审核");
      delegations.refetch();
      return;
    }
    if (chosen && chosen.length === 0) return;
    if (selectionOnly && selection[0] === selection[1]) return;
    phaseRef.current = "start";
    setPhase("start");
    try {
      let targetId = entityId;
      const planOnly =
        !!chosen &&
        chosen.every((item) => item === "plan" || item === "judge_plan");
      if (
        dirty &&
        (!targetId || !planOnly) &&
        !(planOnly && !targetId && !text.trim())
      ) {
        targetId = await save();
        if (!targetId) return;
      }
      if (isJudgeOnly && !targetId) {
        message.info("先保存内容，再单独评分");
        return;
      }
      const kinds: Record<string, string> = {
        P1: "chapter",
        P2: "outline",
        P3: "character",
        P4: "source",
        P5: baseline?.kind || "chapter",
      };
      const body: Json = {
        objective: effectiveObjective,
        scheme,
        mode: "create",
        kind: baseline?.kind || kinds[scheme],
        name: name || "创作候选",
        entity_id: targetId || null,
        delegation_id: delegationId || null,
        source_ids: sourceIds,
        selection_start: selectionOnly
          ? Array.from(text.slice(0, selection[0])).length
          : null,
        selection_end: selectionOnly
          ? Array.from(text.slice(0, selection[1])).length
          : null,
        max_revisions: isJudgeOnly ? 0 : 2,
        token_budget: 24000,
        guidance,
        beat_outline: beatOutline,
        commons_refs: commonsRefs.map((item) => ({
          scope_id: item.scope_id,
          entity_id: item.entity_id,
        })),
        builtin_commons_ids: builtins.map((item) => item.id),
      };
      if (chosen && chosen.length) body.stages = chosen;
      if (marketPlaybookId) body.market_playbook_id = marketPlaybookId;
      const created = await api<Json>(
        scoped(scope.id, "/creation-tasks"),
        "POST",
        body,
      );
      setJobId(created.id);
      setCockpitTab("quality");
      setRightOpen(true);
      syncUrlTarget(targetId, created.id, returnOrigin);
      setAdoptedId(undefined);
      jobs.refetch();
      message.success("已进入自动创作流程");
    } catch (error) {
      const detail = effectDetail(error);
      setDraftStatus(detail);
      message.error(detail);
    } finally {
      phaseRef.current = "idle";
      setPhase("idle");
    }
  }

  async function adoptCandidate() {
    if (!job || adopting) return;
    if (!scope.actions.includes("adopt")) return;
    if (job.payload?.mode === "assess") return;
    if (job.state === "applied" || adoptedId === job.id) return;
    const verdict = candidate?.evaluation?.verdict;
    if (verdict === "blocked" || verdict === "incomplete") return;
    const run = async () => {
      setAdopting(true);
      setAdoptError(undefined);
      try {
        const adopted = await api<Json>(
          scoped(scope.id, `/jobs/${job.id}/adopt`),
          "POST",
        );
        setAdoptedId(job.id);
        if (announced.current !== job.id) {
          announced.current = job.id;
          message.success("已采用");
        }
        const createdId =
          typeof adopted?.entity_id === "string"
            ? adopted.entity_id
            : typeof adopted?.impacts?.[0]?.entity_id === "string"
              ? adopted.impacts[0].entity_id
              : undefined;
        if (!entityId && createdId) {
          setLastEditedChapter(scope.id, createdId);
          resetEditorForTarget(createdId);
          if (candidate?.artifact === "plan") setBeatOpen(true);
        }
        refresh();
        refetchEntity();
        refetchOverview();
        jobs.refetch();
      } catch (error) {
        setAdoptError(effectDetail(error));
      } finally {
        setAdopting(false);
      }
    };
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
    await run();
  }

  async function chooseCandidate(index: number) {
    if (!job) return;
    try {
      await api(scoped(scope.id, `/jobs/${job.id}/intervene`), "POST", {
        action: "choose",
        candidate: index,
      });
      jobs.refetch();
    } catch (error) {
      message.error(effectDetail(error));
    }
  }

  return {
    delegationId,
    setDelegationId,
    availableDelegations,
    jobs,
    job,
    relatedJobs,
    candidate,
    jobsLoading,
    jobsOffline,
    stageError,
    adoptedId,
    adopting,
    adoptError,
    setAdoptError,
    generate,
    adoptCandidate,
    chooseCandidate,
  };
}
