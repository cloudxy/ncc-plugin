import { useQuery } from "@tanstack/react-query";
import { App } from "antd";
import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { adopt, api, scoped, type Entity } from "../../shared/api";
import {
  normalizeChapterStatus,
  type ChapterStatus,
} from "../../shared/chapterStatus";
import type { TextEditorHandle } from "../../shared/components/TextEditor";
import { queryKeys } from "../../shared/queryKeys";
import {
  buildJobsTaskPath,
  countHanChars,
  fetchStudioOverview,
  getLastEditedChapter,
  setLastEditedChapter,
  type BuiltinCommonsAttachment,
  type CrossScopeAttachment,
  type PipelineStage,
  type StudioReturnOrigin,
} from "../../shared/studioApi";
import { useCreationPolicy } from "../../shared/useCreationPolicy";
import { useWorkspace } from "../../shared/WorkspaceContext";
import { QuickExportModal } from "../exchange/QuickExportModal";
import {
  CreativeCockpitPane,
  CreativeMobileDrawers,
  CreativeTopHeader,
} from "./components/CreativeWorkspacePanes";
import { VolumeRail } from "./components/VolumeRail";
import { WritingSheetPane } from "./components/WritingSheetPane";
import "./creation.css";
import { effectDetail } from "./effectDetail";
import { useAuthorDraftSync } from "./hooks/useAuthorDraftSync";
import { useCreativeSessionEffects } from "./hooks/useCreativeSessionEffects";
import { useCreativeTaskActions } from "./hooks/useCreativeTaskActions";
import {
  buildBeatPatch,
  extractEntityChapterFields,
  isChapterKind,
  parseReturnOrigin,
  useNarrow,
  useVolumeChapterActions,
} from "./hooks/useVolumeChapterActions";

