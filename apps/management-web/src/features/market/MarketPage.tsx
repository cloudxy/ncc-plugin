import { useQuery } from "@tanstack/react-query";
import {
  Alert,
  App,
  Button,
  Card,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Select,
  Skeleton,
  Space,
  Spin,
  Tag,
  Typography,
} from "antd";
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ApiError,
  adopt,
  api,
  scoped,
  type Entity,
  type Json,
  type Scope,
} from "../../shared/api";
import { PageTitle } from "../../shared/components/Feedback";
import { queryKeys } from "../../shared/queryKeys";
import { scopeLine } from "../../shared/scopeLabel";
import {
  fetchStudioCatalog,
  fetchStudioOverview,
  saveStudioMarketConfig,
  setStudioHandoff,
  type MarketPlaybook,
  type StudioMarketConfig,
} from "../../shared/studioApi";
import { useDelayed } from "../../shared/useDelayed";
import { waitForCreationDraft } from "../../shared/waitForCreationDraft";
import { useWorkspace } from "../../shared/WorkspaceContext";
import "./market.css";

function versionNumber(version: string) {
  const tail = Number(version.split(":").pop());
  return Number.isFinite(tail) ? tail : 0;
}

function offline(error: unknown) {
  return error instanceof TypeError;
}

function bandText(min: number, max: number, avg: number) {
  const span = `${min}–${max}`;
  if (avg < min) return `${span}，章均 ${avg}，低于目标字数带`;
  if (avg > max) return `${span}，章均 ${avg}，高于目标字数带`;
  return `${span}，章均 ${avg}，落在目标字数带内`;
}

