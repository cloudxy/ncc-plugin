import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  App,
  Button,
  Card,
  Input,
  Select,
  Space,
  Tag,
  Typography,
} from "antd";
import { useEffect, useState } from "react";
import { api } from "../../shared/api";
import { ErrorPanel } from "../../shared/components/Feedback";
import { queryKeys } from "../../shared/queryKeys";

export type ChannelStatus = {
  ready: boolean;
  status: string;
  cli_installed: boolean;
  account: string | null;
  message: string;
  verified: boolean;
};

export type Channel = {
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

export type SubscriptionView = {
  channels: Channel[];
  ready_count: number;
};

type LoginSession = {
  provider: string;
  started: boolean;
  mode: "device_auth" | "manual";
  session_id?: string | null;
  state: "pending" | "authorized" | "failed" | "expired" | "manual";
  auth_url?: string | null;
  device_code?: string | null;
  command?: string | null;
  expires_in?: number | null;
  message?: string;
  channel?: Channel;
};

const STATUS_LABEL: Record<string, { text: string; color: string }> = {
  authorized: { text: "已授权", color: "success" },
  expired: { text: "已过期", color: "error" },
  cli_missing: { text: "未安装", color: "warning" },
  unauthorized: { text: "未登录", color: "default" },
  api_key_only: { text: "仅 API Key", color: "warning" },
  check_failed: { text: "检查未完成", color: "warning" },
};

export function SubscriptionPanel({
  onBindToModels,
}: {
  onBindToModels?: (payload: {
    provider: "grok" | "codex" | "agy";
    title: string;
    modelKey: string;
  }) => void;
}) {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const [models, setModels] = useState<Record<string, string>>({});
  const [custom, setCustom] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState("");
  const [sessions, setSessions] = useState<Record<string, LoginSession>>({});

  const subscriptions = useQuery({
    queryKey: queryKeys.subscriptionAuth(),
    queryFn: () => api<SubscriptionView>("/model-settings/subscriptions"),
  });
  const data = subscriptions.data;

  function remember(next: SubscriptionView) {
    queryClient.setQueryData(queryKeys.subscriptionAuth(), next);
  }

  const pendingEntries = Object.values(sessions).filter(
    (s) => s.state === "pending" && s.session_id,
  );

  useEffect(() => {
    if (pendingEntries.length === 0) return;
    let active = true;
    const timer = window.setInterval(async () => {
      for (const entry of pendingEntries) {
        if (!entry.session_id) continue;
        try {
          const polled = await api<LoginSession>(
            `/model-settings/subscriptions/${encodeURIComponent(entry.provider)}/login/${encodeURIComponent(entry.session_id)}`,
          );
          if (!active) return;
          setSessions((prev) => ({ ...prev, [entry.provider]: polled }));
          if (
            polled.state === "authorized" ||
            polled.channel?.status?.ready === true
          ) {
            await Promise.all([
              subscriptions.refetch(),
              queryClient.invalidateQueries({
                queryKey: queryKeys.modelSettings(),
              }),
            ]);
            message.success("OAuth 授权已完成，订阅通道已就绪！");
          }
        } catch {
          // Keep polling until session expires or user cancels
        }
      }
    }, 2000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [pendingEntries.map((e) => `${e.provider}:${e.session_id}`).join("|")]);

  async function startWebLogin(channel: Channel) {
    setBusy(channel.id + "login");
    try {
      const started = await api<LoginSession>(
        `/model-settings/subscriptions/${encodeURIComponent(channel.id)}/login`,
        "POST",
      );
      setSessions((prev) => ({ ...prev, [channel.id]: started }));
      if (
        started.auth_url &&
        started.auth_url.startsWith("https://") &&
        started.state === "pending"
      ) {
        window.open(started.auth_url, "_blank", "noopener,noreferrer");
      }
      if (started.state === "authorized") {
        await Promise.all([
          subscriptions.refetch(),
          queryClient.invalidateQueries({
            queryKey: queryKeys.modelSettings(),
          }),
        ]);
        message.success(started.message || `${channel.title} 已授权就绪`);
      } else if (started.mode === "manual") {
        message.info(
          started.message ||
            "该 CLI 暂不支持无头设备码授权，请复制下方命令在终端执行后刷新。",
        );
      } else {
        message.info(
          started.message || "已发起网页 OAuth 授权，请在打开的窗口完成验证",
        );
      }
    } catch (error) {
      message.error((error as Error).message);
    } finally {
      setBusy("");
    }
  }

  async function cancelWebLogin(channelId: string, sessionId: string) {
    setBusy(channelId + "cancel");
    try {
      await api(
        `/model-settings/subscriptions/${encodeURIComponent(channelId)}/login/${encodeURIComponent(sessionId)}`,
        "DELETE",
      );
      setSessions((prev) => {
        const next = { ...prev };
        delete next[channelId];
        return next;
      });
      message.info("已取消本次网页授权等待");
    } catch (error) {
      message.error((error as Error).message);
    } finally {
      setBusy("");
    }
  }

  async function verify(channel: Channel) {
    setBusy(channel.id + "verify");
    try {
      const next = await api<SubscriptionView>(
        `/model-settings/subscriptions/${encodeURIComponent(channel.id)}/verify`,
        "POST",
      );
      remember(next);
      const row = next.channels.find((item) => item.id === channel.id);
      message.info(row?.status.message || "授权状态已更新");
    } catch (error) {
      message.error((error as Error).message);
    } finally {
      setBusy("");
    }
  }

  function resolveChannelModel(channel: Channel): string {
    const known = channel.models.some((item) => item.id === channel.model);
    const choice = models[channel.id] ?? (known ? channel.model : "custom");
    return choice === "custom"
      ? (custom[channel.id] ?? (known ? "" : channel.model)).trim()
      : choice.trim();
  }

  async function saveModel(channel: Channel) {
    const model = resolveChannelModel(channel);
    if (!model) {
      message.error("填写公开的模型标识");
      return;
    }
    setBusy(channel.id + "model");
    try {
      const next = await api<SubscriptionView>(
        `/model-settings/subscriptions/${encodeURIComponent(channel.id)}/model`,
        "POST",
        { model },
      );
      remember(next);
      message.success("订阅默认模型已保存");
    } catch (error) {
      message.error((error as Error).message);
    } finally {
      setBusy("");
    }
  }

  async function copyText(text: string, hint: string) {
    try {
      await navigator.clipboard.writeText(text);
      message.success(hint);
    } catch {
      message.info(text);
    }
  }

  return (
    <div data-component="subscription-auth">
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        title={`本机 CLI OAuth 订阅通道：${data?.ready_count ?? 0}/${data?.channels?.length ?? 3} 已就绪`}
        description="支持直接点击「网页发起 OAuth 授权」通过设备码（Device-Auth）在浏览器完成登录，或复制命令在本地终端执行；全程零宿主机弹窗、不回传明文令牌。就绪后可一键绑定到「模型与连接」直接承担章节规划、正文起草、返修与审评。"
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
          const session = sessions[channel.id];
          const chosenModel = resolveChannelModel(channel) || channel.model;

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
                  disabled={!channel.status.cli_installed || !!busy}
                  loading={busy === channel.id + "login"}
                  onClick={() => void startWebLogin(channel)}
                >
                  网页发起 OAuth 授权
                </Button>
                <Button
                  onClick={() =>
                    void copyText(
                      channel.login_command,
                      "已复制终端登录命令，执行完成后点击「刷新状态」",
                    )
                  }
                >
                  复制终端命令
                </Button>
                <Button
                  loading={subscriptions.isFetching && !busy}
                  onClick={() => subscriptions.refetch()}
                >
                  刷新状态
                </Button>
                <Button
                  disabled={!!busy}
                  loading={busy === channel.id + "verify"}
                  onClick={() => void verify(channel)}
                >
                  {channel.verify_label}
                </Button>
              </div>

              {session && (
                <Alert
                  style={{ marginTop: 12 }}
                  type={
                    session.state === "authorized"
                      ? "success"
                      : session.state === "failed" ||
                          session.state === "expired"
                        ? "warning"
                        : "info"
                  }
                  showIcon
                  title={
                    session.state === "pending"
                      ? "正在等待浏览器完成 OAuth 授权确认…"
                      : session.state === "authorized"
                        ? "网页 OAuth 授权成功"
                        : session.message || "授权引导"
                  }
                  description={
                    <Space
                      orientation="vertical"
                      size={6}
                      style={{ width: "100%" }}
                    >
                      {session.device_code && (
                        <div>
                          <span>设备授权码：</span>
                          <code style={{ fontWeight: 600, fontSize: 14 }}>
                            {session.device_code}
                          </code>{" "}
                          <Button
                            size="small"
                            type="link"
                            onClick={() =>
                              void copyText(
                                session.device_code!,
                                "设备授权码已复制",
                              )
                            }
                          >
                            复制设备码
                          </Button>
                        </div>
                      )}
                      {session.auth_url &&
                        session.auth_url.startsWith("https://") && (
                          <div>
                            <Button
                              size="small"
                              type="primary"
                              ghost
                              href={session.auth_url}
                              target="_blank"
                              rel="noopener noreferrer"
                            >
                              打开官方授权页面
                            </Button>
                          </div>
                        )}
                      {session.mode === "manual" && session.command && (
                        <div>
                          <span>终端登录命令：</span>
                          <code>{session.command}</code>
                        </div>
                      )}
                      {session.state === "pending" && session.session_id && (
                        <div>
                          <Button
                            size="small"
                            danger
                            loading={busy === channel.id + "cancel"}
                            onClick={() =>
                              void cancelWebLogin(
                                channel.id,
                                session.session_id!,
                              )
                            }
                          >
                            取消授权等待
                          </Button>
                        </div>
                      )}
                    </Space>
                  }
                />
              )}

              <Typography.Paragraph style={{ marginTop: 10, marginBottom: 8 }}>
                终端备用命令：<code>{channel.login_command}</code>
              </Typography.Paragraph>

              <Typography.Paragraph
                type="secondary"
                style={{ marginBottom: 6 }}
              >
                默认订阅模型
              </Typography.Paragraph>
              <Select
                aria-label={`${channel.title}默认模型`}
                style={{ width: "100%", marginBottom: 10 }}
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
                  style={{ marginBottom: 10 }}
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
              <Space wrap>
                <Button
                  disabled={!!busy}
                  loading={busy === channel.id + "model"}
                  onClick={() => void saveModel(channel)}
                >
                  保存订阅模型
                </Button>
                {onBindToModels &&
                  (channel.id === "grok" ||
                    channel.id === "codex" ||
                    channel.id === "agy") && (
                    <Button
                      type="primary"
                      ghost
                      onClick={() =>
                        onBindToModels({
                          provider: channel.id as "grok" | "codex" | "agy",
                          title: channel.title,
                          modelKey: chosenModel,
                        })
                      }
                    >
                      绑定为写作/审评模型
                    </Button>
                  )}
              </Space>
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
