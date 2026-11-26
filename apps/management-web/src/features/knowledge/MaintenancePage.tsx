import { useQuery } from "@tanstack/react-query";
import {
  Alert,
  App,
  Button,
  Card,
  Form,
  Input,
  Select,
  Space,
  Table,
  Tag,
  Typography,
} from "antd";
import { useState } from "react";
import { api, scoped, type Json } from "../../shared/api";
import {
  ErrorPanel,
  PageTitle,
  Permission,
} from "../../shared/components/Feedback";
import { ReferenceInput } from "../../shared/inputs/ReferenceInput";
import { queryKeys } from "../../shared/queryKeys";
import { useWorkspace } from "../../shared/WorkspaceContext";

const OP_LABELS: Record<string, string> = {
  create: "新建对象",
  update: "更新修订",
  retire: "停用归档",
  restore: "恢复历史版本",
  fact: "写入关系事实",
  retract: "撤回关系事实",
  name: "更新名称",
  adopt: "合并采用",
  definition: "更新类型定义",
};

function summarizeOperation(op: Json): string {
  const parts: string[] = [];
  if (typeof op.name === "string" && op.name) parts.push(`名称「${op.name}」`);
  if (typeof op.kind === "string" && op.kind) parts.push(`类型：${op.kind}`);
  if (op.reactivate) parts.push("重新激活已停用条目");
  if (typeof op.revision_id === "string" && op.revision_id) {
    parts.push(`来源修订：${op.revision_id.slice(0, 8)}…`);
  }
  if (op.data && typeof op.data === "object") {
    const keys = Object.keys(op.data);
    if (keys.length > 0) parts.push(`变更属性：${keys.join("、")}`);
  }
  if (Array.isArray(op.unset) && op.unset.length > 0) {
    parts.push(`清除属性：${op.unset.join("、")}`);
  }
  if (typeof op.text === "string") {
    parts.push(`正文长度：${op.text.length} 字符`);
  }
  if (op.fact && typeof op.fact === "object") {
    parts.push(`关系谓词：${op.fact.predicate || op.fact.category || "事实"}`);
  }
  return parts.join(" · ") || "按受控维护计划执行";
}

