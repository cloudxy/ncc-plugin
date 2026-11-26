import {
  App,
  Button,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Select,
  Space,
  Tag,
} from "antd";
import { useEffect, useState } from "react";
import { adopt, api, scoped, type Json, type Scope } from "../../../shared/api";
import type { StudioForeshadow } from "../../../shared/studioApi";
import { useWorkspace } from "../../../shared/WorkspaceContext";
import { effectDetail } from "../../creation/effectDetail";

const ALERTS = [
  ["overdue", "超期未回收"],
  ["due_soon", "临期预警"],
  ["active", "推进中"],
  ["planned", "待埋设"],
  ["resolved", "已兑现"],
  ["dropped", "已作废"],
] as const;

export function ForeshadowBoard({
  rows,
  canEdit,
  canSecret,
  onChanged,
  onOpen,
}: {
  rows: StudioForeshadow[];
  canEdit: boolean;
  canSecret: boolean;
  onChanged: () => void;
  onOpen: (id: string, title: string) => void;
}) {
  const { scope } = useWorkspace();
  const { message } = App.useApp();
  const [line, setLine] = useState("全部");
  const [alert, setAlert] = useState("全部");
  const [open, setOpen] = useState(false);
  const [editingRow, setEditingRow] = useState<StudioForeshadow | null>(null);

  const visible = rows.filter((row) => {
    if (line !== "全部" && row.line_type !== line && row.kind !== line)
      return false;
    if (alert !== "全部" && row.alert_state !== alert) return false;
    return true;
  });

  const renderedColumns =
    alert === "全部" ? ALERTS : ALERTS.filter(([value]) => value === alert);

  async function updateForeshadowStatus(
    row: StudioForeshadow,
    targetStatus: "已兑现" | "已作废",
  ) {
    if (targetStatus === "已兑现" && row.alert_state === "resolved") {
      message.warning("已兑现不能改回未完成");
      return;
    }
    try {
      const fresh = await api<Scope>(scoped(scope.id, ""));
      await adopt(
        fresh,
        [
          {
            op: "update",
            entity_id: row.id,
            expected: row.version,
            data: { status: targetStatus },
          },
        ],
        `标成${targetStatus}：` + row.name,
      );
      message.success(`伏笔已标为「${targetStatus}」`);
      onChanged();
    } catch (error) {
      message.error(effectDetail(error));
    }
  }

  return (
    <section className="blueprint-stack">
      <div className="blueprint-tools">
        {["全部", "明线", "暗线", "灰线"].map((item) => (
          <Button
            key={item}
            type={line === item ? "primary" : "default"}
            onClick={() => setLine(item)}
          >
            {item}
          </Button>
        ))}
        <Button
          type={alert === "全部" ? "primary" : "default"}
          onClick={() => setAlert("全部")}
        >
          全部状态
        </Button>
        {ALERTS.map(([value, label]) => (
          <Button
            key={value}
            type={alert === value ? "primary" : "default"}
            onClick={() => setAlert(value)}
          >
            {label}
          </Button>
        ))}
        <Button
          type="primary"
          disabled={!canEdit}
          onClick={() => {
            setEditingRow(null);
            setOpen(true);
          }}
        >
          记下一条伏笔
        </Button>
      </div>
      {rows.length === 0 ? <p>还没有伏笔</p> : null}
      {rows.length > 0 && visible.length === 0 ? <p>没有符合的伏笔</p> : null}
      <div className="blueprint-columns">
        {renderedColumns.map(([value, label]) => {
          const colRows = visible.filter((row) => row.alert_state === value);
          return (
            <section key={value} className="blueprint-column">
              <h3>
                {label} <Tag>{colRows.length}</Tag>
              </h3>
              {colRows.map((row) => {
                const chapterSpan = [
                  row.planted_chapter != null
                    ? `埋设第 ${row.planted_chapter} 章`
                    : null,
                  row.expected_chapter != null
                    ? `回收第 ${row.expected_chapter} 章`
                    : null,
                  row.strength != null ? `强度 ${row.strength}/5` : null,
                ]
                  .filter(Boolean)
                  .join(" · ");
                return (
                  <article key={row.id} className="blueprint-card">
                    <h3>{row.name}</h3>
                    <p style={{ margin: "0 0 6px" }}>
                      <Tag>{row.line_type || row.kind}</Tag>
                      {row.alert_state === "overdue" ? (
                        <Tag color="error">超期未回收</Tag>
                      ) : null}
                      {row.planted === false &&
                      (row.due_state === "due_soon" ||
                        row.due_state === "overdue") ? (
                        <Tag color="warning">待埋设（到期提醒）</Tag>
                      ) : null}
                    </p>
                    {chapterSpan ? (
                      <p
                        style={{
                          margin: "0 0 6px",
                          fontSize: 12,
                          color: "#3e5147",
                        }}
                      >
                        {chapterSpan}
                      </p>
                    ) : null}
                    {row.text ? (
                      <p
                        style={{
                          margin: "0 0 6px",
                          whiteSpace: "pre-wrap",
                          fontSize: 13,
                        }}
                      >
                        {row.text}
                      </p>
                    ) : null}
                    {row.secret_note ? (
                      <p className="blueprint-secret">
                        作者秘密：{row.secret_note}
                      </p>
                    ) : null}
                    <div className="blueprint-tools">
                      <Button
                        size="small"
                        disabled={!canEdit}
                        onClick={() => {
                          setEditingRow(row);
                          setOpen(true);
                        }}
                      >
                        编辑
                      </Button>
                      <Button
                        size="small"
                        disabled={!canEdit || row.alert_state === "resolved"}
                        onClick={() =>
                          void updateForeshadowStatus(row, "已兑现")
                        }
                      >
                        标成已兑现
                      </Button>
                      <Popconfirm
                        title={`将伏笔「${row.name}」标为已作废？`}
                        description="作废后不再计入活跃暗线与催收统计，后续仍可再次编辑恢复。"
                        okText="确认作废"
                        cancelText="取消"
                        disabled={!canEdit || row.alert_state === "dropped"}
                        onConfirm={() =>
                          void updateForeshadowStatus(row, "已作废")
                        }
                      >
                        <Button
                          size="small"
                          danger
                          disabled={!canEdit || row.alert_state === "dropped"}
                        >
                          标为已作废
                        </Button>
                      </Popconfirm>
                      <Button
                        size="small"
                        onClick={() => onOpen(row.id, row.name)}
                      >
                        带入创作台给 AI 参考
                      </Button>
                    </div>
                  </article>
                );
              })}
            </section>
          );
        })}
      </div>
      <ForeshadowForm
        open={open}
        editing={editingRow}
        canSecret={canSecret}
        onClose={() => {
          setOpen(false);
          setEditingRow(null);
        }}
        onSaved={() => {
          setOpen(false);
          setEditingRow(null);
          onChanged();
        }}
      />
    </section>
  );
}

