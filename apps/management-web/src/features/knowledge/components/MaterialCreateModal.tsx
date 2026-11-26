import {
  Alert,
  Button,
  Checkbox,
  Form,
  type FormInstance,
  Input,
  Modal,
  Select,
  Space,
  Typography,
} from "antd";
import type { Definition, Json } from "../../../shared/api";
import type { CodexGroup } from "../../../shared/studioApi";
import { resolveFieldLabel } from "../materialHelpers";
import { PropertyFields } from "./PropertyFields";

export function MaterialCreateModal({
  open,
  form,
  groups,
  defs,
  newKind,
  activeGroup,
  definition,
  canEdit,
  canSecret,
  direction,
  drafting,
  draftNote,
  draftError,
  onNewKindChange,
  onDirectionChange,
  onDraftWithAi,
  onCancel,
  onSubmit,
}: {
  open: boolean;
  form: FormInstance;
  groups: CodexGroup[];
  defs: Definition[] | undefined;
  newKind: string;
  activeGroup: CodexGroup | undefined;
  definition: Definition | undefined;
  canEdit: boolean;
  canSecret: boolean;
  direction: string;
  drafting: boolean;
  draftNote: string;
  draftError: string;
  onNewKindChange: (value: string) => void;
  onDirectionChange: (value: string) => void;
  onDraftWithAi: () => void;
  onCancel: () => void;
  onSubmit: (values: Json) => void;
}) {
  return (
    <Modal
      title="新建资料"
      width={720}
      open={open}
      onCancel={onCancel}
      onOk={() => form.submit()}
      okButtonProps={{ disabled: !canEdit }}
      destroyOnHidden
    >
      <Form form={form} layout="vertical" onFinish={onSubmit}>
        <Form.Item label="类型">
          <Select
            showSearch
            value={newKind}
            optionFilterProp="label"
            options={[
              ...groups.map((item) => ({
                label: item.label,
                options: item.kinds.map((token) => {
                  const found = defs?.find(
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
                options: (defs || [])
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
              onNewKindChange(value);
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
              .map((key) => resolveFieldLabel(defs, key))
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
            onChange={(event) => onDirectionChange(event.target.value)}
          />
        </Form.Item>
        <Space direction="vertical" style={{ width: "100%", marginBottom: 12 }}>
          <Button
            htmlType="button"
            disabled={!canEdit}
            loading={drafting}
            onClick={onDraftWithAi}
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
                <Button size="small" onClick={onDraftWithAi}>
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
          <Checkbox disabled={!canSecret}>作者秘密</Checkbox>
        </Form.Item>
      </Form>
    </Modal>
  );
}
