import { Alert, App, Button, Input, Select, Space, Tag } from "antd";
import { useEffect, useMemo, useState } from "react";
import { adopt, api, scoped, type Json, type Scope } from "../../../shared/api";
import {
  CHAPTER_STATUS_OPTIONS,
  chapterStatusFilterKey,
  chapterStatusLabel,
  chapterStatusTagColor,
  normalizeChapterStatus,
  type ChapterStatus,
} from "../../../shared/chapterStatus";
import {
  deleteBlueprintDraft,
  getBlueprintDraft,
  reorderStudioEntities,
  setBlueprintDraft,
  type StudioChapter,
} from "../../../shared/studioApi";
import { useWorkspace } from "../../../shared/WorkspaceContext";
import { effectDetail } from "../../creation/effectDetail";
import type { TrackedBlueprintTask } from "../blueprintTypes";

export function OutlineCorkboard({
  chapters,
  volumes,
  canEdit,
  onDirtyChange,
  onChanged,
  onTaskCreated,
  onOpen,
}: {
  chapters: StudioChapter[];
  volumes: { id: string; name: string }[];
  canEdit: boolean;
  onDirtyChange: () => void;
  onChanged: () => void;
  onTaskCreated: (task: TrackedBlueprintTask) => void;
  onOpen: (chapterId: string) => void;
}) {
  const { scope } = useWorkspace();
  const { message } = App.useApp();
  const [volumeId, setVolumeId] = useState("全部");
  const [plotline, setPlotline] = useState("");
  const [status, setStatus] = useState("全部状态");
  const [keyOnly, setKeyOnly] = useState(false);
  const [sort, setSort] = useState("position");

  const statusOptions = useMemo(() => {
    const hasFailed = chapters.some(
      (chapter) => chapterStatusFilterKey(chapter.status) === "failed",
    );
    return [
      { value: "全部状态", label: "全部状态" },
      ...CHAPTER_STATUS_OPTIONS,
      ...(hasFailed ? [{ value: "failed", label: "待修" }] : []),
    ];
  }, [chapters]);

  const visible = useMemo(() => {
    const rows = chapters.filter((chapter) => {
      if (volumeId === "__loose__") {
        if (
          chapter.parent_id &&
          volumes.some((v) => v.id === chapter.parent_id)
        ) {
          return false;
        }
      } else if (volumeId !== "全部" && chapter.parent_id !== volumeId) {
        return false;
      }
      if (plotline.trim() && !chapter.plotline.includes(plotline.trim()))
        return false;
      if (
        status !== "全部状态" &&
        chapterStatusFilterKey(chapter.status) !== status
      ) {
        return false;
      }
      if (keyOnly && !chapter.key_chapter) return false;
      return true;
    });
    rows.sort((a, b) => {
      if (sort === "name") return a.name.localeCompare(b.name, "zh");
      if (sort === "chars") return b.char_count - a.char_count;
      return (a.book_order ?? a.position) - (b.book_order ?? b.position);
    });
    return rows;
  }, [chapters, volumes, volumeId, plotline, status, keyOnly, sort]);

  async function move(chapter: StudioChapter, direction: -1 | 1) {
    const siblings = chapters
      .filter(
        (item) => (item.parent_id || null) === (chapter.parent_id || null),
      )
      .sort((a, b) => a.position - b.position || a.id.localeCompare(b.id));
    const index = siblings.findIndex((item) => item.id === chapter.id);
    const target = index + direction;
    if (target < 0 || target >= siblings.length) return;
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
      onChanged();
    } catch (error) {
      message.error(effectDetail(error));
    }
  }

  async function changeParentVolume(
    chapter: StudioChapter,
    nextParentId: string | null,
  ) {
    const siblings = chapters.filter(
      (item) =>
        (item.parent_id || null) === nextParentId && item.id !== chapter.id,
    );
    const nextPos =
      siblings.reduce((max, item) => Math.max(max, item.position), -1) + 1;
    try {
      const fresh = await api<Scope>(scoped(scope.id, ""));
      await reorderStudioEntities(scope.id, fresh.version, [
        {
          entity_id: chapter.id,
          position: nextPos,
          parent_id: nextParentId,
          include_parent: true,
        },
      ]);
      onChanged();
      message.success(nextParentId ? "章节所属分卷已更新" : "章节已移至未归卷");
    } catch (error) {
      message.error(effectDetail(error));
    }
  }

  async function plan(chapter: StudioChapter) {
    try {
      const created = await api<Json>(
        scoped(scope.id, "/creation-tasks"),
        "POST",
        {
          objective: "推演这一章细纲",
          scheme: "P1",
          mode: "create",
          kind: "chapter",
          name: chapter.name,
          entity_id: chapter.id,
          stages: ["plan"],
          beat_outline: chapter.beat_outline,
          max_revisions: 0,
          token_budget: 24000,
        },
      );
      onTaskCreated({
        jobId: String(created.id),
        entityId: chapter.id,
        isChapter: true,
        label: `推演细纲：${chapter.name}`,
      });
      message.success("已进入自动创作流程");
    } catch (error) {
      message.error(effectDetail(error));
    }
  }

  return (
    <section className="blueprint-stack">
      <div className="blueprint-tools">
        <Select
          aria-label="按卷"
          value={volumeId}
          style={{ minWidth: 150 }}
          options={[
            { value: "全部", label: "全部分卷" },
            { value: "__loose__", label: "未归卷" },
            ...volumes.map((volume) => ({
              value: volume.id,
              label: volume.name,
            })),
          ]}
          onChange={setVolumeId}
        />
        <Input
          aria-label="按剧情线"
          placeholder="按剧情线"
          style={{ width: 180 }}
          value={plotline}
          onChange={(event) => setPlotline(event.target.value)}
        />
        <Select
          aria-label="按状态"
          value={status}
          style={{ minWidth: 120 }}
          options={statusOptions}
          onChange={setStatus}
        />
        <Button
          type={keyOnly ? "primary" : "default"}
          onClick={() => setKeyOnly((value) => !value)}
        >
          只看关键章
        </Button>
        <Select
          aria-label="卡片排序"
          value={sort}
          style={{ minWidth: 110 }}
          options={[
            { value: "position", label: "排序号" },
            { value: "name", label: "名称" },
            { value: "chars", label: "字数" },
          ]}
          onChange={setSort}
        />
      </div>
      {chapters.length === 0 ? <p>还没有章节</p> : null}
      {chapters.length > 0 && visible.length === 0 ? (
        <p>
          没有符合的卡片{" "}
          <Button
            onClick={() => {
              setVolumeId("全部");
              setPlotline("");
              setStatus("全部状态");
              setKeyOnly(false);
            }}
          >
            清除过滤
          </Button>
        </p>
      ) : null}
      <div className="blueprint-wall">
        {visible.map((chapter) => (
          <ChapterCard
            key={chapter.id}
            chapter={chapter}
            volumes={volumes}
            canEdit={canEdit}
            onDirtyChange={onDirtyChange}
            onSaved={onChanged}
            onMove={move}
            onChangeVolume={changeParentVolume}
            onPlan={plan}
            onOpen={onOpen}
          />
        ))}
      </div>
    </section>
  );
}