function ForeshadowForm({
  open,
  editing,
  canSecret,
  onClose,
  onSaved,
}: {
  open: boolean;
  editing: StudioForeshadow | null;
  canSecret: boolean;
  onClose: () => void;
  onSaved: () => void;
}) {
  const { scope } = useWorkspace();
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) return;
    setError("");
    if (editing) {
      form.setFieldsValue({
        name: editing.name,
        line_type: editing.line_type || "明线",
        status: editing.status || (editing.planted ? "已埋设" : "待埋设"),
        planted_chapter: editing.planted_chapter ?? null,
        expected_chapter: editing.expected_chapter ?? null,
        strength: editing.strength ?? null,
        text: editing.text || "",
        secret_note: editing.secret_note || "",
      });
    } else {
      form.resetFields();
      form.setFieldsValue({
        line_type: "明线",
        status: "自动按埋设章判断",
      });
    }
  }, [open, editing, form]);

  return (
    <Modal
      title={editing ? "编辑伏笔与线索" : "记下一条伏笔"}
      open={open}
      onCancel={onClose}
      onOk={() => form.submit()}
      confirmLoading={saving}
      destroyOnHidden
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={async (values) => {
          setSaving(true);
          setError("");
          try {
            const fresh = await api<Scope>(scoped(scope.id, ""));
            const hasPlanted =
              values.planted_chapter !== undefined &&
              values.planted_chapter !== null;
            const hasExpected =
              values.expected_chapter !== undefined &&
              values.expected_chapter !== null;
            const hasStrength =
              values.strength !== undefined && values.strength !== null;
            const computedStatus =
              values.status && values.status !== "自动按埋设章判断"
                ? values.status
                : hasPlanted
                  ? "已埋设"
                  : "待埋设";

            if (editing) {
              const data: Json = {
                status: computedStatus,
                line_type: values.line_type,
              };
              const unset: string[] = [];
              if (hasPlanted) data.planted_chapter = values.planted_chapter;
              else unset.push("planted_chapter");
              if (hasExpected) data.expected_chapter = values.expected_chapter;
              else unset.push("expected_chapter");
              if (hasStrength) data.strength = values.strength;
              else unset.push("strength");
              if (canSecret) {
                if (values.secret_note?.trim()) {
                  data.secret_note = values.secret_note.trim();
                } else {
                  unset.push("secret_note");
                }
              }
              await adopt(
                fresh,
                [
                  {
                    op: "update",
                    entity_id: editing.id,
                    expected: editing.version,
                    name: values.name,
                    text: values.text || "",
                    data,
                    ...(unset.length ? { unset } : {}),
                  },
                ],
                "编辑伏笔：" + values.name,
              );
            } else {
              await adopt(
                fresh,
                [
                  {
                    op: "create",
                    entity_id: crypto.randomUUID(),
                    kind: "伏笔",
                    name: values.name,
                    text: values.text || "",
                    data: {
                      status: computedStatus,
                      line_type: values.line_type,
                      ...(hasPlanted
                        ? { planted_chapter: values.planted_chapter }
                        : {}),
                      ...(hasExpected
                        ? { expected_chapter: values.expected_chapter }
                        : {}),
                      ...(hasStrength ? { strength: values.strength } : {}),
                      ...(canSecret && values.secret_note?.trim()
                        ? { secret_note: values.secret_note.trim() }
                        : {}),
                    },
                  },
                ],
                "记下一条伏笔：" + values.name,
              );
            }
            form.resetFields();
            onSaved();
          } catch (reason) {
            setError(effectDetail(reason));
          } finally {
            setSaving(false);
          }
        }}
      >
        <Form.Item name="name" label="名称" rules={[{ required: true }]}>
          <Input />
        </Form.Item>
        <Form.Item
          name="line_type"
          label="线索"
          initialValue="明线"
          rules={[{ required: true }]}
        >
          <Select
            options={["明线", "暗线", "灰线"].map((value) => ({
              value,
              label: value,
            }))}
          />
        </Form.Item>
        {editing && (
          <Form.Item name="status" label="状态">
            <Select
              options={["待埋设", "已埋设", "推进中", "已兑现", "已作废"].map(
                (value) => ({
                  value,
                  label: value,
                }),
              )}
            />
          </Form.Item>
        )}
        <Space wrap size={16}>
          <Form.Item name="planted_chapter" label="埋设章">
            <InputNumber min={0} />
          </Form.Item>
          <Form.Item name="expected_chapter" label="期望回收章">
            <InputNumber min={0} />
          </Form.Item>
          <Form.Item name="strength" label="强度（1–5）">
            <InputNumber min={1} max={5} />
          </Form.Item>
        </Space>
        <Form.Item name="text" label="详细说明">
          <Input.TextArea autoSize={{ minRows: 3, maxRows: 6 }} />
        </Form.Item>
        {canSecret && (
          <Form.Item name="secret_note" label="作者秘密（读者视角自动隐藏）">
            <Input.TextArea autoSize={{ minRows: 2, maxRows: 4 }} />
          </Form.Item>
        )}
        {error ? <p>{error}</p> : null}
      </Form>
    </Modal>
  );
}
