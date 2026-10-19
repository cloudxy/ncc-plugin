import { lazy, Suspense, useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Alert,
  App,
  Button,
  Card,
  Checkbox,
  Collapse,
  Drawer,
  Form,
  Input,
  InputNumber,
  Modal,
  Select,
  Space,
  Switch,
  Table,
  Tabs,
  Tag,
  Typography,
} from "antd";
import {
  BranchesOutlined,
  CopyOutlined,
  DeleteOutlined,
  HistoryOutlined,
  PlusOutlined,
  SaveOutlined,
} from "@ant-design/icons";
import {
  api,
  adopt,
  scoped,
  type Definition,
  type Entity,
  type Json,
} from "./api";
import { useWorkspace } from "./context";
import { ErrorPanel, NoData, PageTitle, Permission } from "./common";
import { TextEditor } from "./editor";
const Graph = lazy(() =>
  import("./visuals").then((x) => ({ default: x.GraphCanvas })),
);
const MapCanvas = lazy(() =>
  import("./visuals").then((x) => ({ default: x.WorldMap })),
);

export function ReferenceInput({
  value,
  onChange,
  multiple = false,
  includeRetired = false,
}: {
  value?: string | string[];
  onChange?: (value: any) => void;
  multiple?: boolean;
  includeRetired?: boolean;
}) {
  const { scope } = useWorkspace(),
    [q, setQ] = useState("");
  const query = useQuery({
    queryKey: ["scope", scope.id, "reference-search", q, includeRetired],
    queryFn: () =>
      api<Json>(scoped(scope.id, "/entities/search"), "POST", {
        q,
        limit: 50,
        include_deleted: includeRetired,
      }),
  });
  return (
    <Select
      style={{ width: "100%" }}
      aria-label="查找引用对象"
      value={value}
      onChange={onChange}
      mode={multiple ? "multiple" : undefined}
      allowClear
      showSearch
      filterOption={false}
      onSearch={setQ}
      placeholder="输入名称查找对象"
      options={query.data?.items.map((e: Entity) => ({
        value: e.id,
        label: `${e.name} · ${e.kind}`,
      }))}
    />
  );
}

function StructuredInput({
  value = {},
  onChange,
  fields,
}: {
  value?: Json;
  onChange?: (value: Json) => void;
  fields: [string, string][];
}) {
  return (
    <Space.Compact block>
      {fields.map(([key, label]) => (
        <Input
          key={key}
          aria-label={label}
          placeholder={label}
          value={value[key] || ""}
          onChange={(e) => onChange?.({ ...value, [key]: e.target.value })}
        />
      ))}
    </Space.Compact>
  );
}
function FieldInput({ rule }: { rule: Json }) {
  if (rule.type === "boolean") return <Switch />;
  if (rule.type === "integer")
    return (
      <InputNumber
        min={rule.minimum}
        max={rule.maximum}
        style={{ width: "100%" }}
      />
    );
  if (rule.type === "enum")
    return (
      <Select
        options={rule.enum?.map((v: string) => ({ value: v, label: v }))}
      />
    );
  if (rule.type === "tags")
    return <Select mode="tags" tokenSeparators={[",", "，"]} />;
  if (rule.type === "reference" || rule.type === "references")
    return <ReferenceInput multiple={rule.type === "references"} />;
  if (rule.type === "ratio")
    return (
      <StructuredInput
        fields={[
          ["numerator", "精确分子"],
          ["denominator", "非零分母"],
        ]}
      />
    );
  if (rule.type === "quantity")
    return (
      <StructuredInput
        fields={[
          ["amount", "精确数量"],
          ["unit", "单位"],
        ]}
      />
    );
  if (rule.type === "coordinate")
    return (
      <StructuredInput
        fields={[
          ["x", "X坐标"],
          ["y", "Y坐标"],
          ["frame", "坐标系"],
        ]}
      />
    );
  if (rule.type === "soft_reference")
    return (
      <StructuredInput
        fields={[
          ["uri", "ncc://范围/身份"],
          ["kind", "预期类型"],
          ["label", "未解析名称"],
        ]}
      />
    );
  if (rule.type === "decimal")
    return <Input inputMode="decimal" placeholder="精确数值，按字符串保存" />;
  if (rule.type === "attachment")
    return <Input placeholder="上传后选择附件ID" />;
  if (rule.type === "text")
    return <Input.TextArea autoSize={{ minRows: 1, maxRows: 6 }} />;
  return (
    <Alert type="warning" title="此控件尚不兼容，请保留原值并导出或升级定义" />
  );
}

