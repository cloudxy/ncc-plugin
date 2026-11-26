import { useEffect, useRef, useState } from "react";
import { api, scoped, type Entity, type Json } from "../../../shared/api";
import type { ChapterStatus } from "../../../shared/chapterStatus";
import { effectDetail } from "../effectDetail";

export type AuthorDraftFields = {
  text: string;
  name: string;
  scheme: string;
  chapterStatus: ChapterStatus;
  beatOutline: string;
  hook: string;
  pov: string;
  plotline: string;
  targetWords: string;
  keyChapter: boolean;
};

export function useAuthorDraftSync({
  scopeId,
  entityId,
  entityData,
  baseline,
  isNonChapterTarget,
  phase,
  dirty,
  setDirtyLocal,
  setDirtyGlobal,
  fields,
  onRestoreDraft,
}: {
  scopeId: string;
  entityId: string | undefined;
  entityData: Entity | undefined;
  baseline: Entity | undefined;
  isNonChapterTarget: boolean;
  phase: "idle" | "save" | "start";
  dirty: boolean;
  setDirtyLocal: (dirty: boolean) => void;
  setDirtyGlobal: (dirty: boolean) => void;
  fields: AuthorDraftFields;
  onRestoreDraft: (draft: Json) => void;
}) {
  const draftVersion = useRef(0);
  const editGeneration = useRef(0);
  const savedGeneration = useRef(0);
  const draftBaseline = useRef<string | null>(null);
  const draftReady = useRef(false);
  const draftKey = useRef("");
  const draftQueue = useRef(Promise.resolve());
  const touchedFields = useRef(new Set<string>());
  const restoredFromDraft = useRef(false);
  const restoreCallbackRef = useRef(onRestoreDraft);
  restoreCallbackRef.current = onRestoreDraft;

  const [draftLoaded, setDraftLoaded] = useState(false);
  const [draftStatus, setDraftStatus] = useState("");

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
    draftKey.current = scopeId + ":" + (entityId || "new");
    setDraftStatus("");
    api<Json>(scoped(scopeId, `/author-drafts/${entityId || "new"}`))
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
          restoreCallbackRef.current(draft);
          setDirtyLocal(true);
          setDirtyGlobal(true);
          setDraftStatus("已恢复自动保存的草稿");
        }
      })
      .catch((error) => {
        if (live) setDraftStatus(effectDetail(error));
      });
    return () => {
      live = false;
    };
  }, [scopeId, entityId]);

  function currentDraftPayload() {
    const pinnedBaseline =
      draftBaseline.current ||
      (baseline?.id === entityId ? baseline?.version : undefined) ||
      (entityData?.id === entityId ? entityData?.version : undefined) ||
      null;
    return {
      pinnedBaseline,
      payload: {
        entity_id: entityId || null,
        baseline: pinnedBaseline,
        name: fields.name,
        text: fields.text,
        scheme: fields.scheme,
        chapter_status: isNonChapterTarget ? "" : fields.chapterStatus,
        beat_outline: fields.beatOutline,
        hook: fields.hook,
        pov: fields.pov,
        plotline: fields.plotline,
        target_words: fields.targetWords,
        key_chapter: fields.keyChapter,
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
    if (entityId && (!entityData || entityData.id !== entityId)) return;
    const targetGeneration = editGeneration.current;
    const key = draftKey.current;
    const targetKey = entityId || "new";
    const { pinnedBaseline, payload } = currentDraftPayload();
    const task = draftQueue.current
      .then(async () => {
        if (key !== draftKey.current) return;
        const draft = await api<Json>(
          scoped(scopeId, `/author-drafts/${targetKey}`),
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
    if (entityId && (!entityData || entityData.id !== entityId)) return;
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
            scoped(scopeId, `/author-drafts/${entityId || "new"}`),
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
    fields.text,
    fields.name,
    fields.scheme,
    fields.chapterStatus,
    fields.beatOutline,
    fields.hook,
    fields.pov,
    fields.plotline,
    fields.targetWords,
    fields.keyChapter,
    dirty,
    entityId,
    phase,
    draftLoaded,
    baseline,
    entityData,
    scopeId,
  ]);

  function markDirty(field?: string) {
    if (field) touchedFields.current.add(field);
    editGeneration.current += 1;
    setDirtyLocal(true);
    setDirtyGlobal(true);
    setDraftStatus("未保存修改 · 自动保存尚未成功");
  }

  function resetDraftTracking() {
    draftBaseline.current = null;
    touchedFields.current.clear();
    restoredFromDraft.current = false;
    editGeneration.current = 0;
    savedGeneration.current = 0;
  }

  async function clearServerDraft(
    targetEntityId: string | undefined,
  ): Promise<boolean> {
    try {
      const cleared = await api<Json>(
        scoped(
          scopeId,
          `/author-drafts/${targetEntityId || "new"}?version=${draftVersion.current}`,
        ),
        "DELETE",
      );
      draftVersion.current =
        typeof cleared?.version === "number" ? cleared.version : 0;
      return false;
    } catch {
      return true;
    }
  }

  return {
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
  };
}
