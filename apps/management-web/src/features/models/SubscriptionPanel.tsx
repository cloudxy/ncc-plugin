import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  App,
  Button,
  Card,
  Checkbox,
  Descriptions,
  Form,
  Input,
  Modal,
  Popconfirm,
  Segmented,
  Select,
  Space,
  Switch,
  Tag,
  Typography,
} from "antd";
import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../../shared/api";
import { ErrorPanel } from "../../shared/components/Feedback";
import { queryKeys } from "../../shared/queryKeys";
import { CapabilityDefaultsPanel } from "./components/CapabilityDefaultsPanel";
import type {
  CapabilityId,
  Channel,
  Configuration,
  LoginSession,
  ModelCatalogItem,
  Purpose,
  SettingsView,
  SubscriptionView,
} from "./modelsTypes";

export type { Channel, SubscriptionView };

type SubCategory = "text" | "image" | "video" | "all";

type LegacyCliDraft = {
  name: string;
  model_key: string;
  purposes: Purpose[];
  enabled: boolean;
};

const STATUS_LABEL: Record<string, { text: string; color: string }> = {
  authorized: { text: "已授权", color: "green" },
  expired: { text: "已过期", color: "red" },
  cli_missing: { text: "未安装", color: "orange" },
  unauthorized: { text: "未登录", color: "default" },
  file_detected: { text: "检测到文件 · 待验证", color: "blue" },
  api_key_only: { text: "仅 API Key", color: "orange" },
  check_failed: { text: "检查未完成", color: "orange" },
};

function modelsForCategory(
  channel: Channel,
  category: SubCategory,
  legacyCliRows: Configuration[],
): ModelCatalogItem[] {
  const all = channel.models || [];
  if (category === "text") {
    const base = channel.text_models?.length
      ? channel.text_models
      : all.filter((m) => m.category === "text");
    if (channel.text_model && !base.some((m) => m.id === channel.text_model)) {
      return [
        ...base,
        {
          id: channel.text_model,
          label: `${channel.text_model}（已保存历史偏好）`,
          category: "text",
          capabilities: [],
          capability_source: "unknown",
        },
      ];
    }
    return base;
  }
  if (category === "image") {
    const base = channel.image_models?.length
      ? channel.image_models
      : all.filter((m) => m.category === "image");
    if (
      channel.image_model &&
      !base.some((m) => m.id === channel.image_model)
    ) {
      return [
        ...base,
        {
          id: channel.image_model,
          label: `${channel.image_model}（已保存历史偏好）`,
          category: "image",
          capabilities: [],
          capability_source: "unknown",
        },
      ];
    }
    return base;
  }
  if (category === "video") {
    return channel.video_models?.length
      ? channel.video_models
      : all.filter((m) => m.category === "video");
  }
  const knownIds = new Set(all.map((m) => m.id));
  const extras: ModelCatalogItem[] = [];
  for (const row of legacyCliRows) {
    if (row.model_key && !knownIds.has(row.model_key)) {
      knownIds.add(row.model_key);
      extras.push({
        id: row.model_key,
        label: `${row.model_key}（已登记旧 CLI 路由：${row.name}）`,
        capabilities: [],
        capability_source: "unknown",
      });
    }
  }
  for (const savedId of [channel.text_model, channel.image_model]) {
    if (savedId && !knownIds.has(savedId)) {
      knownIds.add(savedId);
      extras.push({
        id: savedId,
        label: `${savedId}（已保存历史偏好 · 能力未知）`,
        capabilities: [],
        capability_source: "unknown",
      });
    }
  }
  return [...all, ...extras];
}

function defaultModelForCategory(
  channel: Channel,
  category: SubCategory,
  legacyCliRows: Configuration[],
): string {
  const list = modelsForCategory(channel, category, legacyCliRows);
  if (category === "text") {
    return channel.text_model || list[0]?.id || "";
  }
  if (category === "image") {
    return channel.image_model || list[0]?.id || "";
  }
  if (category === "video") {
    return list[0]?.id || "";
  }
  return channel.text_model || list[0]?.id || "";
}

type Props = {
  settingsData?: SettingsView;
  busyCapability?: string;
  onSettingsUpdated?: (next: SettingsView) => void;
  onBindCapability?: (payload: {
    capability: CapabilityId;
    source: "" | "subscription";
    provider?: string;
    model_key?: string;
  }) => Promise<boolean>;
};