function PropertyFields({
  definition,
  existing = {},
}: {
  definition?: Definition;
  existing?: Json;
}) {
  const props = definition?.spec.properties || {},
    required = definition?.spec.required || [];
  const [added, setAdded] = useState<string[]>([]);
  const shown = Array.from(
    new Set([
      ...required,
      ...Object.keys(existing),
      ...["description", "tags"].filter((k) => k in props),
      ...added,
    ]),
  );
  return (
    <>
      <Form.Item label="添加属性">
        <Select
          allowClear
          showSearch
          placeholder="按需添加属性，避免一次填完整张表"
          options={Object.entries(props)
            .filter(([k]) => !shown.includes(k))
            .map(([k, r]) => ({ value: k, label: r.label || k }))}
          onSelect={(v) => setAdded([...added, v])}
        />
      </Form.Item>
      {shown.map((key) => {
        const rule = props[key];
        if (!rule)
          return (
            <Alert
              key={key}
              type="warning"
              title={`旧属性 ${key} 未被当前定义识别，保存前需明确升级或映射`}
            />
          );
        return (
          <Form.Item
            key={key}
            name={["data", key]}
            label={
              <Space>
                {rule.label || key}
                {rule.secret && <Tag color="orange">作者秘密</Tag>}
              </Space>
            }
            valuePropName={rule.type === "boolean" ? "checked" : "value"}
            rules={[
              { required: required.includes(key), message: "此属性为必填" },
            ]}
          >
            <FieldInput rule={rule} />
          </Form.Item>
        );
      })}
    </>
  );
}

