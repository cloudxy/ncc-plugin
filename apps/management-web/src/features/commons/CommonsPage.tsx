import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  App,
  Button,
  Card,
  Form,
  Input,
  Modal,
  Popconfirm,
  Select,
  Skeleton,
  Space,
  Spin,
  Tag,
  Typography,
} from "antd";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
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
  setStudioHandoff,
  type CommonsCard,
} from "../../shared/studioApi";
import { useWorkspace } from "../../shared/WorkspaceContext";
import "./commons.css";

const NAV = [
  { id: "all", label: "全部" },
  { id: "writing_routine", label: "写作套路" },
  { id: "character_portrait", label: "人物描摹" },
  { id: "plot_direction", label: "剧情走向" },
  { id: "character_arc", label: "人物弧光" },
  { id: "psychology", label: "心理分析" },
  { id: "relationship", label: "关系分析" },
  { id: "philosophy", label: "哲学思考" },
  { id: "management", label: "管理" },
  { id: "finance", label: "财务" },
  { id: "technology", label: "技术" },
  { id: "art", label: "艺术" },
  { id: "environment", label: "环境" },
] as const;

function offline(error: unknown) {
  return error instanceof TypeError;
}

function builtinText(card: CommonsCard) {
  const steps = card.structure
    .map((step, index) => `${index + 1}. ${step}`)
    .join("\n");
  const pitfalls = card.pitfalls.map((item) => `- ${item}`).join("\n");
  return `${card.summary}\n\n结构\n${steps}\n\n禁忌\n${pitfalls}\n\nAI 伴写\n${card.ai_prompt_hint}`;
}

