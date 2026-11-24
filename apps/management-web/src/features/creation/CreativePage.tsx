import { SaveOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import {
  Alert,
  App,
  Button,
  Card,
  Collapse,
  Drawer,
  Input,
  Select,
  Space,
  Switch,
  Tag,
} from "antd";
import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  adopt,
  api,
  scoped,
  type Entity,
  type Json,
  type Scope,
} from "../../shared/api";
import { ErrorPanel, PageTitle } from "../../shared/components/Feedback";
import {
  TextEditor,
  type TextEditorHandle,
} from "../../shared/components/TextEditor";
import {
  buildJobsTaskPath,
  consumeStudioHandoff,
  countHanChars,
  fetchStudioOverview,
  reorderStudioEntities,
  setStudioHandoff,
  validateStudioStages,
  type BuiltinCommonsAttachment,
  type CrossScopeAttachment,
  type PipelineStage,
  type StudioChapter,
  type StudioReturnOrigin,
} from "../../shared/studioApi";
import { useCreationPolicy } from "../../shared/useCreationPolicy";
import { useWorkspace } from "../../shared/WorkspaceContext";
import { ScoreCard } from "./components/ScoreCard";
import { StudioCockpit } from "./components/StudioCockpit";
import { VolumeRail } from "./components/VolumeRail";
import "./creation.css";
import { effectDetail } from "./effectDetail";
import {
  chapterCreationJobs,
  currentCreationJob,
  selectedCandidate,
} from "./jobCandidate";

function useNarrow() {
  const [matches, setMatches] = useState(
    () => window.matchMedia("(max-width: 1100px)").matches,
  );
  useEffect(() => {
    const media = window.matchMedia("(max-width: 1100px)");
    const apply = () => setMatches(media.matches);
    apply();
    media.addEventListener("change", apply);
    return () => media.removeEventListener("change", apply);
  }, []);
  return matches;
}

function parseReturnOrigin(
  value: string | null,
): StudioReturnOrigin | undefined {
  if (value === "inbox" || value === "jobs" || value === "blueprint") {
    return value;
  }
  return undefined;
}