export function EntityDrawer({
  id,
  onClose,
}: {
  id?: string;
  onClose: () => void;
}) {
  const { scope, refresh, setDirty } = useWorkspace(),
    { message, modal } = App.useApp(),
    [form] = Form.useForm(),
    [text, setText] = useState(""),
    [dirty, setLocalDirty] = useState(false),
    [saving, setSaving] = useState(false),
    [editingBaseline, setEditingBaseline] = useState<Entity>(),
    [snapshot, setSnapshot] = useState<Json>();
  const entity = useQuery({
    queryKey: ["scope", scope.id, "entity", id],
    queryFn: () =>
      api<Entity>(scoped(scope.id, `/entities/${id}?include_deleted=true`)),
    enabled: !!id,
  });
  const defs = useQuery({
    queryKey: ["scope", scope.id, "definitions"],
    queryFn: () => api<Definition[]>(scoped(scope.id, "/definitions")),
  });
  const history = useQuery({
    queryKey: ["scope", scope.id, "history", id],
    queryFn: () => api<Json[]>(scoped(scope.id, `/entities/${id}/history`)),
    enabled: !!id,
  });
  const currentDef = entity.data?.definition_spec
    ? {
        id: entity.data.definition_id,
        key: entity.data.kind,
        version: 0,
        spec: entity.data.definition_spec,
      }
    : defs.data?.find((d) => d.id === entity.data?.definition_id);
  useEffect(() => {
    if (entity.data && !dirty) {
      form.setFieldsValue(entity.data);
      setText(entity.data.text);
      setEditingBaseline(entity.data);
    }
  }, [entity.data]);
  async function save(values: Json) {
    if (!editingBaseline) return;
    setSaving(true);
    try {
      const data = Object.fromEntries(
        Object.entries(values.data || {}).filter(
          ([, v]) => v !== undefined && v !== null,
        ),
      );
      await adopt(
        scope,
        [
          {
            op: "update",
            entity_id: id,
            expected: editingBaseline.version,
            name: values.name,
            data,
            unset: Object.keys(editingBaseline.data).filter(
              (k) => !(k in data),
            ),
            text,
            secret: !!values.secret,
          },
        ],
        "修改资料：" + editingBaseline.name,
      );
      setLocalDirty(false);
      setDirty(false);
      refresh();
      entity.refetch();
      history.refetch();
      message.success("修订已保存");
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setSaving(false);
    }
  }
  function close() {
    if (dirty)
      modal.confirm({
        title: "离开未保存的编辑？",
        onOk: () => {
          setDirty(false);
          setLocalDirty(false);
          onClose();
        },
      });
    else onClose();
  }
  return (
    <>
      <Drawer
        title={entity.data?.name || "对象详情"}
        width={900}
        open={!!id}
        onClose={close}
        destroyOnHidden
      >
        <ErrorPanel error={entity.error} />
        {entity.data && (
          <Tabs
            items={[
              {
                key: "edit",
                label: "属性与内容",
                children: (
                  <Form
                    form={form}
                    layout="vertical"
                    onFinish={save}
                    disabled={saving || !scope.actions.includes("edit")}
                    onValuesChange={() => {
                      setLocalDirty(true);
                      setDirty(true);
                    }}
                  >
                    <Space style={{ marginBottom: 16 }}>
                      <Tag>{entity.data.kind}</Tag>
                      <Tag>版本 {entity.data.version.split(":").pop()}</Tag>
                      <Button
                        type="primary"
                        loading={saving}
                        htmlType="submit"
                        disabled={!scope.actions.includes("edit")}
                        icon={<SaveOutlined />}
                      >
                        保存新修订
                      </Button>
                    </Space>
                    <Form.Item
                      name="name"
                      label="名称"
                      rules={[{ required: true }]}
                    >
                      <Input />
                    </Form.Item>
                    <Form.Item name="secret" valuePropName="checked">
                      <Checkbox disabled={!scope.actions.includes("secret")}>
                        作者秘密，限制普通检索与视角
                      </Checkbox>
                    </Form.Item>
                    <PropertyFields
                      key={id}
                      definition={currentDef}
                      existing={entity.data.data}
                    />
                    <Typography.Title level={5}>
                      原文 / 正文 / 详细内容
                    </Typography.Title>
                    <TextEditor
                      value={text}
                      readOnly={saving || !scope.actions.includes("edit")}
                      onChange={(value) => {
                        setText(value);
                        setLocalDirty(true);
                        setDirty(true);
                      }}
                      height={400}
                    />
                  </Form>
                ),
              },
              {
                key: "history",
                label: "修订历史",
                children: (
                  <Table
                    rowKey="id"
                    dataSource={history.data}
                    pagination={{ pageSize: 12 }}
                    columns={[
                      { title: "记录版本", dataIndex: "version" },
                      {
                        title: "记录时间",
                        dataIndex: "created_at",
                        render: (v) => new Date(v).toLocaleString(),
                      },
                      {
                        title: "摘要",
                        dataIndex: "hash",
                        render: (v) => <code>{v.slice(0, 12)}</code>,
                      },
                      {
                        title: "查看",
                        render: (_, r) => (
                          <Button
                            type="link"
                            onClick={async () => {
                              try {
                                setSnapshot(
                                  await api(
                                    scoped(
                                      scope.id,
                                      `/entities/${id}/revisions/${r.id}`,
                                    ),
                                  ),
                                );
                              } catch (e) {
                                message.error((e as Error).message);
                              }
                            }}
                          >
                            打开此修订
                          </Button>
                        ),
                      },
                    ]}
                  />
                ),
              },
              {
                key: "graph",
                label: "关系图",
                children: (
                  <Suspense fallback="正在加载图谱">
                    <Graph scope={scope.id} center={id!} />
                  </Suspense>
                ),
              },
              {
                key: "identity",
                label: "身份与引用",
                children: (
                  <>
                    <Typography.Paragraph>
                      稳定身份：<code>{id}</code>
                    </Typography.Paragraph>
                    <Typography.Paragraph>
                      名称、关系和证据独立记录；改名保留历史。
                    </Typography.Paragraph>
                    <Button
                      icon={<CopyOutlined />}
                      onClick={() =>
                        navigator.clipboard.writeText(
                          `${location.origin}/materials?entity=${id}`,
                        )
                      }
                    >
                      复制稳定链接
                    </Button>
                  </>
                ),
              },
            ]}
          />
        )}
      </Drawer>
      <Modal
        open={!!snapshot}
        title="历史修订（只读）"
        width={880}
        footer={
          <Button
            type="primary"
            disabled={!scope.actions.includes("adopt")}
            onClick={async () => {
              try {
                const fresh = await api<Json>(scoped(scope.id, ""));
                const plan = await api<Json>(
                  scoped(scope.id, "/maintenance/plan"),
                  "POST",
                  {
                    action: "restore",
                    base_version: fresh.version,
                    entity_id: id,
                    revision_id: snapshot?.revision,
                  },
                );
                if (!plan.change?.validation?.valid)
                  throw new Error(
                    JSON.stringify(plan.change?.validation?.errors),
                  );
                await api(
                  scoped(scope.id, `/changes/${plan.change.id}/adopt`),
                  "POST",
                );
                setSnapshot(undefined);
                refresh();
                entity.refetch();
                history.refetch();
                message.success("已作为新修订恢复，原历史保留");
              } catch (e) {
                message.error((e as Error).message);
              }
            }}
          >
            恢复为新修订
          </Button>
        }
        onCancel={() => setSnapshot(undefined)}
      >
        <TextEditor value={snapshot?.text || ""} readOnly height={450} />
        <pre className="json-block">
          {JSON.stringify(snapshot?.data, null, 2)}
        </pre>
      </Modal>
    </>
  );
}

