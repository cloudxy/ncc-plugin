import { PlusOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import { App, Button, Card, Form } from "antd";
import { useEffect, useMemo, useRef, useState, type Key } from "react";
import { useNavigate } from "react-router-dom";
import {
  adopt,
  api,
  scoped,
  type Definition,
  type Entity,
  type Json,
} from "../../shared/api";
import { ErrorPanel, PageTitle } from "../../shared/components/Feedback";
import { queryKeys } from "../../shared/queryKeys";
import { scopeLine } from "../../shared/scopeLabel";
import {
  fetchStudioCatalog,
  fetchStudioOverview,
  setStudioHandoff,
} from "../../shared/studioApi";
import { useDelayed } from "../../shared/useDelayed";
import { waitForCreationDraft } from "../../shared/waitForCreationDraft";
import { useWorkspace } from "../../shared/WorkspaceContext";
import { EntityDrawer } from "./components/EntityDrawer";
import { MaterialCardGrid } from "./components/MaterialCardGrid";
import { MaterialCreateModal } from "./components/MaterialCreateModal";
import { MaterialToolbar } from "./components/MaterialToolbar";
import { FALLBACK_GROUPS, viewEntries } from "./materialHelpers";
import "./materials.css";

export function MaterialsPage() {
  const { scope, refresh } = useWorkspace();
  const { message, modal } = App.useApp();
  const navigate = useNavigate();
  const [qInput, setQInput] = useState("");
  const [q, setQ] = useState("");
  const [kind, setKind] = useState<string>();
  const [group, setGroup] = useState("all");
  const [sortKey, setSortKey] = useState("名称");
  const [view, setView] = useState<"表格" | "卡片">("表格");
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<Key[]>([]);
  const [detail, setDetail] = useState<string>();
  const [creating, setCreating] = useState(false);
  const [form] = Form.useForm();
  const [createId, setCreateId] = useState(crypto.randomUUID());
  const [newKind, setNewKind] = useState("character");
  const [direction, setDirection] = useState("");
  const [drafting, setDrafting] = useState(false);
  const [draftNote, setDraftNote] = useState("");
  const [draftError, setDraftError] = useState("");
  const draftAbort = useRef<AbortController | null>(null);
  const canEdit = scope.actions.includes("edit");

  const catalog = useQuery({
    queryKey: queryKeys.studioCatalog(),
    queryFn: fetchStudioCatalog,
  });
  const overview = useQuery({
    queryKey: queryKeys.studioOverview(scope.id),
    queryFn: () => fetchStudioOverview(scope.id),
  });
  const groups = catalog.data?.codex_groups?.length
    ? catalog.data.codex_groups
    : FALLBACK_GROUPS;
  const currentGroup = groups.find((item) => item.id === group);
  const known = useMemo(
    () => new Set(groups.flatMap((item) => item.kinds)),
    [groups],
  );
  const defs = useQuery({
    queryKey: queryKeys.definitions(scope.id),
    queryFn: () => api<Definition[]>(scoped(scope.id, "/definitions")),
  });
  const serverSort =
    sortKey === "排序号"
      ? "position"
      : sortKey === "修订版本"
        ? "version"
        : "name";
  const query = useQuery({
    queryKey: queryKeys.materials(scope.id, {
      q,
      group,
      kind,
      offset,
      sortKey,
    }),
    queryFn: () => {
      const payload: Json = {
        q,
        offset,
        limit: 50,
        sort: serverSort,
      };
      if (kind) {
        payload.kind = kind;
      } else if (group === "other") {
        payload.exclude_kinds = Array.from(known).slice(0, 64);
      } else if (currentGroup) {
        payload.kinds = currentGroup.kinds.slice(0, 64);
      }
      return api<Json>(scoped(scope.id, "/entities/search"), "POST", payload);
    },
  });
  const showSkeleton = useDelayed(query.isPending && !query.data);
  const shown = useMemo(
    () => (query.data?.items || []) as Entity[],
    [query.data],
  );
  const totalCount =
    typeof query.data?.total === "number" ? query.data.total : shown.length;
  const hasNextPage =
    query.data?.next_offset != null || offset + shown.length < totalCount;
  const nextOffset =
    typeof query.data?.next_offset === "number"
      ? query.data.next_offset
      : offset + 50;
  const libraryEmpty =
    query.isSuccess &&
    !q &&
    !kind &&
    group === "all" &&
    offset === 0 &&
    totalCount === 0;
  const searchEmpty =
    query.isSuccess && !!q && group === "all" && !kind && totalCount === 0;
  const filterEmpty =
    query.isSuccess && !libraryEmpty && !searchEmpty && totalCount === 0;
  const definition = defs.data?.find((item) => item.key === newKind);
  const activeGroup = groups.find(
    (item) =>
      item.kinds.includes(newKind) ||
      item.kinds.includes(definition?.spec.label || ""),
  );
  const savedViews = viewEntries(scope.config);

  useEffect(() => {
    const id = new URLSearchParams(location.search).get("entity");
    if (id) setDetail(id);
  }, []);
  useEffect(() => () => draftAbort.current?.abort(), []);

  function chooseGroup(next: string) {
    setGroup(next);
    setKind(undefined);
    setOffset(0);
    setSelected([]);
  }
  function chooseKind(next: string) {
    setKind((current) => (current === next ? undefined : next));
    setOffset(0);
    setSelected([]);
  }
  function showAll() {
    setGroup("all");
    setKind(undefined);
    setOffset(0);
    setSelected([]);
  }
  function clearSearch() {
    setQ("");
    setQInput("");
    setOffset(0);
  }
  function applyView(saved: Json) {
    const nextQ = typeof saved.q === "string" ? saved.q : "";
    const nextKind = typeof saved.kind === "string" ? saved.kind : undefined;
    setQ(nextQ);
    setQInput(nextQ);
    setKind(nextKind);
    setOffset(0);
    setSelected([]);
    if (!nextKind) {
      setGroup("all");
      return;
    }
    const owner = groups.find((item) => item.kinds.includes(nextKind));
    setGroup(owner?.id || "other");
  }
  function handoff(row: Entity) {
    setStudioHandoff({
      scopeId: scope.id,
      sourceEntity: { id: row.id, title: row.name },
    });
    navigate("/work");
  }
  async function create(values: Json) {
    try {
      const data = Object.fromEntries(
        Object.entries(values.data || {}).filter(
          ([, value]) => value !== undefined && value !== null,
        ),
      );
      await adopt(
        scope,
        [
          {
            op: "create",
            entity_id: createId,
            kind: newKind,
            name: values.name,
            data,
            text: values.text || "",
            secret: !!values.secret,
          },
        ],
        "新建资料：" + values.name,
      );
      setCreating(false);
      form.resetFields();
      setDirection("");
      setDraftNote("");
      setDraftError("");
      setCreateId(crypto.randomUUID());
      refresh();
      query.refetch();
      overview.refetch();
      message.success("资料已建立");
    } catch (error) {
      message.error((error as Error).message);
    }
  }
  async function retire() {
    const rows = shown.filter((row) => selected.includes(row.id));
    if (!rows.length) return;
    modal.confirm({
      title: `停用选中的 ${rows.length} 条设定？`,
      content: "历史修订仍在。",
      okText: "停用",
      cancelText: "取消",
      onOk: async () => {
        try {
          await adopt(
            scope,
            rows.map((row) => ({
              op: "retire",
              entity_id: row.id,
              expected: row.version,
            })),
            "批量停用资料",
          );
          setSelected([]);
          refresh();
          query.refetch();
        } catch (error) {
          message.error((error as Error).message);
        }
      },
    });
  }
  async function draftWithAi() {
    const name = String(form.getFieldValue("name") || "").trim();
    if (!canEdit) return;
    if (!name) {
      message.info("先写下名称");
      return;
    }
    draftAbort.current?.abort();
    const controller = new AbortController();
    draftAbort.current = controller;
    setDrafting(true);
    setDraftError("");
    setDraftNote("");
    try {
      const created = await api<Json>(
        scoped(scope.id, "/creation-tasks"),
        "POST",
        {
          objective:
            direction.trim() ||
            `根据名称「${name}」写一份设定初稿，只提供可编辑正文，不写入资料库。`,
          scheme: "P3",
          mode: "create",
          kind: newKind,
          name,
          stages: ["write"],
          guidance: direction.trim(),
          max_revisions: 0,
        },
        controller.signal,
      );
      const text = await waitForCreationDraft(
        scope.id,
        created.id,
        controller.signal,
        "初稿没有写出来",
      );
      form.setFieldValue("text", text);
      setDraftNote("初稿在编辑区，尚未保存。保存后才会写入资料。");
      message.success("初稿已填入，尚未保存");
    } catch (error) {
      if ((error as Error).name === "AbortError") return;
      setDraftError("初稿没有写出来");
    } finally {
      setDrafting(false);
    }
  }

  const selectedRows = shown.filter((row) => selected.includes(row.id));
  const emptyNode = libraryEmpty ? (
    <div className="mat-empty">
      <p>还没有设定</p>
      <p>人物、功法、场景都可以记在这里。</p>
      <Button
        type="primary"
        disabled={!canEdit}
        onClick={() => setCreating(true)}
      >
        新建资料
      </Button>
    </div>
  ) : searchEmpty ? (
    <div className="mat-empty">
      <p>没有符合的设定</p>
      <Button onClick={clearSearch}>清除搜索</Button>
    </div>
  ) : filterEmpty ? (
    <div className="mat-empty">
      <p>这个分类里还没有设定</p>
      <Button onClick={showAll}>查看全部</Button>
    </div>
  ) : (
    "正在载入"
  );

  return (
    <>
      <PageTitle
        title="作品资料"
        note="万象设定与人物角色管理"
        actions={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            disabled={!canEdit}
            onClick={() => setCreating(true)}
          >
            新建资料
          </Button>
        }
      />
      <p className="mat-scope">
        {scopeLine(scope.name, scope.kind, scope.version)}
      </p>
      {!canEdit && <p className="mat-note">当前范围不能编辑</p>}
      <Card>
        <MaterialToolbar
          groups={groups}
          group={group}
          currentGroup={currentGroup}
          kind={kind}
          groupCounts={overview.data?.codex_counts.groups}
          countsLoaded={overview.isSuccess}
          qInput={qInput}
          view={view}
          sortKey={sortKey}
          canEdit={canEdit}
          selectedCount={selectedRows.length}
          savedViews={savedViews}
          onShowAll={showAll}
          onChooseGroup={chooseGroup}
          onChooseKind={chooseKind}
          onQInputChange={(val) => {
            setQInput(val);
            if (!val) {
              setQ("");
              setOffset(0);
            }
          }}
          onSearch={(val) => {
            setQ(val);
            setQInput(val);
            setOffset(0);
          }}
          onViewChange={setView}
          onSortChange={(val) => {
            setSortKey(val);
            setOffset(0);
          }}
          onSaveView={() => {
            modal.confirm({
              title: "保存当前筛选为个人视图",
              content: "此视图仅保存在你的账号下。",
              onOk: () =>
                api(scoped(scope.id, "/views"), "POST", {
                  name: kind || q || currentGroup?.label || "全部资料",
                  query: { q, kind, limit: 50 },
                }).then(() => {
                  refresh();
                  message.success("视图已保存");
                }),
            });
          }}
          onRetireSelected={() => void retire()}
          onApplyView={applyView}
        />
        <ErrorPanel error={query.error} retry={() => query.refetch()} />
        {query.isError && (
          <p>
            {query.error instanceof TypeError
              ? "网络中断了，设定没有载入。"
              : ""}
          </p>
        )}
        <MaterialCardGrid
          view={view}
          showSkeleton={showSkeleton}
          loading={query.isPending}
          rows={shown}
          groups={groups}
          defs={defs.data}
          canEdit={canEdit}
          selected={selected}
          emptyNode={emptyNode}
          offset={offset}
          totalCount={totalCount}
          hasServerTotal={typeof query.data?.total === "number"}
          hasNextPage={hasNextPage}
          nextOffset={nextOffset}
          onSelectedChange={setSelected}
          onOpenDetail={setDetail}
          onHandoff={handoff}
          onPrevPage={() => setOffset(Math.max(0, offset - 50))}
          onNextPage={() => setOffset(nextOffset)}
        />
      </Card>
      <EntityDrawer
        id={detail}
        onClose={() => {
          setDetail(undefined);
          query.refetch();
        }}
      />
      <MaterialCreateModal
        open={creating}
        form={form}
        groups={groups}
        defs={defs.data}
        newKind={newKind}
        activeGroup={activeGroup}
        definition={definition}
        canEdit={canEdit}
        canSecret={scope.actions.includes("secret")}
        direction={direction}
        drafting={drafting}
        draftNote={draftNote}
        draftError={draftError}
        onNewKindChange={setNewKind}
        onDirectionChange={setDirection}
        onDraftWithAi={() => void draftWithAi()}
        onCancel={() => {
          draftAbort.current?.abort();
          setCreating(false);
        }}
        onSubmit={(values) => void create(values)}
      />
    </>
  );
}