export function CreativePage() {
  const creationPolicy = useCreationPolicy();
  const schemeLabels = (creationPolicy.data?.scheme_labels || {}) as Record<
    string,
    string
  >;
  const { scope, refresh, setDirty } = useWorkspace(),
    { message, modal } = App.useApp(),
    navigate = useNavigate(),
    [searchParams, setSearchParams] = useSearchParams(),
    narrow = useNarrow();
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
  const appliedQuerySig = useRef(searchParams.toString());
  const draftVersion = useRef(0),
    editGeneration = useRef(0),
    savedGeneration = useRef(0),
    draftBaseline = useRef<string | null>(null),
    draftReady = useRef(false),
    draftKey = useRef(""),
    draftQueue = useRef(Promise.resolve()),
    touchedFields = useRef(new Set<string>()),
    restoredFromDraft = useRef(false);
  const editorRef = useRef<TextEditorHandle>(null);
  const saveRef = useRef<() => void>(() => {});
  const announced = useRef<string | undefined>(undefined);
  const phaseRef = useRef<"idle" | "save" | "start">("idle");
  const [draftLoaded, setDraftLoaded] = useState(false);
  const [draftStatus, setDraftStatus] = useState(""),
    [sourceIds, setSourceIds] = useState<string[]>([]),
    [sourceTitles, setSourceTitles] = useState<Record<string, string>>({}),
    [builtins, setBuiltins] = useState<BuiltinCommonsAttachment[]>([]),
    [commonsRefs, setCommonsRefs] = useState<CrossScopeAttachment[]>([]),
    [selection, setSelection] = useState<[number, number]>([0, 0]);
  const [entityId, setEntityId] = useState<string | undefined>(initialEntityId),
    [text, setText] = useState(""),
    [baseline, setBaseline] = useState<Entity>(),
    [dirty, dirtyLocal] = useState(false);
  const [name, setName] = useState(""),
    [objective, setObjective] = useState(""),
    [guidance, setGuidance] = useState(""),
    [scheme, setScheme] = useState("P1"),
    [stages, setStages] = useState<PipelineStage[] | null>(null),
    [selectionOnly, setSelectionOnly] = useState(false),
    [beatOutline, setBeatOutline] = useState(""),
    [hook, setHook] = useState(""),
    [pov, setPov] = useState(""),
    [plotline, setPlotline] = useState(""),
    [targetWords, setTargetWords] = useState(""),
    [keyChapter, setKeyChapter] = useState(false),
    [phase, setPhase] = useState<"idle" | "save" | "start">("idle"),
    [jobId, setJobId] = useState<string | undefined>(initialJobId),
    [returnOrigin, setReturnOrigin] = useState<StudioReturnOrigin | undefined>(
      initialFrom,
    );
  const [adoptedId, setAdoptedId] = useState<string>();
  const [adopting, setAdopting] = useState(false);
  const [adoptError, setAdoptError] = useState<string>();
  const [delegationId, setDelegationId] = useState<string>();
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
    queryKey: ["scope", scope.id, "studio-overview"],
    queryFn: () => fetchStudioOverview(scope.id),
  });
  const delegations = useQuery({
    queryKey: ["scope", scope.id, "delegations"],
    queryFn: () => api<Json[]>(scoped(scope.id, "/delegations")),
    enabled: scope.actions.includes("adopt"),
    refetchInterval: 10000,
  });
  useEffect(() => {
    setDelegationId(undefined);
  }, [entityId, scheme]);
  const entities = useQuery({
    queryKey: ["scope", scope.id, "writing-entities"],
    queryFn: () =>
      api<Json>(scoped(scope.id, "/entities/search"), "POST", { limit: 200 }),
  });
  const entity = useQuery({
    queryKey: ["scope", scope.id, "entity", entityId],
    queryFn: () => api<Entity>(scoped(scope.id, `/entities/${entityId}`)),
    enabled: !!entityId,
  });
  const revisionScheme =
    creationPolicy.data?.revision_schemes?.[
      entity.data?.kind || baseline?.kind || "chapter"
    ] || "P3";
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
    queryKey: ["scope", scope.id, "jobs"],
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
  useEffect(() => {
    const sig = searchParams.toString();
    if (sig === appliedQuerySig.current) return;
    appliedQuerySig.current = sig;
    const pScope = searchParams.get("scope");
    if (pScope && pScope !== scope.id) return;
    const nextEntity = searchParams.get("entity") || undefined;
    const nextJob = searchParams.get("job") || undefined;
    const nextFrom = parseReturnOrigin(searchParams.get("from"));
    setReturnOrigin(nextFrom);
    if (nextEntity !== entityId) {
      dirtyLocal(false);
      setDirty(false);
      setBaseline(undefined);
      draftBaseline.current = null;
      touchedFields.current.clear();
      restoredFromDraft.current = false;
      editGeneration.current = 0;
      savedGeneration.current = 0;
      setAdoptError(undefined);
      setEntityId(nextEntity);
      setText("");
      setName("");
      setBeatOutline("");
      setHook("");
      setPov("");
      setPlotline("");
      setTargetWords("");
      setKeyChapter(false);
    }
    setJobId(nextJob);
    if (nextJob) {
      setCockpitTab("quality");
      setRightOpen(true);
    }
  }, [searchParams, scope.id, entityId, setDirty]);
  useEffect(() => {
    if (entityId || !jobId || !jobs.data) return;
    const matched = jobs.data.find((item) => item.id === jobId);
    const target =
      typeof matched?.payload?.entity_id === "string" &&
      matched.payload.entity_id
        ? matched.payload.entity_id
        : undefined;
    if (target) {
      setEntityId(target);
      syncUrlTarget(target, jobId, returnOrigin);
    }
  }, [entityId, jobId, jobs.data, returnOrigin]);
  const options = useMemo(() => {
    const labels = new Map<string, string>();
    for (const chapter of overview.data?.chapters || [])
      labels.set(chapter.id, chapter.name);
    for (const item of (entities.data?.items || []) as Entity[])
      labels.set(item.id, item.name);
    return [...labels].map(([value, label]) => ({ value, label }));
  }, [overview.data, entities.data]);
  useEffect(() => {
    const handoff = consumeStudioHandoff(scope.id);
    if (!handoff) return;
    const nextEntity = handoff.chapterId ?? entityId;
    const nextJob = handoff.jobId ?? jobId;
    const nextFrom = handoff.returnTo ?? returnOrigin;
    if (handoff.chapterId) setEntityId(handoff.chapterId);
    if (handoff.jobId) {
      setJobId(handoff.jobId);
      setCockpitTab("quality");
      setRightOpen(true);
    }
    if (handoff.returnTo) setReturnOrigin(handoff.returnTo);
    if (handoff.chapterId || handoff.jobId || handoff.returnTo) {
      syncUrlTarget(nextEntity, nextJob, nextFrom);
    }
    if (handoff.sourceEntity) {
      const source = handoff.sourceEntity;
      setSourceIds((ids) =>
        ids.includes(source.id) ? ids : [...ids, source.id],
      );
      setSourceTitles((titles) => ({ ...titles, [source.id]: source.title }));
    }
    if (handoff.builtinCommons) {
      const card = handoff.builtinCommons;
      setBuiltins((list) =>
        list.some((item) => item.id === card.id) ? list : [...list, card],
      );
    }
    if (handoff.commonsRef) {
      const card = handoff.commonsRef;
      setCommonsRefs((list) =>
        list.some((item) => item.entity_id === card.entity_id)
          ? list
          : [...list, card],
      );
    }
    let settled = false;
    const timer = window.setTimeout(() => {
      settled = true;
    }, 0);
    return () => {
      window.clearTimeout(timer);
      if (!settled) setStudioHandoff(handoff);
    };
  }, [scope.id]);
  useEffect(() => {
    if (narrow && !jobId) {
      setLeftOpen(false);
      setRightOpen(false);
    }
  }, [narrow, jobId]);
  useEffect(() => {
    if (!focus) return;
    document.documentElement.classList.add("studio-focus-mode");
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "Escape" || event.defaultPrevented) return;
      if (document.querySelector("[role='dialog']")) return;
      setFocus(false);
    };
    window.addEventListener("keydown", onKey);
    return () => {
      document.documentElement.classList.remove("studio-focus-mode");
      window.removeEventListener("keydown", onKey);
    };
  }, [focus]);
  useEffect(() => {
    if (!entity.data || entity.data.id !== entityId) return;
    if (!baseline || baseline.id !== entity.data.id) {
      setBaseline(entity.data);
    }
    if (restoredFromDraft.current) return;
    const data = entity.data.data || {};
    const touched = touchedFields.current;
    if (!dirty) setBaseline(entity.data);
    if (!touched.has("text")) setText(entity.data.text);
    if (!touched.has("name")) setName(entity.data.name);
    if (!touched.has("beat_outline")) {
      setBeatOutline(
        typeof data.beat_outline === "string" ? data.beat_outline : "",
      );
    }
    if (!touched.has("hook")) {
      setHook(typeof data.hook === "string" ? data.hook : "");
    }
    if (!touched.has("pov")) {
      setPov(typeof data.pov === "string" ? data.pov : "");
    }
    if (!touched.has("plotline")) {
      setPlotline(typeof data.plotline === "string" ? data.plotline : "");
    }
    if (!touched.has("target_words")) {
      setTargetWords(
        typeof data.target_words === "number" ? String(data.target_words) : "",
      );
    }
    if (!touched.has("key_chapter")) {
      setKeyChapter(data.key_chapter === true);
    }
  }, [entity.data, entityId, dirty, baseline]);
  useEffect(() => () => setDirty(false), []);
  useEffect(() => {
    let live = true;
    draftReady.current = false;
    restoredFromDraft.current = false;
    touchedFields.current.clear();
    setDraftLoaded(false);
    editGeneration.current = 0;
    savedGeneration.current = 0;
    draftVersion.current = 0;
    draftBaseline.current = null;
    draftKey.current = scope.id + ":" + (entityId || "new");
    setDraftStatus("");
    api<Json>(scoped(scope.id, `/author-drafts/${entityId || "new"}`))
      .then((draft) => {
        if (!live) return;
        draftVersion.current = draft.version;
        draftBaseline.current = draft.baseline || null;
        draftReady.current = true;
        setDraftLoaded(true);
        const hasSavedDraft =
          draft.has_draft === true ||
          (typeof draft.text === "string" && draft.text.length > 0);
        if (hasSavedDraft && editGeneration.current === 0) {
          restoredFromDraft.current = true;
          setText(typeof draft.text === "string" ? draft.text : "");
          setName(typeof draft.name === "string" ? draft.name : "");
          if (typeof draft.scheme === "string" && draft.scheme) {
            setScheme(draft.scheme);
          }
          if (draft.has_draft === true) {
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
          dirtyLocal(true);
          setDirty(true);
          setDraftStatus("已恢复自动保存的草稿");
        }
      })
      .catch((error) => {
        if (live) setDraftStatus(effectDetail(error));
      });
    return () => {
      live = false;
    };
  }, [scope.id, entityId]);
  function currentDraftPayload() {
    const pinnedBaseline =
      draftBaseline.current ||
      (baseline?.id === entityId ? baseline?.version : undefined) ||
      (entity.data?.id === entityId ? entity.data?.version : undefined) ||
      null;
    return {
      pinnedBaseline,
      payload: {
        entity_id: entityId || null,
        baseline: pinnedBaseline,
        name,
        text,
        scheme,
        beat_outline: beatOutline,
        hook,
        pov,
        plotline,
        target_words: targetWords,
        key_chapter: keyChapter,
        has_draft: true,
      },
    };
  }
  async function flushPendingDraft(): Promise<void> {
    if (
      !dirty ||
      !draftReady.current ||
      editGeneration.current === 0 ||
      savedGeneration.current >= editGeneration.current
    ) {
      return;
    }
    if (entityId && (!entity.data || entity.data.id !== entityId)) return;
    const targetGeneration = editGeneration.current;
    const key = draftKey.current;
    const targetKey = entityId || "new";
    const { pinnedBaseline, payload } = currentDraftPayload();
    const task = draftQueue.current
      .then(async () => {
        if (key !== draftKey.current) return;
        const draft = await api<Json>(
          scoped(scope.id, `/author-drafts/${targetKey}`),
          "PUT",
          {
            version: draftVersion.current,
            ...payload,
          },
        );
        if (key === draftKey.current) {
          draftVersion.current = draft.version;
          if (!draftBaseline.current && pinnedBaseline) {
            draftBaseline.current = pinnedBaseline;
          }
          savedGeneration.current = Math.max(
            savedGeneration.current,
            targetGeneration,
          );
        }
      })
      .catch(() => {});
    draftQueue.current = task;
    await task;
  }
  useEffect(() => {
    if (!dirty || !draftLoaded || !draftReady.current || phase !== "idle")
      return;
    if (entityId && (!entity.data || entity.data.id !== entityId)) return;
    const targetGeneration = editGeneration.current;
    if (targetGeneration === 0 || savedGeneration.current >= targetGeneration)
      return;
    let live = true;
    const key = draftKey.current;
    const { pinnedBaseline, payload } = currentDraftPayload();
    const timer = setTimeout(() => {
      if (live && editGeneration.current === targetGeneration) {
        setDraftStatus("正在保存草稿");
      }
      draftQueue.current = draftQueue.current
        .then(async () => {
          if (key !== draftKey.current) return;
          const draft = await api<Json>(
            scoped(scope.id, `/author-drafts/${entityId || "new"}`),
            "PUT",
            {
              version: draftVersion.current,
              ...payload,
            },
          );
          if (key === draftKey.current) {
            draftVersion.current = draft.version;
            if (!draftBaseline.current && pinnedBaseline) {
              draftBaseline.current = pinnedBaseline;
            }
            savedGeneration.current = Math.max(
              savedGeneration.current,
              targetGeneration,
            );
            if (live) {
              setDraftStatus(
                editGeneration.current === targetGeneration
                  ? "草稿已自动保存"
                  : "未保存修改 · 仍有变更正在自动保存",
              );
            }
          }
        })
        .catch((error) => {
          if (live) {
            setDraftStatus("自动草稿尚未全部保存：" + effectDetail(error));
          }
        });
    }, 1500);
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, [
    text,
    name,
    scheme,
    beatOutline,
    hook,
    pov,
    plotline,
    targetWords,
    keyChapter,
    dirty,
    entityId,
    phase,
    draftLoaded,
    baseline,
    entity.data,
    scope.id,
  ]);
  function markDirty(field?: string) {
    if (field) touchedFields.current.add(field);
    editGeneration.current += 1;
    dirtyLocal(true);
    setDirty(true);
    setDraftStatus("未保存修改 · 自动保存尚未成功");
  }
  function update(value: string) {
    setText(value);
    markDirty("text");
  }
  function beatPatch(original?: Entity) {
    const patch: Json = { key_chapter: keyChapter };
    const unset: string[] = [];
    const previous = original?.data || {};
    function textField(key: string, value: string) {
      if (value.trim()) patch[key] = value;
      else if (previous[key]) unset.push(key);
    }
    textField("beat_outline", beatOutline);
    textField("hook", hook);
    textField("pov", pov);
    textField("plotline", plotline);
    if (/^\d+$/.test(targetWords.trim()))
      patch.target_words = Number(targetWords.trim());
    else if (previous.target_words !== undefined) unset.push("target_words");
    return { patch, unset };
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
      const { patch, unset } = beatPatch(
        overrideExpectedVersion && matchedEntity ? matchedEntity : original,
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
            data: patch,
            ...(unset.length ? { unset } : {}),
          }
        : {
            op: "create",
            entity_id: crypto.randomUUID(),
            kind: "chapter",
            name: name || "新章节",
            text,
            data: { status: "draft", position: nextPosition, ...patch },
          };
      await adopt(scope, [operation], "作者保存修订：" + (name || "新章节"));
      let keptDraft = false;
      try {
        const cleared = await api<Json>(
          scoped(
            scope.id,
            `/author-drafts/${entityId || "new"}?version=${draftVersion.current}`,
          ),
          "DELETE",
        );
        draftVersion.current =
          typeof cleared?.version === "number" ? cleared.version : 0;
      } catch {
        keptDraft = true;
      }
      setEntityId(operation.entity_id);
      syncUrlTarget(operation.entity_id, jobId, returnOrigin);
      draftBaseline.current = null;
      touchedFields.current.clear();
      restoredFromDraft.current = false;
      editGeneration.current = 0;
      savedGeneration.current = 0;
      dirtyLocal(false);
      setDirty(false);
      setBaseline(undefined);
      refresh();
      entity.refetch();
      overview.refetch();
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
  saveRef.current = () => {
    if (canEdit && phase === "idle") void save();
  };
  useEffect(() => {
    const onSaveShortcut = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "s") {
        event.preventDefault();
        saveRef.current();
      }
    };
    window.addEventListener("keydown", onSaveShortcut);
    return () => window.removeEventListener("keydown", onSaveShortcut);
  }, []);
  const hasOutlineForStages = Boolean(
    beatOutline.trim() ||
    text.trim() ||
    (entityId &&
      entity.data?.id === entityId &&
      (String(entity.data.data?.beat_outline || "").trim() ||
        String(entity.data.text || "").trim())),
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
    if (!creationPolicy.data) {
      message.error("评分方案尚未载入，请稍后重试");
      creationPolicy.refetch();
      return;
    }
    if (!objective.trim()) {
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
    const chosen = delegationId ? null : stages;
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
      if (chosen?.length === 1 && chosen[0] === "judge" && !targetId) {
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
        objective,
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
        max_revisions: chosen?.length === 1 && chosen[0] === "judge" ? 0 : 2,
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
      const playbook = overview.data?.market_config.playbook_id;
      if (playbook) body.market_playbook_id = playbook;
      const created = await api<Json>(
        scoped(scope.id, "/creation-tasks"),
        "POST",
        body,
      );
      setJobId(created.id);
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
          resetEditorForTarget(createdId);
          if (candidate?.artifact === "plan") setBeatOpen(true);
        }
        refresh();
        entity.refetch();
        overview.refetch();
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
  function resetEditorForTarget(value?: string, initialName = "") {
    dirtyLocal(false);
    setDirty(false);
    setBaseline(undefined);
    draftBaseline.current = null;
    touchedFields.current.clear();
    restoredFromDraft.current = false;
    editGeneration.current = 0;
    savedGeneration.current = 0;
    setJobId(undefined);
    setAdoptError(undefined);
    setEntityId(value);
    syncUrlTarget(value, undefined, returnOrigin);
    setText("");
    setName(initialName);
    setBeatOutline("");
    setHook("");
    setPov("");
    setPlotline("");
    setTargetWords("");
    setKeyChapter(false);
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
    try {
      const cleared = await api<Json>(
        scoped(
          scope.id,
          `/author-drafts/${entityId}?version=${draftVersion.current}`,
        ),
        "DELETE",
      );
      draftVersion.current =
        typeof cleared?.version === "number" ? cleared.version : 0;
    } catch {
      // Ignore if no draft existed on server
    }
    const fresh = entity.data;
    const data = fresh.data || {};
    draftBaseline.current = null;
    touchedFields.current.clear();
    restoredFromDraft.current = false;
    editGeneration.current = 0;
    savedGeneration.current = 0;
    dirtyLocal(false);
    setDirty(false);
    setBaseline(fresh);
    setText(fresh.text);
    setName(fresh.name);
    setBeatOutline(
      typeof data.beat_outline === "string" ? data.beat_outline : "",
    );
    setHook(typeof data.hook === "string" ? data.hook : "");
    setPov(typeof data.pov === "string" ? data.pov : "");
    setPlotline(typeof data.plotline === "string" ? data.plotline : "");
    setTargetWords(
      typeof data.target_words === "number" ? String(data.target_words) : "",
    );
    setKeyChapter(data.key_chapter === true);
    setDraftStatus("已采用服务器最新版本");
  }
  function chooseEntity(value?: string) {
    if (value === entityId) return;
    void confirmSwitchIfDirty(() => {
      resetEditorForTarget(value);
    });
  }
  async function createVolume(volumeName: string) {
    try {
      const position = overview.data?.volumes.length || 0;
      await adopt(
        scope,
        [
          {
            op: "create",
            entity_id: crypto.randomUUID(),
            kind: "volume",
            name: volumeName,
            text: "",
            data: { status: "draft", position },
          },
        ],
        "新建卷：" + volumeName,
      );
      refresh();
      overview.refetch();
    } catch (error) {
      message.error(effectDetail(error));
    }
  }
  async function createChapter(
    parentId: string | null,
    chapterName: string,
  ): Promise<boolean> {
    return confirmSwitchIfDirty(async () => {
      try {
        const siblings = (overview.data?.chapters || []).filter(
          (chapter) => (chapter.parent_id || null) === parentId,
        );
        const position =
          siblings.reduce(
            (max, chapter) => Math.max(max, chapter.position),
            -1,
          ) + 1;
        const id = crypto.randomUUID();
        await adopt(
          scope,
          [
            {
              op: "create",
              entity_id: id,
              kind: "chapter",
              name: chapterName,
              text: "",
              data: {
                status: "draft",
                position,
                ...(parentId ? { parent_id: parentId } : {}),
              },
            },
          ],
          "新建章节：" + chapterName,
        );
        resetEditorForTarget(id, chapterName);
        refresh();
        overview.refetch();
      } catch (error) {
        message.error(effectDetail(error));
      }
    });
  }
  async function moveChapter(chapter: StudioChapter, direction: -1 | 1) {
    const siblings = (overview.data?.chapters || [])
      .filter(
        (item) => (item.parent_id || null) === (chapter.parent_id || null),
      )
      .sort((a, b) => a.position - b.position || a.id.localeCompare(b.id));
    const index = siblings.findIndex((item) => item.id === chapter.id);
    const target = index + direction;
    if (index < 0 || target < 0 || target >= siblings.length) return;
    const order = siblings.slice();
    const [row] = order.splice(index, 1);
    order.splice(target, 0, row);
    try {
      const fresh = await api<Scope>(scoped(scope.id, ""));
      await reorderStudioEntities(
        scope.id,
        fresh.version,
        order.map((item, position) => ({ entity_id: item.id, position })),
      );
      refresh();
      overview.refetch();
    } catch (error) {
      message.error(effectDetail(error));
    }
  }
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
      volumes={overview.data?.volumes || []}
      chapters={overview.data?.chapters || []}
      loading={overview.isPending}
      error={overview.isError}
      currentId={entityId}
      canEdit={canEdit}
      onRetry={() => overview.refetch()}
      onSelect={chooseEntity}
      onCreateVolume={createVolume}
      onCreateChapter={createChapter}
      onMove={moveChapter}
      onToggle={() => setLeftOpen(false)}
    />
  );
  const score = (
    <ScoreCard
      job={jobs.isError ? undefined : job}
      relatedJobs={jobs.isError ? undefined : relatedJobs}
      loading={jobsLoading}
      loadError={
        jobs.isError
          ? jobsOffline
            ? "网络连接失败。恢复连接后可重试。"
            : effectDetail(jobs.error)
          : undefined
      }
      offline={jobs.isError && jobsOffline}
      pending={pendingResult}
      adopted={!!job && (job.state === "applied" || adoptedId === job.id)}
      adopting={adopting}
      adoptError={adoptError}
      returnLabel={returnTarget?.label}
      onReturn={returnTarget ? handleReturn : undefined}
      onSelectJob={selectTask}
      onAdopt={adoptCandidate}
      onEdit={placeCandidate}
      onChoose={chooseCandidate}
      onRefresh={() => jobs.refetch()}
    />
  );
  const cockpit = (
    <StudioCockpit
      scheme={scheme}
      schemeOptions={Object.entries(schemeLabels).map(([value, label]) => ({
        value,
        label,
      }))}
      onScheme={(nextScheme) => {
        if (nextScheme === scheme) return;
        setScheme(nextScheme);
        markDirty("scheme");
      }}
      objective={objective}
      onObjective={setObjective}
      guidance={guidance}
      onGuidance={setGuidance}
      stages={stages}
      stageError={stageError}
      onStages={(value) => {
        setStages(value);
        if (value) setDelegationId(undefined);
      }}
      selectionOnly={selectionOnly}
      onSelectionOnly={setSelectionOnly}
      selectionReady={selection[0] !== selection[1]}
      delegationId={delegationId}
      delegations={availableDelegations.map((item) => ({
        id: item.id,
        label: `${item.authorization?.mode === "author_trial" ? "自动定稿试运行 · 校准未验证" : "自动定稿 · 需已校准策略"} · 剩余${item.remaining}次`,
      }))}
      onDelegation={(value) => {
        setDelegationId(value);
        if (value) setStages(null);
      }}
      sourceIds={sourceIds}
      onSourceIds={setSourceIds}
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
      foreshadows={overview.data?.foreshadows || []}
      onOpenBlueprint={() => navigate("/blueprint")}
      phase={phase}
      canEdit={canEdit}
      policyReady={!!creationPolicy.data}
      entityPending={!!entityId && entity.isPending}
      onStart={generate}
      activeTab={cockpitTab}
      onTabChange={setCockpitTab}
      hasCandidate={!!candidate}
      jobRunning={job?.state === "running" || job?.state === "queued"}
      score={score}
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
      <PageTitle
        title="创作台"
        note="说出你想写的内容。准备、检查、评分与返修交给流程。"
        actions={
          <Space>
            {returnTarget ? (
              <Button onClick={handleReturn}>{returnTarget.label}</Button>
            ) : null}
            <Tag color="green">作者可随时接管</Tag>
          </Space>
        }
      />
      <div className={layoutClass}>
        {!narrow && leftOpen ? rail : null}
        <div className="studio-sheet">
          {narrow ? (
            <div className="studio-narrow-tools">
              <Button onClick={() => setLeftOpen(true)}>目录</Button>
              <Button onClick={() => setRightOpen(true)}>工作舱</Button>
            </div>
          ) : null}
          {!narrow && !leftOpen ? (
            <Button onClick={() => setLeftOpen(true)}>展开目录</Button>
          ) : null}
          {!narrow && !rightOpen ? (
            <Button onClick={() => setRightOpen(true)}>展开工作舱</Button>
          ) : null}
          <Card
            className="writing-card"
            title={
              <Space>
                <Select
                  aria-label="编辑对象"
                  allowClear
                  placeholder="选择已有内容，或开始新稿"
                  value={entityId}
                  style={{ width: 196 }}
                  showSearch
                  optionFilterProp="label"
                  options={options}
                  onChange={(value) => chooseEntity(value)}
                />
                <Tag>
                  {dirty ? "未保存修改" : baseline ? "已保存修订" : "新稿"}
                </Tag>
              </Space>
            }
            extra={
              <Space>
                <Button onClick={() => setFocus((value) => !value)}>
                  {focus ? "退出专注" : "进入专注"}
                </Button>
                <Button
                  disabled={!canEdit || phase !== "idle"}
                  icon={<SaveOutlined />}
                  onClick={() => void save()}
                >
                  {phase === "save" ? "正在保存" : "保存修订"}
                </Button>
              </Space>
            }
          >
            <ErrorPanel
              error={entity.error || entities.error}
              retry={() => {
                if (entity.error) entity.refetch();
                if (entities.error) entities.refetch();
              }}
            />
            {!canEdit && <p className="creation-note">当前范围不能编辑</p>}
            {hasEntityConflict && entity.data && (
              <Alert
                type="warning"
                showIcon
                title="这一章在别处更新了。你的字还在编辑器里。"
                description={
                  <div>
                    <p>
                      <b>服务器最新版本（{entity.data.version}）：</b>
                      正文「
                      {(entity.data.text || "").slice(0, 80) || "（空）"}
                      {(entity.data.text || "").length > 80 ? "…" : ""}」
                    </p>
                    <p>
                      <b>你的本地草稿（基于 {activeBaselineVersion}）：</b>
                      正文「{text.slice(0, 80) || "（空）"}
                      {text.length > 80 ? "…" : ""}」
                    </p>
                    <Space wrap>
                      <Button
                        size="small"
                        onClick={() => void adoptServerLatestEntity()}
                      >
                        采用服务器最新版
                      </Button>
                      <Button
                        size="small"
                        type="primary"
                        disabled={!canEdit || phase !== "idle"}
                        onClick={() => void save(entity.data.version)}
                      >
                        基于新版保存我的修改
                      </Button>
                    </Space>
                  </div>
                }
              />
            )}
            <Collapse
              className="studio-beat"
              bordered={false}
              activeKey={beatOpen ? ["beat"] : []}
              onChange={(keys) =>
                setBeatOpen(
                  Array.isArray(keys) ? keys.includes("beat") : keys === "beat",
                )
              }
              items={[
                {
                  key: "beat",
                  label: (
                    <span className="studio-beat-summary">
                      <b>本章把控</b>
                      <small>
                        {[
                          beatOutline.trim() ? "已设细纲" : "细纲未填",
                          hook.trim() ? "已设章尾钩" : null,
                          pov.trim() ? `POV ${pov.trim()}` : null,
                          target > 0 ? `目标 ${target} 字` : null,
                          keyChapter ? "关键章" : null,
                        ]
                          .filter(Boolean)
                          .join(" · ")}
                      </small>
                    </span>
                  ),
                  children: (
                    <div className="studio-beat-grid">
                      <label className="studio-beat-full">
                        <span>本章细纲（起 / 承 / 转 / 合 / 钩）</span>
                        <Input.TextArea
                          aria-label="本章细纲"
                          disabled={phase !== "idle" || !canEdit}
                          placeholder="写下本章核心节拍与冲突推进，AI 起草与审评将严格对齐"
                          value={beatOutline}
                          autoSize={{ minRows: 2, maxRows: 6 }}
                          onChange={(event) => {
                            setBeatOutline(event.target.value);
                            markDirty("beat_outline");
                          }}
                        />
                      </label>
                      <label className="studio-beat-full">
                        <span>章尾追读钩</span>
                        <Input
                          aria-label="章尾追读钩"
                          disabled={phase !== "idle" || !canEdit}
                          placeholder="章末留下的悬念、反转或代价"
                          value={hook}
                          onChange={(event) => {
                            setHook(event.target.value);
                            markDirty("hook");
                          }}
                        />
                      </label>
                      <label>
                        <span>视角人物</span>
                        <Input
                          aria-label="视角人物"
                          disabled={phase !== "idle" || !canEdit}
                          placeholder="本章主视角人物"
                          value={pov}
                          onChange={(event) => {
                            setPov(event.target.value);
                            markDirty("pov");
                          }}
                        />
                      </label>
                      <label>
                        <span>所属剧情线</span>
                        <Input
                          aria-label="所属剧情线"
                          disabled={phase !== "idle" || !canEdit}
                          placeholder="例如：主线·渡口之变"
                          value={plotline}
                          onChange={(event) => {
                            setPlotline(event.target.value);
                            markDirty("plotline");
                          }}
                        />
                      </label>
                      <label>
                        <span>目标字数（汉字）</span>
                        <Input
                          aria-label="目标字数"
                          disabled={phase !== "idle" || !canEdit}
                          placeholder="例如：3000"
                          value={targetWords}
                          inputMode="numeric"
                          onChange={(event) => {
                            setTargetWords(event.target.value);
                            markDirty("target_words");
                          }}
                        />
                      </label>
                      <span className="studio-beat-switch">
                        <Switch
                          aria-label="关键章"
                          disabled={phase !== "idle" || !canEdit}
                          checked={keyChapter}
                          onChange={(value) => {
                            setKeyChapter(value);
                            markDirty("key_chapter");
                          }}
                        />{" "}
                        关键章（重点把控高潮与兑现）
                      </span>
                    </div>
                  ),
                },
              ]}
            />
            <Input
              className="chapter-title"
              aria-label="稿件名称"
              disabled={phase !== "idle" || !canEdit}
              variant="borderless"
              value={name}
              onChange={(event) => {
                setName(event.target.value);
                markDirty("name");
              }}
              placeholder="给这一章或这份内容起个名字"
            />
            <TextEditor
              ref={editorRef}
              value={text}
              readOnly={phase !== "idle" || !canEdit}
              onChange={update}
              onSelection={(from, to) => setSelection([from, to])}
              fitContent
            />
            <div className="editor-footer">
              <span>
                {draftStatus} · {hanLabel}
                {target > 0 && han >= target ? " · 已达到目标" : ""}
              </span>
              <span>正文变动后，旧评分不沿用</span>
            </div>
          </Card>
        </div>
        {!narrow && rightOpen ? cockpit : null}
      </div>
      {narrow && leftOpen ? (
        <Drawer
          title="卷章与细纲目录"
          open
          onClose={() => setLeftOpen(false)}
          size="default"
        >
          {rail}
        </Drawer>
      ) : null}
      {narrow && rightOpen ? (
        <Drawer
          title="出品人工作舱"
          open
          onClose={() => setRightOpen(false)}
          size="large"
        >
          {cockpit}
        </Drawer>
      ) : null}
    </>
  );
}