function ChapterCard({
  chapter,
  volumes,
  canEdit,
  onDirtyChange,
  onSaved,
  onMove,
  onChangeVolume,
  onPlan,
  onOpen,
}: {
  chapter: StudioChapter;
  volumes: { id: string; name: string }[];
  canEdit: boolean;
  onDirtyChange: () => void;
  onSaved: () => void;
  onMove: (chapter: StudioChapter, direction: -1 | 1) => void;
  onChangeVolume: (chapter: StudioChapter, parentId: string | null) => void;
  onPlan: (chapter: StudioChapter) => void;
  onOpen: (chapterId: string) => void;
}) {
  const { scope, sessionKey } = useWorkspace();
  const { message } = App.useApp();
  const cached = getBlueprintDraft(
    sessionKey,
    scope.id,
    scope.actions,
    "chapter",
    chapter.id,
  );
  const [beat, setBeat] = useState(
    cached ? cached.first : chapter.beat_outline,
  );
  const [hook, setHook] = useState(cached ? cached.second : chapter.hook);
  const [cardStatus, setCardStatus] = useState<ChapterStatus>(() =>
    normalizeChapterStatus(chapter.status),
  );
  const [baseVersion, setBaseVersion] = useState(
    cached ? cached.baseVersion : chapter.version,
  );
  const [dirty, setDirty] = useState(Boolean(cached));
  const [conflictTriggered, setConflictTriggered] = useState(false);

  useEffect(() => {
    if (dirty) return;
    setBeat(chapter.beat_outline);
    setHook(chapter.hook);
    setCardStatus(normalizeChapterStatus(chapter.status));
    setBaseVersion(chapter.version);
  }, [
    chapter.version,
    chapter.beat_outline,
    chapter.hook,
    chapter.status,
    dirty,
  ]);

  const hasConflict =
    dirty && (chapter.version !== baseVersion || conflictTriggered);

  function updateDraft(nextBeat: string, nextHook: string) {
    const pinned = dirty ? baseVersion : chapter.version;
    setBeat(nextBeat);
    setHook(nextHook);
    setBaseVersion(pinned);
    setDirty(true);
    setBlueprintDraft(
      sessionKey,
      scope.id,
      scope.actions,
      "chapter",
      chapter.id,
      {
        baseVersion: pinned,
        first: nextBeat,
        second: nextHook,
      },
    );
    onDirtyChange();
  }

  async function handleStatusChange(nextStatus: ChapterStatus) {
    setCardStatus(nextStatus);
    if (dirty) {
      message.info("状态已选定，点击「保存这张卡」时将与细纲草稿一并保存");
      return;
    }
    try {
      const fresh = await api<Scope>(scoped(scope.id, ""));
      await adopt(
        fresh,
        [
          {
            op: "update",
            entity_id: chapter.id,
            expected: chapter.version,
            data: { status: nextStatus },
          },
        ],
        `更新章节状态：${chapter.name} -> ${chapterStatusLabel(nextStatus)}`,
      );
      message.success(`已设为「${chapterStatusLabel(nextStatus)}」`);
      onSaved();
    } catch (error) {
      setCardStatus(normalizeChapterStatus(chapter.status));
      message.error(effectDetail(error));
    }
  }

  async function saveWithExpected(expectedVersion: string) {
    try {
      const fresh = await api<Scope>(scoped(scope.id, ""));
      await adopt(
        fresh,
        [
          {
            op: "update",
            entity_id: chapter.id,
            expected: expectedVersion,
            data: { beat_outline: beat, hook, status: cardStatus },
          },
        ],
        "保存细纲：" + chapter.name,
      );
      deleteBlueprintDraft(sessionKey, scope.id, "chapter", chapter.id);
      setDirty(false);
      setConflictTriggered(false);
      onDirtyChange();
      message.success("这张卡已保存");
      onSaved();
    } catch (error) {
      const detail = effectDetail(error);
      const status = (error as { status?: number })?.status;
      if (status === 409 || status === 412) {
        setConflictTriggered(true);
        onSaved();
      }
      message.error(detail);
    }
  }

  return (
    <article className="blueprint-card">
      <h3>
        {chapter.book_order ? `第${chapter.book_order}章 · ` : ""}
        {chapter.name}
      </h3>
      <div className="blueprint-meta-row">
        <span>
          汉字 {chapter.char_count}
          {chapter.key_chapter ? " · 关键章" : ""}
        </span>
        <Tag color={chapterStatusTagColor(chapter.status)}>
          {chapterStatusLabel(chapter.status)}
        </Tag>
      </div>
      <div className="blueprint-meta-row" style={{ marginBottom: 8 }}>
        <Select
          size="small"
          aria-label="章节状态"
          disabled={!canEdit || hasConflict}
          value={cardStatus}
          style={{ width: 96 }}
          options={CHAPTER_STATUS_OPTIONS}
          onChange={(val) => void handleStatusChange(val)}
        />
        {volumes.length > 0 && (
          <Select
            size="small"
            aria-label="所属分卷"
            disabled={!canEdit || dirty || hasConflict}
            value={
              chapter.parent_id &&
              volumes.some((v) => v.id === chapter.parent_id)
                ? chapter.parent_id
                : "__loose__"
            }
            style={{ flex: "1 1 110px", minWidth: 0 }}
            options={[
              { value: "__loose__", label: "未归卷" },
              ...volumes.map((v) => ({ value: v.id, label: v.name })),
            ]}
            onChange={(val) =>
              onChangeVolume(chapter, val === "__loose__" ? null : val)
            }
          />
        )}
      </div>
      {hasConflict ? (
        <Alert
          type="warning"
          showIcon
          title="检测到并发更新冲突：其他窗口已修改本章，请比较后选择处理方式。"
          description={
            <div>
              <p>
                <b>服务器最新版本（{chapter.version}）：</b>
                细纲「{chapter.beat_outline || "（空）"}」 · 章尾钩「
                {chapter.hook || "（空）"}」
              </p>
              <p>
                <b>你的本地草稿（基于 {baseVersion}）：</b>
                细纲「{beat || "（空）"}」 · 章尾钩「{hook || "（空）"}」
              </p>
              <Space wrap>
                <Button
                  size="small"
                  onClick={() => {
                    deleteBlueprintDraft(
                      sessionKey,
                      scope.id,
                      "chapter",
                      chapter.id,
                    );
                    setBeat(chapter.beat_outline);
                    setHook(chapter.hook);
                    setCardStatus(normalizeChapterStatus(chapter.status));
                    setBaseVersion(chapter.version);
                    setDirty(false);
                    setConflictTriggered(false);
                    onDirtyChange();
                  }}
                >
                  采用服务器最新版
                </Button>
                <Button
                  size="small"
                  type="primary"
                  disabled={!canEdit || chapter.version === baseVersion}
                  onClick={() => saveWithExpected(chapter.version)}
                >
                  基于新版保存我的草稿
                </Button>
              </Space>
            </div>
          }
        />
      ) : null}
      <Input.TextArea
        aria-label="本章细纲"
        value={beat}
        autoSize={{ minRows: 3, maxRows: 8 }}
        onChange={(event) => updateDraft(event.target.value, hook)}
      />
      <Input
        aria-label="章尾追读钩"
        value={hook}
        onChange={(event) => updateDraft(beat, event.target.value)}
      />
      <div className="blueprint-tools">
        <Button
          disabled={!canEdit || hasConflict}
          onClick={() => saveWithExpected(baseVersion)}
        >
          保存这张卡
        </Button>
        <Button disabled={!canEdit} onClick={() => onMove(chapter, -1)}>
          上移
        </Button>
        <Button disabled={!canEdit} onClick={() => onMove(chapter, 1)}>
          下移
        </Button>
        <Button disabled={!canEdit} onClick={() => onPlan(chapter)}>
          推演这一章细纲
        </Button>
        <Button onClick={() => onOpen(chapter.id)}>到创作台开写</Button>
      </div>
    </article>
  );
}
