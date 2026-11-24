import { Button, Input, Select, Tag } from "antd";
import { useMemo, useState } from "react";
import type { StudioChapter, StudioVolume } from "../../../shared/studioApi";

export function VolumeRail({
  volumes,
  chapters,
  loading,
  error,
  currentId,
  canEdit,
  onRetry,
  onSelect,
  onCreateVolume,
  onCreateChapter,
  onMove,
  onToggle,
}: {
  volumes: StudioVolume[];
  chapters: StudioChapter[];
  loading: boolean;
  error: boolean;
  currentId?: string;
  canEdit: boolean;
  onRetry: () => void;
  onSelect: (id: string) => void;
  onCreateVolume: (name: string) => void;
  onCreateChapter: (
    parentId: string | null,
    name: string,
  ) => Promise<boolean> | boolean | void;
  onMove: (chapter: StudioChapter, direction: -1 | 1) => void;
  onToggle: () => void;
}) {
  const [status, setStatus] = useState("全部状态");
  const [keyOnly, setKeyOnly] = useState(false);
  const [plotline, setPlotline] = useState("");
  const [sort, setSort] = useState<"position" | "name">("position");
  const [volumeName, setVolumeName] = useState("");
  const [chapterName, setChapterName] = useState("");
  const [parentId, setParentId] = useState<string | null>(null);
  const statuses = useMemo(() => {
    const values = new Set(
      chapters.map((chapter) => chapter.status).filter(Boolean),
    );
    return ["全部状态", ...values];
  }, [chapters]);
  const visible = useMemo(() => {
    const rows = chapters.filter((chapter) => {
      if (status !== "全部状态" && chapter.status !== status) return false;
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
        <Button type="link" onClick={onToggle}>
          收起目录
        </Button>
      </div>
      <div className="studio-rail-tools">
        <Select
          aria-label="目录状态"
          value={status}
          options={statuses.map((value) => ({ value, label: value }))}
          onChange={setStatus}
        />
        <Button
          type={keyOnly ? "primary" : "default"}
          onClick={() => setKeyOnly((value) => !value)}
        >
          关键章
        </Button>
        <Input
          aria-label="剧情线"
          placeholder="剧情线"
          value={plotline}
          onChange={(event) => setPlotline(event.target.value)}
        />
        <Select
          aria-label="目录排序"
          value={sort}
          options={[
            { value: "position", label: "排序号" },
            { value: "name", label: "名称" },
          ]}
          onChange={setSort}
        />
      </div>
      {loading ? <p>目录正在读取</p> : null}
      {error ? (
        <p>
          目录没有载入 <Button onClick={onRetry}>重试</Button>
        </p>
      ) : null}
      {!loading && !error && chapters.length === 0 ? <p>还没有卷章</p> : null}
      {!loading && !error && chapters.length > 0 && visible.length === 0 ? (
        <p>没有符合的章节</p>
      ) : null}
      {loose.length > 0 ? (
        <section>
          <h4>未归卷</h4>
          {loose.map((chapter) => (
            <ChapterRow
              key={chapter.id}
              chapter={chapter}
              current={chapter.id === currentId}
              canEdit={canEdit}
              onSelect={onSelect}
              onMove={onMove}
            />
          ))}
        </section>
      ) : null}
      {grouped.map(({ volume, chapters: rows }) => (
        <section key={volume.id}>
          <h4>{volume.name}</h4>
          {rows.map((chapter) => (
            <ChapterRow
              key={chapter.id}
              chapter={chapter}
              current={chapter.id === currentId}
              canEdit={canEdit}
              onSelect={onSelect}
              onMove={onMove}
            />
          ))}
        </section>
      ))}
      <div className="studio-rail-create">
        <Input
          aria-label="新卷名称"
          placeholder="新卷名称"
          value={volumeName}
          onChange={(event) => setVolumeName(event.target.value)}
        />
        <Button
          disabled={!canEdit || !volumeName.trim()}
          onClick={() => {
            onCreateVolume(volumeName.trim());
            setVolumeName("");
          }}
        >
          新建卷
        </Button>
        <Select
          aria-label="所属卷"
          allowClear
          placeholder="不归入卷"
          value={parentId || undefined}
          options={volumes.map((volume) => ({
            value: volume.id,
            label: volume.name,
          }))}
          onChange={(value) => setParentId(value || null)}
        />
        <Input
          aria-label="新章节名称"
          placeholder="新章节名称"
          value={chapterName}
          onChange={(event) => setChapterName(event.target.value)}
        />
        <Button
          disabled={!canEdit}
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
    </aside>
  );
}

function ChapterRow({
  chapter,
  current,
  canEdit,
  onSelect,
  onMove,
}: {
  chapter: StudioChapter;
  current: boolean;
  canEdit: boolean;
  onSelect: (id: string) => void;
  onMove: (chapter: StudioChapter, direction: -1 | 1) => void;
}) {
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
          {chapter.status ? ` · ${chapter.status}` : ""}
        </small>
      </button>
      {chapter.key_chapter ? <Tag>关键章</Tag> : null}
      <Button
        type="link"
        disabled={!canEdit}
        onClick={() => onMove(chapter, -1)}
      >
        上移
      </Button>
      <Button
        type="link"
        disabled={!canEdit}
        onClick={() => onMove(chapter, 1)}
      >
        下移
      </Button>
    </div>
  );
}
