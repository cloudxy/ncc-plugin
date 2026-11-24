import { useQuery } from "@tanstack/react-query";
import {
  Alert,
  App,
  Button,
  Form,
  Input,
  InputNumber,
  Modal,
  Segmented,
  Select,
  Space,
} from "antd";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { adopt, api, scoped, type Json, type Scope } from "../../shared/api";
import { ErrorPanel, PageTitle } from "../../shared/components/Feedback";
import { scopeLine } from "../../shared/scopeLabel";
import {
  countBlueprintDrafts,
  deleteBlueprintDraft,
  fetchStudioOverview,
  getBlueprintDraft,
  reorderStudioEntities,
  setBlueprintDraft,
  setStudioHandoff,
  type StudioChapter,
  type StudioForeshadow,
  type StudioOutline,
} from "../../shared/studioApi";
import { useWorkspace } from "../../shared/WorkspaceContext";
import "./blueprint.css";
import { effectDetail } from "../creation/effectDetail";

const ALERTS = [
  ["overdue", "超期未回收"],
  ["due_soon", "临期预警"],
  ["active", "推进中"],
  ["planned", "待埋设"],
  ["resolved", "已兑现"],
  ["dropped", "已作废"],
] as const;

export function BlueprintPage() {
  const { scope, sessionKey, refresh, setDirty } = useWorkspace();
  const { message, modal } = App.useApp();
  const navigate = useNavigate();
  const [view, setView] = useState("总纲与剧情走向");
  const [creating, setCreating] = useState<"outline" | "volume" | null>(null);
  const [name, setName] = useState("");
  const [dirtyTick, setDirtyTick] = useState(0);
  const canEdit = scope.actions.includes("edit");
  const syncDirty = useCallback(() => {
    const hasUnsaved =
      countBlueprintDrafts(sessionKey, scope.id, scope.actions) > 0;
    setDirty(hasUnsaved);
    setDirtyTick((n) => n + 1);
  }, [sessionKey, scope.id, scope.actions, setDirty]);
  useEffect(() => {
    setDirty(countBlueprintDrafts(sessionKey, scope.id, scope.actions) > 0);
    return () => setDirty(false);
  }, [sessionKey, scope.id, scope.actions, setDirty]);
  const hasUnsavedDrafts = useMemo(
    () => countBlueprintDrafts(sessionKey, scope.id, scope.actions) > 0,
    [sessionKey, scope.id, scope.actions, dirtyTick],
  );
  function navigateWithGuard(run: () => void) {
    if (!hasUnsavedDrafts) {
      run();
      return;
    }
    modal.confirm({
      title: "离开尚未保存的大纲/细纲草稿？",
      content:
        "当前页面有未保存的卡片草稿。离开后草稿仍暂存在本会话蓝图页，返回后可继续保存或比较。",
      okText: "离开蓝图页",
      cancelText: "留在当前页",
      autoFocusButton: "cancel",
      onOk: () => {
        setDirty(false);
        run();
      },
    });
  }
  const overview = useQuery({
    queryKey: ["scope", scope.id, "studio-overview"],
    queryFn: () => fetchStudioOverview(scope.id),
  });
  async function create(kind: "outline" | "volume") {
    const label = name.trim();
    if (!label) return;
    try {
      const position =
        kind === "volume"
          ? overview.data?.volumes.length || 0
          : overview.data?.outlines.length || 0;
      await adopt(
        scope,
        [
          {
            op: "create",
            entity_id: crypto.randomUUID(),
            kind: kind === "volume" ? "volume" : "outline",
            name: label,
            text: "",
            data: { status: "draft", position },
          },
        ],
        (kind === "volume" ? "新建分卷：" : "新建总纲：") + label,
      );
      setName("");
      setCreating(null);
      refresh();
      overview.refetch();
    } catch (error) {
      message.error(effectDetail(error));
    }
  }
  async function planOutline(outline?: StudioOutline) {
    try {
      await api(scoped(scope.id, "/creation-tasks"), "POST", {
        objective: "推演全书大纲与分卷走向",
        scheme: "P2",
        mode: "create",
        kind: outline?.kind || "outline",
        name: outline?.name || "全书大纲",
        entity_id: outline?.id || null,
        stages: ["plan"],
        max_revisions: 0,
        token_budget: 24000,
      });
      message.success("已进入自动创作流程");
    } catch (error) {
      message.error(effectDetail(error));
    }
  }
  return (
    <div className="blueprint-page">
      <PageTitle
        title="大纲与暗线"
        note={scopeLine(scope.name, scope.kind, scope.version)}
      />
      {!canEdit ? <p className="creation-note">当前范围不能编辑</p> : null}
      <Segmented
        value={view}
        options={["总纲与剧情走向", "细纲卡片墙", "伏笔与明暗灰线"]}
        onChange={(value) => setView(String(value))}
      />
      {hasUnsavedDrafts ? (
        <p className="creation-note">
          当前有未保存的大纲或细纲草稿（切换上方切片不会丢失草稿）
        </p>
      ) : null}
      {overview.data?.pagination?.truncated ? (
        <Alert
          type="info"
          showIcon
          title={`目录对象较多，当前展示前 ${overview.data.pagination.returned_structural} / ${overview.data.pagination.structural_count} 条结构项（全书共 ${overview.data.pagination.total_entities} 条对象）。`}
        />
      ) : null}
      <ErrorPanel error={overview.error} retry={() => overview.refetch()} />
      {overview.isPending ? <p>正在读取大纲</p> : null}
      {view === "总纲与剧情走向" && overview.data ? (
        <section className="blueprint-stack">
          <div className="blueprint-tools">
            <Button disabled={!canEdit} onClick={() => setCreating("outline")}>
              新建总纲
            </Button>
            <Button disabled={!canEdit} onClick={() => setCreating("volume")}>
              新建分卷
            </Button>
            <Button
              disabled={!canEdit}
              onClick={() => planOutline(overview.data.outlines[0])}
            >
              推演大纲
            </Button>
          </div>
          {creating ? (
            <div className="blueprint-tools">
              <Input
                aria-label={creating === "volume" ? "分卷名称" : "总纲名称"}
                value={name}
                onChange={(event) => setName(event.target.value)}
              />
              <Button
                type="primary"
                disabled={!name.trim()}
                onClick={() => create(creating)}
              >
                保存
              </Button>
            </div>
          ) : null}
          {overview.data.outlines.length === 0 ? <p>还没有总纲</p> : null}
          {overview.data.outlines.map((outline) => (
            <OutlineEditor
              key={outline.id}
              outline={outline}
              canEdit={canEdit}
              onDirtyChange={syncDirty}
              onSaved={() => {
                refresh();
                overview.refetch();
              }}
            />
          ))}
          {overview.data.volumes.map((volume) => (
            <article key={volume.id} className="blueprint-card">
              <h3>{volume.name}</h3>
              <p>分卷 · 排序号 {volume.position}</p>
            </article>
          ))}
        </section>
      ) : null}
      {view === "细纲卡片墙" && overview.data ? (
        <Corkboard
          chapters={overview.data.chapters}
          volumes={overview.data.volumes.map((volume) => ({
            id: volume.id,
            name: volume.name,
          }))}
          canEdit={canEdit}
          onDirtyChange={syncDirty}
          onChanged={() => {
            refresh();
            overview.refetch();
          }}
          onOpen={(chapterId) =>
            navigateWithGuard(() => {
              setStudioHandoff({
                scopeId: scope.id,
                chapterId,
                returnTo: "blueprint",
              });
              navigate("/work");
            })
          }
        />
      ) : null}
      {view === "伏笔与明暗灰线" && overview.data ? (
        <ForeshadowBoard
          rows={overview.data.foreshadows}
          canEdit={canEdit}
          onChanged={() => {
            refresh();
            overview.refetch();
          }}
          onOpen={(id, title) =>
            navigateWithGuard(() => {
              setStudioHandoff({
                scopeId: scope.id,
                sourceEntity: { id, title },
                returnTo: "blueprint",
              });
              navigate("/work");
            })
          }
        />
      ) : null}
    </div>
  );
}