export function MaterialsPage() {
  const { scope, refresh } = useWorkspace(),
    { message, modal } = App.useApp(),
    [q, setQ] = useState(""),
    [kind, setKind] = useState<string>(),
    [offset, setOffset] = useState(0),
    [selected, setSelected] = useState<React.Key[]>([]),
    [detail, setDetail] = useState<string>(),
    [creating, setCreating] = useState(false),
    [form] = Form.useForm(),
    [createId, setCreateId] = useState(crypto.randomUUID());
  const [newKind, setNewKind] = useState("character");
  const defs = useQuery({
    queryKey: ["scope", scope.id, "definitions"],
    queryFn: () => api<Definition[]>(scoped(scope.id, "/definitions")),
  });
  const query = useQuery({
    queryKey: ["scope", scope.id, "materials", q, kind, offset],
    queryFn: () =>
      api<Json>(scoped(scope.id, "/entities/search"), "POST", {
        q,
        kind,
        offset,
        limit: 50,
      }),
  });
  const options = defs.data
    ?.filter((d) => !d.spec.relation)
    .map((d) => ({
      value: d.key,
      label: d.spec.label === d.key ? d.key : `${d.spec.label} · ${d.key}`,
    }));
  const definition = defs.data?.find((d) => d.key === newKind);
  async function create(values: Json) {
    try {
      const data = Object.fromEntries(
        Object.entries(values.data || {}).filter(
          ([, v]) => v !== undefined && v !== null,
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
      setCreateId(crypto.randomUUID());
      refresh();
      query.refetch();
      message.success("资料已建立");
    } catch (e) {
      message.error((e as Error).message);
    }
  }
  async function retire() {
    const rows = (query.data?.items || []).filter((e: Entity) =>
      selected.includes(e.id),
    );
    modal.confirm({
      title: `停用选中的 ${rows.length} 项资料？`,
      content: "保留稳定身份、修订及历史引用，新的引用会提示已停用。",
      onOk: async () => {
        try {
          await adopt(
            scope,
            rows.map((e: Entity) => ({
              op: "retire",
              entity_id: e.id,
              expected: e.version,
            })),
            "批量停用资料",
          );
          setSelected([]);
          refresh();
          query.refetch();
        } catch (e) {
          message.error((e as Error).message);
        }
      },
    });
  }
  useEffect(() => {
    const id = new URLSearchParams(location.search).get("entity");
    if (id) setDetail(id);
  }, []);
  return (
    <>
      <PageTitle
        title="作品资料"
        note="人物、世界、剧情和来源共用稳定身份，按需要逐步完善。"
        actions={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            disabled={!scope.actions.includes("edit")}
            onClick={() => setCreating(true)}
          >
            新建资料
          </Button>
        }
      />
      <Card>
        <div className="table-toolbar">
          <Space wrap>
            <Input.Search
              aria-label="搜索作品资料"
              placeholder="搜索名称或原文，支持中文专名"
              onSearch={(v) => {
                setQ(v);
                setOffset(0);
              }}
              allowClear
              style={{ width: 300 }}
            />
            <Select
              aria-label="资料类型"
              showSearch
              allowClear
              optionFilterProp="label"
              value={kind}
              placeholder="全部类型"
              style={{ width: 230 }}
              options={options}
              onChange={(v) => {
                setKind(v);
                setOffset(0);
              }}
            />
            <Button
              onClick={() => {
                modal.confirm({
                  title: "保存当前筛选为个人视图",
                  content: "此视图仅保存在你的账号下。",
                  onOk: () =>
                    api(scoped(scope.id, "/views"), "POST", {
                      name: kind || q || "全部资料",
                      query: { q, kind, limit: 50 },
                    }).then(() => message.success("视图已保存")),
                });
              }}
            >
              保存视图
            </Button>
          </Space>
          {selected.length > 0 && (
            <Space>
              <Tag>选中本页 {selected.length} 项</Tag>
              <Button danger icon={<DeleteOutlined />} onClick={retire}>
                批量停用
              </Button>
            </Space>
          )}
        </div>
        <ErrorPanel error={query.error} retry={() => query.refetch()} />
        <Table
          rowKey="id"
          loading={query.isPending}
          dataSource={query.data?.items}
          pagination={false}
          scroll={{ x: 1000 }}
          rowSelection={
            scope.actions.includes("edit")
              ? { selectedRowKeys: selected, onChange: setSelected }
              : undefined
          }
          columns={[
            {
              title: "名称",
              dataIndex: "name",
              width: 220,
              render: (name: string, row: Entity) => (
                <Button type="link" onClick={() => setDetail(row.id)}>
                  {name}
                </Button>
              ),
            },
            {
              title: "类型",
              dataIndex: "kind",
              width: 160,
              render: (v) => (
                <Tag>
                  {defs.data?.find((d) => d.key === v)?.spec.label || v}
                </Tag>
              ),
            },
            {
              title: "摘要",
              render: (_, r) => r.data?.description || r.text_preview || "—",
            },
            {
              title: "标签",
              render: (_, r) => (
                <Space wrap>
                  {r.data?.tags?.map((v: string) => (
                    <Tag key={v}>{v}</Tag>
                  ))}
                </Space>
              ),
            },
            {
              title: "版本",
              dataIndex: "version",
              width: 100,
              render: (v) => v.split(":").pop(),
            },
            {
              title: "范围",
              dataIndex: "secret",
              width: 100,
              render: (v) => (
                <Tag color={v ? "orange" : "default"}>
                  {v ? "作者秘密" : "普通资料"}
                </Tag>
              ),
            },
          ]}
        />
        <div className="pager">
          <Typography.Text type="secondary">
            当前 {query.data?.items.length || 0} 条 · 服务端分页
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
        onCancel={() => setCreating(false)}
        onOk={() => form.submit()}
        destroyOnHidden
      >
        <Form form={form} layout="vertical" onFinish={create}>
          <Form.Item label="类型">
            <Select
              showSearch
              value={newKind}
              options={options}
              optionFilterProp="label"
              onChange={(v) => {
                setNewKind(v);
                form.setFieldsValue({ data: {} });
              }}
            />
          </Form.Item>
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input placeholder="稳定身份会自动分配" />
          </Form.Item>
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

export function DefinitionsPage() {
  const { scope, refresh } = useWorkspace(),
    { message } = App.useApp(),
    [open, setOpen] = useState(false),
    [form] = Form.useForm(),
    [relation, setRelation] = useState(false);
  const query = useQuery({
    queryKey: ["scope", scope.id, "definitions"],
    queryFn: () => api<Definition[]>(scoped(scope.id, "/definitions")),
  });
  async function publish(values: Json) {
    try {
      const properties: Json = {};
      const required: string[] = [];
      for (const p of values.fields || []) {
        if (!p?.key) continue;
        properties[p.key] = { type: p.type, label: p.label || p.key };
        if (p.type === "enum")
          properties[p.key].enum = (p.enum || "")
            .split(",")
            .map((s: string) => s.trim())
            .filter(Boolean);
        if (p.required) required.push(p.key);
      }
      const spec = relation
        ? {
            label: values.label,
            relation: true,
            exclusive_target: !!values.exclusive_target,
            acyclic: !!values.acyclic,
          }
        : {
            label: values.label,
            domain: values.domain || "自定义",
            properties,
            required,
          };
      await adopt(
        scope,
        [
          {
            op: "definition",
            definition: {
              key:
                relation && !values.key.startsWith("rel:")
                  ? "rel:" + values.key
                  : values.key,
              version: values.version || 1,
              spec,
            },
          },
        ],
        "发布定义：" + values.label,
      );
      setOpen(false);
      form.resetFields();
      query.refetch();
      refresh();
      message.success("定义已发布并在当前范围采用");
    } catch (e) {
      message.error((e as Error).message);
    }
  }
  return (
    <Permission allowed={scope.actions.includes("admin")}>
      <PageTitle
        title="定义中心"
        note="新增领域通过定义注册。发布新版本保留旧实例使用的定义，不静默改写历史。"
        actions={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              form.resetFields();
              setRelation(false);
              setOpen(true);
            }}
          >
            注册类型或关系
          </Button>
        }
      />
      <Card>
        <ErrorPanel error={query.error} />
        <Table
          rowKey="id"
          dataSource={query.data}
          loading={query.isPending}
          pagination={{ pageSize: 15, showSizeChanger: true }}
          columns={[
            {
              title: "名称",
              render: (_, r) => (
                <Space>
                  {r.spec.label}
                  <Tag>{r.spec.relation ? "关系" : "对象类型"}</Tag>
                </Space>
              ),
            },
            { title: "稳定键", dataIndex: "key" },
            { title: "领域", render: (_, r) => r.spec.domain || "通用" },
            { title: "版本", dataIndex: "version" },
            {
              title: "属性数",
              render: (_, r) => Object.keys(r.spec.properties || {}).length,
            },
            {
              title: "升级",
              render: (_, r) => (
                <Button
                  type="link"
                  onClick={() => {
                    setRelation(!!r.spec.relation);
                    form.setFieldsValue({
                      key: r.key,
                      label: r.spec.label,
                      domain: r.spec.domain,
                      version: r.version + 1,
                      exclusive_target: r.spec.exclusive_target,
                      acyclic: r.spec.acyclic,
                      fields: Object.entries(r.spec.properties || {}).map(
                        ([key, p]) => ({
                          key,
                          ...p,
                          enum: p.enum?.join(","),
                          required: r.spec.required?.includes(key),
                        }),
                      ),
                    });
                    setOpen(true);
                  }}
                >
                  新版本
                </Button>
              ),
            },
          ]}
        />
      </Card>
      <Modal
        title="定义与控件"
        open={open}
        width={940}
        onCancel={() => setOpen(false)}
        onOk={() => form.submit()}
        okText="预检并发布"
        destroyOnHidden
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            version: 1,
            fields: [{ key: "description", label: "说明", type: "text" }],
          }}
          onFinish={publish}
        >
          <Space align="start" wrap>
            <Form.Item name="key" label="稳定键" rules={[{ required: true }]}>
              <Input placeholder="如：异火 / route" />
            </Form.Item>
            <Form.Item name="label" label="显示名" rules={[{ required: true }]}>
              <Input />
            </Form.Item>
            <Form.Item name="version" label="版本">
              <InputNumber min={1} />
            </Form.Item>
            <Form.Item name="domain" label="领域">
              <Input placeholder="自定义" />
            </Form.Item>
          </Space>
          <Form.Item label="定义用途">
            <Switch
              checked={relation}
              onChange={setRelation}
              checkedChildren="关系"
              unCheckedChildren="对象类型"
            />
          </Form.Item>
          {relation ? (
            <Space>
              <Form.Item name="exclusive_target" valuePropName="checked">
                <Checkbox>同一时段目标排他（例如所有权）</Checkbox>
              </Form.Item>
              <Form.Item name="acyclic" valuePropName="checked">
                <Checkbox>禁止循环（例如行政指挥）</Checkbox>
              </Form.Item>
            </Space>
          ) : (
            <Form.List name="fields">
              {(fields, { add, remove }) => (
                <>
                  {fields.map((field) => (
                    <Space key={field.key} align="start" wrap>
                      <Form.Item
                        name={[field.name, "key"]}
                        rules={[{ required: true }]}
                      >
                        <Input placeholder="属性稳定键" />
                      </Form.Item>
                      <Form.Item name={[field.name, "label"]}>
                        <Input placeholder="显示名" />
                      </Form.Item>
                      <Form.Item
                        name={[field.name, "type"]}
                        rules={[{ required: true }]}
                      >
                        <Select
                          style={{ width: 145 }}
                          options={[
                            "text",
                            "integer",
                            "decimal",
                            "boolean",
                            "enum",
                            "tags",
                            "reference",
                            "references",
                            "ratio",
                            "quantity",
                            "coordinate",
                            "attachment",
                            "soft_reference",
                          ].map((value) => ({ value, label: value }))}
                        />
                      </Form.Item>
                      <Form.Item name={[field.name, "enum"]}>
                        <Input placeholder="枚举项，以逗号分隔" />
                      </Form.Item>
                      <Form.Item
                        name={[field.name, "required"]}
                        valuePropName="checked"
                      >
                        <Checkbox>必填</Checkbox>
                      </Form.Item>
                      <Button
                        type="text"
                        danger
                        onClick={() => remove(field.name)}
                      >
                        删除
                      </Button>
                    </Space>
                  ))}
                  <Button
                    block
                    icon={<PlusOutlined />}
                    onClick={() => add({ type: "text" })}
                  >
                    添加属性
                  </Button>
                </>
              )}
            </Form.List>
          )}
        </Form>
        <Alert
          style={{ marginTop: 16 }}
          type="info"
          title="定义的校验与关系语义由服务端执行；配置不会运行任意脚本。"
        />
      </Modal>
    </Permission>
  );
}

