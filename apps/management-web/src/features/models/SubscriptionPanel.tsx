import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, App, Button, Card, Input, Select, Tag, Typography } from "antd";
import { useState } from "react";
import { api } from "../../shared/api";
import { ErrorPanel } from "../../shared/components/Feedback";

type ChannelStatus = {
  ready: boolean;
  status: string;
  cli_installed: boolean;
  account: string | null;
  message: string;
  verified: boolean;
};

type Channel = {
  id: string;
  title: string;
  path_label: string;
  login_command: string;
  login_label: string;
  verify_label: string;
  note: string;
  models: { id: string; label: string }[];
  model: string;
  status: ChannelStatus;
};

type SubscriptionView = {
  channels: Channel[];
  ready_count: number;
};

const STATUS_LABEL: Record<string, { text: string; color: string }> = {
  authorized: { text: "已授权", color: "success" },
  expired: { text: "已过期", color: "error" },
  cli_missing: { text: "未安装", color: "warning" },
  unauthorized: { text: "未登录", color: "default" },
  api_key_only: { text: "仅 API Key", color: "warning" },
  check_failed: { text: "检查未完成", color: "warning" },
};

export function SubscriptionPanel() {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const [models, setModels] = useState<Record<string, string>>({});
  const [custom, setCustom] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState("");
  const subscriptions = useQuery({
    queryKey: ["subscription-auth"],
    queryFn: () => api<SubscriptionView>("/model-settings/subscriptions"),
  });
  const data = subscriptions.data;

  function remember(next: SubscriptionView) {
    queryClient.setQueryData(["subscription-auth"], next);
  }

  async function run(channel: Channel, action: "verify" | "login") {
    setBusy(channel.id + action);
    try {
      if (action === "login") {
        const result = await api<{ message: string }>(
          `/model-settings/subscriptions/${channel.id}/login`,
          "POST",
        );
        message.info(result.message);
        subscriptions.refetch();
      } else {
        const next = await api<SubscriptionView>(
          `/model-settings/subscriptions/${channel.id}/verify`,
          "POST",
        );
        remember(next);
        const row = next.channels.find((item) => item.id === channel.id);
        message.info(row?.status.message || "授权状态已更新");
      }
    } catch (error) {
      message.error((error as Error).message);
    } finally {
      setBusy("");
    }
  }

  async function saveModel(channel: Channel) {
    const known = channel.models.some((item) => item.id === channel.model);
    const choice = models[channel.id] ?? (known ? channel.model : "custom");
    const model =
      choice === "custom"
        ? (custom[channel.id] ?? (known ? "" : channel.model))
        : choice;
    if (!model.trim()) {
      message.error("填写公开的模型标识");
      return;
    }
    setBusy(channel.id + "model");
    try {
      const next = await api<SubscriptionView>(
        `/model-settings/subscriptions/${channel.id}/model`,
        "POST",
        { model },
      );
      remember(next);
      message.success("订阅模型已保存");
    } catch (error) {
      message.error((error as Error).message);
    } finally {
      setBusy("");
    }
  }

  async function copyCommand(command: string) {
    try {
      await navigator.clipboard.writeText(command);
      message.success("已复制终端命令");
    } catch {
      message.info(command);
    }
  }

  return (
    <div data-component="subscription-auth">
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        title={`本机订阅 ${data?.ready_count ?? 0}/3 已就绪`}
        description="这里只看 Grok、Codex、AGY 的本机登录态，并记下公开模型名。令牌留在本机 CLI 里，不会回传，也不会当作按量接口的密钥。写作任务仍走「模型与连接」。在线验证不发起付费生成。"
      />
      <ErrorPanel
        error={subscriptions.error}
        retry={() => subscriptions.refetch()}
      />
      {subscriptions.isPending && (
        <Typography.Paragraph type="secondary">
          正在检查本机订阅登录态。
        </Typography.Paragraph>
      )}
      <div className="subscription-grid">
        {(data?.channels || []).map((channel) => {
          const badge =
            STATUS_LABEL[channel.status.status] || STATUS_LABEL.unauthorized;
          const known = channel.models.some(
            (item) => item.id === channel.model,
          );
          const choice =
            models[channel.id] ?? (known ? channel.model : "custom");
          const customText = custom[channel.id] ?? (known ? "" : channel.model);
          return (
            <Card key={channel.id} title={channel.title}>
              <Typography.Paragraph
                type="secondary"
                className="subscription-path"
              >
                {channel.path_label}
              </Typography.Paragraph>
              <div className="subscription-status">
                <Tag color={badge.color}>{badge.text}</Tag>
                {channel.status.account && (
                  <span>账号 {channel.status.account}</span>
                )}
              </div>
              <Typography.Paragraph>
                {channel.status.message}
              </Typography.Paragraph>
              <div className="model-actions">
                <Button
                  type="primary"
                  disabled={!!busy}
                  loading={busy === channel.id + "login"}
                  onClick={() => run(channel, "login")}
                >
                  {channel.login_label}
                </Button>
                <Button
                  disabled={!!busy}
                  loading={busy === channel.id + "verify"}
                  onClick={() => run(channel, "verify")}
                >
                  {channel.verify_label}
                </Button>
                <Button onClick={() => subscriptions.refetch()}>
                  刷新授权状态
                </Button>
                <Button onClick={() => copyCommand(channel.login_command)}>
                  复制命令
                </Button>
              </div>
              <Typography.Paragraph>
                <code>{channel.login_command}</code>
              </Typography.Paragraph>
              <Typography.Paragraph type="secondary">
                默认订阅模型
              </Typography.Paragraph>
              <Select
                aria-label={`${channel.title}默认模型`}
                style={{ width: "100%", marginBottom: 12 }}
                value={choice}
                options={[
                  ...channel.models.map((item) => ({
                    value: item.id,
                    label: item.label,
                  })),
                  { value: "custom", label: "其他公开模型标识" },
                ]}
                onChange={(value) =>
                  setModels((current) => ({ ...current, [channel.id]: value }))
                }
              />
              {choice === "custom" && (
                <Input
                  aria-label={`${channel.title}模型标识`}
                  style={{ marginBottom: 12 }}
                  maxLength={128}
                  autoComplete="off"
                  placeholder="公开模型标识，不要填写密钥"
                  value={customText}
                  onChange={(event) =>
                    setCustom((current) => ({
                      ...current,
                      [channel.id]: event.target.value,
                    }))
                  }
                />
              )}
              <Button
                disabled={!!busy}
                loading={busy === channel.id + "model"}
                onClick={() => saveModel(channel)}
              >
                保存模型
              </Button>
              <Typography.Paragraph type="secondary" style={{ marginTop: 12 }}>
                {channel.note}
              </Typography.Paragraph>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