function OutlineEditor({
  outline,
  canEdit,
  onDirtyChange,
  onSaved,
}: {
  outline: StudioOutline;
  canEdit: boolean;
  onDirtyChange: () => void;
  onSaved: () => void;
}) {
  const { scope, sessionKey } = useWorkspace();
  const { message } = App.useApp();
  const cached = getBlueprintDraft(
    sessionKey,
    scope.id,
    scope.actions,
    "outline",
    outline.id,
  );
  const [beat, setBeat] = useState(
    cached ? cached.first : outline.beat_outline,
  );
  const [plotline, setPlotline] = useState(
    cached ? cached.second : outline.plotline,
  );
  const [baseVersion, setBaseVersion] = useState(
    cached ? cached.baseVersion : outline.version,
  );
  const [dirty, setDirty] = useState(Boolean(cached));
  const [conflictTriggered, setConflictTriggered] = useState(false);
  useEffect(() => {
    if (dirty) return;
    setBeat(outline.beat_outline);
    setPlotline(outline.plotline);
    setBaseVersion(outline.version);
  }, [outline.version, outline.beat_outline, outline.plotline, dirty]);
  const hasConflict =
    dirty && (outline.version !== baseVersion || conflictTriggered);
  function updateDraft(nextBeat: string, nextPlotline: string) {
    const pinned = dirty ? baseVersion : outline.version;
    setBeat(nextBeat);
    setPlotline(nextPlotline);
    setBaseVersion(pinned);
    setDirty(true);
    setBlueprintDraft(
      sessionKey,
      scope.id,
      scope.actions,
      "outline",
      outline.id,
      {
        baseVersion: pinned,
        first: nextBeat,
        second: nextPlotline,
      },
    );
    onDirtyChange();
  }
  async function saveWithExpected(expectedVersion: string) {
    try {
      await adopt(
        scope,
        [
          {
            op: "update",
            entity_id: outline.id,
            expected: expectedVersion,
            data: { beat_outline: beat, plotline },
          },
        ],
        "保存总纲：" + outline.name,
      );
      deleteBlueprintDraft(sessionKey, scope.id, "outline", outline.id);
      setDirty(false);
      setConflictTriggered(false);
      onDirtyChange();
      message.success("总纲已保存");
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
      <h3>{outline.name}</h3>
      {hasConflict ? (
        <Alert
          type="warning"
          showIcon
          title="检测到并发更新冲突：其他窗口已保存新版本，你的草稿尚未覆盖服务器内容。"
          description={
            <div>
              <p>
                <b>服务器最新版本（{outline.version}）：</b>
                细纲「{outline.beat_outline || "（空）"}」 · 剧情走向「
                {outline.plotline || "（空）"}」
              </p>
              <p>
                <b>你的本地草稿（基于 {baseVersion}）：</b>
                细纲「{beat || "（空）"}」 · 剧情走向「{plotline || "（空）"}」
              </p>
              <Space wrap>
                <Button
                  size="small"
                  onClick={() => {
                    deleteBlueprintDraft(
                      sessionKey,
                      scope.id,
                      "outline",
                      outline.id,
                    );
                    setBeat(outline.beat_outline);
                    setPlotline(outline.plotline);
                    setBaseVersion(outline.version);
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
                  disabled={!canEdit || outline.version === baseVersion}
                  onClick={() => saveWithExpected(outline.version)}
                >
                  基于新版保存我的草稿
                </Button>
              </Space>
            </div>
          }
        />
      ) : null}
      <Input.TextArea
        aria-label="总纲细纲"
        value={beat}
        autoSize={{ minRows: 3, maxRows: 8 }}
        onChange={(event) => updateDraft(event.target.value, plotline)}
      />
      <Input
        aria-label="剧情走向"
        value={plotline}
        onChange={(event) => updateDraft(beat, event.target.value)}
      />
      <p>五拍：起、承、转、合、钩。主线写在剧情走向。</p>
      <Button
        disabled={!canEdit || hasConflict}
        onClick={() => saveWithExpected(baseVersion)}
      >
        保存总纲
      </Button>
    </article>
  );
}

function Corkboard({
  chapters,
  volumes,
  canEdit,
  onDirtyChange,
  onChanged,
  onOpen,
}: {
  chapters: StudioChapter[];
  volumes: { id: string; name: string }[];
  canEdit: boolean;
  onDirtyChange: () => void;
  onChanged: () => void;
  onOpen: (chapterId: string) => void;
}) {
  const { scope } = useWorkspace();
  const { message } = App.useApp();
  const [volumeId, setVolumeId] = useState("全部");
  const [plotline, setPlotline] = useState("");
  const [status, setStatus] = useState("全部状态");
  const [keyOnly, setKeyOnly] = useState(false);
  const [sort, setSort] = useState("position");
  const statuses = [
    "全部状态",
    ...new Set(chapters.map((chapter) => chapter.status).filter(Boolean)),
  ];
  const visible = useMemo(() => {
    const rows = chapters.filter((chapter) => {
      if (volumeId !== "全部" && chapter.parent_id !== volumeId) return false;
      if (plotline.trim() && !chapter.plotline.includes(plotline.trim()))
        return false;
      if (status !== "全部状态" && chapter.status !== status) return false;
      if (keyOnly && !chapter.key_chapter) return false;
      return true;
    });
    rows.sort((a, b) => {
      if (sort === "name") return a.name.localeCompare(b.name, "zh");
      if (sort === "chars") return b.char_count - a.char_count;
      return a.position - b.position;
    });
    return rows;
  }, [chapters, volumeId, plotline, status, keyOnly, sort]);
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
  async function plan(chapter: StudioChapter) {
    try {
      await api(scoped(scope.id, "/creation-tasks"), "POST", {
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
          options={[
            { value: "全部", label: "按卷" },
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
          value={plotline}
          onChange={(event) => setPlotline(event.target.value)}
        />
        <Select
          aria-label="按状态"
          value={status}
          options={statuses.map((value) => ({ value, label: value }))}
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
            canEdit={canEdit}
            onDirtyChange={onDirtyChange}
            onSaved={onChanged}
            onMove={move}
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
  canEdit,
  onDirtyChange,
  onSaved,
  onMove,
  onPlan,
  onOpen,
}: {
  chapter: StudioChapter;
  canEdit: boolean;
  onDirtyChange: () => void;
  onSaved: () => void;
  onMove: (chapter: StudioChapter, direction: -1 | 1) => void;
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
  const [baseVersion, setBaseVersion] = useState(
    cached ? cached.baseVersion : chapter.version,
  );
  const [dirty, setDirty] = useState(Boolean(cached));
  const [conflictTriggered, setConflictTriggered] = useState(false);
  useEffect(() => {
    if (dirty) return;
    setBeat(chapter.beat_outline);
    setHook(chapter.hook);
    setBaseVersion(chapter.version);
  }, [chapter.version, chapter.beat_outline, chapter.hook, dirty]);
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
  async function saveWithExpected(expectedVersion: string) {
    try {
      await adopt(
        scope,
        [
          {
            op: "update",
            entity_id: chapter.id,
            expected: expectedVersion,
            data: { beat_outline: beat, hook },
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
      <p>
        汉字 {chapter.char_count}
        {chapter.key_chapter ? " · 关键章" : ""}
      </p>
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

function ForeshadowBoard({
  rows,
  canEdit,
  onChanged,
  onOpen,
}: {
  rows: StudioForeshadow[];
  canEdit: boolean;
  onChanged: () => void;
  onOpen: (id: string, title: string) => void;
}) {
  const { scope } = useWorkspace();
  const { message } = App.useApp();
  const [line, setLine] = useState("全部");
  const [alert, setAlert] = useState("全部");
  const [open, setOpen] = useState(false);
  const visible = rows.filter((row) => {
    if (line !== "全部" && row.line_type !== line && row.kind !== line)
      return false;
    if (alert !== "全部" && row.alert_state !== alert) return false;
    return true;
  });
  async function resolve(row: StudioForeshadow) {
    if (row.alert_state === "resolved") {
      message.warning("已兑现不能改回未完成");
      return;
    }
    try {
      await adopt(
        scope,
        [
          {
            op: "update",
            entity_id: row.id,
            expected: row.version,
            data: { status: "已兑现" },
          },
        ],
        "标成已兑现：" + row.name,
      );
      onChanged();
    } catch (error) {
      message.error(effectDetail(error));
    }
  }
  return (
    <section className="blueprint-stack">
      <div className="blueprint-tools">
        {["全部", "明线", "暗线", "灰线"].map((item) => (
          <Button
            key={item}
            type={line === item ? "primary" : "default"}
            onClick={() => setLine(item)}
          >
            {item}
          </Button>
        ))}
        <Button
          type={alert === "全部" ? "primary" : "default"}
          onClick={() => setAlert("全部")}
        >
          全部状态
        </Button>
        {ALERTS.map(([value, label]) => (
          <Button
            key={value}
            type={alert === value ? "primary" : "default"}
            onClick={() => setAlert(value)}
          >
            {label}
          </Button>
        ))}
        <Button disabled={!canEdit} onClick={() => setOpen(true)}>
          记下一条伏笔
        </Button>
      </div>
      {rows.length === 0 ? <p>还没有伏笔</p> : null}
      {rows.length > 0 && visible.length === 0 ? <p>没有符合的伏笔</p> : null}
      <div className="blueprint-columns">
        {ALERTS.map(([value, label]) => (
          <section key={value}>
            <h3>{label}</h3>
            {visible
              .filter((row) => row.alert_state === value)
              .map((row) => (
                <article key={row.id} className="blueprint-card">
                  <h3>{row.name}</h3>
                  <p>
                    {row.line_type || row.kind}
                    {row.alert_state === "overdue" ? " · 超期未回收" : ""}
                    {row.planted === false &&
                    (row.due_state === "due_soon" ||
                      row.due_state === "overdue")
                      ? " · 待埋设（到期提醒）"
                      : ""}
                  </p>
                  <div className="blueprint-tools">
                    <Button
                      disabled={!canEdit || row.alert_state === "resolved"}
                      onClick={() => resolve(row)}
                    >
                      标成已兑现
                    </Button>
                    <Button onClick={() => onOpen(row.id, row.name)}>
                      带入创作台给 AI 参考
                    </Button>
                  </div>
                </article>
              ))}
          </section>
        ))}
      </div>
      <ForeshadowForm
        open={open}
        onClose={() => setOpen(false)}
        onCreated={() => {
          setOpen(false);
          onChanged();
        }}
      />
    </section>
  );
}

function ForeshadowForm({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}) {
  const { scope } = useWorkspace();
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  return (
    <Modal
      title="记下一条伏笔"
      open={open}
      onCancel={onClose}
      onOk={() => form.submit()}
      confirmLoading={saving}
      destroyOnHidden
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={async (values) => {
          setSaving(true);
          setError("");
          try {
            await adopt(
              scope,
              [
                {
                  op: "create",
                  entity_id: crypto.randomUUID(),
                  kind: "伏笔",
                  name: values.name,
                  text: values.text || "",
                  data: {
                    status:
                      values.planted_chapter !== undefined &&
                      values.planted_chapter !== null
                        ? "已埋设"
                        : "待埋设",
                    line_type: values.line_type,
                    ...(values.planted_chapter !== undefined &&
                    values.planted_chapter !== null
                      ? { planted_chapter: values.planted_chapter }
                      : {}),
                    ...(values.expected_chapter !== undefined &&
                    values.expected_chapter !== null
                      ? { expected_chapter: values.expected_chapter }
                      : {}),
                  },
                },
              ],
              "记下一条伏笔：" + values.name,
            );
            form.resetFields();
            onCreated();
          } catch (reason) {
            setError(effectDetail(reason));
          } finally {
            setSaving(false);
          }
        }}
      >
        <Form.Item name="name" label="名称" rules={[{ required: true }]}>
          <Input />
        </Form.Item>
        <Form.Item
          name="line_type"
          label="线索"
          initialValue="明线"
          rules={[{ required: true }]}
        >
          <Select
            options={["明线", "暗线", "灰线"].map((value) => ({
              value,
              label: value,
            }))}
          />
        </Form.Item>
        <Form.Item name="planted_chapter" label="埋设章">
          <InputNumber min={0} />
        </Form.Item>
        <Form.Item name="expected_chapter" label="期望回收章">
          <InputNumber min={0} />
        </Form.Item>
        <Form.Item name="text" label="详细说明">
          <Input.TextArea autoSize={{ minRows: 3, maxRows: 6 }} />
        </Form.Item>
        {error ? <p>{error}</p> : null}
      </Form>
    </Modal>
  );
}