export function RelationsPage() {
  const { scope, refresh } = useWorkspace(),
    { message } = App.useApp(),
    [category, setCategory] = useState("relation"),
    [calendar, setCalendar] = useState(""),
    [worldAt, setWorldAt] = useState(""),
    [asOf, setAsOf] = useState<number>(),
    [open, setOpen] = useState(false),
    [form] = Form.useForm(),
    [graph, setGraph] = useState<string>(),
    [transfer, setTransfer] = useState<Json>();
  const [transferForm] = Form.useForm();
  const defs = useQuery({
    queryKey: ["scope", scope.id, "definitions"],
    queryFn: () => api<Definition[]>(scoped(scope.id, "/definitions")),
  });
  const entities = useQuery({
    queryKey: ["scope", scope.id, "relation-labels"],
    queryFn: () =>
      api<Json>(scoped(scope.id, "/entities/search"), "POST", { limit: 200 }),
  });
  const labels = new Map<string, string>(
    entities.data?.items.map((e: Entity) => [e.id, e.name]),
  );
  const query = useQuery({
    queryKey: ["scope", scope.id, "facts", category, calendar, worldAt, asOf],
    queryFn: () =>
      api<Json>(scoped(scope.id, "/state/query"), "POST", {
        category,
        calendar: calendar || null,
        world_at: worldAt || null,
        as_of: asOf,
        limit: 200,
      }),
  });
  async function save(values: Json) {
    try {
      const value =
        category === "belief"
          ? {
              proposition: values.proposition,
              stance: values.stance,
              attitude: values.attitude || "",
              confidence: values.confidence || "",
            }
          : { text: values.value || "" };
      const fact = {
        predicate: values.predicate || category,
        category,
        object_id: values.object_id || null,
        value,
        calendar: values.calendar || null,
        world_from: values.world_from || null,
        world_to: values.world_to || null,
        chapter_id: values.chapter_id || null,
        secret: !!values.secret,
        source: { kind: "author", note: values.note || "" },
      };
      await adopt(
        scope,
        [{ op: "fact", entity_id: values.subject_id, fact }],
        "维护关系与历史",
      );
      setOpen(false);
      form.resetFields();
      refresh();
      query.refetch();
      message.success("记录已采用");
    } catch (e) {
      message.error((e as Error).message);
    }
  }
  async function move(values: Json) {
    try {
      const old = transfer!;
      const retained = {
        predicate: old.predicate,
        category: "relation",
        object_id: old.object_id,
        value: old.value,
        calendar: old.calendar,
        world_from: old.world_from,
        world_to: values.time,
        supersedes: old.id,
        source: { kind: "author", note: "关闭流转前区间" },
      };
      const next = {
        ...retained,
        world_from: values.time,
        world_to: null,
        supersedes: null,
        source: { kind: "author", note: values.note || "流转" },
      };
      await adopt(
        scope,
        [
          { op: "fact", entity_id: old.subject_id, fact: retained },
          { op: "fact", entity_id: values.owner, fact: next },
        ],
        "物品流转",
      );
      setTransfer(undefined);
      query.refetch();
      refresh();
      message.success("流转与历史已同步");
    } catch (e) {
      message.error((e as Error).message);
    }
  }
  return (
    <>
      <PageTitle
        title="关系、认知与时间"
        note="世界有效时间和系统记录版本分别查询。多重隶属、名义/实际关系分别保留。"
        actions={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            disabled={!scope.actions.includes("edit")}
            onClick={() => setOpen(true)}
          >
            新增记录
          </Button>
        }
      />
      <Card>
        <Space wrap style={{ marginBottom: 20 }}>
          <Select
            aria-label="记录类别"
            value={category}
            onChange={setCategory}
            style={{ width: 150 }}
            options={[
              ["relation", "关系与组织"],
              ["belief", "角色认知"],
              ["reveal", "读者揭示"],
              ["fact", "世界事实"],
              ["name", "名称与别名"],
              ["plan", "未来规划"],
            ].map(([value, label]) => ({ value, label }))}
          />
          <Input
            placeholder="历法 / 坐标口径"
            style={{ width: 160 }}
            value={calendar}
            onChange={(e) => setCalendar(e.target.value)}
          />
          <Input
            placeholder="故事内时点"
            style={{ width: 160 }}
            value={worldAt}
            onChange={(e) => setWorldAt(e.target.value)}
          />
          <InputNumber
            aria-label="记录截至版本"
            placeholder="当前记录版本"
            min={0}
            max={scope.version}
            value={asOf}
            onChange={(v) => setAsOf(v ?? undefined)}
          />
        </Space>
        <ErrorPanel error={query.error} />
        {query.data?.uncertain_time_count > 0 && (
          <Alert
            type="info"
            title={`${query.data?.uncertain_time_count}项历法不明确，未伪造精确时点`}
          />
        )}
        <Table<Json>
          rowKey="id"
          loading={query.isPending}
          dataSource={query.data?.items}
          pagination={{ pageSize: 15 }}
          scroll={{ x: 1100 }}
          columns={[
            {
              title: "对象",
              dataIndex: "subject_id",
              render: (v) => (
                <Button type="link" onClick={() => setGraph(v)}>
                  {labels.get(v) || v.slice(0, 8)}
                </Button>
              ),
            },
            { title: "关系/命题", dataIndex: "predicate" },
            {
              title: "关联对象 / 值",
              render: (_, r) =>
                r.object_id
                  ? labels.get(r.object_id) || r.object_id.slice(0, 8)
                  : JSON.stringify(r.value),
            },
            {
              title: "世界有效区间",
              render: (_, r) =>
                r.calendar
                  ? `${r.calendar} [${r.world_from ?? "未知"}, ${r.world_to ?? "持续"})`
                  : "未知 / 未定时",
            },
            { title: "记录版本", dataIndex: "recorded_from" },
            {
              title: "操作",
              render: (_, r) => (
                <Space>
                  {["owns", "custody"].includes(r.predicate) &&
                    r.calendar &&
                    scope.actions.includes("edit") && (
                      <Button type="link" onClick={() => setTransfer(r)}>
                        流转
                      </Button>
                    )}
                  <Button
                    type="link"
                    disabled={!scope.actions.includes("edit")}
                    onClick={async () => {
                      try {
                        await adopt(
                          scope,
                          [
                            {
                              op: "retract",
                              entity_id: r.subject_id,
                              fact_id: r.id,
                            },
                          ],
                          "撤回事实记录",
                        );
                        query.refetch();
                        refresh();
                      } catch (e) {
                        message.error((e as Error).message);
                      }
                    }}
                  >
                    撤回
                  </Button>
                </Space>
              ),
            },
          ]}
        />
      </Card>
      <Modal
        title="维护一项记录"
        open={open}
        width={720}
        onCancel={() => setOpen(false)}
        onOk={() => form.submit()}
        destroyOnHidden
      >
        <Form form={form} layout="vertical" onFinish={save}>
          <Form.Item
            name="subject_id"
            label="主体"
            rules={[{ required: true }]}
          >
            <ReferenceInput />
          </Form.Item>
          <Form.Item
            name="predicate"
            label="关系/属性"
            rules={[{ required: true }]}
          >
            {category === "relation" ? (
              <Select
                options={defs.data
                  ?.filter((d) => d.spec.relation)
                  .map((d) => ({
                    value: d.key.replace(/^rel:/, ""),
                    label: d.spec.label,
                  }))}
              />
            ) : (
              <Input />
            )}
          </Form.Item>
          {category === "relation" && (
            <Form.Item
              name="object_id"
              label="目标"
              rules={[{ required: true }]}
            >
              <ReferenceInput />
            </Form.Item>
          )}
          {category === "belief" ? (
            <>
              <Form.Item
                name="proposition"
                label="命题"
                rules={[{ required: true }]}
              >
                <Input />
              </Form.Item>
              <Form.Item
                name="stance"
                label="信念状态"
                rules={[{ required: true }]}
              >
                <Select
                  options={[
                    ["knows", "知道"],
                    ["suspects", "怀疑"],
                    ["misbelieves", "误信"],
                    ["unaware", "不知"],
                    ["denies", "否认"],
                  ].map(([value, label]) => ({ value, label }))}
                />
              </Form.Item>
              <Form.Item name="attitude" label="对外态度">
                <Input />
              </Form.Item>
            </>
          ) : (
            <Form.Item name="value" label="说明 / 值">
              <Input.TextArea />
            </Form.Item>
          )}
          <Space align="start">
            <Form.Item name="calendar" label="历法">
              <Input />
            </Form.Item>
            <Form.Item name="world_from" label="有效起点">
              <Input />
            </Form.Item>
            <Form.Item name="world_to" label="有效终点">
              <Input placeholder="不填为持续" />
            </Form.Item>
          </Space>
          <Form.Item name="chapter_id" label="从哪章出现 / 揭示">
            <ReferenceInput />
          </Form.Item>
          <Form.Item name="note" label="来源或作者决定">
            <Input.TextArea />
          </Form.Item>
          <Form.Item name="secret" valuePropName="checked">
            <Checkbox>隐藏关系 / 作者秘密</Checkbox>
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={!!transfer}
        title="转移所有权或保管关系"
        onCancel={() => setTransfer(undefined)}
        onOk={() => transferForm.submit()}
      >
        <Form form={transferForm} layout="vertical" onFinish={move}>
          <Form.Item name="owner" label="新的主体" rules={[{ required: true }]}>
            <ReferenceInput />
          </Form.Item>
          <Form.Item
            name="time"
            label={`生效时点（${transfer?.calendar || ""}）`}
            rules={[{ required: true }]}
          >
            <Input />
          </Form.Item>
          <Form.Item name="note" label="流转事件与来源">
            <Input />
          </Form.Item>
        </Form>
      </Modal>
      <Drawer
        title="局部关系图"
        width={1000}
        open={!!graph}
        onClose={() => setGraph(undefined)}
      >
        <Suspense fallback="加载图谱">
          {graph && <Graph scope={scope.id} center={graph} />}
        </Suspense>
      </Drawer>
    </>
  );
}

export function MapPage() {
  const { scope } = useWorkspace();
  const entities = useQuery({
    queryKey: ["scope", scope.id, "map-entities"],
    queryFn: () =>
      api<Json>(scoped(scope.id, "/entities/search"), "POST", { limit: 200 }),
  });
  return (
    <>
      <PageTitle
        title="地图与地点"
        note="支持虚构坐标与本地底图。标注使用稳定地点身份，未知坐标保持未知。"
      />
      <Card>
        <Suspense fallback="加载地图">
          <MapCanvas scope={scope.id} entities={entities.data?.items || []} />
        </Suspense>
        <Typography.Paragraph type="secondary">
          当前显示已加载资料中的坐标。编辑地点的 coordinate
          属性维护位置，移动布局不会改变故事中的地理事实。
        </Typography.Paragraph>
      </Card>
    </>
  );
}
