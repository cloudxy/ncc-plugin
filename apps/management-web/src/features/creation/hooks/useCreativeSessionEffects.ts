import {
  useEffect,
  type Dispatch,
  type MutableRefObject,
  type SetStateAction,
} from "react";
import type { Json } from "../../../shared/api";
import {
  consumeStudioHandoff,
  getLastEditedChapter,
  setLastEditedChapter,
  setStudioHandoff,
  type BuiltinCommonsAttachment,
  type CrossScopeAttachment,
  type StudioChapter,
  type StudioReturnOrigin,
} from "../../../shared/studioApi";
import { parseReturnOrigin } from "./useVolumeChapterActions";

export function useCreativeSessionEffects({
  scopeId,
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
  overviewSuccess,
  overviewChapters,
  jobsData,
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
  setDirtyGlobal,
  saveRef,
  syncUrlTarget,
  resetEditorForTarget,
  clearTargetFieldsWithoutUrlSync,
}: {
  scopeId: string;
  searchParams: URLSearchParams;
  appliedQuerySig: MutableRefObject<string>;
  userClearedToNew: MutableRefObject<boolean>;
  initialEntityId: string | undefined;
  entityId: string | undefined;
  setEntityId: (id: string | undefined) => void;
  jobId: string | undefined;
  setJobId: (id: string | undefined) => void;
  returnOrigin: StudioReturnOrigin | undefined;
  setReturnOrigin: (origin: StudioReturnOrigin | undefined) => void;
  overviewSuccess: boolean;
  overviewChapters: StudioChapter[];
  jobsData: Json[] | undefined;
  dirty: boolean;
  narrow: boolean;
  focus: boolean;
  setFocus: (focus: boolean) => void;
  setLeftOpen: (open: boolean) => void;
  setRightOpen: (open: boolean) => void;
  setCockpitTab: (tab: string) => void;
  setSourceIds: Dispatch<SetStateAction<string[]>>;
  setSourceTitles: Dispatch<SetStateAction<Record<string, string>>>;
  setBuiltins: Dispatch<SetStateAction<BuiltinCommonsAttachment[]>>;
  setCommonsRefs: Dispatch<SetStateAction<CrossScopeAttachment[]>>;
  setDirtyGlobal: (dirty: boolean) => void;
  saveRef: MutableRefObject<() => void>;
  syncUrlTarget: (
    nextEntityId: string | undefined,
    nextJobId: string | undefined,
    nextFrom: StudioReturnOrigin | undefined,
  ) => void;
  resetEditorForTarget: (value?: string, initialName?: string) => void;
  clearTargetFieldsWithoutUrlSync: (targetEntity: string | undefined) => void;
}) {
  useEffect(() => {
    if (!overviewSuccess) return;
    const remembered = getLastEditedChapter(scopeId);
    if (
      remembered &&
      entityId === remembered &&
      !initialEntityId &&
      !jobId &&
      !overviewChapters.some((ch) => ch.id === remembered)
    ) {
      setLastEditedChapter(scopeId, undefined);
      if (!dirty) resetEditorForTarget(undefined);
    }
  }, [
    overviewSuccess,
    overviewChapters,
    scopeId,
    entityId,
    initialEntityId,
    jobId,
    dirty,
  ]);

  useEffect(() => {
    const sig = searchParams.toString();
    if (sig === appliedQuerySig.current) return;
    appliedQuerySig.current = sig;
    const pScope = searchParams.get("scope");
    if (pScope && pScope !== scopeId) return;
    const nextEntity = searchParams.get("entity") || undefined;
    const nextJob = searchParams.get("job") || undefined;
    const nextFrom = parseReturnOrigin(searchParams.get("from"));
    setReturnOrigin(nextFrom);
    const targetEntity =
      nextEntity ||
      (!nextJob && !userClearedToNew.current
        ? getLastEditedChapter(scopeId)
        : undefined);
    if (targetEntity !== entityId) {
      clearTargetFieldsWithoutUrlSync(targetEntity);
    }
    setJobId(nextJob);
    if (nextJob) {
      setCockpitTab("quality");
      setRightOpen(true);
    }
  }, [searchParams, scopeId, entityId, setDirtyGlobal]);

  useEffect(() => {
    if (entityId || !jobId || !jobsData) return;
    const matched = jobsData.find((item) => item.id === jobId);
    const target =
      typeof matched?.payload?.entity_id === "string" &&
      matched.payload.entity_id
        ? matched.payload.entity_id
        : undefined;
    if (target) {
      setEntityId(target);
      syncUrlTarget(target, jobId, returnOrigin);
    }
  }, [entityId, jobId, jobsData, returnOrigin]);

  useEffect(() => {
    const handoff = consumeStudioHandoff(scopeId);
    if (!handoff) return;
    const nextEntity =
      handoff.chapterId ?? (handoff.jobId ? undefined : entityId);
    const nextJob = handoff.jobId ?? jobId;
    const nextFrom = handoff.returnTo ?? returnOrigin;
    if (handoff.chapterId) {
      userClearedToNew.current = false;
      setLastEditedChapter(scopeId, handoff.chapterId);
      setEntityId(handoff.chapterId);
    } else if (handoff.jobId && !initialEntityId) {
      setEntityId(undefined);
    }
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
  }, [scopeId]);

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

  useEffect(() => () => setDirtyGlobal(false), []);

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
}