export function SubscriptionPanel({
  settingsData,
  busyCapability = "",
  onSettingsUpdated,
  onBindCapability,
}: Props) {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const [legacyForm] = Form.useForm<LegacyCliDraft>();

  const [selectedProvider, setSelectedProvider] = useState<string>("grok");
  const [categoryByProvider, setCategoryByProvider] = useState<
    Record<string, SubCategory>
  >({});
  const [choiceByProvider, setChoiceByProvider] = useState<
    Record<string, string>
  >({});
  const [customByProvider, setCustomByProvider] = useState<
    Record<string, string>
  >({});
  const [sessions, setSessions] = useState<Record<string, LoginSession>>({});
  const [busyByProvider, setBusyByProvider] = useState<Record<string, string>>(
    {},
  );
  const [authModalProvider, setAuthModalProvider] = useState<string | null>(
    null,
  );
  const [localAuthModalProvider, setLocalAuthModalProvider] = useState<
    string | null
  >(null);
  const [editingLegacyRow, setEditingLegacyRow] =
    useState<Configuration | null>(null);
  const [savingLegacy, setSavingLegacy] = useState(false);

  const activeProviderRef = useRef(selectedProvider);
  activeProviderRef.current = selectedProvider;
  const refreshSeqByProviderRef = useRef<Record<string, number>>({});

  const subscriptions = useQuery({
    queryKey: queryKeys.subscriptionAuth(),
    queryFn: () => api<SubscriptionView>("/model-settings/subscriptions"),
  });
  const data = subscriptions.data;
  const channels = data?.channels || [];

  // Hydrate safe active_session summary (no device_code/auth_url in list response)
  useEffect(() => {
    if (!channels.length) return;
    setSessions((prev) => {
      let changed = false;
      const next = { ...prev };
      for (const ch of channels) {
        if (ch.active_session && !next[ch.id]) {
          next[ch.id] = {
            provider: ch.active_session.provider,
            session_id: ch.active_session.session_id,
            mode: ch.active_session.mode,
            state: "pending",
            expires_in: ch.active_session.expires_in,
          };
          changed = true;
        }
      }
      return changed ? next : prev;
    });
  }, [channels]);

  useEffect(() => {
    if (!channels.length) return;
    if (!channels.some((c) => c.id === selectedProvider)) {
      setSelectedProvider(channels[0].id);
    }
  }, [channels, selectedProvider]);

  function remember(next: SubscriptionView) {
    queryClient.setQueryData(queryKeys.subscriptionAuth(), next);
  }

  function updateSingleChannelCache(updated: Channel) {
    queryClient.setQueryData<SubscriptionView>(
      queryKeys.subscriptionAuth(),
      (prev) => {
        if (!prev) return prev;
        const nextChannels = prev.channels.map((ch) =>
          ch.id === updated.id ? updated : ch,
        );
        return {
          channels: nextChannels,
          ready_count: nextChannels.filter((ch) => ch.status.ready).length,
        };
      },
    );
  }

  function setProviderBusy(provider: string, action: string) {
    setBusyByProvider((prev) => ({ ...prev, [provider]: action }));
  }

  const pendingEntries = Object.values(sessions).filter(
    (s) => s.state === "pending" && s.session_id,
  );

  async function pollOnce(provider: string, sessionId: string) {
    try {
      const polled = await api<LoginSession>(
        `/model-settings/subscriptions/${encodeURIComponent(provider)}/login/${encodeURIComponent(sessionId)}`,
      );
      setSessions((prev) => ({ ...prev, [provider]: polled }));
      if (polled.channel) {
        updateSingleChannelCache(polled.channel);
      }
      if (polled.state === "authorized") {
        await Promise.all([
          subscriptions.refetch(),
          queryClient.invalidateQueries({
            queryKey: queryKeys.modelSettings(),
          }),
        ]);
        if (activeProviderRef.current === provider) {
          message.success("OAuth 授权已完成，订阅通道已就绪！");
        }
      }
    } catch {
      // Keep polling until session expires or user cancels
    }
  }

  useEffect(() => {
    if (pendingEntries.length === 0) return;
    let active = true;
    const timer = window.setInterval(async () => {
      for (const entry of pendingEntries) {
        if (!active || !entry.session_id) continue;
        await pollOnce(entry.provider, entry.session_id);
      }
    }, 2000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [pendingEntries.map((e) => `${e.provider}:${e.session_id}`).join("|")]);

  function selectPlatform(provider: string) {
    setSelectedProvider(provider);
    setAuthModalProvider(null);
    setLocalAuthModalProvider(null);
    setEditingLegacyRow(null);
  }

  async function openAndStartAuth(channel: Channel) {
    const provider = channel.id;
    setAuthModalProvider(provider);
    const existing = sessions[provider];
    if (existing && existing.state === "pending" && existing.session_id) {
      // Explicitly fetch live auth_url/device_code via poll endpoint when user returns to active session
      void pollOnce(provider, existing.session_id);
      return;
    }
    setProviderBusy(provider, "login");
    try {
      const started = await api<LoginSession>(
        `/model-settings/subscriptions/${encodeURIComponent(provider)}/login`,
        "POST",
      );
      setSessions((prev) => ({ ...prev, [provider]: started }));
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
        if (activeProviderRef.current === provider) {
          message.success(started.message || `${channel.title} 已授权就绪`);
        }
      } else if (activeProviderRef.current === provider) {
        message.info(
          started.message ||
            (started.mode === "manual"
              ? "请在本地终端执行授权命令后点击「刷新状态」。"
              : "已发起网页 OAuth 授权，请在浏览器完成确认。"),
        );
      }
    } catch (error) {
      if (activeProviderRef.current === provider) {
        message.error((error as Error).message);
      }
    } finally {
      setProviderBusy(provider, "");
    }
  }

  async function cancelWebLogin(provider: string, sessionId: string) {
    setProviderBusy(provider, "cancel");
    try {
      await api(
        `/model-settings/subscriptions/${encodeURIComponent(provider)}/login/${encodeURIComponent(sessionId)}`,
        "DELETE",
      );
      setSessions((prev) => {
        const next = { ...prev };
        delete next[provider];
        return next;
      });
      if (authModalProvider === provider) {
        setAuthModalProvider(null);
      }
      if (activeProviderRef.current === provider) {
        message.info("已取消本次网页授权等待");
      }
    } catch (error) {
      if (activeProviderRef.current === provider) {
        message.error((error as Error).message);
      }
    } finally {
      setProviderBusy(provider, "");
    }
  }

  async function refreshPlatform(channel: Channel) {
    const provider = channel.id;
    const seq = (refreshSeqByProviderRef.current[provider] || 0) + 1;
    refreshSeqByProviderRef.current[provider] = seq;
    setProviderBusy(provider, "refresh");
    try {
      const updated = await api<Channel>(
        `/model-settings/subscriptions/${encodeURIComponent(provider)}`,
      );
      if (refreshSeqByProviderRef.current[provider] !== seq) return;
      updateSingleChannelCache(updated);
      await queryClient.invalidateQueries({
        queryKey: queryKeys.modelSettings(),
      });
      if (activeProviderRef.current === provider) {
        message.info(`${channel.title} 状态已刷新`);
      }
    } catch (error) {
      if (
        refreshSeqByProviderRef.current[provider] === seq &&
        activeProviderRef.current === provider
      ) {
        message.error((error as Error).message);
      }
    } finally {
      if (refreshSeqByProviderRef.current[provider] === seq) {
        setProviderBusy(provider, "");
      }
    }
  }

  async function verifyPlatform(channel: Channel) {
    const provider = channel.id;
    const seq = (refreshSeqByProviderRef.current[provider] || 0) + 1;
    refreshSeqByProviderRef.current[provider] = seq;
    setProviderBusy(provider, "verify");
    try {
      const next = await api<SubscriptionView>(
        `/model-settings/subscriptions/${encodeURIComponent(provider)}/verify`,
        "POST",
      );
      if (refreshSeqByProviderRef.current[provider] !== seq) return;
      remember(next);
      const row = next.channels.find((item) => item.id === provider);
      if (activeProviderRef.current === provider) {
        message.info(row?.status.message || "本次验证状态已更新");
      }
    } catch (error) {
      if (
        refreshSeqByProviderRef.current[provider] === seq &&
        activeProviderRef.current === provider
      ) {
        message.error((error as Error).message);
      }
    } finally {
      if (refreshSeqByProviderRef.current[provider] === seq) {
        setProviderBusy(provider, "");
      }
    }
  }

  async function savePreference(
    channel: Channel,
    kind: "text" | "image",
    modelKey: string,
  ) {
    const provider = channel.id;
    const cleaned = modelKey.trim();
    if (!cleaned) {
      message.error(
        kind === "text" ? "填写公开的文本模型标识" : "填写公开的图片模型标识",
      );
      return;
    }
    setProviderBusy(provider, "pref");
    try {
      const payload =
        kind === "text" ? { text_model: cleaned } : { image_model: cleaned };
      const next = await api<SubscriptionView>(
        `/model-settings/subscriptions/${encodeURIComponent(provider)}/model`,
        "POST",
        payload,
      );
      remember(next);
      if (activeProviderRef.current === provider) {
        message.success(
          kind === "text"
            ? "已保存本平台文本偏好（不改动已设默认）"
            : "已保存本平台图片偏好（不改动已设默认）",
        );
      }
    } catch (error) {
      if (activeProviderRef.current === provider) {
        message.error((error as Error).message);
      }
    } finally {
      setProviderBusy(provider, "");
    }
  }

  async function saveLegacyCliRow(values: LegacyCliDraft) {
    if (!editingLegacyRow) return;
    setSavingLegacy(true);
    try {
      const saved = await api<SettingsView>(
        "/model-settings/configurations",
        "POST",
        {
          id: editingLegacyRow.id,
          name: values.name,
          supplier: editingLegacyRow.supplier,
          platform_id: editingLegacyRow.platform_id || "",
          transport: "cli_oauth",
          cli_provider: editingLegacyRow.cli_provider || "",
          base_url: "",
          auth_ref: "NCC_MODEL_KEY",
          model_key: values.model_key,
          capabilities: ["text"],
          purposes: values.purposes,
          enabled: Boolean(values.enabled),
        },
      );
      onSettingsUpdated?.(saved);
      setEditingLegacyRow(null);
      message.success("已更新旧 CLI 登记");
    } catch (error) {
      message.error((error as Error).message);
    } finally {
      setSavingLegacy(false);
    }
  }

  async function toggleLegacyCliEnabled(row: Configuration) {
    try {
      const saved = await api<SettingsView>(
        `/model-settings/configurations/${encodeURIComponent(row.id)}/enabled`,
        "POST",
        { enabled: !row.enabled },
      );
      onSettingsUpdated?.(saved);
      message.success(row.enabled ? "已停用旧 CLI 登记" : "已启用旧 CLI 登记");
    } catch (error) {
      message.error((error as Error).message);
    }
  }

  async function deleteLegacyCliRow(row: Configuration) {
    try {
      const saved = await api<SettingsView>(
        `/model-settings/configurations/${encodeURIComponent(row.id)}`,
        "DELETE",
      );
      onSettingsUpdated?.(saved);
      message.success("已删除旧 CLI 登记");
    } catch (error) {
      message.error((error as Error).message);
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

  const activeChannel =
    channels.find((c) => c.id === selectedProvider) || channels[0] || null;

  const legacyCliRows = useMemo(
    () =>
      activeChannel
        ? (settingsData?.configurations || []).filter(
            (row) =>
              row.transport === "cli_oauth" &&
              row.cli_provider === activeChannel.id,
          )
        : [],
    [settingsData?.configurations, activeChannel],
  );

  const activeCategory: SubCategory = activeChannel
    ? categoryByProvider[activeChannel.id] || "text"
    : "text";

  const activeList = useMemo(
    () =>
      activeChannel
        ? modelsForCategory(activeChannel, activeCategory, legacyCliRows)
        : [],
    [activeChannel, activeCategory, legacyCliRows],
  );

  const activeChoice = useMemo(() => {
    if (!activeChannel) return "";
    const explicit = choiceByProvider[activeChannel.id];
    if (explicit !== undefined) return explicit;
    return defaultModelForCategory(
      activeChannel,
      activeCategory,
      legacyCliRows,
    );
  }, [activeChannel, activeCategory, choiceByProvider, legacyCliRows]);

  const activeCustomInput = activeChannel
    ? customByProvider[activeChannel.id] || ""
    : "";

  const currentModelKey =
    activeChoice === "__custom__"
      ? activeCustomInput.trim()
      : activeChoice.trim();

  const matchedCatalogModel: ModelCatalogItem | undefined = activeChannel
    ? (activeChannel.models || []).find((m) => m.id === currentModelKey)
    : undefined;

  const supportedCapabilities: CapabilityId[] =
    matchedCatalogModel?.capabilities
      ? (matchedCatalogModel.capabilities as CapabilityId[])
      : [];

  const capabilitySource: "catalog" | "unknown" = matchedCatalogModel
    ? "catalog"
    : "unknown";

  const activeSession = activeChannel ? sessions[activeChannel.id] : undefined;
  const activeBusy = activeChannel
    ? busyByProvider[activeChannel.id] || ""
    : "";
  const activeBadge = activeChannel
    ? STATUS_LABEL[activeChannel.status.status] || STATUS_LABEL.unauthorized
    : STATUS_LABEL.unauthorized;

  function handleCategoryChange(channel: Channel, nextCategory: SubCategory) {
    setCategoryByProvider((prev) => ({ ...prev, [channel.id]: nextCategory }));
    const nextDefault = defaultModelForCategory(
      channel,
      nextCategory,
      legacyCliRows,
    );
    setChoiceByProvider((prev) => ({
      ...prev,
      [channel.id]: nextDefault,
    }));
  }

  const authModalChannel = authModalProvider
    ? channels.find((c) => c.id === authModalProvider) || null
    : null;
  const authModalSession = authModalChannel
    ? sessions[authModalChannel.id]
    : undefined;
  const localAuthChannel = localAuthModalProvider
    ? channels.find((c) => c.id === localAuthModalProvider) || null
    : null;

  return (
    <div data-component="subscription-auth">
      <ErrorPanel
        error={subscriptions.error}
        retry={() => subscriptions.refetch()}
      />
      {subscriptions.isPending && (
        <Typography.Paragraph type="secondary">
          正在检查本机订阅登录态…
        </Typography.Paragraph>
      )}

      {activeChannel && (
        <div className="platform-layout">
          <aside
            className="platform-rail"
            aria-label="订阅平台列表"
            data-rail="subscription-platforms"
          >
            <div className="platform-rail-title">
              订阅平台（{data?.ready_count ?? 0}/{channels.length} 就绪）
            </div>
            {channels.map((ch) => {
              const badge =
                STATUS_LABEL[ch.status.status] || STATUS_LABEL.unauthorized;
              const isSelected = ch.id === activeChannel.id;
              const hasPendingAuth =
                sessions[ch.id]?.state === "pending" &&
                Boolean(sessions[ch.id]?.session_id);
              const legacyCount = (settingsData?.configurations || []).filter(
                (r) => r.transport === "cli_oauth" && r.cli_provider === ch.id,
              ).length;
              return (
                <button
                  type="button"
                  key={ch.id}
                  className={
                    isSelected
                      ? "platform-rail-item selected"
                      : "platform-rail-item"
                  }
                  aria-current={isSelected ? "true" : undefined}
                  data-provider={ch.id}
                  onClick={() => selectPlatform(ch.id)}
                >
                  <div className="platform-rail-row">
                    <strong>{ch.title}</strong>
                  </div>
                  <div className="platform-rail-tags">
                    <Tag color={badge.color}>{badge.text}</Tag>
                    {hasPendingAuth && <Tag color="blue">授权等待中</Tag>}
                    {legacyCount > 0 && <Tag>旧登记 {legacyCount}</Tag>}
                  </div>
                  {ch.status.account && <small>账号 {ch.status.account}</small>}
                </button>
              );
            })}
          </aside>

          <div
            className="platform-detail"
            data-active-provider={activeChannel.id}
          >
            <Card size="small">
              {/* 1. 平台名称与状态 */}
              <div className="sub-detail-header">
                <h3>{activeChannel.title}</h3>
                <div className="subscription-status">
                  <Tag color={activeBadge.color}>{activeBadge.text}</Tag>
                  {activeChannel.verified ? (
                    <Tag color="green">本次验证通过</Tag>
                  ) : activeChannel.status.ready ? (
                    <Tag color="blue">本机已登录</Tag>
                  ) : null}
                  {activeChannel.status.account && (
                    <span className="sub-account-masked">
                      账号 {activeChannel.status.account}
                    </span>
                  )}
                </div>
                <Typography.Paragraph style={{ marginBottom: 8, fontSize: 13 }}>
                  {activeChannel.status.message}
                </Typography.Paragraph>
              </div>

              {activeSession &&
                activeSession.state === "pending" &&
                activeSession.session_id &&
                authModalProvider !== activeChannel.id && (
                  <Alert
                    type="info"
                    showIcon
                    style={{ marginBottom: 10 }}
                    title="当前平台存在进行中的授权会话"
                    description={
                      <div className="sub-pending-alert-body">
                        <div>
                          点击「返回活动授权会话」查看授权链接与设备码，或直接取消等待。
                        </div>
                        <Space wrap size={6} style={{ marginTop: 8 }}>
                          <Button
                            size="small"
                            type="primary"
                            onClick={() => void openAndStartAuth(activeChannel)}
                          >
                            返回活动授权会话
                          </Button>
                          <Button
                            size="small"
                            danger
                            loading={activeBusy === "cancel"}
                            onClick={() =>
                              void cancelWebLogin(
                                activeChannel.id,
                                activeSession.session_id!,
                              )
                            }
                          >
                            取消授权
                          </Button>
                        </Space>
                      </div>
                    }
                  />
                )}

              {/* 2. 授权 / 刷新状态 / 查看本机授权 */}
              <div className="model-actions" style={{ marginTop: 0 }}>
                <Button
                  type="primary"
                  loading={activeBusy === "login"}
                  disabled={!!activeBusy && activeBusy !== "login"}
                  onClick={() => void openAndStartAuth(activeChannel)}
                >
                  授权
                </Button>
                <Button
                  loading={activeBusy === "refresh"}
                  disabled={!!activeBusy && activeBusy !== "refresh"}
                  onClick={() => void refreshPlatform(activeChannel)}
                >
                  刷新状态
                </Button>
                <Button
                  onClick={() => setLocalAuthModalProvider(activeChannel.id)}
                >
                  查看本机授权
                </Button>
              </div>

              {/* 3. 模型选择（默认文本，支持图片/视频/全部筛选与搜索，保留自定义公开标识与偏好） */}
              <section
                className="subscription-model-section"
                aria-label="订阅模型选择"
              >
                <div className="subscription-model-header">
                  <span>选择模型</span>
                  <Segmented
                    size="small"
                    aria-label="订阅模型类别筛选"
                    value={activeCategory}
                    onChange={(val) =>
                      handleCategoryChange(activeChannel, val as SubCategory)
                    }
                    options={[
                      { value: "text", label: "文本" },
                      { value: "image", label: "图片" },
                      { value: "video", label: "视频" },
                      { value: "all", label: "全部 / 已登记" },
                    ]}
                  />
                </div>

                {activeList.length === 0 && activeChoice !== "__custom__" && (
                  <Alert
                    type="info"
                    showIcon
                    title={`当前 ${activeChannel.title} 订阅通道暂无已证实的「${activeCategory === "video" ? "视频" : activeCategory === "image" ? "图片" : "该类"}」能力`}
                    description="订阅可用性仅依据该 CLI 通道证据；如需供应商独立视频或图像 API 模型，请在「API 配置」对应平台登记。"
                  />
                )}

                <Select
                  showSearch
                  optionFilterProp="label"
                  aria-label="选择模型"
                  style={{ width: "100%" }}
                  placeholder="搜索或选择订阅模型"
                  value={activeChoice || undefined}
                  options={[
                    ...activeList.map((item) => ({
                      value: item.id,
                      label: item.label,
                    })),
                    { value: "__custom__", label: "其他自定义公开模型标识" },
                  ]}
                  onChange={(val) =>
                    setChoiceByProvider((prev) => ({
                      ...prev,
                      [activeChannel.id]: val,
                    }))
                  }
                />

                {activeChoice === "__custom__" && (
                  <Input
                    aria-label="自定义公开模型标识"
                    maxLength={128}
                    autoComplete="off"
                    placeholder="填写公开模型标识（勿填密钥）；未登记目录项能力标记为未知"
                    value={activeCustomInput}
                    onChange={(event) =>
                      setCustomByProvider((prev) => ({
                        ...prev,
                        [activeChannel.id]: event.target.value,
                      }))
                    }
                  />
                )}

                <div className="subscription-pref-bar">
                  <span className="subscription-model-hint">
                    已保存偏好：文本{" "}
                    <code>{activeChannel.text_model || "未设"}</code> · 图片{" "}
                    <code>{activeChannel.image_model || "未设"}</code>
                  </span>
                  <Space wrap size={6}>
                    {(activeCategory === "text" ||
                      matchedCatalogModel?.category === "text") && (
                      <Button
                        size="small"
                        loading={activeBusy === "pref"}
                        disabled={!currentModelKey || !!activeBusy}
                        onClick={() =>
                          void savePreference(
                            activeChannel,
                            "text",
                            currentModelKey,
                          )
                        }
                      >
                        保存为文本偏好
                      </Button>
                    )}
                    {(activeCategory === "image" ||
                      matchedCatalogModel?.category === "image") && (
                      <Button
                        size="small"
                        loading={activeBusy === "pref"}
                        disabled={!currentModelKey || !!activeBusy}
                        onClick={() =>
                          void savePreference(
                            activeChannel,
                            "image",
                            currentModelKey,
                          )
                        }
                      >
                        保存为图片偏好
                      </Button>
                    )}
                  </Space>
                </div>
              </section>

              {/* 4. 底部能力推导与默认操作 */}
              <CapabilityDefaultsPanel
                capabilities={settingsData?.capabilities || []}
                supportedCapabilities={supportedCapabilities}
                capabilitySource={
                  currentModelKey ? capabilitySource : "unknown"
                }
                entryKind={matchedCatalogModel?.entry_kind || "model"}
                modelKey={currentModelKey}
                canBind={
                  Boolean(currentModelKey) &&
                  capabilitySource === "catalog" &&
                  supportedCapabilities.length > 0 &&
                  Boolean(onBindCapability)
                }
                blockedReason={
                  !currentModelKey
                    ? "请先在上方选择一个目录模型或工具后再设为默认。"
                    : undefined
                }
                isCurrentDefault={(cap) => {
                  const slot = settingsData?.capability_defaults?.[cap];
                  return Boolean(
                    slot &&
                    slot.source === "subscription" &&
                    slot.provider === activeChannel.id &&
                    slot.model_key === currentModelKey,
                  );
                }}
                effectiveCapabilities={settingsData?.effective_capabilities}
                busyCapability={busyCapability}
                onSetDefault={async (cap) => {
                  if (!onBindCapability || !currentModelKey) return;
                  await onBindCapability({
                    capability: cap,
                    source: "subscription",
                    provider: activeChannel.id,
                    model_key: currentModelKey,
                  });
                }}
                onClearDefault={async (cap) => {
                  if (!onBindCapability) return;
                  await onBindCapability({ capability: cap, source: "" });
                }}
              />

              {/* 旧 CLI 订阅路由登记管理（保留对历史审评/自定义 CLI 登记的编辑、启停与删除入口） */}
              {legacyCliRows.length > 0 && (
                <section
                  className="legacy-cli-box"
                  data-section="legacy-cli-registrations"
                  aria-label="已登记旧 CLI 路由"
                >
                  <div className="legacy-cli-head">
                    <strong>本平台历史 CLI 路由登记</strong>
                    <span className="subscription-model-hint">
                      可用于「默认配置 → 小说进阶设置」单独指定审评/写作工序。
                    </span>
                  </div>
                  <div className="legacy-cli-list">
                    {legacyCliRows.map((row) => (
                      <div key={row.id} className="legacy-cli-row">
                        <div className="legacy-cli-info">
                          <strong>{row.name}</strong>
                          <code>{row.model_key}</code>
                          <Tag color={row.enabled ? "green" : "default"}>
                            {row.enabled ? "启用" : "停用"}
                          </Tag>
                          <span className="subscription-model-hint">
                            用途：
                            {row.purposes
                              .map(
                                (p) =>
                                  settingsData?.purposes?.find(
                                    (item) => item.id === p,
                                  )?.label || p,
                              )
                              .join("、")}
                          </span>
                        </div>
                        <Space size={6}>
                          <Button
                            size="small"
                            onClick={() => {
                              setEditingLegacyRow(row);
                              legacyForm.setFieldsValue({
                                name: row.name,
                                model_key: row.model_key,
                                purposes: row.purposes,
                                enabled: row.enabled,
                              });
                            }}
                          >
                            编辑
                          </Button>
                          <Button
                            size="small"
                            onClick={() => void toggleLegacyCliEnabled(row)}
                          >
                            {row.enabled ? "停用" : "启用"}
                          </Button>
                          <Popconfirm
                            title="删除此旧 CLI 登记？"
                            description="指向它的进阶用途默认会被清理，正在运行任务不受影响。"
                            okText="删除"
                            cancelText="取消"
                            onConfirm={() => void deleteLegacyCliRow(row)}
                          >
                            <Button size="small" danger>
                              删除
                            </Button>
                          </Popconfirm>
                        </Space>
                      </div>
                    ))}
                  </div>
                </section>
              )}

              <Typography.Paragraph
                type="secondary"
                style={{ marginTop: 12, marginBottom: 0, fontSize: 12 }}
              >
                {activeChannel.note}
              </Typography.Paragraph>
            </Card>
          </div>
        </div>
      )}

      {/* 独立「授权」弹窗 */}
      <Modal
        open={Boolean(authModalChannel)}
        title={authModalChannel ? `授权 · ${authModalChannel.title}` : "授权"}
        onCancel={() => setAuthModalProvider(null)}
        footer={
          authModalChannel ? (
            <Space wrap>
              {authModalSession?.state === "pending" &&
                authModalSession.session_id && (
                  <Button
                    danger
                    loading={busyByProvider[authModalChannel.id] === "cancel"}
                    onClick={() =>
                      void cancelWebLogin(
                        authModalChannel.id,
                        authModalSession.session_id!,
                      )
                    }
                  >
                    取消授权等待
                  </Button>
                )}
              <Button onClick={() => setAuthModalProvider(null)}>
                {authModalSession?.state === "pending"
                  ? "后台等待并关闭返回"
                  : "关闭返回"}
              </Button>
            </Space>
          ) : null
        }
      >
        {authModalChannel && (
          <Space orientation="vertical" size={12} style={{ width: "100%" }}>
            {busyByProvider[authModalChannel.id] === "login" && (
              <Alert
                type="info"
                showIcon
                title="正在发起受管授权会话…"
                description="不会弹出宿主机终端窗口，也不会回传明文令牌。"
              />
            )}
            {authModalSession && (
              <Alert
                type={
                  authModalSession.state === "authorized"
                    ? "success"
                    : authModalSession.state === "failed" ||
                        authModalSession.state === "expired"
                      ? "warning"
                      : "info"
                }
                showIcon
                title={
                  authModalSession.state === "pending"
                    ? "正在等待浏览器完成 OAuth 授权确认…"
                    : authModalSession.state === "authorized"
                      ? "网页 OAuth 授权成功"
                      : authModalSession.message || "授权引导"
                }
                description={
                  <Space
                    orientation="vertical"
                    size={8}
                    style={{ width: "100%" }}
                  >
                    {authModalSession.device_code && (
                      <div>
                        <span>设备授权码：</span>
                        <code style={{ fontWeight: 600, fontSize: 14 }}>
                          {authModalSession.device_code}
                        </code>{" "}
                        <Button
                          size="small"
                          type="link"
                          onClick={() =>
                            void copyText(
                              authModalSession.device_code!,
                              "设备授权码已复制",
                            )
                          }
                        >
                          复制设备码
                        </Button>
                      </div>
                    )}
                    {authModalSession.auth_url &&
                      authModalSession.auth_url.startsWith("https://") && (
                        <div>
                          <Button
                            size="small"
                            type="primary"
                            ghost
                            href={authModalSession.auth_url}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            打开官方授权页面
                          </Button>
                        </div>
                      )}
                    {authModalSession.mode === "manual" &&
                      authModalSession.command && (
                        <div>
                          <span>终端授权命令：</span>
                          <code>{authModalSession.command}</code>
                        </div>
                      )}
                  </Space>
                }
              />
            )}
            <div>
              <Typography.Paragraph style={{ marginBottom: 6 }}>
                终端备用命令：<code>{authModalChannel.login_command}</code>
              </Typography.Paragraph>
              <Space wrap>
                <Button
                  size="small"
                  onClick={() =>
                    void copyText(
                      authModalChannel.login_command,
                      "已复制终端登录命令，执行完成后点击「刷新状态」",
                    )
                  }
                >
                  复制终端命令
                </Button>
                <Button
                  size="small"
                  loading={busyByProvider[authModalChannel.id] === "verify"}
                  onClick={() => void verifyPlatform(authModalChannel)}
                >
                  {authModalChannel.verify_label}
                </Button>
              </Space>
            </div>
          </Space>
        )}
      </Modal>

      {/* 独立「查看本机授权」摘要弹窗 */}
      <Modal
        open={Boolean(localAuthChannel)}
        title={
          localAuthChannel
            ? `本机授权摘要 · ${localAuthChannel.title}`
            : "本机授权摘要"
        }
        onCancel={() => setLocalAuthModalProvider(null)}
        footer={
          localAuthChannel ? (
            <Space wrap>
              <Button
                loading={busyByProvider[localAuthChannel.id] === "refresh"}
                onClick={() => void refreshPlatform(localAuthChannel)}
              >
                刷新状态
              </Button>
              <Button
                type="primary"
                ghost
                loading={busyByProvider[localAuthChannel.id] === "verify"}
                onClick={() => void verifyPlatform(localAuthChannel)}
              >
                {localAuthChannel.verify_label}
              </Button>
              <Button onClick={() => setLocalAuthModalProvider(null)}>
                关闭返回
              </Button>
            </Space>
          ) : null
        }
      >
        {localAuthChannel && (
          <Space orientation="vertical" size={12} style={{ width: "100%" }}>
            <Alert
              type="info"
              showIcon
              title="凭据仅留在本机，不经浏览器或日志流转"
            />
            <Descriptions column={1} size="small" bordered>
              <Descriptions.Item label="订阅平台">
                {localAuthChannel.title}
              </Descriptions.Item>
              <Descriptions.Item label="本机路径">
                <code>{localAuthChannel.path_label}</code>
              </Descriptions.Item>
              <Descriptions.Item label="CLI 检测">
                {localAuthChannel.status.cli_installed ? "已安装" : "未检测到"}
              </Descriptions.Item>
              <Descriptions.Item label="授权状态">
                <Tag
                  color={
                    (
                      STATUS_LABEL[localAuthChannel.status.status] ||
                      STATUS_LABEL.unauthorized
                    ).color
                  }
                >
                  {
                    (
                      STATUS_LABEL[localAuthChannel.status.status] ||
                      STATUS_LABEL.unauthorized
                    ).text
                  }
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="脱敏账号">
                {localAuthChannel.status.account || "未返回可展示账号"}
              </Descriptions.Item>
              <Descriptions.Item label="状态说明">
                {localAuthChannel.status.message}
              </Descriptions.Item>
              <Descriptions.Item label="终端命令">
                <code>{localAuthChannel.login_command}</code>
              </Descriptions.Item>
            </Descriptions>
          </Space>
        )}
      </Modal>

      {/* 编辑旧 CLI 订阅路由登记弹窗 */}
      <Modal
        open={Boolean(editingLegacyRow)}
        title="编辑历史 CLI 路由登记"
        onCancel={() => setEditingLegacyRow(null)}
        footer={null}
      >
        <Form
          form={legacyForm}
          layout="vertical"
          onFinish={(values) => void saveLegacyCliRow(values)}
        >
          <Form.Item
            name="name"
            label="配置名称"
            rules={[{ required: true, message: "填写配置名称" }]}
          >
            <Input maxLength={80} />
          </Form.Item>
          <Form.Item
            name="model_key"
            label="模型标识"
            rules={[{ required: true, message: "填写公开模型标识" }]}
          >
            <Input maxLength={128} autoComplete="off" />
          </Form.Item>
          <Form.Item
            name="purposes"
            label="小说进阶用途"
            rules={[
              {
                required: true,
                type: "array",
                min: 1,
                message: "至少选择一项用途",
              },
            ]}
          >
            <Checkbox.Group
              options={(settingsData?.purposes || []).map((item) => ({
                label: item.label,
                value: item.id,
              }))}
            />
          </Form.Item>
          <Form.Item name="enabled" label="启用" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Space>
            <Button type="primary" htmlType="submit" loading={savingLegacy}>
              保存修改
            </Button>
            <Button onClick={() => setEditingLegacyRow(null)}>取消</Button>
          </Space>
        </Form>
      </Modal>
    </div>
  );
}
