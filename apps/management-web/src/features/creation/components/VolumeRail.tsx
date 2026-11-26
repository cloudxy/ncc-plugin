import { App, Button, Dropdown, Input, Select, Tag } from "antd";
import { useMemo, useState } from "react";
import {
  CHAPTER_STATUS_OPTIONS,
  chapterStatusFilterKey,
  chapterStatusLabel,
} from "../../../shared/chapterStatus";
import type { StudioChapter, StudioVolume } from "../../../shared/studioApi";

export function VolumeRail({
  volumes,
  chapters,
  loading,
  error,
  currentId,
  canEdit,
  readOnlyPerspective = false,
  onRetry,
  onSelect,
  onCreateVolume,
  onRenameVolume,
  onMoveVolume,
  onArchiveVolume,
  onCreateChapter,
  onMove,
  onMoveChapterToVolume,
  onToggle,
}: {
  volumes: StudioVolume[];
  chapters: StudioChapter[];
  loading: boolean;
  error: boolean;
  currentId?: string;
  canEdit: boolean;
  readOnlyPerspective?: boolean;
  onRetry: () => void;
  onSelect: (id: string) => void;
  onCreateVolume: (name: string) => void;
  onRenameVolume?: (
    volume: StudioVolume,
    nextName: string,
  ) => Promise<void> | void;
  onMoveVolume?: (
    volume: StudioVolume,
    direction: -1 | 1,
  ) => Promise<void> | void;
  onArchiveVolume?: (volume: StudioVolume) => Promise<void> | void;
  onCreateChapter: (
    parentId: string | null,
    name: string,
  ) => Promise<boolean> | boolean | void;
  onMove: (chapter: StudioChapter, direction: -1 | 1) => void;
  onMoveChapterToVolume?: (
    chapter: StudioChapter,
    parentId: string | null,
  ) => Promise<void> | void;
  onToggle: () => void;
}) {
  const { modal } = App.useApp();
  const [status, setStatus] = useState("全部状态");
  const [keyOnly, setKeyOnly] = useState(false);
  const [plotline, setPlotline] = useState("");
  const [sort, setSort] = useState<"position" | "name">("position");
  const [volumeName, setVolumeName] = useState("");
  const [chapterName, setChapterName] = useState("");
  const [parentId, setParentId] = useState<string | null>(null);
  const [renamingVolumeId, setRenamingVolumeId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");

  const allowMutate = canEdit && !readOnlyPerspective;

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
      if (
        status !== "全部状态" &&
        chapterStatusFilterKey(chapter.status) !== status
      ) {
        return false;
      }
      if (keyOnly && !chapter.key_chapter) return false;
      if (plotline.trim() && !chapter.plotline.includes(plotline.trim()))
        return false;
      return true;
    });
    rows.sort((a, b) =>
      sort === "name"
        ? a.name.localeCompare(b.name, "zh")
        : a.position - b.position || a.name.localeCompare(b.name, "zh"),
    );
    return rows;
  }, [chapters, status, keyOnly, plotline, sort]);

  const grouped = volumes.map((volume) => ({
    volume,
    chapters: visible.filter((chapter) => chapter.parent_id === volume.id),
  }));
  const loose = visible.filter(
    (chapter) =>
      !chapter.parent_id ||
      !volumes.some((volume) => volume.id === chapter.parent_id),
  );

  return (
    <aside className="studio-rail" aria-label="卷章与细纲目录">
      <div className="studio-rail-head">
        <b>卷章与细纲目录</b>
        <Button type="link" size="small" onClick={onToggle}>
          收起目录
        </Button>
      </div>
      <div className="studio-rail-tools">
        <Select
          aria-label="目录状态"
          size="small"
          style={{ minWidth: 96 }}
          value={status}
          options={statusOptions}
          onChange={setStatus}
        />
        <Button
          size="small"
          type={keyOnly ? "primary" : "default"}
          onClick={() => setKeyOnly((value) => !value)}
        >
          关键章
        </Button>
        <Select
          aria-label="目录排序"
          size="small"
          style={{ minWidth: 82 }}
          value={sort}
          options={[
            { value: "position", label: "排序号" },
            { value: "name", label: "名称" },
          ]}
          onChange={setSort}
        />
        <Input
          aria-label="剧情线"
          size="small"
          placeholder="筛选剧情线"
          value={plotline}
          onChange={(event) => setPlotline(event.target.value)}
        />
      </div>
      {readOnlyPerspective && (
        <p className="studio-rail-note">
          读者此刻视角下仅展示截至当前章的目录，卷章调整已锁定。
        </p>
      )}
      {loading ? <p>目录正在读取</p> : null}
      {error ? (
        <p>
          目录没有载入 <Button onClick={onRetry}>重试</Button>
        </p>
      ) : null}
      {!loading && !error && chapters.length === 0 && volumes.length === 0 ? (
        <p>还没有卷章</p>
      ) : null}
      {!loading && !error && chapters.length > 0 && visible.length === 0 ? (
        <p>没有符合的章节</p>
      ) : null}
      {loose.length > 0 ? (
        <section className="studio-volume-section">
          <div className="studio-volume-head">
            <h4>未归卷</h4>
          </div>
          {loose.map((chapter) => (
            <ChapterRow
              key={chapter.id}
              chapter={chapter}
              volumes={volumes}
              current={chapter.id === currentId}
              canEdit={allowMutate}
              onSelect={onSelect}
              onMove={onMove}
              onMoveToVolume={onMoveChapterToVolume}
            />
          ))}
        </section>
      ) : null}
      {grouped.map(({ volume, chapters: rows }, volIndex) => (
        <section key={volume.id} className="studio-volume-section">
          <div className="studio-volume-head">
            <h4>{volume.name}</h4>
            {allowMutate &&
              (onRenameVolume || onMoveVolume || onArchiveVolume) && (
                <Dropdown
                  trigger={["click"]}
                  menu={{
                    items: [
                      ...(onRenameVolume
                        ? [
                            {
                              key: "rename",
                              label: "修改卷名",
                              onClick: () => {
                                setRenamingVolumeId(volume.id);
                                setRenameValue(volume.name);
                              },
                            },
                          ]
                        : []),
                      ...(onMoveVolume
                        ? [
                            {
                              key: "up",
                              label: "分卷上移",
                              disabled: volIndex === 0,
                              onClick: () => void onMoveVolume(volume, -1),
                            },
                            {
                              key: "down",
                              label: "分卷下移",
                              disabled: volIndex === volumes.length - 1,
                              onClick: () => void onMoveVolume(volume, 1),
                            },
                          ]
                        : []),
                      ...(onArchiveVolume
                        ? [
                            {
                              key: "archive",
                              danger: true,
                              label: "归档分卷",
                              onClick: () => {
                                modal.confirm({
                                  title: `归档分卷「${volume.name}」？`,
                                  content:
                                    "归档后分卷内原有章节不会丢失，将自动回到「未归卷」分组；分卷本身可在「身份与历史维护」恢复。",
                                  okText: "确认归档",
                                  cancelText: "取消",
                                  okButtonProps: { danger: true },
                                  onOk: () => onArchiveVolume(volume),
                                });
                              },
                            },
                          ]
                        : []),
                    ],
                  }}
                >
                  <Button type="link" size="small">
                    管理
                  </Button>
                </Dropdown>
              )}
          </div>
          {renamingVolumeId === volume.id && onRenameVolume && (
            <div className="studio-volume-rename">
              <Input
                size="small"
                aria-label="修改卷名输入"
                value={renameValue}
                onChange={(event) => setRenameValue(event.target.value)}
              />
              <Button
                size="small"
                type="primary"
                disabled={!renameValue.trim()}
                onClick={async () => {
                  await onRenameVolume(volume, renameValue.trim());
                  setRenamingVolumeId(null);
                }}
              >
                保存卷名
              </Button>
              <Button size="small" onClick={() => setRenamingVolumeId(null)}>
                取消
              </Button>
            </div>
          )}
          {rows.map((chapter) => (
            <ChapterRow
              key={chapter.id}
              chapter={chapter}
              volumes={volumes}
              current={chapter.id === currentId}
              canEdit={allowMutate}
              onSelect={onSelect}
              onMove={onMove}
              onMoveToVolume={onMoveChapterToVolume}
            />
          ))}
        </section>
      ))}
      <div className="studio-rail-create">
        <div className="studio-rail-inline">
          <Input
            size="small"
            aria-label="新卷名称"
            placeholder="新卷名称"
            value={volumeName}
            disabled={!allowMutate}
            onChange={(event) => setVolumeName(event.target.value)}
          />
          <Button
            size="small"
            disabled={!allowMutate || !volumeName.trim()}
            onClick={() => {
              onCreateVolume(volumeName.trim());
              setVolumeName("");
            }}
          >
            新建卷
          </Button>
        </div>
        <Select
          size="small"
          aria-label="所属卷"
          allowClear
          placeholder="不归入卷"
          disabled={!allowMutate}
          value={parentId || undefined}
          options={volumes.map((volume) => ({
            value: volume.id,
            label: volume.name,
          }))}
          onChange={(value) => setParentId(value || null)}
        />
        <div className="studio-rail-inline">
          <Input
            size="small"
            aria-label="新章节名称"
            placeholder="新章节名称"
            value={chapterName}
            disabled={!allowMutate}
            onChange={(event) => setChapterName(event.target.value)}
          />
          <Button
            size="small"
            disabled={!allowMutate}
            onClick={async () => {
              const ok = await onCreateChapter(
                parentId,
                chapterName.trim() || "新章节",
              );
              if (ok !== false) setChapterName("");
            }}
          >
            新建章节
          </Button>
        </div>
      </div>
    </aside>
  );
}

