import { DeleteOutlined, PlusOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import {
  App,
  Button,
  Card,
  Checkbox,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Table,
  Tag,
  Typography,
} from "antd";
import { useEffect, useState } from "react";
import {
  adopt,
  api,
  scoped,
  type Definition,
  type Entity,
  type Json,
} from "../../shared/api";
import { ErrorPanel, PageTitle } from "../../shared/components/Feedback";
import { useWorkspace } from "../../shared/WorkspaceContext";
import { EntityDrawer } from "./components/EntityDrawer";
import { PropertyFields } from "./components/PropertyFields";

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
