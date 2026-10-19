import { PlusOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import {
  Alert,
  App,
  Button,
  Card,
  Checkbox,
  Form,
  Input,
  InputNumber,
  Modal,
  Select,
  Space,
  Switch,
  Table,
  Tag,
} from "antd";
import { useState } from "react";
import {
  adopt,
  api,
  scoped,
  type Definition,
  type Json,
} from "../../shared/api";
import {
  ErrorPanel,
  PageTitle,
  Permission,
} from "../../shared/components/Feedback";
import { useWorkspace } from "../../shared/WorkspaceContext";

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