function formatConflictSide(val: unknown): string {
  if (val === undefined || val === null || val === "") return "（空）";
  if (typeof val === "string")
    return val.length > 160 ? `${val.slice(0, 160)}…` : val;
  if (typeof val === "number" || typeof val === "boolean") return String(val);
  return JSON.stringify(val);
}

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

  const canMaintain =
    scope.actions.includes("edit") || scope.actions.includes("adopt");

  const history = useQuery({
    queryKey: queryKeys.entityHistory(scope.id, entity),
    enabled: !!entity && canMaintain,
    queryFn: () => api<Json[]>(scoped(scope.id, `/entities/${entity}/history`)),
  });
  const scopes = useQuery({
    queryKey: queryKeys.scopesRoot(),
    enabled: canMaintain,
    queryFn: () => api<Json[]>("/scopes"),
  });
  const object = useQuery({
    queryKey: queryKeys.entity(scope.id, entity),
    enabled: !!entity && canMaintain,
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
    <Permission allowed={canMaintain}>
      <PageTitle
        title="身份与历史维护"
        note="先检查影响与冲突，再采用新变更。原身份、历史与审计完整保留。"
      />
      <Card>
        <Form form={form} layout="vertical" onFinish={plan}>
          <Form.Item label="维护操作">
            <Select
              aria-label="维护操作"
              value={action}
              onChange={(value) => {
                setAction(value);
                setPreview(undefined);
                setChoices({});
                form.resetFields();
              }}
              options={[
                { value: "restore", label: "恢复历史修订（含恢复已停用条目）" },
                { value: "merge", label: "合并重复身份" },
                { value: "split", label: "拆分身份信息" },
                { value: "branch_merge", label: "合并 IF 分支（三方比较）" },
              ]}
            />
          </Form.Item>
          {action !== "branch_merge" && (
            <Form.Item
              label="来源对象"
              name="entity_id"
              rules={[{ required: true, message: "请选择来源对象" }]}
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
              rules={[{ required: true, message: "请选择要恢复的历史版本" }]}
            >
              <Select
                placeholder="先选择来源对象，再挑选历史修订版本"
                options={history.data?.map((r) => ({
                  value: r.id,
                  label: `v${r.version} · ${new Date(r.created_at).toLocaleString()}${r.deleted ? "（停用快照）" : ""}`,
                }))}
              />
            </Form.Item>
          )}
          {action === "merge" && (
            <Form.Item
              label="保留的目标身份"
              name="target_id"
              rules={[{ required: true, message: "请选择保留的目标身份" }]}
            >
              <ReferenceInput />
            </Form.Item>
          )}
          {action === "split" && (
            <>
              <Form.Item
                label="新身份名称"
                name="name"
                rules={[
                  { required: true, message: "请填写拆分后的新身份名称" },
                ]}
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
              rules={[{ required: true, message: "请选择待合并的 IF 分支" }]}
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
        <Card style={{ marginTop: 24 }} title="影响与冲突预览">
          {preview.conflicts?.length > 0 ? (
            <>
              <Alert
                type="warning"
                showIcon
                title={`检测到 ${preview.conflicts.length} 项需要人工裁定的冲突`}
                description="请逐项选择采用来源/分支还是保留当前目标/正史，选定后点击上方「生成影响预览」重新校验。"
              />
              {preview.conflicts.map((c: Json) => {
                const key = String(c.field || c.entity_id);
                return (
                  <Card
                    key={key}
                    size="small"
                    style={{ marginTop: 12 }}
                    title={`冲突项：${c.name || c.field || key}`}
                  >
                    <Space
                      orientation="vertical"
                      size={6}
                      style={{ width: "100%" }}
                    >
                      <div>
                        <b>来源 / 分支侧：</b>
                        <span>
                          {formatConflictSide(c.source ?? c.branch ?? c.left)}
                        </span>
                      </div>
                      <div>
                        <b>目标 / 正史侧：</b>
                        <span>
                          {formatConflictSide(c.target ?? c.main ?? c.right)}
                        </span>
                      </div>
                      <Select
                        aria-label={`选择冲突项 ${key} 的保留侧`}
                        style={{ width: 240 }}
                        placeholder="选择采用哪一侧"
                        value={choices[key]}
                        onChange={(value) =>
                          setChoices({ ...choices, [key]: value })
                        }
                        options={[
                          { value: "source", label: "采用来源 / 分支侧" },
                          { value: "target", label: "保留目标 / 正史侧" },
                        ]}
                      />
                      <details>
                        <summary>查看冲突原始数据 JSON</summary>
                        <pre className="json-small">
                          {JSON.stringify(c, null, 2)}
                        </pre>
                      </details>
                    </Space>
                  </Card>
                );
              })}
            </>
          ) : (
            <>
              <Alert
                type={preview.change?.validation?.valid ? "success" : "error"}
                showIcon
                title={
                  preview.change?.validation?.valid
                    ? "预检通过，等待正式采用"
                    : "预检未通过"
                }
                description={
                  !preview.change?.validation?.valid
                    ? JSON.stringify(preview.change?.validation?.errors)
                    : "采用前仍会再次核对当前范围版本号与采用权限。"
                }
              />
              <Table<Json>
                rowKey={(_, i) => String(i)}
                pagination={{ pageSize: 10 }}
                dataSource={preview.change?.operations}
                columns={[
                  {
                    title: "维护动作",
                    dataIndex: "op",
                    width: 140,
                    render: (v: string) => <Tag>{OP_LABELS[v] || v}</Tag>,
                  },
                  {
                    title: "目标对象",
                    width: 200,
                    render: (_, r) => (
                      <Typography.Text>
                        {r.name ||
                          (typeof r.entity_id === "string"
                            ? `${r.entity_id.slice(0, 8)}…`
                            : "-")}
                      </Typography.Text>
                    ),
                  },
                  {
                    title: "变更摘要与详情",
                    render: (_, r) => (
                      <div>
                        <div>{summarizeOperation(r)}</div>
                        <details>
                          <summary>查看原始操作 JSON</summary>
                          <pre className="json-small">
                            {JSON.stringify(r, null, 2)}
                          </pre>
                        </details>
                      </div>
                    ),
                  },
                ]}
              />
              <Button
                type="primary"
                style={{ marginTop: 12 }}
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
                    message.success("已采用新变更，原历史版本完整保留");
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
    </Permission>
  );
}