function ChapterRow({
  chapter,
  volumes,
  current,
  canEdit,
  onSelect,
  onMove,
  onMoveToVolume,
}: {
  chapter: StudioChapter;
  volumes: StudioVolume[];
  current: boolean;
  canEdit: boolean;
  onSelect: (id: string) => void;
  onMove: (chapter: StudioChapter, direction: -1 | 1) => void;
  onMoveToVolume?: (
    chapter: StudioChapter,
    parentId: string | null,
  ) => Promise<void> | void;
}) {
  const statusText = chapterStatusLabel(chapter.status);
  return (
    <div className={current ? "studio-chapter is-current" : "studio-chapter"}>
      <button type="button" onClick={() => onSelect(chapter.id)}>
        <span>
          {chapter.book_order ? `第${chapter.book_order}章 · ` : ""}
          {chapter.name}
        </span>
        <small>
          汉字 {chapter.char_count}
          {chapter.key_chapter ? " · 关键章" : ""}
          {` · ${statusText}`}
        </small>
      </button>
      {chapter.key_chapter ? <Tag>关键章</Tag> : null}
      <div className="studio-chapter-actions">
        <Button
          type="link"
          size="small"
          disabled={!canEdit}
          onClick={() => onMove(chapter, -1)}
        >
          上移
        </Button>
        <Button
          type="link"
          size="small"
          disabled={!canEdit}
          onClick={() => onMove(chapter, 1)}
        >
          下移
        </Button>
        {canEdit && onMoveToVolume && volumes.length > 0 && (
          <Dropdown
            trigger={["click"]}
            menu={{
              items: [
                {
                  key: "__loose__",
                  label: "移至：未归卷",
                  disabled: !chapter.parent_id,
                  onClick: () => void onMoveToVolume(chapter, null),
                },
                ...volumes.map((vol) => ({
                  key: vol.id,
                  label: `移至：${vol.name}`,
                  disabled: chapter.parent_id === vol.id,
                  onClick: () => void onMoveToVolume(chapter, vol.id),
                })),
              ],
            }}
          >
            <Button type="link" size="small">
              移卷
            </Button>
          </Dropdown>
        )}
      </div>
    </div>
  );
}
