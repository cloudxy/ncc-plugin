import { App } from "antd";
import { useEffect, useState } from "react";
import {
  adopt,
  api,
  scoped,
  type Entity,
  type Json,
  type Scope,
} from "../../../shared/api";
import {
  normalizeChapterStatus,
  type ChapterStatus,
} from "../../../shared/chapterStatus";
import {
  reorderStudioEntities,
  setLastEditedChapter,
  type StudioChapter,
  type StudioReturnOrigin,
  type StudioVolume,
} from "../../../shared/studioApi";
import { effectDetail } from "../effectDetail";

export function useNarrow(): boolean {
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

export function parseReturnOrigin(
  value: string | null,
): StudioReturnOrigin | undefined {
  if (value === "inbox" || value === "jobs" || value === "blueprint") {
    return value;
  }
  return undefined;
}

export function isChapterKind(kind?: string | null): boolean {
  return !kind || kind === "chapter" || kind === "章节";
}

export function extractEntityChapterFields(data: Json | undefined) {
  const src = data || {};
  return {
    chapterStatus: normalizeChapterStatus(
      typeof src.status === "string" ? src.status : "draft",
    ),
    beatOutline: typeof src.beat_outline === "string" ? src.beat_outline : "",
    hook: typeof src.hook === "string" ? src.hook : "",
    pov: typeof src.pov === "string" ? src.pov : "",
    plotline: typeof src.plotline === "string" ? src.plotline : "",
    targetWords:
      typeof src.target_words === "number" ? String(src.target_words) : "",
    keyChapter: src.key_chapter === true,
  };
}

export function buildBeatPatch(
  original: Entity | undefined,
  fields: {
    chapterStatus: ChapterStatus;
    keyChapter: boolean;
    beatOutline: string;
    hook: string;
    pov: string;
    plotline: string;
    targetWords: string;
  },
): { patch: Json; unset: string[] } {
  if (original && !isChapterKind(original.kind)) {
    return { patch: {}, unset: [] };
  }
  const patch: Json = {
    status: fields.chapterStatus,
    key_chapter: fields.keyChapter,
  };
  const unset: string[] = [];
  const previous = original?.data || {};
  function textField(key: string, value: string) {
    if (value.trim()) patch[key] = value;
    else if (previous[key]) unset.push(key);
  }
  textField("beat_outline", fields.beatOutline);
  textField("hook", fields.hook);
  textField("pov", fields.pov);
  textField("plotline", fields.plotline);
  if (/^\d+$/.test(fields.targetWords.trim()))
    patch.target_words = Number(fields.targetWords.trim());
  else if (previous.target_words !== undefined) unset.push("target_words");
  return { patch, unset };
}

export function useVolumeChapterActions({
  scope,
  volumes,
  chapters,
  refresh,
  refetchOverview,
  confirmSwitchIfDirty,
  onCreatedChapter,
}: {
  scope: Scope;
  volumes: StudioVolume[];
  chapters: StudioChapter[];
  refresh: () => void;
  refetchOverview: () => void;
  confirmSwitchIfDirty: (
    action: () => void | Promise<void>,
  ) => Promise<boolean>;
  onCreatedChapter: (id: string, chapterName: string) => void;
}) {
  const { message } = App.useApp();

  async function createVolume(volumeName: string) {
    try {
      const freshScope = await api<Scope>(scoped(scope.id, ""));
      const position = volumes.length;
      await adopt(
        freshScope,
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
      refetchOverview();
    } catch (error) {
      message.error(effectDetail(error));
    }
  }

  async function renameVolume(volume: StudioVolume, nextName: string) {
    try {
      const freshScope = await api<Scope>(scoped(scope.id, ""));
      await adopt(
        freshScope,
        [
          {
            op: "update",
            entity_id: volume.id,
            expected: volume.version,
            name: nextName,
          },
        ],
        "修改卷名：" + nextName,
      );
      refresh();
      refetchOverview();
      message.success("分卷已改名");
    } catch (error) {
      message.error(effectDetail(error));
    }
  }

  async function moveVolume(volume: StudioVolume, direction: -1 | 1) {
    const vols = volumes
      .slice()
      .sort((a, b) => a.position - b.position || a.id.localeCompare(b.id));
    const index = vols.findIndex((item) => item.id === volume.id);
    const target = index + direction;
    if (index < 0 || target < 0 || target >= vols.length) return;
    const order = vols.slice();
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
      refetchOverview();
    } catch (error) {
      message.error(effectDetail(error));
    }
  }

  async function archiveVolume(volume: StudioVolume) {
    try {
      const fresh = await api<Scope>(scoped(scope.id, ""));
      const childChapters = chapters.filter((ch) => ch.parent_id === volume.id);
      const ops: Json[] = childChapters.map((ch) => ({
        op: "update",
        entity_id: ch.id,
        expected: ch.version,
        unset: ["parent_id"],
      }));
      ops.push({
        op: "retire",
        entity_id: volume.id,
        expected: volume.version,
      });
      await adopt(fresh, ops, "归档分卷：" + volume.name);
      refresh();
      refetchOverview();
      message.success("分卷已归档，原章节已移入未归卷");
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
        const freshScope = await api<Scope>(scoped(scope.id, ""));
        const siblings = chapters.filter(
          (chapter) => (chapter.parent_id || null) === parentId,
        );
        const position =
          siblings.reduce(
            (max, chapter) => Math.max(max, chapter.position),
            -1,
          ) + 1;
        const id = crypto.randomUUID();
        await adopt(
          freshScope,
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
        setLastEditedChapter(scope.id, id);
        onCreatedChapter(id, chapterName);
        refresh();
        refetchOverview();
      } catch (error) {
        message.error(effectDetail(error));
      }
    });
  }

  async function moveChapter(chapter: StudioChapter, direction: -1 | 1) {
    const siblings = chapters
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
      refetchOverview();
    } catch (error) {
      message.error(effectDetail(error));
    }
  }

  async function moveChapterToVolume(
    chapter: StudioChapter,
    parentId: string | null,
  ) {
    const siblings = chapters.filter(
      (item) => (item.parent_id || null) === parentId && item.id !== chapter.id,
    );
    const nextPos =
      siblings.reduce((max, item) => Math.max(max, item.position), -1) + 1;
    try {
      const fresh = await api<Scope>(scoped(scope.id, ""));
      await reorderStudioEntities(scope.id, fresh.version, [
        {
          entity_id: chapter.id,
          position: nextPos,
          parent_id: parentId,
          include_parent: true,
        },
      ]);
      refresh();
      refetchOverview();
      message.success(parentId ? "章节已移入目标分卷" : "章节已移至未归卷");
    } catch (error) {
      message.error(effectDetail(error));
    }
  }

  return {
    createVolume,
    renameVolume,
    moveVolume,
    archiveVolume,
    createChapter,
    moveChapter,
    moveChapterToVolume,
  };
}
