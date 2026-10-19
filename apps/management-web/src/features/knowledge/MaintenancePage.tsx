import { useQuery } from "@tanstack/react-query";
import {
  Alert,
  App,
  Button,
  Card,
  Form,
  Input,
  Select,
  Table,
  Typography,
} from "antd";
import { useState } from "react";
import { api, scoped, type Json } from "../../shared/api";
import { ErrorPanel, PageTitle } from "../../shared/components/Feedback";
import { ReferenceInput } from "../../shared/inputs/ReferenceInput";
import { useWorkspace } from "../../shared/WorkspaceContext";

export function MaintenancePage() {
  const { scope, refresh } = useWorkspace(),
    { message } = App.useApp(),
    [form] = Form.useForm();
  const [action, setAction] = useState("restore"),
    [entity, setEntity] = useState<string>(),
    [preview, setPreview] = useState<Json>(),
    [error, setError] = useState<unknown>(),
    [choices, setChoices] = useState<Json>({}),
    [busy, setBusy] = useState(false);
  const history = useQuery({
    queryKey: ["scope", scope.id, "history", entity],
    enabled: !!entity,
    queryFn: () => api<Json[]>(scoped(scope.id, `/entities/${entity}/history`)),
  });
  const scopes = useQuery({
    queryKey: ["scopes-maintenance"],
    queryFn: () => api<Json[]>("/scopes"),
  });
  const object = useQuery({
    queryKey: ["scope", scope.id, "entity", entity],
    enabled: !!entity,
    queryFn: () =>
      api<Json>(scoped(scope.id, `/entities/${entity}?include_deleted=true`)),
  });
  async function plan(values: Json) {
    setBusy(true);
    setError(undefined);
    try {
      const current = await api<Json>(scoped(scope.id, ""));
      setPreview(
        await api(scoped(scope.id, "/maintenance/plan"), "POST", {
          ...values,
          action,
          base_version: current.version,
          choices,
        }),
      );
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <PageTitle
        title="身份与历史维护"
        note="先检查影响与冲突，再采用新变更。原身份、历史与审计保留。"
      />
      <Card>
        <Form form={form} layout="vertical" onFinish={plan}>
          <Form.Item label="维护操作">
            <Select
              value={action}
              onChange={(value) => {
                setAction(value);
                setPreview(undefined);
                setChoices({});
                form.resetFields();
              }}
              options={[
                { value: "restore", label: "恢复历史修订" },
                { value: "merge", label: "合并重复身份" },
                { value: "split", label: "拆分身份信息" },
                { value: "branch_merge", label: "合并IF分支（三方比较）" },
              ]}
            />
          </Form.Item>
          {action !== "branch_merge" && (
            <Form.Item
              label="来源对象"
              name="entity_id"
              rules={[{ required: true }]}
            >
              <ReferenceInput
                includeRetired={action === "restore"}
                onChange={setEntity}
              />
            </Form.Item>
          )}
          {action === "restore" && (
            <Form.Item
              label="恢复来源修订"
              name="revision_id"
              rules={[{ required: true }]}
            >
              <Select
                options={history.data?.map((r) => ({
                  value: r.id,
                  label: `v${r.version} · ${new Date(r.created_at).toLocaleString()}`,
                }))}
              />
            </Form.Item>
          )}
          {action === "merge" && (
            <Form.Item
              label="保留的目标身份"
              name="target_id"
              rules={[{ required: true }]}
            >
              <ReferenceInput />
            </Form.Item>
          )}
          {action === "split" && (
            <>
              <Form.Item
                label="新身份名称"
                name="name"
                rules={[{ required: true }]}
              >
                <Input />
              </Form.Item>
              <Form.Item label="移动到新身份的属性" name="fields">
                <Select
                  mode="multiple"
                  options={Object.keys(object.data?.data || {}).map((key) => ({
                    value: key,
                    label: key,
                  }))}
                />
              </Form.Item>
              <Form.Item label="新身份文本（其余原文保留在源身份）" name="text">
                <Input.TextArea rows={5} />
              </Form.Item>
            </>
          )}
          {action === "branch_merge" && (
            <Form.Item
              label="待合并分支"
              name="branch_id"
              rules={[{ required: true }]}
            >
              <Select
                options={scopes.data
                  ?.filter((s) => s.base_id === scope.id)
                  .map((s) => ({ value: s.id, label: s.name }))}
              />
            </Form.Item>
          )}
          <Button type="primary" htmlType="submit" loading={busy}>
            生成影响预览
          </Button>
        </Form>
        <ErrorPanel error={error} />
      </Card>
      {preview && (
        <Card style={{ marginTop: 24 }} title="影响与冲突">
          {preview.conflicts?.length > 0 ? (
            <>
              <Alert
                type="warning"
                title="存在需要你选择的冲突"
                description="选择来源或目标后重新预览；不会自动覆盖。"
              />
              {preview.conflicts.map((c: Json) => {
                const key = c.field || c.entity_id;
                return (
                  <div key={key} style={{ marginTop: 20 }}>
                    <Typography.Text strong>{key}</Typography.Text>
                    <pre className="json-small">
                      {JSON.stringify(c, null, 2)}
                    </pre>
                    <Select
                      style={{ width: 240 }}
                      placeholder="选择采用哪一侧"
                      value={choices[key]}
                      onChange={(value) =>
                        setChoices({ ...choices, [key]: value })
                      }
                      options={[
                        { value: "source", label: "采用来源 / 分支" },
                        { value: "target", label: "保留目标 / 正史" },
                      ]}
                    />
                  </div>
                );
              })}
            </>
          ) : (
            <>
              <Alert
                type={preview.change?.validation?.valid ? "success" : "error"}
                title={
                  preview.change?.validation?.valid
                    ? "预检通过，等待采用"
                    : "预检未通过"
                }
                description={
                  !preview.change?.validation?.valid
                    ? JSON.stringify(preview.change?.validation?.errors)
                    : "采用前仍会重新核对当前范围版本和权限。"
                }
              />
              <Table<Json>
                rowKey={(_, i) => String(i)}
                pagination={{ pageSize: 10 }}
                dataSource={preview.change?.operations}
                columns={[
                  { title: "动作", dataIndex: "op" },
                  { title: "对象", dataIndex: "entity_id" },
                  {
                    title: "变化",
                    render: (_, r) => <code>{JSON.stringify(r)}</code>,
                  },
                ]}
              />
              <Button
                type="primary"
                disabled={
                  !preview.change?.validation?.valid ||
                  !scope.actions.includes("adopt")
                }
                onClick={async () => {
                  try {
                    await api(
                      scoped(scope.id, `/changes/${preview.change.id}/adopt`),
                      "POST",
                    );
                    setPreview(undefined);
                    refresh();
                    message.success("已采用新变更，原历史保留");
                  } catch (e) {
                    setError(e);
                  }
                }}
              >
                采用以上变更
              </Button>
            </>
          )}
        </Card>
      )}
    </>
  );
}
