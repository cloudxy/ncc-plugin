import { useQueryClient } from "@tanstack/react-query";
import {
  App,
  Button,
  Card,
  Checkbox,
  Form,
  Input,
  Popconfirm,
  Select,
  Space,
  Table,
  Tag,
  Typography,
} from "antd";
import { useState } from "react";
import { api, scoped, type Json, type Scope } from "../../../shared/api";
import { NoData } from "../../../shared/components/Feedback";
import { queryKeys } from "../../../shared/queryKeys";
import { effectDetail } from "../../creation/effectDetail";
import { actionLabel } from "../adminConstants";

export function ScopedTokensCard({
  scope,
  tokensData,
  tokensLoading,
}: {
  scope: Scope;
  tokensData: Json[] | undefined;
  tokensLoading: boolean;
}) {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const [tokenForm] = Form.useForm();
  const [token, setToken] = useState("");

  async function revokeScopedToken(tokenId: string) {
    try {
      await api(scoped(scope.id, `/tokens/${tokenId}`), "DELETE");
      await queryClient.invalidateQueries({
        queryKey: queryKeys.tokens(scope.id),
      });
      message.success("范围凭据已吊销");
    } catch (e) {
      message.error(effectDetail(e));
    }
  }

  return (
    <Card title="本范围自动化凭据">
      <Typography.Paragraph type="secondary">
        用于本地 CLI 工作副本同步或只读 MCP
        连接。令牌仅在签发时显示一次，请保存到私有环境变量，不要写入仓库。
      </Typography.Paragraph>
      <Form
        name="tokenForm"
        form={tokenForm}
        layout="vertical"
        initialValues={{ actions: ["read"], hours: 24 }}
        onFinish={async (values) => {
          try {
            const actions = Array.from(
              new Set(["read", ...(values.actions || [])]),
            );
            const result = await api<Json>(
              scoped(scope.id, "/tokens"),
              "POST",
              {
                actions,
                hours: values.hours,
              },
            );
            setToken(result.token);
            await queryClient.invalidateQueries({
              queryKey: queryKeys.tokens(scope.id),
            });
            message.success("范围凭据已签发");
          } catch (e) {
            message.error(effectDetail(e));
          }
        }}
      >
        <Form.Item name="actions" label="包含权限（自动含只读浏览）">
          <Checkbox.Group
            options={scope.actions.map((act) => ({
              value: act,
              label: actionLabel(act),
            }))}
          />
        </Form.Item>
        <Form.Item name="hours" label="有效时长">
          <Select
            options={[
              { value: 1, label: "1 小时" },
              { value: 8, label: "8 小时" },
              { value: 24, label: "24 小时（1 天）" },
              { value: 72, label: "72 小时（3 天）" },
              { value: 168, label: "168 小时（7 天）" },
            ]}
          />
        </Form.Item>
        <Button htmlType="submit">生成范围凭据</Button>
      </Form>
      {token && (
        <Input.Password
          style={{ marginTop: 16 }}
          value={token}
          readOnly
          addonAfter={
            <Button
              type="link"
              size="small"
              onClick={() => {
                void navigator.clipboard.writeText(token);
                message.success("凭据已复制到剪贴板");
              }}
            >
              复制
            </Button>
          }
        />
      )}
      <div style={{ marginTop: 16 }}>
        <Typography.Text strong>当前有效凭据</Typography.Text>
        <Table<Json>
          style={{ marginTop: 8 }}
          rowKey="id"
          size="small"
          loading={tokensLoading}
          dataSource={tokensData}
          locale={{
            emptyText: <NoData text="当前没有已签发的活跃范围凭据" />,
          }}
          pagination={{ pageSize: 5 }}
          columns={[
            {
              title: "权限",
              dataIndex: "actions",
              render: (v: string[]) => (
                <Space wrap size={4}>
                  {(v || []).map((a) => (
                    <Tag key={a}>{actionLabel(a)}</Tag>
                  ))}
                </Space>
              ),
            },
            {
              title: "到期时间",
              dataIndex: "expires_at",
              render: (v) => new Date(v).toLocaleString(),
            },
            {
              title: "操作",
              width: 72,
              render: (_, r) => (
                <Popconfirm
                  title="立即吊销此范围凭据？"
                  okText="吊销"
                  cancelText="取消"
                  onConfirm={() => void revokeScopedToken(String(r.id))}
                >
                  <Button type="link" danger size="small">
                    吊销
                  </Button>
                </Popconfirm>
              ),
            },
          ]}
        />
      </div>
    </Card>
  );
}
