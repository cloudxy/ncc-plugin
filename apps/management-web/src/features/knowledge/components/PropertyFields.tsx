import {
  Alert,
  Form,
  Input,
  InputNumber,
  Select,
  Space,
  Switch,
  Tag,
} from "antd";
import { useState } from "react";
import { type Definition, type Json } from "../../../shared/api";
import { ReferenceInput } from "../../../shared/inputs/ReferenceInput";

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

export function PropertyFields({
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
