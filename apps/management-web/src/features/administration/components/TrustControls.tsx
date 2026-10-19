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
  Select,
  Space,
  Table,
  Typography,
  Upload,
} from "antd";
import { useState } from "react";
import { useCreationPolicy } from "../../../shared/useCreationPolicy";
import { api, scoped, type Json } from "../../../shared/api";
import { ErrorPanel } from "../../../shared/components/Feedback";
import { ReferenceInput } from "../../../shared/inputs/ReferenceInput";
import { useWorkspace } from "../../../shared/WorkspaceContext";

export function TrustControls() {
  const policy = useCreationPolicy();
  const { scope } = useWorkspace(),
    { message } = App.useApp(),
    [form] = Form.useForm(),
    [record, setRecord] = useState<Json>(),
    [activate, setActivate] = useState(false),
    [error, setError] = useState<unknown>();
  const authorizationMode = Form.useWatch("mode", form);
  const delegations = useQuery({
    queryKey: ["scope", scope.id, "delegations"],
    queryFn: () => api<Json[]>(scoped(scope.id, "/delegations")),
  });
  const calibrations = useQuery({
    queryKey: ["scope", scope.id, "calibrations"],
    enabled: scope.actions.includes("secret"),
    queryFn: () => api<Json[]>(scoped(scope.id, "/calibrations")),
  });
  const tokens = useQuery({
    queryKey: ["scope", scope.id, "tokens"],
    queryFn: () => api<Json[]>(scoped(scope.id, "/tokens")),
  });
  async function revoke(kind: string, id: string) {
    try {
      await api(scoped(scope.id, `/${kind}/${id}`), "DELETE");
      delegations.refetch();
      calibrations.refetch();
      tokens.refetch();
      message.success("已撤销，后续执行会重新检查");
    } catch (e) {
      setError(e);
    }
  }
  return (
    <>
      <ErrorPanel error={error} />
      <Card title="自动定稿授权" style={{ marginTop: 24 }}>
        <Typography.Paragraph>
          可选择作者授权试运行，或使用完成校准的策略。试运行由作品所有者启用，仍须通过评分、硬伤、证据和版本检查；开篇与关键章由作者选定。
        </Typography.Paragraph>
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            schemes: ["P1"],
            hours: 24,
            count: 3,
            mode: "author_trial",
            note: "作者主动启用限额自动定稿试运行，知悉评分尚未经真实校准。",
          }}
          onFinish={async (value) => {
            try {
              await api(scoped(scope.id, "/delegations"), "POST", value);
              delegations.refetch();
              message.success(
                value.mode === "author_trial"
                  ? "试运行授权已启用；到创作台选择此授权"
                  : "授权已登记；未校准的策略仍会等待审核",
              );
            } catch (e) {
              setError(e);
            }
          }}
        >
          <Form.Item name="mode" label="自动定稿模式">
            <Select
              options={[
                { value: "author_trial", label: "作者授权试运行 · 校准未验证" },
                { value: "calibrated", label: "仅使用已校准策略" },
              ]}
            />
          </Form.Item>
          {authorizationMode === "author_trial" && (
            <Alert
              type="warning"
              title="试运行不代表评分已校准"
              description="仅在你授权的对象、期限和次数内自动采用达标稿；真实模型与人工偏好效果仍需验证。评分策略变更后需重新授权。"
            />
          )}
          <Form.Item
            name="note"
            label="授权依据"
            rules={
              authorizationMode === "author_trial"
                ? [{ required: true, whitespace: true }]
                : []
            }
          >
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item
            name="target_ids"
            label="允许修改的对象"
            rules={[{ required: true }]}
          >
            <ReferenceInput multiple />
          </Form.Item>
          <Form.Item
            name="schemes"
            label="允许方案"
            rules={[{ required: true }]}
          >
            <Checkbox.Group
              options={Object.keys(policy.data?.profiles || {})}
            />
          </Form.Item>
          <Space>
            <Form.Item name="hours" label="有效小时">
              <InputNumber min={1} max={168} />
            </Form.Item>
            <Form.Item name="count" label="最多采用次数">
              <InputNumber min={1} max={100} />
            </Form.Item>
          </Space>
          <Button htmlType="submit" disabled={!scope.actions.includes("adopt")}>
            登记本次授权
          </Button>
        </Form>
        <Table<Json>
          size="small"
          rowKey="id"
          pagination={{ pageSize: 5 }}
          dataSource={delegations.data}
          columns={[
            {
              title: "模式",
              render: (_, r) =>
                r.authorization?.mode === "author_trial"
                  ? "作者试运行 · 未校准"
                  : "校准策略",
            },
            {
              title: "方案",
              dataIndex: "schemes",
              render: (v) => v.join(" / "),
            },
            { title: "剩余", dataIndex: "remaining" },
            {
              title: "到期",
              dataIndex: "expires_at",
              render: (v) => new Date(v).toLocaleString(),
            },
            {
              title: "操作",
              render: (_, r) => (
                <Button
                  type="link"
                  disabled={r.revoked}
                  onClick={() => revoke("delegations", r.id)}
                >
                  {r.revoked ? "已撤销" : "撤销"}
                </Button>
              ),
            },
          ]}
        />
      </Card>
      {scope.actions.includes("secret") && (
        <Card title="评分校准与启用" style={{ marginTop: 24 }}>
          <Alert
            type="info"
            title="只接受作者标注的实际评估记录"
            description="按当前量表、方案和评价器提交开发/留出样本及偏好。系统计算样本数量、稳定性、误放和一致性；不足或未达标不会启用。"
          />
          <Space wrap style={{ marginTop: 16 }}>
            <Upload
              accept=".json"
              showUploadList={false}
              beforeUpload={async (file) => {
                try {
                  setRecord(JSON.parse(await file.text()));
                  setError(undefined);
                } catch (e) {
                  setError(e);
                }
                return false;
              }}
            >
              <Button>选择校准记录 JSON</Button>
            </Upload>
            <Checkbox
              checked={activate}
              onChange={(e) => setActivate(e.target.checked)}
            >
              指标达标后启用本策略
            </Checkbox>
            <Button
              disabled={!record}
              onClick={async () => {
                try {
                  const result = await api<Json>(
                    scoped(scope.id, "/calibrations"),
                    "POST",
                    { ...record, activate },
                  );
                  calibrations.refetch();
                  message.info(
                    result.active
                      ? "校准通过并已启用"
                      : "已保存报告，当前未启用",
                  );
                } catch (e) {
                  setError(e);
                }
              }}
            >
              计算并保存
            </Button>
          </Space>
          {record && (
            <Typography.Paragraph type="secondary">
              {record.scheme} · {record.evaluator} ·{" "}
              {record.samples?.length || 0}个样本；不会修改旧分数。
            </Typography.Paragraph>
          )}
          <Table<Json>
            size="small"
            rowKey="id"
            pagination={{ pageSize: 5 }}
            dataSource={calibrations.data}
            expandable={{
              expandedRowRender: (r) => (
                <pre className="json-small">
                  {JSON.stringify(r.report?.metrics, null, 2)}
                </pre>
              ),
            }}
            columns={[
              { title: "方案", dataIndex: "scheme" },
              { title: "评价器", dataIndex: "evaluator" },
              {
                title: "状态",
                render: (_, r) =>
                  r.active
                    ? "已启用"
                    : r.report?.passed
                      ? "已达标，未启用"
                      : "未达标 / 样本不足",
              },
              {
                title: "操作",
                render: (_, r) => (
                  <Button
                    type="link"
                    disabled={!r.active}
                    onClick={() => revoke("calibrations", r.id)}
                  >
                    停用
                  </Button>
                ),
              },
            ]}
          />
        </Card>
      )}
      <Card title="范围凭据管理" style={{ marginTop: 24 }}>
        <Table<Json>
          rowKey="id"
          size="small"
          dataSource={tokens.data}
          pagination={{ pageSize: 5 }}
          columns={[
            {
              title: "动作",
              dataIndex: "actions",
              render: (v) => v.join(" / "),
            },
            {
              title: "到期",
              dataIndex: "expires_at",
              render: (v) => new Date(v).toLocaleString(),
            },
            {
              title: "操作",
              render: (_, r) => (
                <Button type="link" onClick={() => revoke("tokens", r.id)}>
                  撤销
                </Button>
              ),
            },
          ]}
        />
      </Card>
    </>
  );
}