export function CreativePage() {
  const creationPolicy = useCreationPolicy();
  const schemeLabels = (creationPolicy.data?.scheme_labels || {}) as Record<
    string,
    string
  >;
  const { scope, refresh, setDirty } = useWorkspace();
  const { message, modal } = App.useApp();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const narrow = useNarrow();

  const paramScope = searchParams.get("scope");
  const validParamScope = !paramScope || paramScope === scope.id;
  const initialEntityId = validParamScope
    ? searchParams.get("entity") || undefined
    : undefined;
  const initialJobId = validParamScope
    ? searchParams.get("job") || undefined
    : undefined;
  const initialFrom = validParamScope
    ? parseReturnOrigin(searchParams.get("from"))
    : undefined;
  const rememberedOnMount =
    !initialEntityId && !initialJobId
      ? getLastEditedChapter(scope.id)
      : undefined;

  const appliedQuerySig = useRef(searchParams.toString());
  const userClearedToNew = useRef(false);
  const editorRef = useRef<TextEditorHandle>(null);
  const saveRef = useRef<() => void>(() => {});
  const phaseRef = useRef<"idle" | "save" | "start">("idle");

  const [sourceIds, setSourceIds] = useState<string[]>([]);
  const [sourceTitles, setSourceTitles] = useState<Record<string, string>>({});
  const [builtins, setBuiltins] = useState<BuiltinCommonsAttachment[]>([]);
  const [commonsRefs, setCommonsRefs] = useState<CrossScopeAttachment[]>([]);
  const [selection, setSelection] = useState<[number, number]>([0, 0]);
  const [entityId, setEntityId] = useState<string | undefined>(
    initialEntityId || rememberedOnMount,
  );
  const [text, setText] = useState("");
  const [baseline, setBaseline] = useState<Entity>();
  const [dirty, dirtyLocal] = useState(false);
  const [name, setName] = useState("");
  const [chapterStatus, setChapterStatus] = useState<ChapterStatus>("draft");
  const [objective, setObjective] = useState("");
  const [guidance, setGuidance] = useState("");
  const [scheme, setScheme] = useState("P1");
  const [stages, setStages] = useState<PipelineStage[] | null>(null);
  const [selectionOnly, setSelectionOnly] = useState(false);
  const [beatOutline, setBeatOutline] = useState("");
  const [hook, setHook] = useState("");
  const [pov, setPov] = useState("");
  const [plotline, setPlotline] = useState("");
  const [targetWords, setTargetWords] = useState("");
  const [keyChapter, setKeyChapter] = useState(false);
  const [phase, setPhase] = useState<"idle" | "save" | "start">("idle");
  const [jobId, setJobId] = useState<string | undefined>(initialJobId);
  const [returnOrigin, setReturnOrigin] = useState<
    StudioReturnOrigin | undefined
  >(initialFrom);
  const [viewRole, setViewRole] = useState<"author" | "reader">("author");
  const [exportOpen, setExportOpen] = useState(false);
  const [focus, setFocus] = useState(false);
  const [beatOpen, setBeatOpen] = useState(false);
  const [cockpitTab, setCockpitTab] = useState(initialJobId ? "quality" : "ai");
  const wideEnough = () => !window.matchMedia("(max-width: 1100px)").matches;
  const [leftOpen, setLeftOpen] = useState(wideEnough);
  const [rightOpen, setRightOpen] = useState(
    () => Boolean(initialJobId) || wideEnough(),
  );
  const canEdit = scope.actions.includes("edit");

  const overview = useQuery({
    queryKey: queryKeys.studioOverview(scope.id),
    queryFn: () => fetchStudioOverview(scope.id),
    staleTime: 0,
    refetchOnMount: "always",
  });

  const entity = useQuery({
    queryKey: queryKeys.entity(scope.id, entityId),
    queryFn: () => api<Entity>(scoped(scope.id, `/entities/${entityId}`)),
    enabled: !!entityId,
    staleTime: 0,
    refetchOnMount: "always",
  });

  const currentEntityKind = entity.data?.kind || baseline?.kind;
  const isNonChapterTarget = Boolean(
    entityId && currentEntityKind && !isChapterKind(currentEntityKind),
  );
  const canUseReaderView = Boolean(
    entityId &&
    !isNonChapterTarget &&
    overview.data?.chapters.some((ch) => ch.id === entityId),
  );
  const effectiveViewRole: "author" | "reader" =
    viewRole === "reader" && canUseReaderView ? "reader" : "author";

  useEffect(() => {
    if (viewRole === "reader" && !entityId) {
      setViewRole("author");
    }
  }, [viewRole, entityId]);

  const readerOverview = useQuery({
    queryKey: queryKeys.studioOverview(scope.id, "reader", entityId),
    queryFn: () =>
      fetchStudioOverview(scope.id, { role: "reader", chapterId: entityId }),
    enabled: effectiveViewRole === "reader" && Boolean(entityId),
    staleTime: 0,
    refetchOnMount: "always",
  });

  const activeOverviewData =
    effectiveViewRole === "reader"
      ? readerOverview.data || overview.data
      : overview.data;

  const {
    draftStatus,
    setDraftStatus,
    draftBaseline,
    touchedFields,
    restoredFromDraft,
    editGeneration,
    draftQueue,
    markDirty,
    flushPendingDraft,
    resetDraftTracking,
    clearServerDraft,
  } = useAuthorDraftSync({
    scopeId: scope.id,
    entityId,
    entityData: entity.data,
    baseline,
    isNonChapterTarget,
    phase,
    dirty,
    setDirtyLocal: dirtyLocal,
    setDirtyGlobal: setDirty,
    fields: {
      text,
      name,
      scheme,
      chapterStatus,
      beatOutline,
      hook,
      pov,
      plotline,
      targetWords,
      keyChapter,
    },
    onRestoreDraft: (draft) => {
      setText(typeof draft.text === "string" ? draft.text : "");
      setName(typeof draft.name === "string" ? draft.name : "");
      if (typeof draft.scheme === "string" && draft.scheme) {
        setScheme(draft.scheme);
      }
      if (draft.has_draft === true) {
        if (typeof draft.chapter_status === "string" && draft.chapter_status) {
          setChapterStatus(normalizeChapterStatus(draft.chapter_status));
        }
        const nextBeat =
          typeof draft.beat_outline === "string" ? draft.beat_outline : "";
        const nextHook = typeof draft.hook === "string" ? draft.hook : "";
        const nextPov = typeof draft.pov === "string" ? draft.pov : "";
        const nextPlotline =
          typeof draft.plotline === "string" ? draft.plotline : "";
        const nextTargetWords =
          typeof draft.target_words === "string" ? draft.target_words : "";
        const nextKeyChapter = draft.key_chapter === true;
        setBeatOutline(nextBeat);
        setHook(nextHook);
        setPov(nextPov);
        setPlotline(nextPlotline);
        setTargetWords(nextTargetWords);
        setKeyChapter(nextKeyChapter);
        if (
          nextBeat ||
          nextHook ||
          nextPov ||
          nextPlotline ||
          nextTargetWords ||
          nextKeyChapter
        ) {
          setBeatOpen(true);
        }
      }
    },
  });

  function syncUrlTarget(
    nextEntityId: string | undefined,
    nextJobId: string | undefined,
    nextFrom: StudioReturnOrigin | undefined,
  ) {
    const params = new URLSearchParams();
    if (nextEntityId || nextJobId || nextFrom) {
      params.set("scope", scope.id);
    }
    if (nextEntityId) params.set("entity", nextEntityId);
    if (nextJobId) params.set("job", nextJobId);
    if (nextFrom) params.set("from", nextFrom);
    const sig = params.toString();
    appliedQuerySig.current = sig;
    if (sig !== searchParams.toString()) {
      setSearchParams(params, { replace: true });
    }
  }

  function clearTargetFieldsWithoutUrlSync(
    targetEntity: string | undefined,
    initialName = "",
  ) {
    dirtyLocal(false);
    setDirty(false);
    setBaseline(undefined);
    resetDraftTracking();
    setAdoptError(undefined);
    setEntityId(targetEntity);
    setText("");
    setName(initialName);
    setChapterStatus("draft");
    setBeatOutline("");
    setHook("");
    setPov("");
    setPlotline("");
    setTargetWords("");
    setKeyChapter(false);
  }

  function resetEditorForTarget(value?: string, initialName = "") {
    clearTargetFieldsWithoutUrlSync(value, initialName);
    setJobId(undefined);
    syncUrlTarget(value, undefined, returnOrigin);
  }

  async function save(overrideExpectedVersion?: string) {
    const nested = phaseRef.current === "start";
    if (!nested) {
      phaseRef.current = "save";
      setPhase("save");
    }
    try {
      await draftQueue.current;
      const matchedBaseline =
        baseline && baseline.id === entityId ? baseline : undefined;
      const matchedEntity =
        entity.data && entity.data.id === entityId ? entity.data : undefined;
      const original = entityId ? matchedBaseline || matchedEntity : undefined;
      if (entityId && !original) throw new Error("对象尚在读取，请稍后保存");
      const { patch, unset } = buildBeatPatch(
        overrideExpectedVersion && matchedEntity ? matchedEntity : original,
        {
          chapterStatus,
          keyChapter,
          beatOutline,
          hook,
          pov,
          plotline,
          targetWords,
        },
      );
      const looseChapters = (overview.data?.chapters || []).filter(
        (chapter) => !chapter.parent_id,
      );
      const nextPosition =
        looseChapters.reduce(
          (max, chapter) => Math.max(max, chapter.position),
          -1,
        ) + 1;
      const operation = original
        ? {
            op: "update",
            entity_id: original.id,
            expected:
              overrideExpectedVersion ||
              draftBaseline.current ||
              original.version,
            text,
            name: name || original.name,
            ...(Object.keys(patch).length ? { data: patch } : {}),
            ...(unset.length ? { unset } : {}),
          }
        : {
            op: "create",
            entity_id: crypto.randomUUID(),
            kind: "chapter",
            name: name || "新章节",
            text,
            data: { status: chapterStatus, position: nextPosition, ...patch },
          };
      await adopt(scope, [operation], "作者保存修订：" + (name || "新章节"));
      const keptDraft = await clearServerDraft(entityId);
      setEntityId(operation.entity_id);
      syncUrlTarget(operation.entity_id, jobId, returnOrigin);
      resetDraftTracking();
      dirtyLocal(false);
      setDirty(false);
      setBaseline(undefined);
      refresh();
      entity.refetch();
      overview.refetch();
      if (effectiveViewRole === "reader") readerOverview.refetch();
      if (keptDraft) message.info("未清理的草稿已保留供比较");
      message.success("新修订已保存；旧评分将重新检查有效性");
      return operation.entity_id;
    } catch (error) {
      const status = (error as { status?: number })?.status;
      if (status === 409 || status === 412) {
        entity.refetch();
        overview.refetch();
      }
      const detail = effectDetail(error);
      setDraftStatus(detail);
      message.error(detail);
    } finally {
      if (!nested) {
        phaseRef.current = "idle";
        setPhase("idle");
      }
    }
  }

  const {
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
  } = useCreativeTaskActions({
    scope,
    entityId,
    entityData: entity.data,
    baseline,
    currentEntityKind,
    creationPolicyData: creationPolicy.data,
    refetchCreationPolicy: () => void creationPolicy.refetch(),
    marketPlaybookId: overview.data?.market_config.playbook_id,
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
    refetchEntity: () => void entity.refetch(),
    refetchOverview: () => void overview.refetch(),
  });

  saveRef.current = () => {
    if (canEdit && phase === "idle") void save();
  };

  useCreativeSessionEffects({
    scopeId: scope.id,
    searchParams,
    appliedQuerySig,
    userClearedToNew,
    initialEntityId,
    entityId,
    setEntityId,
    jobId,
    setJobId,
    returnOrigin,
    setReturnOrigin,
    overviewSuccess: overview.isSuccess,
    overviewChapters: overview.data?.chapters || [],
    jobsData: jobs.data,
    dirty,
    narrow,
    focus,
    setFocus,
    setLeftOpen,
    setRightOpen,
    setCockpitTab,
    setSourceIds,
    setSourceTitles,
    setBuiltins,
    setCommonsRefs,
    setDirtyGlobal: setDirty,
    saveRef,
    syncUrlTarget,
    resetEditorForTarget,
    clearTargetFieldsWithoutUrlSync,
  });

  useEffect(() => {
    if (!entity.data || entity.data.id !== entityId) return;
    if (!baseline || baseline.id !== entity.data.id) {
      setBaseline(entity.data);
    }
    if (restoredFromDraft.current) return;
    const touched = touchedFields.current;
    if (!dirty) setBaseline(entity.data);
    if (!touched.has("text")) setText(entity.data.text);
    if (!touched.has("name")) setName(entity.data.name);
    if (isChapterKind(entity.data.kind)) {
      const hydrated = extractEntityChapterFields(entity.data.data);
      if (!touched.has("chapter_status"))
        setChapterStatus(hydrated.chapterStatus);
      if (!touched.has("beat_outline")) setBeatOutline(hydrated.beatOutline);
      if (!touched.has("hook")) setHook(hydrated.hook);
      if (!touched.has("pov")) setPov(hydrated.pov);
      if (!touched.has("plotline")) setPlotline(hydrated.plotline);
      if (!touched.has("target_words")) setTargetWords(hydrated.targetWords);
      if (!touched.has("key_chapter")) setKeyChapter(hydrated.keyChapter);
    }
  }, [entity.data, entityId, dirty, baseline]);

  const options = useMemo(() => {
    const items: { value: string; label: string; status?: string }[] = [];
    const seen = new Set<string>();
    for (const chapter of overview.data?.chapters || []) {
      seen.add(chapter.id);
      items.push({
        value: chapter.id,
        label: chapter.name,
        status: chapter.status,
      });
    }
    if (entityId && !seen.has(entityId) && entity.data?.id === entityId) {
      items.push({ value: entity.data.id, label: entity.data.name });
    }
    return items;
  }, [overview.data, entityId, entity.data]);

  const latestChapter = useMemo(() => {
    const list = overview.data?.chapters || [];
    return list.length > 0 ? list[list.length - 1] : undefined;
  }, [overview.data]);

  function update(value: string) {
    setText(value);
    markDirty("text");
  }

  function placeCandidate(value: string, artifact: "plan" | "draft") {
    if (artifact === "plan") {
      setBeatOutline(value);
      setBeatOpen(true);
      markDirty("beat_outline");
      setDraftStatus("未保存修改 · 细纲已放入本章把控 · 保存前不会当成已采用");
      return;
    }
    update(value);
    setDraftStatus("未保存修改 · 已放入当前候选 · 保存前不会当成已采用");
    requestAnimationFrame(() => editorRef.current?.focus());
  }

  function confirmSwitchIfDirty(
    action: () => void | Promise<void>,
  ): Promise<boolean> {
    if (!dirty) {
      return Promise.resolve(action()).then(() => true);
    }
    return new Promise<boolean>((resolve) => {
      modal.confirm({
        title: "离开未保存的编辑？",
        content:
          "当前稿件有尚未保存为正式修订的修改。离开后将切换到目标章节；原章节草稿会保留在原章节下，不会混入新章节。",
        okText: "离开当前章节",
        cancelText: "继续编辑",
        autoFocusButton: "cancel",
        onOk: async () => {
          await flushPendingDraft();
          await action();
          resolve(true);
        },
        onCancel: () => resolve(false),
      });
    });
  }

  function selectTask(nextJobId: string) {
    setJobId(nextJobId);
    setCockpitTab("quality");
    setRightOpen(true);
    syncUrlTarget(entityId, nextJobId, returnOrigin);
  }

  const returnTarget = useMemo(() => {
    if (returnOrigin === "inbox") {
      return { label: "返回我的待办", to: "/inbox" };
    }
    if (returnOrigin === "jobs") {
      return {
        label: "返回任务中心",
        to: jobId ? buildJobsTaskPath(scope.id, jobId, "work") : "/admin/jobs",
      };
    }
    if (returnOrigin === "blueprint") {
      return { label: "返回大纲与暗线", to: "/blueprint" };
    }
    return undefined;
  }, [returnOrigin, jobId, scope.id]);

  function handleReturn() {
    if (!returnTarget) return;
    if (!dirty || editGeneration.current === 0) {
      setDirty(false);
      navigate(returnTarget.to);
      return;
    }
    void confirmSwitchIfDirty(() => {
      setDirty(false);
      navigate(returnTarget.to);
    });
  }

  async function adoptServerLatestEntity() {
    if (!entityId || !entity.data || entity.data.id !== entityId) return;
    await clearServerDraft(entityId);
    const fresh = entity.data;
    const hydrated = extractEntityChapterFields(fresh.data);
    resetDraftTracking();
    dirtyLocal(false);
    setDirty(false);
    setBaseline(fresh);
    setText(fresh.text);
    setName(fresh.name);
    setChapterStatus(hydrated.chapterStatus);
    setBeatOutline(hydrated.beatOutline);
    setHook(hydrated.hook);
    setPov(hydrated.pov);
    setPlotline(hydrated.plotline);
    setTargetWords(hydrated.targetWords);
    setKeyChapter(hydrated.keyChapter);
    setDraftStatus("已采用服务器最新版本");
  }

  function chooseEntity(value?: string) {
    if (value === entityId) return;
    void confirmSwitchIfDirty(() => {
      if (value) {
        userClearedToNew.current = false;
        setLastEditedChapter(scope.id, value);
      } else {
        userClearedToNew.current = true;
        setLastEditedChapter(scope.id, undefined);
      }
      resetEditorForTarget(value);
    });
  }

  const {
    createVolume,
    renameVolume,
    moveVolume,
    archiveVolume,
    createChapter,
    moveChapter,
    moveChapterToVolume,
  } = useVolumeChapterActions({
    scope,
    volumes: overview.data?.volumes || [],
    chapters: overview.data?.chapters || [],
    refresh,
    refetchOverview: () => void overview.refetch(),
    confirmSwitchIfDirty,
    onCreatedChapter: (id, chapterName) => {
      userClearedToNew.current = false;
      resetEditorForTarget(id, chapterName);
    },
  });

  function mountSource(id: string, title: string) {
    setSourceIds((ids) => (ids.includes(id) ? ids : [...ids, id]));
    setSourceTitles((titles) => ({ ...titles, [id]: title }));
  }

  const han = countHanChars(text);
  const target = /^\d+$/.test(targetWords.trim())
    ? Number(targetWords.trim())
    : 0;
  const hanLabel =
    target > 0 ? `汉字 ${han} / 目标 ${target}` : `汉字 ${han} · 未设目标`;
  const pendingResult = !!jobId && !job && !jobsLoading && !jobs.isError;
  const layoutClass = [
    "studio-layout",
    !narrow && leftOpen ? "has-left" : "",
    !narrow && rightOpen ? "has-right" : "",
  ]
    .filter(Boolean)
    .join(" ");

  const rail = (
    <VolumeRail
      volumes={activeOverviewData?.volumes || []}
      chapters={activeOverviewData?.chapters || []}
      loading={
        effectiveViewRole === "reader"
          ? readerOverview.isPending
          : overview.isPending
      }
      error={
        effectiveViewRole === "reader"
          ? readerOverview.isError
          : overview.isError
      }
      currentId={entityId}
      canEdit={canEdit}
      readOnlyPerspective={effectiveViewRole === "reader"}
      onRetry={() =>
        effectiveViewRole === "reader"
          ? readerOverview.refetch()
          : overview.refetch()
      }
      onSelect={chooseEntity}
      onCreateVolume={createVolume}
      onRenameVolume={renameVolume}
      onMoveVolume={moveVolume}
      onArchiveVolume={archiveVolume}
      onCreateChapter={createChapter}
      onMove={moveChapter}
      onMoveChapterToVolume={moveChapterToVolume}
      onToggle={() => setLeftOpen(false)}
    />
  );

  const cockpit = (
    <CreativeCockpitPane
      scheme={scheme}
      schemeLabels={schemeLabels}
      onSchemeChange={(nextScheme) => {
        if (nextScheme === scheme) return;
        setScheme(nextScheme);
        markDirty("scheme");
      }}
      objective={objective}
      onObjectiveChange={setObjective}
      guidance={guidance}
      onGuidanceChange={setGuidance}
      stages={stages}
      stageError={stageError}
      onStagesChange={(value) => {
        setStages(value);
        if (value) setDelegationId(undefined);
      }}
      selectionOnly={selectionOnly}
      onSelectionOnlyChange={setSelectionOnly}
      selectionReady={selection[0] !== selection[1]}
      delegationId={delegationId}
      availableDelegations={availableDelegations}
      onDelegationChange={(value) => {
        setDelegationId(value);
        if (value) setStages(null);
      }}
      sourceIds={sourceIds}
      onSourceIdsChange={setSourceIds}
      builtins={builtins}
      onRemoveBuiltin={(id) =>
        setBuiltins((list) => list.filter((item) => item.id !== id))
      }
      commonsRefs={commonsRefs}
      onRemoveCommons={(id) =>
        setCommonsRefs((list) => list.filter((item) => item.entity_id !== id))
      }
      sourceTitles={sourceTitles}
      onMountSource={mountSource}
      foreshadows={activeOverviewData?.foreshadows || []}
      onOpenBlueprint={() => navigate("/blueprint")}
      phase={phase}
      canEdit={canEdit}
      policyReady={!!creationPolicy.data}
      entityPending={!!entityId && entity.isPending}
      onStart={() => void generate()}
      cockpitTab={cockpitTab}
      onCockpitTabChange={setCockpitTab}
      hasCandidate={!!candidate}
      job={job}
      relatedJobs={relatedJobs}
      jobsError={jobs.isError ? jobs.error : undefined}
      jobsLoading={jobsLoading}
      jobsOffline={jobsOffline}
      pendingResult={pendingResult}
      adopted={!!job && (job.state === "applied" || adoptedId === job.id)}
      adopting={adopting}
      adoptError={adoptError}
      returnLabel={returnTarget?.label}
      onReturn={returnTarget ? handleReturn : undefined}
      onSelectJob={selectTask}
      onAdopt={() => void adoptCandidate()}
      onEditCandidate={placeCandidate}
      onChooseCandidate={(index) => void chooseCandidate(index)}
      onRefreshJobs={() => void jobs.refetch()}
      effectiveViewRole={effectiveViewRole}
      chapterId={entityId}
      onCollapse={() => setRightOpen(false)}
    />
  );

  const activeBaselineVersion = draftBaseline.current || baseline?.version;
  const hasEntityConflict =
    dirty &&
    Boolean(entity.data && entity.data.id === entityId) &&
    Boolean(activeBaselineVersion) &&
    activeBaselineVersion !== entity.data?.version;

  return (
    <>
      <CreativeTopHeader
        returnTarget={returnTarget}
        onReturn={handleReturn}
        effectiveViewRole={effectiveViewRole}
        canUseReaderView={canUseReaderView}
        onViewRoleChange={setViewRole}
        onOpenExport={() => setExportOpen(true)}
      />
      <div className={layoutClass}>
        {!narrow && leftOpen ? rail : null}
        <WritingSheetPane
          narrow={narrow}
          leftOpen={leftOpen}
          rightOpen={rightOpen}
          onOpenLeft={() => setLeftOpen(true)}
          onOpenRight={() => setRightOpen(true)}
          effectiveViewRole={effectiveViewRole}
          onExitReaderView={() => setViewRole("author")}
          entityId={entityId}
          jobId={jobId}
          options={options}
          isNonChapterTarget={isNonChapterTarget}
          phase={phase}
          canEdit={canEdit}
          dirty={dirty}
          hasBaseline={Boolean(baseline)}
          latestChapter={latestChapter}
          onChooseEntity={chooseEntity}
          focus={focus}
          onToggleFocus={() => setFocus((value) => !value)}
          onSave={() => void save()}
          loadError={entity.error || overview.error}
          onRetryLoad={() => {
            if (entity.error) entity.refetch();
            if (overview.error) overview.refetch();
          }}
          currentEntityKind={currentEntityKind}
          onOpenMaterials={() => navigate("/materials")}
          hasEntityConflict={hasEntityConflict}
          serverEntity={entity.data}
          activeBaselineVersion={activeBaselineVersion}
          text={text}
          onTextChange={update}
          onAdoptServerLatest={() => void adoptServerLatestEntity()}
          onSaveOverServerLatest={(ver) => void save(ver)}
          beat={{
            open: beatOpen,
            onOpenChange: setBeatOpen,
            chapterStatus,
            beatOutline,
            hook,
            pov,
            plotline,
            targetWords,
            targetCount: target,
            keyChapter,
            onPatch: (field, val) => {
              if (field === "chapter_status")
                setChapterStatus(val as ChapterStatus);
              else if (field === "beat_outline") setBeatOutline(String(val));
              else if (field === "hook") setHook(String(val));
              else if (field === "pov") setPov(String(val));
              else if (field === "plotline") setPlotline(String(val));
              else if (field === "target_words") setTargetWords(String(val));
              else if (field === "key_chapter") setKeyChapter(Boolean(val));
              markDirty(field);
            },
          }}
          name={name}
          onNameChange={(val) => {
            setName(val);
            markDirty("name");
          }}
          editorRef={editorRef}
          onSelectionChange={(from, to) => setSelection([from, to])}
          draftStatus={draftStatus}
          hanLabel={hanLabel}
          hanCount={han}
        />
        {!narrow && rightOpen ? cockpit : null}
      </div>
      <CreativeMobileDrawers
        narrow={narrow}
        leftOpen={leftOpen}
        onCloseLeft={() => setLeftOpen(false)}
        rightOpen={rightOpen}
        onCloseRight={() => setRightOpen(false)}
        rail={rail}
        cockpit={cockpit}
      />
      <QuickExportModal
        open={exportOpen}
        onClose={() => setExportOpen(false)}
        volumes={overview.data?.volumes || []}
        chapters={overview.data?.chapters || []}
        origin="work"
      />
    </>
  );
}
