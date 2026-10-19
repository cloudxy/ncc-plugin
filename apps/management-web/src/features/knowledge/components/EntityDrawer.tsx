import { CopyOutlined, SaveOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import {
  App,
  Button,
  Checkbox,
  Drawer,
  Form,
  Input,
  Modal,
  Space,
  Table,
  Tabs,
  Tag,
  Typography,
} from "antd";
import { Suspense, useEffect, useState } from "react";
import {
  adopt,
  api,
  scoped,
  type Definition,
  type Entity,
  type Json,
} from "../../../shared/api";
import { ErrorPanel } from "../../../shared/components/Feedback";
import { TextEditor } from "../../../shared/components/TextEditor";
import { useWorkspace } from "../../../shared/WorkspaceContext";
import { Graph } from "./KnowledgeVisuals";
import { PropertyFields } from "./PropertyFields";

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
