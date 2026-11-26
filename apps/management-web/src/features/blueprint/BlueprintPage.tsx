import { DownloadOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import { Alert, App, Button, Input, Segmented } from "antd";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { adopt, api, scoped, type Json, type Scope } from "../../shared/api";
import { ErrorPanel, PageTitle } from "../../shared/components/Feedback";
import { queryKeys } from "../../shared/queryKeys";
import { scopeLine } from "../../shared/scopeLabel";
import {
  countBlueprintDrafts,
  fetchStudioOverview,
  reorderStudioEntities,
  setLastEditedChapter,
  setStudioHandoff,
  type StudioOutline,
  type StudioVolume,
} from "../../shared/studioApi";
import { useWorkspace } from "../../shared/WorkspaceContext";
import { effectDetail } from "../creation/effectDetail";
import { QuickExportModal } from "../exchange/QuickExportModal";
import "./blueprint.css";
import type { TrackedBlueprintTask } from "./blueprintTypes";
import {
  BlueprintTaskBanner,
  OutlineEditor,
  VolumeCard,
} from "./components/BlueprintStructureCards";
import { ForeshadowBoard } from "./components/ForeshadowBoard";
import { FoundingProfileCard } from "./components/FoundingProfileCard";
import { OutlineCorkboard } from "./components/OutlineCorkboard";

export function BlueprintPage() {
  const { scope, sessionKey, refresh, setDirty } = useWorkspace();
  const { message, modal } = App.useApp();
  const navigate = useNavigate();
  const [view, setView] = useState("总纲与剧情走向");
  const [creating, setCreating] = useState<"outline" | "volume" | null>(null);
  const [name, setName] = useState("");
  const [dirtyTick, setDirtyTick] = useState(0);
  const [exportOpen, setExportOpen] = useState(false);
  const [trackedTasks, setTrackedTasks] = useState<TrackedBlueprintTask[]>([]);

  const canEdit = scope.actions.includes("edit");
  const canCheckOps = scope.actions.some((a) =>
    ["operate", "edit", "assess", "export"].includes(a),
  );

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
    queryKey: queryKeys.studioOverview(scope.id),
    queryFn: () => fetchStudioOverview(scope.id),
    staleTime: 0,
    refetchOnMount: "always",
  });

  const jobs = useQuery({
    queryKey: queryKeys.jobs(scope.id, { summary: true }),
    queryFn: () => api<Json[]>(scoped(scope.id, "/jobs?summary=true")),
    enabled: trackedTasks.length > 0,
    refetchInterval: 2500,
  });

  const trackedRows = useMemo(() => {
    if (!trackedTasks.length) return [];
    const byId = new Map((jobs.data || []).map((j) => [String(j.id), j]));
    return trackedTasks.map((t) => ({
      ...t,
      job: byId.get(t.jobId),
    }));
  }, [trackedTasks, jobs.data]);

  const anyTrackedQueued = trackedRows.some((r) => r.job?.state === "queued");
  const operations = useQuery({
    queryKey: queryKeys.operations(scope.id),
    queryFn: () => api<Json>(scoped(scope.id, "/operations")),
    enabled: anyTrackedQueued && canCheckOps,
    refetchInterval: 8000,
  });
  const workerOffline =
    anyTrackedQueued && operations.data?.worker?.online === false;

  async function create(kind: "outline" | "volume") {
    const label = name.trim();
    if (!label) return;
    try {
      const fresh = await api<Scope>(scoped(scope.id, ""));
      const position =
        kind === "volume"
          ? overview.data?.volumes.length || 0
          : overview.data?.outlines.length || 0;
      await adopt(
        fresh,
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
      const created = await api<Json>(
        scoped(scope.id, "/creation-tasks"),
        "POST",
        {
          objective: "推演全书大纲与分卷走向",
          scheme: "P2",
          mode: "create",
          kind: outline?.kind || "outline",
          name: outline?.name || "全书大纲",
          entity_id: outline?.id || null,
          stages: ["plan"],
          max_revisions: 0,
          token_budget: 24000,
        },
      );
      setTrackedTasks((prev) => [
        {
          jobId: String(created.id),
          entityId: outline?.id,
          isChapter: false,
          label: `推演大纲：${outline?.name || "全书大纲"}`,
        },
        ...prev.filter((item) => item.jobId !== String(created.id)),
      ]);
      message.success("已进入自动创作流程");
    } catch (error) {
      message.error(effectDetail(error));
    }
  }

  function registerTrackedTask(task: TrackedBlueprintTask) {
    setTrackedTasks((prev) => [
      task,
      ...prev.filter((item) => item.jobId !== task.jobId),
    ]);
  }

  function jumpToWorkTask(item: TrackedBlueprintTask) {
    navigateWithGuard(() => {
      if (item.isChapter && item.entityId) {
        setLastEditedChapter(scope.id, item.entityId);
      }
      setStudioHandoff({
        scopeId: scope.id,
        chapterId: item.isChapter ? item.entityId : undefined,
        jobId: item.jobId,
        returnTo: "blueprint",
      });
      const qs = new URLSearchParams();
      qs.set("scope", scope.id);
      if (item.entityId) qs.set("entity", item.entityId);
      qs.set("job", item.jobId);
      qs.set("from", "blueprint");
      navigate(`/work?${qs.toString()}`);
    });
  }

  async function moveVolume(volume: StudioVolume, direction: -1 | 1) {
    const vols = (overview.data?.volumes || [])
      .slice()
      .sort((a, b) => a.position - b.position || a.id.localeCompare(b.id));
    const index = vols.findIndex((v) => v.id === volume.id);
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
      overview.refetch();
    } catch (error) {
      message.error(effectDetail(error));
    }
  }

  async function archiveVolume(volume: StudioVolume) {
    try {
      const fresh = await api<Scope>(scoped(scope.id, ""));
      const childChapters = (overview.data?.chapters || []).filter(
        (ch) => ch.parent_id === volume.id,
      );
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
      overview.refetch();
      message.success("分卷已归档，所属章节已回到未归卷");
    } catch (error) {
      message.error(effectDetail(error));
    }
  }

  return (
    <div className="blueprint-page">
      <PageTitle
        title="大纲与暗线"
        note={scopeLine(scope.name, scope.kind, scope.version)}
        actions={
          <Button
            icon={<DownloadOutlined />}
            onClick={() => setExportOpen(true)}
          >
            导出成稿
          </Button>
        }
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
      <BlueprintTaskBanner
        rows={trackedRows}
        workerOffline={workerOffline}
        onJumpToWork={jumpToWorkTask}
        onDismiss={(jobId) =>
          setTrackedTasks((prev) => prev.filter((t) => t.jobId !== jobId))
        }
      />
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
          <FoundingProfileCard
            founding={overview.data.founding}
            canEdit={canEdit}
            onSaved={() => {
              refresh();
              overview.refetch();
            }}
          />
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
                style={{ maxWidth: 320 }}
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
              <Button
                onClick={() => {
                  setCreating(null);
                  setName("");
                }}
              >
                取消
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
          {overview.data.volumes.map((volume, idx) => (
            <VolumeCard
              key={volume.id}
              volume={volume}
              isFirst={idx === 0}
              isLast={idx === overview.data.volumes.length - 1}
              chapterCount={
                overview.data.chapters.filter((c) => c.parent_id === volume.id)
                  .length
              }
              canEdit={canEdit}
              onMove={moveVolume}
              onArchive={archiveVolume}
              onSaved={() => {
                refresh();
                overview.refetch();
              }}
            />
          ))}
        </section>
      ) : null}
      {view === "细纲卡片墙" && overview.data ? (
        <OutlineCorkboard
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
          onTaskCreated={registerTrackedTask}
          onOpen={(chapterId) =>
            navigateWithGuard(() => {
              setLastEditedChapter(scope.id, chapterId);
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
          canSecret={scope.actions.includes("secret")}
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
      <QuickExportModal
        open={exportOpen}
        onClose={() => setExportOpen(false)}
        volumes={overview.data?.volumes || []}
        chapters={overview.data?.chapters || []}
        origin="blueprint"
      />
    </div>
  );
}
