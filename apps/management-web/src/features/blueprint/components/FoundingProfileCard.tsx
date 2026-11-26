import { App, Button, Collapse, Form, Input, Select, Space, Tag } from "antd";
import { useEffect, useState } from "react";
import type { Json } from "../../../shared/api";
import {
  saveStudioFounding,
  type StudioFoundingConfig,
} from "../../../shared/studioApi";
import { useWorkspace } from "../../../shared/WorkspaceContext";
import { effectDetail } from "../../creation/effectDetail";

export function FoundingProfileCard({
  founding,
  canEdit,
  onSaved,
}: {
  founding?: StudioFoundingConfig;
  canEdit: boolean;
  onSaved: () => void;
}) {
  const { scope } = useWorkspace();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!founding || form.isFieldsTouched()) return;
    form.setFieldsValue({
      soul_question: founding.soul_question || "",
      soul_answer: founding.soul_answer || "",
      soul_injustice: founding.soul_injustice || "",
      soul_ending: founding.soul_ending || "",
      soul_arc: founding.soul_arc || "",
      soul_status: founding.soul_status || "",
      writing_mode: founding.writing_mode || "",
      contract_main: founding.contract_main || "",
      contract_audience: founding.contract_audience || "",
      contract_extras: founding.contract_extras || [],
      poison_lines: founding.poison_lines || [],
      style_anchor: founding.style_anchor || "",
    });
  }, [founding, form]);

  const summaryBadges = [
    founding?.soul_status ? `书魂：${founding.soul_status}` : null,
    founding?.writing_mode ? `模式：${founding.writing_mode}` : null,
    founding?.contract_main ? `主契约：${founding.contract_main}` : null,
    founding?.poison_lines?.length
      ? `毒点红线 ${founding.poison_lines.length} 条`
      : null,
  ].filter(Boolean);

  async function handleSave(values: Json) {
    setSaving(true);
    try {
      await saveStudioFounding(scope.id, {
        soul_question: String(values.soul_question || ""),
        soul_answer: String(values.soul_answer || ""),
        soul_injustice: String(values.soul_injustice || ""),
        soul_ending: String(values.soul_ending || ""),
        soul_arc: (values.soul_arc || "") as "" | "正向" | "负向" | "平弧",
        soul_status: (values.soul_status || "") as "" | "暂定" | "确定",
        contract_main: String(values.contract_main || ""),
        contract_extras: ((values.contract_extras || []) as string[])
          .map((item) => String(item).slice(0, 120))
          .slice(0, 12),
        contract_audience: String(values.contract_audience || ""),
        poison_lines: ((values.poison_lines || []) as string[])
          .map((item) => String(item).slice(0, 400))
          .slice(0, 30),
        writing_mode: (values.writing_mode || "") as
          "" | "建筑师" | "混合" | "园丁",
        style_anchor: String(values.style_anchor || "").slice(0, 4000),
      });
      message.success("立书档案已保存");
      onSaved();
    } catch (error) {
      message.error(effectDetail(error));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Collapse
      className="blueprint-founding"
      defaultActiveKey={[]}
      items={[
        {
          key: "founding",
          label: (
            <Space wrap>
              <b>立书档案卡（书魂 · 主契约 · 毒点红线 · 文风基准）</b>
              {summaryBadges.length > 0 ? (
                summaryBadges.map((item) => <Tag key={item}>{item}</Tag>)
              ) : (
                <small style={{ color: "#3e5147" }}>
                  可选填写 · 与 CLI book.json 及 03-文风/文风基准.md 双向同步
                </small>
              )}
            </Space>
          ),
          children: (
            <Form
              form={form}
              layout="vertical"
              onFinish={handleSave}
              disabled={!canEdit}
              initialValues={{
                soul_arc: "",
                soul_status: "",
                writing_mode: "",
                contract_extras: [],
                poison_lines: [],
              }}
            >
              <div className="blueprint-founding-grid">
                <Form.Item name="soul_question" label="书魂核心追问">
                  <Input
                    aria-label="书魂核心追问"
                    maxLength={500}
                    placeholder="这本书到底在追问什么人的处境？"
                  />
                </Form.Item>
                <Form.Item name="soul_answer" label="书魂终极回答">
                  <Input
                    aria-label="书魂终极回答"
                    maxLength={500}
                    placeholder="主角将用怎样的行动给出回答？"
                  />
                </Form.Item>
                <Form.Item name="soul_injustice" label="核心不公 / 意难平">
                  <Input
                    aria-label="核心不公"
                    maxLength={500}
                    placeholder="推动全书破局的核心痛点或不公"
                  />
                </Form.Item>
                <Form.Item name="soul_ending" label="终局锚点画面">
                  <Input
                    aria-label="终局锚点画面"
                    maxLength={500}
                    placeholder="收束全书时的决定性场景"
                  />
                </Form.Item>
                <Form.Item name="soul_arc" label="主角弧光方向">
                  <Select
                    aria-label="主角弧光方向"
                    options={[
                      { value: "", label: "未指定" },
                      { value: "正向", label: "正向成长" },
                      { value: "负向", label: "负向沉沦" },
                      { value: "平弧", label: "平弧信念改变世界" },
                    ]}
                  />
                </Form.Item>
                <Form.Item name="soul_status" label="书魂定稿状态">
                  <Select
                    aria-label="书魂定稿状态"
                    options={[
                      { value: "", label: "未指定" },
                      { value: "暂定", label: "暂定（随前几章校准）" },
                      { value: "确定", label: "确定（冻结核心锚点）" },
                    ]}
                  />
                </Form.Item>
                <Form.Item name="writing_mode" label="推演与创作模式">
                  <Select
                    aria-label="推演与创作模式"
                    options={[
                      { value: "", label: "未指定" },
                      { value: "建筑师", label: "建筑师（重详纲严密结构）" },
                      { value: "混合", label: "混合（卷纲清晰+章内生长）" },
                      { value: "园丁", label: "园丁（人物驱动自然生长）" },
                    ]}
                  />
                </Form.Item>
                <Form.Item name="contract_main" label="主类型契约">
                  <Input
                    aria-label="主类型契约"
                    maxLength={200}
                    placeholder="例如：古典仙侠·凡人经营破局"
                  />
                </Form.Item>
                <Form.Item name="contract_audience" label="目标读者期待">
                  <Input
                    aria-label="目标读者期待"
                    maxLength={300}
                    placeholder="读者点进来最想持续获得的阅读体验"
                  />
                </Form.Item>
                <Form.Item name="contract_extras" label="副标签与爽点承诺">
                  <Select
                    aria-label="副标签与爽点承诺"
                    mode="tags"
                    placeholder="回车添加标签（最多 12 条）"
                  />
                </Form.Item>
                <Form.Item
                  name="poison_lines"
                  label="毒点红线清单（全书禁区）"
                  className="blueprint-founding-span"
                >
                  <Select
                    aria-label="毒点红线清单"
                    mode="tags"
                    placeholder="回车添加绝对禁止触碰的剧情毒点（最多 30 条）"
                  />
                </Form.Item>
                <Form.Item
                  name="style_anchor"
                  label="文风基准与叙事锚点"
                  className="blueprint-founding-span"
                >
                  <Input.TextArea
                    aria-label="文风基准与叙事锚点"
                    rows={4}
                    maxLength={4000}
                    placeholder="句式呼吸感、叙事距离、禁用腔调与代表性段落要求"
                  />
                </Form.Item>
              </div>
              <Button
                type="primary"
                htmlType="submit"
                disabled={!canEdit}
                loading={saving}
              >
                保存立书档案
              </Button>
            </Form>
          ),
        },
      ]}
    />
  );
}
