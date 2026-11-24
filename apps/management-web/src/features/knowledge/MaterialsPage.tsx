import { DeleteOutlined, PlusOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import {
  Alert,
  App,
  Button,
  Card,
  Checkbox,
  Form,
  Input,
  Modal,
  Segmented,
  Select,
  Skeleton,
  Space,
  Table,
  Tag,
  Typography,
} from "antd";
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
import { scopeLine } from "../../shared/scopeLabel";
import {
  fetchStudioCatalog,
  fetchStudioOverview,
  setStudioHandoff,
  type CodexGroup,
} from "../../shared/studioApi";
import { useWorkspace } from "../../shared/WorkspaceContext";
import { selectedCandidate } from "../creation/jobCandidate";
import { EntityDrawer } from "./components/EntityDrawer";
import { PropertyFields } from "./components/PropertyFields";
import "./materials.css";

const FALLBACK_GROUPS: CodexGroup[] = [
  {
    id: "characters",
    label: "人物与角色职业",
    description: "",
    kinds: [
      "人物",
      "身份",
      "法师",
      "人物弧",
      "动机",
      "秘密",
      "血脉",
      "体质",
      "语言风格",
      "character",
    ],
    recommended_fields: [
      "motivation",
      "psychology",
      "arc_type",
      "voice",
      "factions",
      "pov",
    ],
  },
  {
    id: "beings",
    label: "种族与异界生物",
    description: "",
    kinds: [
      "种族",
      "妖兽",
      "魔兽",
      "异世界生物",
      "亡灵",
      "鬼",
      "魔",
      "异族人",
      "神兽",
      "灵宠",
      "妖",
      "兽",
      "精怪",
    ],
    recommended_fields: ["habitat", "limitations", "factions", "description"],
  },
  {
    id: "techniques",
    label: "功法技能与特效",
    description: "",
    kinds: [
      "功法",
      "技能",
      "特效",
      "法术",
      "神通",
      "阵法",
      "符箓",
      "境界",
      "招式",
    ],
    recommended_fields: [
      "limitations",
      "side_effects",
      "usage_guide",
      "description",
    ],
  },
  {
    id: "artifacts",
    label: "丹药武器与器物",
    description: "",
    kinds: ["丹药", "现代武器", "法宝", "武器", "道具", "异火", "配方", "丹方"],
    recommended_fields: ["limitations", "side_effects", "cost", "usage_guide"],
  },
  {
    id: "places",
    label: "场景地图与都市舞台",
    description: "",
    kinds: [
      "场景",
      "地图",
      "都市",
      "城池",
      "秘境",
      "拍卖会",
      "拍卖行",
      "战场",
      "scene",
      "location",
    ],
    recommended_fields: ["description", "plotline", "hook"],
  },
  {
    id: "orders",
    label: "组织势力与世界规则",
    description: "",
    kinds: ["宗门", "帝国", "商会", "法则", "制度", "货币", "家族", "王朝"],
    recommended_fields: ["factions", "limitations", "description"],
  },
];

const CARD_LABELS: Record<string, string> = {
  motivation: "动机",
  psychology: "心理与伤口",
  arc_type: "人物弧光",
  voice: "语言风格",
  factions: "阵营",
  pov: "视角人物",
  habitat: "栖息地",
  limitations: "限制与代价",
  side_effects: "副作用",
  usage_guide: "用法禁忌",
  description: "摘要",
  cost: "代价",
  plotline: "剧情线",
  hook: "追读钩",
};

function useDelayed(active: boolean) {
  const [ready, setReady] = useState(false);
  useEffect(() => {
    if (!active) {
      setReady(false);
      return;
    }
    const timer = window.setTimeout(() => setReady(true), 200);
    return () => window.clearTimeout(timer);
  }, [active]);
  return ready;
}

function versionNumber(version: string) {
  const tail = Number(version.split(":").pop());
  return Number.isFinite(tail) ? tail : 0;
}

function viewEntries(config: Json | undefined): [string, Json][] {
  const views = config?.views;
  if (!views || typeof views !== "object" || Array.isArray(views)) return [];
  return Object.entries(views).filter(
    (entry): entry is [string, Json] =>
      !!entry[1] && typeof entry[1] === "object" && !Array.isArray(entry[1]),
  );
}

function fieldText(value: unknown): string {
  if (value === undefined || value === null || value === "") return "";
  if (typeof value === "string" || typeof value === "number")
    return String(value);
  if (typeof value === "boolean") return value ? "是" : "否";
  if (Array.isArray(value))
    return value
      .map((item) => fieldText(item))
      .filter(Boolean)
      .join("、");
  return "";
}

async function waitForDraft(
  scopeId: string,
  jobId: string,
  signal: AbortSignal,
) {
  for (let attempt = 0; attempt < 30; attempt += 1) {
    const job = await api<Json>(
      scoped(scopeId, `/jobs/${jobId}`),
      "GET",
      undefined,
      signal,
    );
    const text = selectedCandidate(job)?.text;
    if (typeof text === "string" && text.trim()) return text;
    if (job.state === "failed" || job.state === "cancelled") {
      throw new Error("初稿没有写出来");
    }
    if (["waiting", "qualified", "succeeded", "applied"].includes(job.state)) {
      throw new Error("初稿没有写出来");
    }
    await new Promise<void>((resolve, reject) => {
      const timer = window.setTimeout(resolve, 2000);
      signal.addEventListener(
        "abort",
        () => {
          window.clearTimeout(timer);
          reject(new DOMException("aborted", "AbortError"));
        },
        { once: true },
      );
    });
  }
  throw new Error("初稿没有写出来");
}

export function MaterialsPage() {
  const { scope, refresh } = useWorkspace(),
    { message, modal } = App.useApp(),
    navigate = useNavigate(),
    [qInput, setQInput] = useState(""),
    [q, setQ] = useState(""),
    [kind, setKind] = useState<string>(),
    [group, setGroup] = useState("all"),
    [sortKey, setSortKey] = useState("名称"),
    [view, setView] = useState<"表格" | "卡片">("表格"),
    [offset, setOffset] = useState(0),
    [selected, setSelected] = useState<Key[]>([]),
    [detail, setDetail] = useState<string>(),
    [creating, setCreating] = useState(false),
    [form] = Form.useForm(),
    [createId, setCreateId] = useState(crypto.randomUUID());
  const [newKind, setNewKind] = useState("character");
  const [direction, setDirection] = useState("");
  const [drafting, setDrafting] = useState(false);
  const [draftNote, setDraftNote] = useState("");
  const [draftError, setDraftError] = useState("");
  const draftAbort = useRef<AbortController | null>(null);
  const canEdit = scope.actions.includes("edit");
  const catalog = useQuery({
    queryKey: ["studio", "catalog"],
    queryFn: fetchStudioCatalog,
  });
  const overview = useQuery({
    queryKey: ["scope", scope.id, "studio", "overview"],
    queryFn: () => fetchStudioOverview(scope.id),
  });
  const groups = catalog.data?.codex_groups?.length
    ? catalog.data.codex_groups
    : FALLBACK_GROUPS;
  const defs = useQuery({
    queryKey: ["scope", scope.id, "definitions"],
    queryFn: () => api<Definition[]>(scoped(scope.id, "/definitions")),
  });
  const query = useQuery({
    queryKey: ["scope", scope.id, "materials", q, kind, offset, sortKey],
    queryFn: () =>
      api<Json>(scoped(scope.id, "/entities/search"), "POST", {
        q,
        kind,
        offset,
        limit: 50,
        sort: sortKey === "排序号" ? "position" : "name",
      }),
  });
  const showSkeleton = useDelayed(query.isPending && !query.data);
  const known = useMemo(
    () => new Set(groups.flatMap((item) => item.kinds)),
    [groups],
  );
  const shown = useMemo(() => {
    const items = ((query.data?.items || []) as Entity[]).filter((row) => {
      if (group === "all") return true;
      const hit = known.has(row.kind);
      if (group === "other") return !hit;
      const current = groups.find((item) => item.id === group);
      return current ? current.kinds.includes(row.kind) : true;
    });
    if (sortKey !== "修订版本") return items;
    return [...items].sort(
      (a, b) =>
        versionNumber(b.version) - versionNumber(a.version) ||
        a.name.localeCompare(b.name, "zh"),
    );
  }, [query.data, group, groups, known, sortKey]);
  const libraryEmpty =
    query.isSuccess &&
    !q &&
    !kind &&
    group === "all" &&
    offset === 0 &&
    (query.data?.items?.length || 0) === 0;
  const searchEmpty =
    query.isSuccess && !!q && group === "all" && !kind && shown.length === 0;
  const filterEmpty =
    query.isSuccess && !libraryEmpty && !searchEmpty && shown.length === 0;
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
  function kindLabel(value: string) {
    const found = defs.data?.find((item) => item.key === value);
    return found?.spec.label || value;
  }
  function fieldLabel(key: string) {
    if (CARD_LABELS[key]) return CARD_LABELS[key];
    for (const item of defs.data || []) {
      const rule = item.spec.properties?.[key];
      if (rule?.label) return String(rule.label);
    }
    return key;
  }
  function openDetail(id: string) {
    setDetail(id);
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
      const text = await waitForDraft(scope.id, created.id, controller.signal);
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

  const currentGroup = groups.find((item) => item.id === group);
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
        <div className="mat-capsules" role="group" aria-label="万象设定领域">
          <Button
            type={group === "all" ? "primary" : "default"}
            aria-pressed={group === "all"}
            onClick={showAll}
          >
            全部
          </Button>
          {groups.map((item) => {
            const count = overview.data?.codex_counts.groups.find(
              (entry) => entry.id === item.id,
            )?.count;
            return (
              <Button
                key={item.id}
                type={group === item.id ? "primary" : "default"}
                aria-pressed={group === item.id}
                onClick={() => chooseGroup(item.id)}
              >
                {item.label}
                {overview.isSuccess && typeof count === "number"
                  ? ` ${count}`
                  : ""}
              </Button>
            );
          })}
          <Button
            type={group === "other" ? "primary" : "default"}
            aria-pressed={group === "other"}
            onClick={() => chooseGroup("other")}
          >
            其他/未归类
          </Button>
        </div>
        {currentGroup && (
          <Space wrap style={{ marginBottom: 12 }}>
            {currentGroup.kinds.map((token) => (
              <Tag.CheckableTag
                key={token}
                checked={kind === token}
                onChange={() => chooseKind(token)}
              >
                {token}
              </Tag.CheckableTag>
            ))}
          </Space>
        )}
        <div className="table-toolbar">
          <Space wrap>
            <Input.Search
              aria-label="搜索作品资料"
              placeholder="搜索名称或原文，支持中文专名"
              value={qInput}
              allowClear
              style={{ width: 300 }}
              onChange={(event) => {
                setQInput(event.target.value);
                if (!event.target.value) {
                  setQ("");
                  setOffset(0);
                }
              }}
              onSearch={(value) => {
                setQ(value);
                setQInput(value);
                setOffset(0);
              }}
            />
            <Segmented
              aria-label="视图"
              value={view}
              options={["表格", "卡片"]}
              onChange={(value) => setView(value as "表格" | "卡片")}
            />
            <Select
              aria-label="排序"
              value={sortKey}
              style={{ width: 140 }}
              options={[
                { value: "名称", label: "名称" },
                { value: "排序号", label: "排序号" },
                { value: "修订版本", label: "修订版本" },
              ]}
              onChange={(value) => {
                setSortKey(value);
                setOffset(0);
              }}
            />
            <Button
              disabled={!canEdit}
              onClick={() => {
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
            >
              保存视图
            </Button>
          </Space>
          <Space wrap>
            {selectedRows.length > 0 && (
              <Tag>选中本页 {selectedRows.length} 项</Tag>
            )}
            <Button
              danger
              icon={<DeleteOutlined />}
              disabled={!canEdit || selectedRows.length === 0}
              onClick={retire}
            >
              批量停用
            </Button>
          </Space>
        </div>
        {savedViews.length > 0 && (
          <Space wrap style={{ marginBottom: 12 }}>
            {savedViews.map(([name, saved]) => (
              <Button key={name} onClick={() => applyView(saved)}>
                {name}
              </Button>
            ))}
          </Space>
        )}
        <ErrorPanel error={query.error} retry={() => query.refetch()} />
        {query.isError && (
          <p>
            {query.error instanceof TypeError
              ? "网络中断了，设定没有载入。"
              : ""}
          </p>
        )}
        {showSkeleton ? (
          <Skeleton active paragraph={{ rows: 8 }} />
        ) : view === "表格" ? (
          <Table
            rowKey="id"
            loading={query.isPending}
            dataSource={shown}
            pagination={false}
            scroll={{ x: 1000 }}
            locale={{ emptyText: emptyNode }}
            rowSelection={
              canEdit
                ? { selectedRowKeys: selected, onChange: setSelected }
                : undefined
            }
            columns={[
              {
                title: "名称",
                dataIndex: "name",
                width: 220,
                onCell: (row: Entity) => ({
                  onClick: () => openDetail(row.id),
                  style: { cursor: "pointer" },
                }),
                render: (name: string, row: Entity) => (
                  <Button type="link" onClick={() => openDetail(row.id)}>
                    {name}
                  </Button>
                ),
              },
              {
                title: "类型",
                dataIndex: "kind",
                width: 160,
                render: (value: string) => <Tag>{kindLabel(value)}</Tag>,
              },
              {
                title: "摘要",
                render: (_value, row: Entity) =>
                  row.data?.description || row.text_preview || "—",
              },
              {
                title: "标签",
                render: (_value, row: Entity) => (
                  <Space wrap>
                    {row.data?.tags?.map((value: string) => (
                      <Tag key={value}>{value}</Tag>
                    ))}
                  </Space>
                ),
              },
              {
                title: "排序号",
                width: 90,
                render: (_value, row: Entity) =>
                  typeof row.data?.position === "number"
                    ? row.data.position
                    : "—",
              },
              {
                title: "版本",
                dataIndex: "version",
                width: 100,
                render: (value: string) => value.split(":").pop(),
              },
              {
                title: "范围",
                dataIndex: "secret",
                width: 100,
                render: (value: boolean) => (
                  <Tag color={value ? "orange" : "default"}>
                    {value ? "作者秘密" : "普通资料"}
                  </Tag>
                ),
              },
            ]}
          />
        ) : (
          <>
            {shown.length === 0 ? (
              emptyNode
            ) : (
              <div className="mat-card-grid">
                {shown.map((row) => {
                  const owner = groups.find((item) =>
                    item.kinds.includes(row.kind),
                  );
                  const keys = owner?.recommended_fields || [];
                  return (
                    <article key={row.id} className="mat-card">
                      <Card
                        title={
                          <h3 className="mat-card-name" title={row.name}>
                            {row.name}
                          </h3>
                        }
                        extra={
                          canEdit ? (
                            <Checkbox
                              aria-label={`选择 ${row.name}`}
                              checked={selected.includes(row.id)}
                              onChange={(event) =>
                                setSelected((current) =>
                                  event.target.checked
                                    ? [...current, row.id]
                                    : current.filter((id) => id !== row.id),
                                )
                              }
                            />
                          ) : null
                        }
                      >
                        <Tag>{kindLabel(row.kind)}</Tag>
                        <p>
                          {row.data?.description ||
                            row.text_preview ||
                            "还没有摘要"}
                        </p>
                        <div className="mat-highlight">
                          {keys.map((key) => {
                            const text = fieldText(row.data?.[key]);
                            if (!text) return null;
                            return (
                              <div key={key}>
                                <strong>{fieldLabel(key)}：</strong>
                                {text}
                              </div>
                            );
                          })}
                        </div>
                        <Space wrap>
                          <Button onClick={() => openDetail(row.id)}>
                            详情编辑
                          </Button>
                          <Button onClick={() => handoff(row)}>
                            带入创作台
                          </Button>
                        </Space>
                      </Card>
                    </article>
                  );
                })}
              </div>
            )}
          </>
        )}
        <div className="pager">
          <Typography.Text type="secondary">
            {query.isPending
              ? "正在载入"
              : `当前 ${shown.length} 条 · 服务端分页`}
          </Typography.Text>
          <Space>
            <Button
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - 50))}
            >
              上一页
            </Button>
            <Button
              disabled={query.data?.next_offset == null}
              onClick={() => setOffset(query.data?.next_offset || 0)}
            >
              下一页
            </Button>
          </Space>
        </div>
      </Card>
      <EntityDrawer
        id={detail}
        onClose={() => {
          setDetail(undefined);
          query.refetch();
        }}
      />
      <Modal
        title="新建资料"
        width={720}
        open={creating}
        onCancel={() => {
          draftAbort.current?.abort();
          setCreating(false);
        }}
        onOk={() => form.submit()}
        okButtonProps={{ disabled: !canEdit }}
        destroyOnHidden
      >
        <Form form={form} layout="vertical" onFinish={create}>
          <Form.Item label="类型">
            <Select
              showSearch
              value={newKind}
              optionFilterProp="label"
              options={[
                ...groups.map((item) => ({
                  label: item.label,
                  options: item.kinds.map((token) => {
                    const found = defs.data?.find(
                      (entry) =>
                        entry.key === token || entry.spec.label === token,
                    );
                    return {
                      value: found?.key || token,
                      label: found
                        ? found.spec.label === found.key
                          ? found.key
                          : `${found.spec.label} · ${found.key}`
                        : token,
                    };
                  }),
                })),
                {
                  label: "其他/未归类",
                  options: (defs.data || [])
                    .filter(
                      (entry) =>
                        !entry.spec.relation &&
                        !groups.some(
                          (item) =>
                            item.kinds.includes(entry.key) ||
                            item.kinds.includes(entry.spec.label),
                        ),
                    )
                    .map((entry) => ({
                      value: entry.key,
                      label:
                        entry.spec.label === entry.key
                          ? entry.key
                          : `${entry.spec.label} · ${entry.key}`,
                    })),
                },
              ]}
              onChange={(value) => {
                setNewKind(value);
                form.setFieldsValue({ data: {} });
              }}
            />
          </Form.Item>
          {activeGroup && (
            <Alert
              type="info"
              showIcon
              title="这类设定建议先写"
              description={activeGroup.recommended_fields
                .map((key) => fieldLabel(key))
                .join("、")}
            />
          )}
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input placeholder="稳定身份会自动分配" maxLength={512} />
          </Form.Item>
          <Form.Item label="一句话方向">
            <Input
              value={direction}
              maxLength={500}
              placeholder="给 AI 的方向，不会直接写入已保存资料"
              onChange={(event) => setDirection(event.target.value)}
            />
          </Form.Item>
          <Space
            direction="vertical"
            style={{ width: "100%", marginBottom: 12 }}
          >
            <Button
              htmlType="button"
              disabled={!canEdit}
              loading={drafting}
              onClick={draftWithAi}
            >
              {drafting ? "正在起草" : "让 AI 起草设定"}
            </Button>
            {draftNote && <Typography.Text>{draftNote}</Typography.Text>}
            {draftError && (
              <Alert
                type="error"
                showIcon
                title="初稿没有写出来"
                action={
                  <Button size="small" onClick={draftWithAi}>
                    重试
                  </Button>
                }
              />
            )}
          </Space>
          <PropertyFields key={newKind} definition={definition} />
          <Form.Item name="text" label="详细内容">
            <Input.TextArea rows={6} />
          </Form.Item>
          <Form.Item name="secret" valuePropName="checked">
            <Checkbox disabled={!scope.actions.includes("secret")}>
              作者秘密
            </Checkbox>
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