export function CommonsPage() {
  const { scope, refresh } = useWorkspace(),
    { message } = App.useApp(),
    navigate = useNavigate(),
    client = useQueryClient(),
    [category, setCategory] = useState("all"),
    [qInput, setQInput] = useState(""),
    [q, setQ] = useState(""),
    [sortKey, setSortKey] = useState("名称"),
    [offset, setOffset] = useState(0),
    [commonsId, setCommonsId] = useState(""),
    [creatingLibrary, setCreatingLibrary] = useState(false),
    [libraryError, setLibraryError] = useState(""),
    [adding, setAdding] = useState(false),
    [cardError, setCardError] = useState(""),
    [cloning, setCloning] = useState(""),
    [editingCard, setEditingCard] = useState<Entity | null>(null),
    [loadingCardId, setLoadingCardId] = useState(""),
    [savingEdit, setSavingEdit] = useState(false),
    [editError, setEditError] = useState(""),
    [retiringId, setRetiringId] = useState(""),
    [form] = Form.useForm(),
    [editForm] = Form.useForm();
  const canEdit = scope.actions.includes("edit");
  const catalog = useQuery({
    queryKey: queryKeys.studioCatalog(),
    queryFn: fetchStudioCatalog,
  });
  const overview = useQuery({
    queryKey: queryKeys.studioOverview(scope.id),
    queryFn: () => fetchStudioOverview(scope.id),
  });
  const libraries = overview.data?.commons_scopes || [];
  const selectedId = libraries.some((item) => item.id === commonsId)
    ? commonsId
    : libraries[0]?.id || "";
  const labelOf = useMemo(() => {
    const map = new Map<string, string>(
      NAV.map((item) => [item.id, item.label]),
    );
    for (const item of catalog.data?.commons_categories || [])
      map.set(item.id, item.label);
    return map;
  }, [catalog.data]);
  const activeCatValues = useMemo(() => {
    if (category === "all") return [];
    const label = labelOf.get(category);
    return Array.from(
      new Set([category, label].filter((v): v is string => Boolean(v))),
    );
  }, [category, labelOf]);
  const library = useQuery({
    queryKey: queryKeys.commonsLibrary(selectedId, {
      category,
      q,
      offset,
      sortKey,
    }),
    enabled: !!selectedId,
    queryFn: () =>
      api<Json>(scoped(selectedId, "/entities/search"), "POST", {
        q,
        kind: "公共母本",
        offset,
        limit: 50,
        sort: sortKey === "修订版本" ? "version" : "name",
        ...(category !== "all"
          ? {
              filters: [
                {
                  field: "commons_category",
                  op: "in",
                  value: activeCatValues,
                },
              ],
            }
          : {}),
      }),
  });
  const libraryScope = useQuery({
    queryKey: queryKeys.scopeInfo(selectedId),
    enabled: !!selectedId,
    queryFn: () => api<Scope>(scoped(selectedId, "")),
  });
  const canEditLibrary = libraryScope.data?.actions.includes("edit") ?? false;
  const needle = q.trim().toLowerCase();
  const builtin = (catalog.data?.commons_cards || [])
    .filter((card) => category === "all" || card.category === category)
    .filter((card) => {
      if (!needle) return true;
      const hay = [
        card.title,
        card.summary,
        card.ai_prompt_hint,
        ...card.structure,
        ...card.pitfalls,
        ...card.tags,
      ]
        .join("\n")
        .toLowerCase();
      return hay.includes(needle);
    })
    .sort((a, b) => a.title.localeCompare(b.title, "zh"));
  const authorCards = (library.data?.items || []) as Entity[];
  const bothOffline =
    catalog.isError &&
    overview.isError &&
    offline(catalog.error) &&
    offline(overview.error);

  const authorTotal =
    typeof library.data?.total === "number"
      ? library.data.total
      : authorCards.length;
  const hasNextAuthorPage =
    library.data?.next_offset != null || offset + 50 < authorTotal;
  const nextAuthorOffset =
    typeof library.data?.next_offset === "number"
      ? library.data.next_offset
      : offset + 50;

  function clearSearch() {
    setQ("");
    setQInput("");
    setOffset(0);
  }
  async function createLibrary() {
    setCreatingLibrary(true);
    setLibraryError("");
    try {
      const created = await api<Scope>("/scopes", "POST", {
        name: "我的公共陈列库",
        kind: "author",
      });
      setCommonsId(created.id);
      await client.invalidateQueries({ queryKey: queryKeys.scopesRoot() });
      await overview.refetch();
      message.success("公共陈列库已建立");
    } catch (error) {
      setLibraryError(
        offline(error)
          ? "网络中断了，公共库没有建起来。"
          : "公共库没有建起来。",
      );
    } finally {
      setCreatingLibrary(false);
    }
  }
  async function cloneBuiltin(card: CommonsCard) {
    if (!canEdit) return;
    setCloning(card.id);
    try {
      await adopt(
        scope,
        [
          {
            op: "create",
            entity_id: crypto.randomUUID(),
            kind: "公共母本",
            name: card.title,
            text: builtinText(card),
            data: {
              commons_category: card.category,
              description: card.summary,
              usage_guide: card.ai_prompt_hint,
              tags: card.tags,
            },
          },
        ],
        "克隆公共母本：" + card.title,
      );
      refresh();
      message.success("已克隆到当前书");
    } catch (error) {
      message.error(
        offline(error)
          ? "没有克隆过去。"
          : (error as Error).message || "没有克隆过去。",
      );
    } finally {
      setCloning("");
    }
  }
  async function cloneAuthor(item: Entity) {
    if (!canEdit || !selectedId) return;
    setCloning(item.id);
    try {
      const full = await api<Entity>(
        scoped(selectedId, `/entities/${item.id}`),
      );
      await adopt(
        scope,
        [
          {
            op: "create",
            entity_id: crypto.randomUUID(),
            kind: "公共母本",
            name: full.name,
            text: full.text || "",
            data: {
              commons_category: full.data?.commons_category || category,
              description: full.data?.description || "",
              usage_guide: full.data?.usage_guide || "",
            },
          },
        ],
        "克隆公共母本：" + full.name,
      );
      refresh();
      message.success("已克隆到当前书");
    } catch {
      message.error("没有克隆过去。");
    } finally {
      setCloning("");
    }
  }
  function mountBuiltin(card: CommonsCard) {
    if (!canEdit) return;
    setStudioHandoff({
      scopeId: scope.id,
      builtinCommons: { id: card.id, title: card.title },
    });
    navigate("/work");
  }
  function mountAuthor(item: Entity) {
    if (!canEdit || !selectedId) return;
    setStudioHandoff({
      scopeId: scope.id,
      commonsRef: {
        scope_id: selectedId,
        entity_id: item.id,
        title: item.name,
      },
    });
    navigate("/work");
  }
  async function addCard(values: Json) {
    if (!selectedId) return;
    try {
      const freshScope = await api<Scope>(scoped(selectedId, ""));
      await adopt(
        freshScope,
        [
          {
            op: "create",
            entity_id: crypto.randomUUID(),
            kind: "公共母本",
            name: values.name,
            text: values.text || "",
            data: {
              commons_category: values.commons_category,
              description: values.description || "",
              usage_guide: values.usage_guide || "",
            },
          },
        ],
        "新增公共卡：" + values.name,
      );
      setAdding(false);
      setCardError("");
      form.resetFields();
      await Promise.all([
        library.refetch(),
        libraryScope.refetch(),
        overview.refetch(),
      ]);
      message.success("公共卡已保存");
    } catch (error) {
      setCardError(
        error instanceof ApiError && error.status === 409
          ? "对方先保存了同名卡片。"
          : (error as Error).message || "这一次没有写上。",
      );
    }
  }

  async function openCardDetail(item: Entity) {
    if (!selectedId) return;
    setLoadingCardId(item.id);
    setEditError("");
    try {
      const full = await api<Entity>(
        scoped(selectedId, `/entities/${item.id}`),
      );
      setEditingCard(full);
      const rawCat = String(full.data?.commons_category || "");
      const matchedNav = NAV.find(
        (nav) =>
          nav.id !== "all" && (nav.id === rawCat || nav.label === rawCat),
      );
      editForm.setFieldsValue({
        name: full.name,
        commons_category: matchedNav
          ? matchedNav.id
          : rawCat || "writing_routine",
        description: full.data?.description || "",
        usage_guide: full.data?.usage_guide || "",
        text: full.text || "",
      });
    } catch (error) {
      message.error(
        offline(error)
          ? "网络中断了，无法读取公共卡全文。"
          : (error as Error).message || "读取公共卡失败。",
      );
    } finally {
      setLoadingCardId("");
    }
  }

  async function reloadEditingCard() {
    if (!editingCard || !selectedId) return;
    await openCardDetail(editingCard);
  }

  async function saveEditedCard(values: Json) {
    if (!editingCard || !selectedId || !canEditLibrary) return;
    setSavingEdit(true);
    setEditError("");
    try {
      const freshScope = await api<Scope>(scoped(selectedId, ""));
      await adopt(
        freshScope,
        [
          {
            op: "update",
            entity_id: editingCard.id,
            expected: editingCard.version,
            name: values.name,
            text: values.text || "",
            data: {
              commons_category: values.commons_category,
              description: values.description || "",
              usage_guide: values.usage_guide || "",
            },
          },
        ],
        "编辑公共卡：" + values.name,
      );
      setEditingCard(null);
      editForm.resetFields();
      await Promise.all([
        library.refetch(),
        libraryScope.refetch(),
        overview.refetch(),
      ]);
      message.success("公共卡修订已保存");
    } catch (error) {
      setEditError(
        error instanceof ApiError &&
          (error.status === 409 || error.status === 412)
          ? "这张公共卡在别处已被修改，请点击「重新载入最新版」比对后再保存。"
          : (error as Error).message || "公共卡保存失败。",
      );
    } finally {
      setSavingEdit(false);
    }
  }

  async function retireCard(item: Entity) {
    if (!selectedId || !canEditLibrary) return;
    setRetiringId(item.id);
    try {
      const freshScope = await api<Scope>(scoped(selectedId, ""));
      await adopt(
        freshScope,
        [
          {
            op: "retire",
            entity_id: item.id,
            expected: item.version,
          },
        ],
        "停用公共卡：" + item.name,
      );
      if (editingCard?.id === item.id) {
        setEditingCard(null);
      }
      await Promise.all([
        library.refetch(),
        libraryScope.refetch(),
        overview.refetch(),
      ]);
      message.success("公共卡已停用");
    } catch (error) {
      message.error(
        error instanceof ApiError &&
          (error.status === 409 || error.status === 412)
          ? "卡片版本已变更，已为你刷新列表，请重试。"
          : (error as Error).message || "停用公共卡失败。",
      );
      library.refetch();
    } finally {
      setRetiringId("");
    }
  }

  const blockReason = !canEdit ? "当前书不能编辑" : "";

  return (
    <>
      <PageTitle title="公共陈列库" note="所有书都能用的写法、人物和通识。" />
      <p className="com-scope">
        {scopeLine(scope.name, scope.kind, scope.version)}
      </p>
      {blockReason && <p className="com-note">{blockReason}</p>}
      <div className="com-capsules" role="group" aria-label="公共陈列板块">
        {NAV.map((item) => (
          <Button
            key={item.id}
            type={category === item.id ? "primary" : "default"}
            aria-pressed={category === item.id}
            onClick={() => {
              setCategory(item.id);
              setOffset(0);
            }}
          >
            {item.label}
          </Button>
        ))}
      </div>
      <Space wrap style={{ marginBottom: 12 }}>
        <Input.Search
          aria-label="搜索陈列卡"
          placeholder="在这个板块里搜索"
          value={qInput}
          allowClear
          style={{ width: 280 }}
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
        <Select
          aria-label="排序"
          value={sortKey}
          style={{ width: 140 }}
          options={[
            { value: "名称", label: "名称" },
            { value: "修订版本", label: "修订版本" },
          ]}
          onChange={(value) => {
            setSortKey(value);
            setOffset(0);
          }}
        />
      </Space>
      {bothOffline ? (
        <Alert
          type="error"
          showIcon
          title="网络中断了，陈列库没有载入。"
          action={
            <Button
              onClick={() => {
                catalog.refetch();
                overview.refetch();
              }}
            >
              重试
            </Button>
          }
        />
      ) : (
        <div className="com-split">
          <section className="com-column" aria-readonly="true">
            <Typography.Title level={4}>
              内置母本 <Tag>只读</Tag>
            </Typography.Title>
            {catalog.isPending && <Skeleton active paragraph={{ rows: 6 }} />}
            {catalog.isError && (
              <Alert
                type="error"
                showIcon
                title={
                  offline(catalog.error)
                    ? "网络中断了，这一栏没有载入。"
                    : "母本清单没有载入。"
                }
                action={<Button onClick={() => catalog.refetch()}>重试</Button>}
              />
            )}
            {catalog.isSuccess && builtin.length === 0 && (
              <div className="com-empty">
                <p>{q ? "没有符合的陈列卡" : "这个板块还没有内置母本"}</p>
                {q && <Button onClick={clearSearch}>清除搜索</Button>}
              </div>
            )}
            {builtin.map((card) => (
              <Card key={card.id} className="com-card">
                <h3>{card.title}</h3>
                <Tag>{labelOf.get(card.category) || card.category}</Tag>
                <p>{card.summary}</p>
                <ol>
                  {card.structure.map((step) => (
                    <li key={step}>{step}</li>
                  ))}
                </ol>
                <p>
                  <strong>AI 伴写指令：</strong>
                  {card.ai_prompt_hint}
                </p>
                <ul>
                  {card.pitfalls.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
                <Space wrap className="com-actions">
                  <Button
                    disabled={!canEdit}
                    loading={cloning === card.id}
                    onClick={() => cloneBuiltin(card)}
                  >
                    {cloning === card.id ? "正在克隆" : "克隆到当前书"}
                  </Button>
                  <Button
                    disabled={!canEdit}
                    onClick={() => mountBuiltin(card)}
                  >
                    带入创作台给 AI 参考
                  </Button>
                </Space>
              </Card>
            ))}
          </section>
          <section className="com-column">
            <Typography.Title level={4}>我的公共陈列库</Typography.Title>
            {overview.isPending && <Skeleton active paragraph={{ rows: 6 }} />}
            {overview.isError && (
              <Alert
                type="error"
                showIcon
                title={
                  offline(overview.error)
                    ? "网络中断了，这一栏没有载入。"
                    : "公共库没有载入。"
                }
                action={
                  <Button onClick={() => overview.refetch()}>重试</Button>
                }
              />
            )}
            {overview.isSuccess && libraries.length === 0 && (
              <div className="com-empty">
                <p>还没有你的公共库</p>
                <Button
                  type="primary"
                  className="com-actions"
                  loading={creatingLibrary}
                  disabled={creatingLibrary}
                  onClick={createLibrary}
                >
                  {creatingLibrary ? "正在创建" : "创建我的公共陈列库"}
                </Button>
                {libraryError && (
                  <Alert
                    style={{ marginTop: 12 }}
                    type="error"
                    showIcon
                    title={libraryError}
                    action={<Button onClick={createLibrary}>重试</Button>}
                  />
                )}
              </div>
            )}
            {overview.isSuccess && libraries.length > 0 && (
              <>
                <Space
                  wrap
                  style={{ marginBottom: 12 }}
                  className="com-actions"
                >
                  <Select
                    aria-label="公共库"
                    value={selectedId}
                    style={{ minWidth: 220 }}
                    options={libraries.map((item) => ({
                      value: item.id,
                      label: `${item.name} · ${item.kind}`,
                    }))}
                    onChange={(value) => {
                      setCommonsId(value);
                      setOffset(0);
                    }}
                  />
                  <Button
                    type="primary"
                    disabled={!canEditLibrary}
                    onClick={() => {
                      setCardError("");
                      form.setFieldsValue({
                        commons_category:
                          category === "all" ? "writing_routine" : category,
                      });
                      setAdding(true);
                    }}
                  >
                    新增公共卡
                  </Button>
                </Space>
                {!canEditLibrary && libraryScope.isSuccess && (
                  <p className="com-note">这个公共库不能编辑</p>
                )}
                {library.isPending && (
                  <Skeleton active paragraph={{ rows: 4 }} />
                )}
                {library.isError && (
                  <Alert
                    type="error"
                    showIcon
                    title={
                      offline(library.error)
                        ? "网络中断了，这一栏没有载入。"
                        : "公共卡没有载入。"
                    }
                    action={
                      <Button onClick={() => library.refetch()}>重试</Button>
                    }
                  />
                )}
                {library.isSuccess && authorCards.length === 0 && (
                  <div className="com-empty">
                    <p>{q ? "没有符合的陈列卡" : "这个板块还没有你的卡片"}</p>
                    {q ? (
                      <Button onClick={clearSearch}>清除搜索</Button>
                    ) : (
                      <Button
                        disabled={!canEditLibrary}
                        onClick={() => setAdding(true)}
                      >
                        新增公共卡
                      </Button>
                    )}
                  </div>
                )}
                {authorCards.map((item) => (
                  <Card key={item.id} className="com-card">
                    <h3>{item.name}</h3>
                    <Tag>
                      {labelOf.get(String(item.data?.commons_category || "")) ||
                        item.data?.commons_category ||
                        item.kind}
                    </Tag>
                    <p>
                      {item.data?.description ||
                        item.text_preview ||
                        "还没有摘要"}
                    </p>
                    {item.data?.usage_guide && (
                      <p>
                        <strong>AI 用法提示：</strong>
                        {item.data.usage_guide}
                      </p>
                    )}
                    <Space wrap className="com-actions">
                      <Button
                        loading={loadingCardId === item.id}
                        onClick={() => void openCardDetail(item)}
                      >
                        {canEditLibrary ? "查看 / 编辑" : "查看全文"}
                      </Button>
                      <Button
                        disabled={!canEdit}
                        loading={cloning === item.id}
                        onClick={() => cloneAuthor(item)}
                      >
                        {cloning === item.id ? "正在克隆" : "克隆到当前书"}
                      </Button>
                      <Button
                        disabled={!canEdit}
                        onClick={() => mountAuthor(item)}
                      >
                        带入创作台给 AI 参考
                      </Button>
                      <Popconfirm
                        title="停用这张公共卡？"
                        description="停用后不再出现在陈列库；需要时可在该公共库的「身份与历史维护」中恢复。"
                        okText="确认停用"
                        cancelText="取消"
                        disabled={!canEditLibrary}
                        onConfirm={() => void retireCard(item)}
                      >
                        <Button
                          danger
                          disabled={!canEditLibrary}
                          loading={retiringId === item.id}
                        >
                          停用
                        </Button>
                      </Popconfirm>
                    </Space>
                  </Card>
                ))}
                {(authorTotal > 50 || offset > 0) && (
                  <div className="pager">
                    <Typography.Text type="secondary">
                      {`本页 ${authorCards.length} 张 · 共 ${authorTotal} 张公共卡`}
                    </Typography.Text>
                    <Space>
                      <Button
                        disabled={offset === 0}
                        onClick={() => setOffset(Math.max(0, offset - 50))}
                      >
                        上一页
                      </Button>
                      <Button
                        disabled={!hasNextAuthorPage}
                        onClick={() => setOffset(nextAuthorOffset)}
                      >
                        下一页
                      </Button>
                    </Space>
                  </div>
                )}
              </>
            )}
          </section>
        </div>
      )}
      <Modal
        title="新增公共卡"
        open={adding}
        onCancel={() => setAdding(false)}
        onOk={() => form.submit()}
        okButtonProps={{ disabled: !canEditLibrary }}
        destroyOnHidden
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={addCard}
          initialValues={{ commons_category: "writing_routine" }}
        >
          {cardError && (
            <Alert
              type="error"
              showIcon
              style={{ marginBottom: 12 }}
              title={cardError}
              action={
                <Space>
                  <Button
                    size="small"
                    onClick={() => {
                      library.refetch();
                    }}
                  >
                    重新载入
                  </Button>
                  <Button size="small" onClick={() => setCardError("")}>
                    留着我的修改
                  </Button>
                </Space>
              }
            />
          )}
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input maxLength={512} />
          </Form.Item>
          <Form.Item
            name="commons_category"
            label="所属板块"
            rules={[{ required: true }]}
          >
            <Select
              options={NAV.filter((item) => item.id !== "all").map((item) => ({
                value: item.id,
                label: item.label,
              }))}
            />
          </Form.Item>
          <Form.Item name="description" label="核心摘要">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item name="usage_guide" label="AI 用法提示">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item name="text" label="正文">
            <Input.TextArea rows={6} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={canEditLibrary ? "查看 / 编辑公共卡" : "查看公共卡全文"}
        open={editingCard !== null}
        onCancel={() => {
          setEditingCard(null);
          setEditError("");
        }}
        onOk={() => editForm.submit()}
        okText="保存修改"
        cancelText={canEditLibrary ? "取消" : "关闭"}
        confirmLoading={savingEdit}
        okButtonProps={{
          disabled: !canEditLibrary,
          style: canEditLibrary ? undefined : { display: "none" },
        }}
        destroyOnHidden
      >
        {loadingCardId ? (
          <Spin description="正在读取公共卡全文" />
        ) : (
          <Form
            form={editForm}
            layout="vertical"
            onFinish={saveEditedCard}
            disabled={!canEditLibrary}
          >
            {editError && (
              <Alert
                type="warning"
                showIcon
                style={{ marginBottom: 12 }}
                title={editError}
                action={
                  <Button size="small" onClick={() => void reloadEditingCard()}>
                    重新载入最新版
                  </Button>
                }
              />
            )}
            <Form.Item name="name" label="名称" rules={[{ required: true }]}>
              <Input maxLength={512} />
            </Form.Item>
            <Form.Item
              name="commons_category"
              label="所属板块"
              rules={[{ required: true }]}
            >
              <Select
                options={NAV.filter((item) => item.id !== "all").map(
                  (item) => ({
                    value: item.id,
                    label: item.label,
                  }),
                )}
              />
            </Form.Item>
            <Form.Item name="description" label="核心摘要">
              <Input.TextArea rows={3} />
            </Form.Item>
            <Form.Item name="usage_guide" label="AI 用法提示">
              <Input.TextArea rows={3} />
            </Form.Item>
            <Form.Item name="text" label="正文全文">
              <Input.TextArea rows={8} />
            </Form.Item>
          </Form>
        )}
      </Modal>
    </>
  );
}