function PlaybookBody({ book }: { book: MarketPlaybook }) {
  return (
    <>
      <h4>核心爽感杠杆</h4>
      <p>{book.core_hook}</p>
      <h4>3·10·30 配速</h4>
      <p>{book.pacing_3_10_30}</p>
      <h4>五类追读钩</h4>
      <p>{book.hook_mix}</p>
      <h4>中期崩盘陷阱</h4>
      <p>{book.midgame_trap}</p>
      <h4>毒点红线</h4>
      <ul>
        {book.poison_list.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
      <p>
        推荐字数带 {book.target_words_band[0]}–{book.target_words_band[1]}
      </p>
    </>
  );
}

export function MarketPage() {
  const { scope, refresh } = useWorkspace(),
    { message } = App.useApp(),
    navigate = useNavigate(),
    [form] = Form.useForm(),
    [windForm] = Form.useForm(),
    [editWindForm] = Form.useForm(),
    [track, setTrack] = useState<string>(),
    [qInput, setQInput] = useState(""),
    [q, setQ] = useState(""),
    [sortKey, setSortKey] = useState("名称"),
    [playbookQuery, setPlaybookQuery] = useState(""),
    [saving, setSaving] = useState(false),
    [creating, setCreating] = useState(false),
    [windError, setWindError] = useState(""),
    [distilling, setDistilling] = useState(false),
    [distillError, setDistillError] = useState(""),
    [editingWind, setEditingWind] = useState<Entity | null>(null),
    [loadingWindId, setLoadingWindId] = useState(""),
    [savingWindEdit, setSavingWindEdit] = useState(false),
    [editWindError, setEditWindError] = useState(""),
    [retiringWindId, setRetiringWindId] = useState("");
  const canEdit = scope.actions.includes("edit");
  const distillAbort = useRef<AbortController | null>(null);
  const catalog = useQuery({
    queryKey: queryKeys.studioCatalog(),
    queryFn: fetchStudioCatalog,
  });
  const overview = useQuery({
    queryKey: queryKeys.studioOverview(scope.id),
    queryFn: () => fetchStudioOverview(scope.id),
  });
  const winds = useQuery({
    queryKey: queryKeys.marketWinds(scope.id, { q, track, sortKey }),
    queryFn: () =>
      api<Json>(scoped(scope.id, "/entities/search"), "POST", {
        q,
        kind: "市场风向",
        limit: 50,
        sort: "name",
        filters: track
          ? [{ field: "market_track", op: "eq", value: track }]
          : [],
      }),
  });
  const healthSkeleton = useDelayed(overview.isPending && !overview.data);
  const playbooks = catalog.data?.market_playbooks || [];
  const filteredPlaybooks = playbooks.filter((item) => {
    const needle = playbookQuery.trim().toLowerCase();
    if (!needle) return true;
    return [item.name, item.core_hook, item.midgame_trap, ...item.poison_list]
      .join("\n")
      .toLowerCase()
      .includes(needle);
  });
  const saved = overview.data?.market_config;
  const bound = playbooks.find((item) => item.id === saved?.playbook_id);
  const diagnostics = overview.data?.diagnostics;
  const rows = ((winds.data?.items || []) as Entity[])
    .slice()
    .sort((a, b) =>
      sortKey === "更新时间"
        ? versionNumber(b.version) - versionNumber(a.version)
        : a.name.localeCompare(b.name, "zh"),
    );
  const tracks = Array.from(
    new Set(
      rows
        .map((item) => item.data?.market_track)
        .filter(
          (item): item is string => typeof item === "string" && item.length > 0,
        ),
    ),
  );
  const windEmpty =
    winds.isSuccess && !q && !track && (winds.data?.items?.length || 0) === 0;
  const windFiltered = winds.isSuccess && (!!q || !!track) && rows.length === 0;

  useEffect(() => () => distillAbort.current?.abort(), []);
  useEffect(() => {
    if (!saved || form.isFieldsTouched()) return;
    form.setFieldsValue({
      playbook_id: saved.playbook_id || undefined,
      custom_track: saved.custom_track || "",
      target_min_words: saved.target_min_words ?? 2500,
      target_max_words: saved.target_max_words ?? 4500,
      poison_notes: saved.poison_notes || [],
      direction_note: saved.direction_note || "",
    });
  }, [saved, form]);

  function clearWindFilter() {
    setQ("");
    setQInput("");
    setTrack(undefined);
  }
  async function saveConfig(values: StudioMarketConfig) {
    const minimum = Number(values.target_min_words ?? 2500);
    const maximum = Number(values.target_max_words ?? 4500);
    if (maximum < minimum) {
      message.error("目标字数上限不能低于下限");
      return;
    }
    setSaving(true);
    try {
      await saveStudioMarketConfig(scope.id, {
        playbook_id: values.playbook_id || "",
        custom_track: values.custom_track || "",
        target_min_words: minimum,
        target_max_words: maximum,
        poison_notes: (values.poison_notes || [])
          .map((item) => item.slice(0, 400))
          .slice(0, 30),
        direction_note: values.direction_note || "",
      });
      await overview.refetch();
      message.success(saved?.playbook_id ? "母本已更换" : "赛道母本已绑定");
    } catch (error) {
      message.error((error as Error).message);
    } finally {
      setSaving(false);
    }
  }
  async function createWind(values: Json) {
    try {
      const freshScope = await api<Scope>(scoped(scope.id, ""));
      await adopt(
        freshScope,
        [
          {
            op: "create",
            entity_id: crypto.randomUUID(),
            kind: "市场风向",
            name: values.name,
            text: values.text || "",
            data: {
              market_track: values.market_track || "",
              description: values.description || "",
              note: values.note || "",
            },
          },
        ],
        "新建风向：" + values.name,
      );
      setCreating(false);
      setWindError("");
      windForm.resetFields();
      refresh();
      winds.refetch();
      message.success("风向已保存");
    } catch (error) {
      setWindError(
        error instanceof ApiError && error.status === 409
          ? "对方先保存了这条风向。"
          : offline(error)
            ? "网络中断了，这一次没有写上。"
            : "这一次没有写上。",
      );
    }
  }
  async function openWindDetail(row: Entity) {
    setLoadingWindId(row.id);
    setEditWindError("");
    try {
      const full = await api<Entity>(scoped(scope.id, `/entities/${row.id}`));
      setEditingWind(full);
      editWindForm.setFieldsValue({
        name: full.name,
        market_track: full.data?.market_track || "",
        description: full.data?.description || "",
        text: full.text || "",
        note: full.data?.note || "",
      });
    } catch (error) {
      message.error(
        offline(error)
          ? "网络中断了，无法读取风向全文。"
          : (error as Error).message || "读取风向全文失败。",
      );
    } finally {
      setLoadingWindId("");
    }
  }
  async function saveEditedWind(values: Json) {
    if (!editingWind || !canEdit) return;
    setSavingWindEdit(true);
    setEditWindError("");
    try {
      const freshScope = await api<Scope>(scoped(scope.id, ""));
      await adopt(
        freshScope,
        [
          {
            op: "update",
            entity_id: editingWind.id,
            expected: editingWind.version,
            name: values.name,
            text: values.text || "",
            data: {
              market_track: values.market_track || "",
              description: values.description || "",
              note: values.note || "",
            },
          },
        ],
        "编辑风向：" + values.name,
      );
      setEditingWind(null);
      editWindForm.resetFields();
      refresh();
      await winds.refetch();
      message.success("市场风向修订已保存");
    } catch (error) {
      setEditWindError(
        error instanceof ApiError &&
          (error.status === 409 || error.status === 412)
          ? "这条风向在别处已被修改，请点击「重新载入最新版」比对后再保存。"
          : offline(error)
            ? "网络中断了，修改没有保存。"
            : (error as Error).message || "保存风向失败。",
      );
    } finally {
      setSavingWindEdit(false);
    }
  }
  async function retireWind(row: Entity) {
    if (!canEdit) return;
    setRetiringWindId(row.id);
    try {
      const freshScope = await api<Scope>(scoped(scope.id, ""));
      await adopt(
        freshScope,
        [
          {
            op: "retire",
            entity_id: row.id,
            expected: row.version,
          },
        ],
        "停用风向：" + row.name,
      );
      if (editingWind?.id === row.id) {
        setEditingWind(null);
      }
      refresh();
      await winds.refetch();
      message.success("市场风向已停用");
    } catch (error) {
      message.error(
        error instanceof ApiError &&
          (error.status === 409 || error.status === 412)
          ? "风向版本已变更，已为你刷新列表，请重试。"
          : (error as Error).message || "停用风向失败。",
      );
      winds.refetch();
    } finally {
      setRetiringWindId("");
    }
  }
  async function distill() {
    const name = String(windForm.getFieldValue("name") || "").trim();
    const description = String(
      windForm.getFieldValue("description") || "",
    ).trim();
    const note = String(windForm.getFieldValue("note") || "").trim();
    if (!canEdit) return;
    if (!name && !description && !note) {
      message.info("先写下要看的书或链接说明");
      return;
    }
    distillAbort.current?.abort();
    const controller = new AbortController();
    distillAbort.current = controller;
    setDistilling(true);
    setDistillError("");
    try {
      const created = await api<Json>(
        scoped(scope.id, "/creation-tasks"),
        "POST",
        {
          objective:
            description ||
            note ||
            `提炼「${name}」的卖点结构，只给可编辑笔记，不写入资料库。`,
          scheme: "P4",
          mode: "create",
          kind: "市场风向",
          name: name || "市场风向",
          stages: ["write"],
          guidance: [description, note].filter(Boolean).join("\n"),
          max_revisions: 0,
        },
        controller.signal,
      );
      const text = await waitForCreationDraft(
        scope.id,
        created.id,
        controller.signal,
        "没有提炼出来",
      );
      windForm.setFieldValue("text", text);
      message.success("提炼结果在编辑区，尚未保存");
    } catch (error) {
      if ((error as Error).name === "AbortError") return;
      setDistillError("没有提炼出来");
    } finally {
      setDistilling(false);
    }
  }
  function handoff(row: Entity) {
    setStudioHandoff({
      scopeId: scope.id,
      sourceEntity: { id: row.id, title: row.name },
    });
    navigate("/work");
  }

  const watchedId = Form.useWatch("playbook_id", form) as string | undefined;
  const preview = playbooks.find((item) => item.id === watchedId) || bound;

  return (
    <>
      <PageTitle
        title="市场与风向"
        note="赛道白金母本、市场监控与连载健康度。"
      />
      <p className="mkt-scope">
        {scopeLine(scope.name, scope.kind, scope.version)}
      </p>
      {!canEdit && <p className="mkt-note">当前范围不能编辑</p>}
      <div className="mkt-layout">
        <section className="mkt-playbooks">
          <Typography.Title level={4}>赛道白金母本</Typography.Title>
          {catalog.isPending && <Skeleton active paragraph={{ rows: 6 }} />}
          {catalog.isError && (
            <Alert
              type="error"
              showIcon
              title={
                offline(catalog.error)
                  ? "网络中断了，母本清单没有载入。"
                  : "母本清单没有载入。"
              }
              action={<Button onClick={() => catalog.refetch()}>重试</Button>}
            />
          )}
          {catalog.isSuccess && playbooks.length === 0 && (
            <p>还没有可绑定的母本</p>
          )}
          {catalog.isSuccess && !saved?.playbook_id && (
            <div className="mkt-empty">
              <p>还没有绑定赛道母本</p>
              <Button
                disabled={!canEdit}
                onClick={() =>
                  document
                    .getElementById("playbook-form")
                    ?.scrollIntoView({ block: "nearest" })
                }
              >
                选择赛道母本
              </Button>
            </div>
          )}
          <Input.Search
            aria-label="搜索母本"
            placeholder="搜索母本"
            allowClear
            style={{ width: 240, margin: "12px 0" }}
            onSearch={setPlaybookQuery}
            onChange={(event) => {
              if (!event.target.value) setPlaybookQuery("");
            }}
          />
          {catalog.isSuccess &&
            playbookQuery &&
            filteredPlaybooks.length === 0 && (
              <div className="mkt-empty">
                <p>没有符合的母本</p>
                <Button onClick={() => setPlaybookQuery("")}>清除搜索</Button>
              </div>
            )}
          {filteredPlaybooks.map((book) => (
            <Card
              key={book.id}
              className="mkt-playbook"
              title={book.name}
              extra={
                saved?.playbook_id === book.id ? <Tag>当前绑定</Tag> : null
              }
            >
              <PlaybookBody book={book} />
              <Button
                disabled={!canEdit}
                onClick={() => form.setFieldValue("playbook_id", book.id)}
              >
                {saved?.playbook_id ? "更换母本" : "选择赛道母本"}
              </Button>
            </Card>
          ))}
          <div id="playbook-form">
            <Form
              form={form}
              layout="vertical"
              onFinish={saveConfig}
              initialValues={{
                target_min_words: 2500,
                target_max_words: 4500,
                poison_notes: [],
              }}
            >
              <Form.Item name="playbook_id" label="赛道母本">
                <Select
                  aria-label="赛道母本"
                  allowClear
                  disabled={!canEdit}
                  options={playbooks.map((item) => ({
                    value: item.id,
                    label: item.name,
                  }))}
                />
              </Form.Item>
              {preview && <PlaybookBody book={preview} />}
              <Form.Item name="custom_track" label="自定义赛道">
                <Input maxLength={128} disabled={!canEdit} />
              </Form.Item>
              <Form.Item name="target_min_words" label="目标字数下限">
                <InputNumber
                  min={200}
                  max={50000}
                  style={{ width: "100%" }}
                  disabled={!canEdit}
                />
              </Form.Item>
              <Form.Item name="target_max_words" label="目标字数上限">
                <InputNumber
                  min={200}
                  max={50000}
                  style={{ width: "100%" }}
                  disabled={!canEdit}
                />
              </Form.Item>
              <Form.Item name="poison_notes" label="毒点备注">
                <Select
                  mode="tags"
                  disabled={!canEdit}
                  placeholder="每条不超过 400 字"
                />
              </Form.Item>
              <Form.Item name="direction_note" label="方向备注">
                <Input.TextArea rows={4} maxLength={4000} disabled={!canEdit} />
              </Form.Item>
              <Button
                type="primary"
                htmlType="submit"
                disabled={!canEdit}
                loading={saving}
              >
                {saved?.playbook_id ? "更换母本" : "绑定到当前书"}
              </Button>
            </Form>
          </div>
        </section>
        <section className="mkt-health-block" aria-label="连载健康度">
          <Typography.Title level={4}>连载健康度</Typography.Title>
          {healthSkeleton && <Skeleton active paragraph={{ rows: 8 }} />}
          {!healthSkeleton && overview.isPending && <p>正在载入</p>}
          {overview.isError && (
            <Alert
              type="error"
              showIcon
              title={
                offline(overview.error)
                  ? "网络中断了。健康度没有算出来。"
                  : "健康度没有算出来。"
              }
              action={<Button onClick={() => overview.refetch()}>重试</Button>}
            />
          )}
          {overview.isSuccess && diagnostics && (
            <>
              {overview.data?.pagination?.truncated && (
                <Alert
                  type="info"
                  showIcon
                  style={{ marginBottom: 12 }}
                  title={`结构目录已分页展示（${overview.data.pagination.returned_structural} / ${overview.data.pagination.structural_count} 条），资料分类汇总已覆盖全范围 ${overview.data.pagination.total_entities} 条对象。`}
                />
              )}
              <dl className="mkt-health">
                <dt>总章数</dt>
                <dd>{diagnostics.chapter_count}</dd>
                <dt>总字数（汉字）</dt>
                <dd>{diagnostics.total_chars}</dd>
                <dt>章均字数（汉字）</dt>
                <dd>
                  {diagnostics.chapter_count === 0
                    ? "还没有章节"
                    : diagnostics.avg_chars}
                </dd>
                <dt>关键章数量</dt>
                <dd>{diagnostics.key_chapter_count}</dd>
                <dt>关键章占比</dt>
                <dd>
                  {diagnostics.chapter_count === 0
                    ? "还没有章节"
                    : `${Math.round((diagnostics.key_chapter_count / diagnostics.chapter_count) * 100)}%`}
                </dd>
                <dt>活跃暗线</dt>
                <dd>
                  {diagnostics.active_hidden_lines} / 5
                  {diagnostics.planned_hidden_lines ||
                  diagnostics.resolved_hidden_lines ||
                  diagnostics.dropped_hidden_lines ? (
                    <small>
                      {" "}
                      （
                      {[
                        diagnostics.planned_hidden_lines
                          ? `待埋设 ${diagnostics.planned_hidden_lines}`
                          : null,
                        `已兑现 ${diagnostics.resolved_hidden_lines ?? 0}`,
                        `已作废 ${diagnostics.dropped_hidden_lines ?? 0}`,
                      ]
                        .filter(Boolean)
                        .join(" · ")}
                      ）
                    </small>
                  ) : null}
                </dd>
                <dt>临期伏笔</dt>
                <dd>
                  {diagnostics.due_soon_foreshadow_count}
                  {diagnostics.unplanted_due_foreshadow_count ? (
                    <small>
                      {" "}
                      （含待埋设提醒{" "}
                      {diagnostics.unplanted_due_foreshadow_count}）
                    </small>
                  ) : null}
                </dd>
                <dt>超期伏笔</dt>
                <dd>
                  {diagnostics.overdue_foreshadow_count}{" "}
                  <Link to="/blueprint">去看超期伏笔</Link>
                </dd>
                <dt>字数带</dt>
                <dd>
                  {typeof saved?.target_min_words === "number" &&
                  typeof saved.target_max_words === "number"
                    ? bandText(
                        saved.target_min_words,
                        saved.target_max_words,
                        diagnostics.avg_chars,
                      )
                    : "还没有目标字数带"}
                </dd>
              </dl>
              {diagnostics.hidden_line_cap_exceeded && (
                <p className="mkt-warn">
                  活跃暗线 {diagnostics.active_hidden_lines} 条，超过 5
                  条封顶。活跃暗线已超过 5 条上限建议，请注意收束合拢
                </p>
              )}
            </>
          )}
        </section>
        <section className="mkt-notes">
          <Typography.Title level={4}>市场风向</Typography.Title>
          <Space wrap className="mkt-actions" style={{ marginBottom: 12 }}>
            <Button
              type="primary"
              disabled={!canEdit}
              onClick={() => setCreating(true)}
            >
              新建风向
            </Button>
            <Input.Search
              aria-label="搜索风向"
              placeholder="搜索风向"
              value={qInput}
              allowClear
              style={{ width: 220 }}
              onChange={(event) => {
                setQInput(event.target.value);
                if (!event.target.value) setQ("");
              }}
              onSearch={(value) => {
                setQ(value);
                setQInput(value);
              }}
            />
            <Select
              aria-label="赛道"
              allowClear
              placeholder="全部赛道"
              value={track}
              style={{ width: 180 }}
              options={tracks.map((item) => ({ value: item, label: item }))}
              onChange={(value) => setTrack(value)}
            />
            <Select
              aria-label="排序"
              value={sortKey}
              style={{ width: 140 }}
              options={[
                { value: "名称", label: "名称" },
                { value: "更新时间", label: "更新时间" },
              ]}
              onChange={setSortKey}
            />
          </Space>
          {winds.isPending && <Skeleton active paragraph={{ rows: 4 }} />}
          {winds.isError && (
            <Alert
              type="error"
              showIcon
              title={
                offline(winds.error)
                  ? "网络中断了，风向没有载入。"
                  : "风向没有载入。"
              }
              action={<Button onClick={() => winds.refetch()}>重试</Button>}
            />
          )}
          {windEmpty && (
            <div className="mkt-empty">
              <p>还没有市场风向</p>
              <Button
                type="primary"
                disabled={!canEdit}
                onClick={() => setCreating(true)}
              >
                新建风向
              </Button>
            </div>
          )}
          {windFiltered && (
            <div className="mkt-empty">
              <p>没有符合的风向</p>
              <Button onClick={clearWindFilter}>清除筛选</Button>
            </div>
          )}
          {rows.map((row) => (
            <Card key={row.id} className="mkt-wind">
              <h3>{row.name}</h3>
              {row.data?.market_track && <Tag>{row.data.market_track}</Tag>}
              <p>{row.data?.description || row.text_preview || "还没有观察"}</p>
              {row.data?.note && (
                <p>
                  <strong>避坑备注：</strong>
                  {row.data.note}
                </p>
              )}
              <Space wrap>
                <Button
                  loading={loadingWindId === row.id}
                  onClick={() => void openWindDetail(row)}
                >
                  {canEdit ? "查看全文 / 编辑" : "查看全文"}
                </Button>
                <Button onClick={() => handoff(row)}>带入创作台</Button>
                <Popconfirm
                  title="停用这条市场风向？"
                  description="停用后不再在风向列表中显示；需要时可在「身份与历史维护」中恢复。"
                  okText="确认停用"
                  cancelText="取消"
                  disabled={!canEdit}
                  onConfirm={() => void retireWind(row)}
                >
                  <Button
                    danger
                    disabled={!canEdit}
                    loading={retiringWindId === row.id}
                  >
                    停用
                  </Button>
                </Popconfirm>
              </Space>
            </Card>
          ))}
        </section>
      </div>
      <Modal
        title="新建风向"
        open={creating}
        onCancel={() => {
          distillAbort.current?.abort();
          setCreating(false);
        }}
        onOk={() => windForm.submit()}
        okButtonProps={{ disabled: !canEdit }}
        destroyOnHidden
      >
        <Form form={windForm} layout="vertical" onFinish={createWind}>
          {windError && (
            <Alert
              type="error"
              showIcon
              style={{ marginBottom: 12 }}
              title={windError}
              action={
                <Space>
                  <Button size="small" onClick={() => winds.refetch()}>
                    重新载入
                  </Button>
                  <Button size="small" onClick={() => setWindError("")}>
                    留着我的修改
                  </Button>
                </Space>
              }
            />
          )}
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input maxLength={512} />
          </Form.Item>
          <Form.Item name="market_track" label="赛道">
            <Input maxLength={128} placeholder="例如 西部奥术" />
          </Form.Item>
          <Form.Item name="description" label="热点观察">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item name="text" label="对标作品爽点分析">
            <Input.TextArea rows={5} />
          </Form.Item>
          <Form.Item name="note" label="避坑备注">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Space orientation="vertical">
            <Button disabled={!canEdit} loading={distilling} onClick={distill}>
              {distilling ? "正在提炼" : "AI 提炼风向"}
            </Button>
            <Typography.Text type="secondary">
              让 AI 提炼卖点结构。结果先留在编辑区，保存才落库。
            </Typography.Text>
            {distillError && (
              <Alert
                type="error"
                showIcon
                title="没有提炼出来"
                action={
                  <Button size="small" onClick={distill}>
                    重试
                  </Button>
                }
              />
            )}
          </Space>
        </Form>
      </Modal>

      <Modal
        title={canEdit ? "查看全文 / 编辑市场风向" : "查看市场风向全文"}
        open={editingWind !== null}
        onCancel={() => {
          setEditingWind(null);
          setEditWindError("");
        }}
        onOk={() => editWindForm.submit()}
        okText="保存修改"
        cancelText={canEdit ? "取消" : "关闭"}
        confirmLoading={savingWindEdit}
        okButtonProps={{
          disabled: !canEdit,
          style: canEdit ? undefined : { display: "none" },
        }}
        destroyOnHidden
      >
        {loadingWindId ? (
          <Spin description="正在读取风向全文" />
        ) : (
          <Form
            form={editWindForm}
            layout="vertical"
            onFinish={saveEditedWind}
            disabled={!canEdit}
          >
            {editWindError && (
              <Alert
                type="warning"
                showIcon
                style={{ marginBottom: 12 }}
                title={editWindError}
                action={
                  <Button
                    size="small"
                    onClick={() => {
                      if (editingWind) void openWindDetail(editingWind);
                    }}
                  >
                    重新载入最新版
                  </Button>
                }
              />
            )}
            <Form.Item name="name" label="名称" rules={[{ required: true }]}>
              <Input maxLength={512} />
            </Form.Item>
            <Form.Item name="market_track" label="赛道">
              <Input maxLength={128} placeholder="例如 西部奥术" />
            </Form.Item>
            <Form.Item name="description" label="热点观察">
              <Input.TextArea rows={3} />
            </Form.Item>
            <Form.Item name="text" label="对标作品爽点分析全文">
              <Input.TextArea rows={7} />
            </Form.Item>
            <Form.Item name="note" label="避坑备注">
              <Input.TextArea rows={3} />
            </Form.Item>
          </Form>
        )}
      </Modal>
    </>
  );
}
