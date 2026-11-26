import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  App,
  Button,
  Card,
  Checkbox,
  Form,
  Input,
  Popconfirm,
  Result,
  Segmented,
  Select,
  Space,
  Switch,
  Tabs,
  Tag,
  Typography,
} from "antd";
import { useState } from "react";
import { api, type Json } from "../../shared/api";
import { ErrorPanel, PageTitle } from "../../shared/components/Feedback";
import { queryKeys } from "../../shared/queryKeys";
import "./model-settings.css";
import { SubscriptionPanel, type SubscriptionView } from "./SubscriptionPanel";

type Purpose = "plan" | "write" | "revise" | "judge" | "judge_secondary";
type TransportMode = "http" | "cli_oauth";
type CliProvider = "" | "grok" | "codex" | "agy";

type Configuration = {
  id: string;
  name: string;
  transport?: TransportMode;
  cli_provider?: CliProvider;
  supplier: string;
  base_url: string;
  auth_ref: string;
  model_key: string;
  purposes: Purpose[];
  enabled: boolean;
  connection?: { status: string; credential: string; message: string };
};

type Draft = {
  name: string;
  transport: TransportMode;
  cli_provider: CliProvider;
  supplier: string;
  base_url: string;
  auth_ref: string;
  model_key: string;
  purposes: Purpose[];
  enabled: boolean;
};

type SettingsView = {
  configurations: Configuration[];
  defaults: Record<string, string>;
  purposes: { id: Purpose; label: string }[];
  presets: Array<Partial<Draft> & { id: string; name: string }>;
  source: string;
  effective: Record<
    string,
    {
      label: string;
      configuration_id: string;
      name: string;
      model_key: string;
      bound: boolean;
    }
  >;
  saved_id?: string;
};

type ProbeState = {
  configId: string;
  mode: "config" | "live";
  ok: boolean;
  message: string;
  statusCode?: number | null;
  modelFound?: boolean | null;
  elapsedMs?: number;
};

const EMPTY: Draft = {
  name: "",
  transport: "http",
  cli_provider: "",
  supplier: "兼容接口",
  base_url: "",
  auth_ref: "NCC_MODEL_KEY",
  model_key: "",
  purposes: ["write"],
  enabled: false,
};

const CLI_PROVIDER_OPTIONS: {
  value: Exclude<CliProvider, "">;
  label: string;
  supplier: string;
}[] = [
  { value: "grok", label: "Grok CLI OAuth 订阅", supplier: "Grok CLI OAuth" },
  {
    value: "codex",
    label: "Codex CLI OAuth 订阅",
    supplier: "Codex CLI OAuth",
  },
  { value: "agy", label: "AGY CLI OAuth 订阅", supplier: "AGY CLI OAuth" },
];

function draftOf(row: Configuration | null): Draft {
  if (!row) return EMPTY;
  return {
    name: row.name,
    transport: row.transport === "cli_oauth" ? "cli_oauth" : "http",
    cli_provider: (row.cli_provider || "") as CliProvider,
    supplier: row.supplier,
    base_url: row.base_url,
    auth_ref: row.auth_ref,
    model_key: row.model_key,
    purposes: row.purposes,
    enabled: row.enabled,
  };
}

export function ModelSettingsPage() {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const [form] = Form.useForm<Draft>();
  const [activeTab, setActiveTab] = useState("models");
  const [selected, setSelected] = useState<string | null>(null);
  const [preset, setPreset] = useState<string | undefined>();
  const [probe, setProbe] = useState<ProbeState | null>(null);
  const [checkingMode, setCheckingMode] = useState<"" | "config" | "live">("");
  const [binds, setBinds] = useState<Record<string, string>>({});

  const watchedTransport = Form.useWatch("transport", form) || "http";
  const watchedCliProvider = Form.useWatch("cli_provider", form) || "";

  const me = useQuery({
    queryKey: queryKeys.me(),
    queryFn: () => api<Json>("/me"),
  });
  const settings = useQuery({
    queryKey: queryKeys.modelSettings(),
    queryFn: () => api<SettingsView>("/model-settings"),
    enabled: !!me.data?.admin,
  });
  const subscriptions = useQuery({
    queryKey: queryKeys.subscriptionAuth(),
    queryFn: () => api<SubscriptionView>("/model-settings/subscriptions"),
    enabled: !!me.data?.admin,
  });

  if (me.isPending) return null;
  if (!me.data?.admin)
    return (
      <>
        <PageTitle
          title="AI 配置"
          note="模型登记由系统管理员维护。密钥只留在服务端环境变量里，页面不接收密钥。"
          actions={<Tag color="green">全局系统配置 · 所有作品共用</Tag>}
        />
        <Result
          status="403"
          title="当前账号不能修改模型登记"
          subTitle="请由系统管理员打开这一页。密钥不会发到浏览器。"
        />
      </>
    );

  const data = settings.data;
  const configurations = data?.configurations || [];
  const purposes = data?.purposes || [];
  const selectedRow = configurations.find((row) => row.id === selected) || null;
  const purposeLabel = (id: string) =>
    purposes.find((item) => item.id === id)?.label || id;

  const matchedChannel = subscriptions.data?.channels?.find(
    (ch) => ch.id === watchedCliProvider,
  );

  function remember(next: SettingsView) {
    queryClient.setQueryData(queryKeys.modelSettings(), next);
  }

  function showNew() {
    setSelected(null);
    setPreset(undefined);
    setProbe(null);
    form.setFieldsValue(EMPTY);
  }

  function showRow(row: Configuration) {
    setSelected(row.id);
    setPreset(undefined);
    setProbe(null);
    form.setFieldsValue(draftOf(row));
  }

  function handleBindFromSubscription(payload: {
    provider: "grok" | "codex" | "agy";
    title: string;
    modelKey: string;
  }) {
    setActiveTab("models");
    const existing = configurations.find(
      (row) =>
        row.transport === "cli_oauth" && row.cli_provider === payload.provider,
    );
    if (existing) {
      setSelected(existing.id);
      setPreset(undefined);
      setProbe(null);
      form.setFieldsValue({
        ...draftOf(existing),
        model_key: payload.modelKey || existing.model_key,
        enabled: true,
      });
      message.info(
        `已定位到「${existing.name}」，核对适用用途后点击「保存配置」即可生效`,
      );
      return;
    }
    const meta = CLI_PROVIDER_OPTIONS.find((o) => o.value === payload.provider);
    setSelected(null);
    setPreset(undefined);
    setProbe(null);
    form.setFieldsValue({
      name: `${payload.title}（CLI OAuth）`,
      transport: "cli_oauth",
      cli_provider: payload.provider,
      supplier: meta?.supplier || `${payload.title} OAuth`,
      base_url: "",
      auth_ref: "",
      model_key: payload.modelKey,
      purposes: ["plan", "write", "revise", "judge"],
      enabled: true,
    });
    message.info("已填入 CLI OAuth 订阅配置，点击「保存配置」即可启用");
  }

  async function saveDraft(values: Draft) {
    if (!values.purposes?.length) {
      message.error("至少选择一个用途");
      return;
    }
    const isCli = values.transport === "cli_oauth";
    if (isCli && !values.cli_provider) {
      message.error("请选择 CLI 订阅通道");
      return;
    }
    const payload = {
      ...(selected ? { id: selected } : {}),
      name: values.name,
      transport: isCli ? "cli_oauth" : "http",
      cli_provider: isCli ? values.cli_provider : "",
      supplier:
        values.supplier ||
        (isCli ? `${values.cli_provider.toUpperCase()} CLI OAuth` : "兼容接口"),
      base_url: isCli ? "" : values.base_url || "",
      auth_ref: isCli ? "" : values.auth_ref || "NCC_MODEL_KEY",
      model_key: values.model_key || "",
      purposes: values.purposes,
      enabled: Boolean(values.enabled),
    };
    try {
      const saved = await api<SettingsView>(
        "/model-settings/configurations",
        "POST",
        payload,
      );
      remember(saved);
      const savedId = saved.saved_id || selected;
      const row =
        saved.configurations.find((item) => item.id === savedId) || null;
      setSelected(savedId);
      setPreset(undefined);
      setProbe(null);
      form.setFieldsValue(draftOf(row));
      message.success("模型配置已保存");
    } catch (error) {
      message.error((error as Error).message);
    }
  }

  async function toggleEnabled(row: Configuration) {
    try {
      const saved = await api<SettingsView>(
        `/model-settings/configurations/${encodeURIComponent(row.id)}/enabled`,
        "POST",
        { enabled: !row.enabled },
      );
      remember(saved);
      const next = saved.configurations.find((item) => item.id === row.id);
      if (next) form.setFieldsValue(draftOf(next));
      message.success(row.enabled ? "已停用" : "已启用");
    } catch (error) {
      message.error((error as Error).message);
    }
  }

  async function remove(row: Configuration) {
    try {
      const saved = await api<SettingsView>(
        `/model-settings/configurations/${encodeURIComponent(row.id)}`,
        "DELETE",
      );
      remember(saved);
      if (selected === row.id) showNew();
      message.success("已删除");
    } catch (error) {
      message.error((error as Error).message);
    }
  }

  async function check(row: Configuration, live = false) {
    if (checkingMode) return;
    const mode = live ? "live" : "config";
    setCheckingMode(mode);
    const startedAt = performance.now();
    try {
      const suffix = live ? "?live=true" : "";
      const value = await api<Json>(
        `/model-settings/configurations/${encodeURIComponent(row.id)}/check${suffix}`,
        "POST",
      );
      const elapsedMs = Math.round(performance.now() - startedAt);
      const ok =
        typeof value?.ok === "boolean"
          ? value.ok
          : value?.connection?.status !== "not_configured" &&
            value?.connection?.status !== "invalid";
      const msg =
        (typeof value?.message === "string" && value.message) ||
        (typeof value?.connection?.message === "string" &&
          value.connection.message) ||
        (live ? "在线连通探测完成" : "静态配置检查完成");
      setProbe({
        configId: row.id,
        mode,
        ok,
        message: msg,
        statusCode:
          typeof value?.status_code === "number" ? value.status_code : null,
        modelFound:
          typeof value?.model_found === "boolean" ? value.model_found : null,
        elapsedMs,
      });
      if (live) {
        if (ok) message.success(msg);
        else message.warning(msg);
      } else {
        message.info(msg);
      }
    } catch (error) {
      message.error((error as Error).message);
    } finally {
      setCheckingMode("");
    }
  }

  async function saveDefault(purpose: Purpose) {
    const configurationId =
      binds[purpose] !== undefined
        ? binds[purpose]
        : data?.defaults?.[purpose] || "";
    try {
      const saved = await api<SettingsView>(
        "/model-settings/defaults",
        "POST",
        {
          purpose,
          configuration_id: configurationId,
        },
      );
      remember(saved);
      setBinds((current) => ({
        ...current,
        [purpose]: saved.defaults?.[purpose] || "",
      }));
      message.success("默认用途已保存，只影响新任务");
    } catch (error) {
      message.error((error as Error).message);
    }
  }

  const note =
    data?.source === "environment"
      ? "还没有启用的模型登记。新任务继续使用进程环境变量。"
      : "新任务按默认用途取已启用的配置（支持兼容 HTTP 接口与本机 CLI OAuth 订阅）。没有指定时，用第一个包含该用途的已启用配置；仍然没有，才用进程环境。";

  const currentProbe =
    selectedRow && probe?.configId === selectedRow.id ? probe : null;
  const liveProbeMeta =
    currentProbe?.mode === "live"
      ? [
          currentProbe.statusCode != null
            ? `HTTP ${currentProbe.statusCode}`
            : null,
          currentProbe.modelFound === true
            ? "模型列表已确认包含该模型"
            : currentProbe.modelFound === false
              ? "接口已连通，但远端模型列表未见该模型名"
              : null,
          currentProbe.elapsedMs != null
            ? `耗时 ${currentProbe.elapsedMs} ms`
            : null,
        ]
          .filter(Boolean)
          .join(" · ")
      : undefined;

  return (
    <div className="model-settings" data-component="model-settings">
      <PageTitle
        title="AI 配置"
        note="可混合登记兼容 HTTP 接口与本机 CLI OAuth 订阅通道，把细纲推演、正文起草、定向返修、独立评价与第二评价分别绑定。静态检查与在线探测均不产生付费生成。"
        actions={<Tag color="green">全局系统配置 · 所有作品共用</Tag>}
      />
      <ErrorPanel error={settings.error} retry={() => settings.refetch()} />
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: "models",
            label: "模型与连接",
            children: (
              <>
                <Alert
                  type="info"
                  showIcon
                  title={note}
                  style={{ marginBottom: 16 }}
                />
                <div className="model-grid">
                  <aside className="model-list">
                    <Button onClick={showNew}>新建配置</Button>
                    {!configurations.length && (
                      <p className="model-empty">
                        还没有模型配置。新建一项或从预设一键填入后，可以按用途分别绑定。
                      </p>
                    )}
                    {configurations.map((row) => (
                      <button
                        type="button"
                        key={row.id}
                        className={
                          row.id === selected
                            ? "model-list-item selected"
                            : "model-list-item"
                        }
                        aria-current={row.id === selected ? "true" : undefined}
                        onClick={() => showRow(row)}
                      >
                        <strong>{row.name}</strong>
                        <small>
                          {row.transport === "cli_oauth"
                            ? `CLI 订阅(${row.cli_provider})`
                            : row.supplier}{" "}
                          · {row.model_key || "未填模型"} ·{" "}
                          {row.enabled ? "启用" : "停用"}
                        </small>
                        <small>
                          {row.purposes.map(purposeLabel).join("、")}
                        </small>
                      </button>
                    ))}
                  </aside>
                  <Card>
                    <Typography.Paragraph type="secondary">
                      {selectedRow ? "编辑配置" : "新建配置"}
                      。支持兼容 HTTP 接口（API Key 环境变量）与本机 CLI OAuth
                      订阅两种通道；保存后可点击「在线探测连通」验证可用性。
                    </Typography.Paragraph>
                    <Select
                      aria-label="供应商预设"
                      allowClear
                      placeholder="选择供应商或 CLI OAuth 预设，一键填入表单"
                      style={{ width: "100%", marginBottom: 16 }}
                      value={preset}
                      options={(data?.presets || []).map((item) => ({
                        value: item.id,
                        label: item.name,
                      }))}
                      onChange={(id) => {
                        setPreset(id);
                        const item = data?.presets?.find(
                          (row) => row.id === id,
                        );
                        if (!item) return;
                        const isCli = item.transport === "cli_oauth";
                        form.setFieldsValue({
                          name: item.name,
                          transport: isCli ? "cli_oauth" : "http",
                          cli_provider: (item.cli_provider ||
                            "") as CliProvider,
                          supplier: item.supplier || "兼容接口",
                          base_url: item.base_url || "",
                          auth_ref: isCli
                            ? ""
                            : item.auth_ref || "NCC_MODEL_KEY",
                          model_key: item.model_key || "",
                          purposes: (item.purposes as Purpose[]) || ["write"],
                          enabled: false,
                        });
                      }}
                    />
                    <Form
                      form={form}
                      layout="vertical"
                      initialValues={EMPTY}
                      onFinish={saveDraft}
                    >
                      <Form.Item name="transport" label="接入通道类型">
                        <Segmented
                          aria-label="接入通道类型"
                          options={[
                            {
                              value: "http",
                              label: "兼容 HTTP 接口（API Key）",
                            },
                            {
                              value: "cli_oauth",
                              label: "本机 CLI OAuth 订阅",
                            },
                          ]}
                          onChange={(val) => {
                            if (val === "cli_oauth") {
                              const currentProvider =
                                form.getFieldValue("cli_provider") || "grok";
                              const ch = subscriptions.data?.channels?.find(
                                (c) => c.id === currentProvider,
                              );
                              const meta = CLI_PROVIDER_OPTIONS.find(
                                (o) => o.value === currentProvider,
                              );
                              form.setFieldsValue({
                                cli_provider: currentProvider,
                                supplier: meta?.supplier || "CLI OAuth",
                                model_key:
                                  form.getFieldValue("model_key") ||
                                  ch?.model ||
                                  "",
                              });
                            } else if (
                              !form.getFieldValue("auth_ref")?.trim()
                            ) {
                              form.setFieldValue("auth_ref", "NCC_MODEL_KEY");
                            }
                          }}
                        />
                      </Form.Item>

                      <Form.Item
                        name="name"
                        label="配置名称"
                        rules={[{ required: true, message: "填写配置名称" }]}
                      >
                        <Input
                          maxLength={80}
                          placeholder={
                            watchedTransport === "cli_oauth"
                              ? "例如 正文起草 · Codex 订阅"
                              : "例如 正文用 DeepSeek"
                          }
                        />
                      </Form.Item>

                      {watchedTransport === "cli_oauth" ? (
                        <>
                          <Form.Item
                            name="cli_provider"
                            label="CLI 订阅通道"
                            rules={[
                              {
                                required: true,
                                message: "请选择 CLI 订阅通道",
                              },
                            ]}
                          >
                            <Select
                              aria-label="CLI 订阅通道"
                              options={CLI_PROVIDER_OPTIONS.map((o) => ({
                                value: o.value,
                                label: o.label,
                              }))}
                              onChange={(
                                provider: Exclude<CliProvider, "">,
                              ) => {
                                const meta = CLI_PROVIDER_OPTIONS.find(
                                  (o) => o.value === provider,
                                );
                                const ch = subscriptions.data?.channels?.find(
                                  (c) => c.id === provider,
                                );
                                form.setFieldsValue({
                                  supplier: meta?.supplier || "CLI OAuth",
                                  ...(ch?.model ? { model_key: ch.model } : {}),
                                });
                              }}
                            />
                          </Form.Item>
                          {matchedChannel && (
                            <Alert
                              style={{ marginBottom: 16 }}
                              type={
                                matchedChannel.status.ready
                                  ? "success"
                                  : "warning"
                              }
                              showIcon
                              title={
                                matchedChannel.status.ready
                                  ? `${matchedChannel.title} 已授权就绪${matchedChannel.status.account ? `（账号：${matchedChannel.status.account}）` : ""}`
                                  : `${matchedChannel.title} 当前未就绪：${matchedChannel.status.message}`
                              }
                              action={
                                !matchedChannel.status.ready ? (
                                  <Button
                                    size="small"
                                    type="primary"
                                    onClick={() => setActiveTab("subscription")}
                                  >
                                    去完成网页 OAuth 授权
                                  </Button>
                                ) : undefined
                              }
                            />
                          )}
                          <Form.Item name="supplier" hidden>
                            <Input />
                          </Form.Item>
                        </>
                      ) : (
                        <>
                          <Form.Item name="supplier" label="供应商或接口">
                            <Input maxLength={64} placeholder="兼容接口" />
                          </Form.Item>
                          <Form.Item
                            name="base_url"
                            label="网关地址"
                            extra="兼容 Chat JSON 的基础地址，请求发往 /chat/completions。不要把密钥写进地址。"
                          >
                            <Input
                              maxLength={512}
                              placeholder="https://example.test/v1"
                              autoComplete="off"
                            />
                          </Form.Item>
                          <Form.Item
                            name="auth_ref"
                            label="凭证环境变量名"
                            extra="只填变量名，例如 NCC_MODEL_KEY 或 DEEPSEEK_API_KEY。页面不接收密钥值。"
                          >
                            <Input
                              maxLength={128}
                              placeholder="NCC_MODEL_KEY"
                              autoComplete="off"
                            />
                          </Form.Item>
                        </>
                      )}

                      <Form.Item
                        name="model_key"
                        label="模型标识"
                        rules={
                          watchedTransport === "cli_oauth"
                            ? [
                                {
                                  required: true,
                                  message: "请填写或选择公开模型标识",
                                },
                              ]
                            : undefined
                        }
                        extra={
                          watchedTransport === "cli_oauth" &&
                          matchedChannel?.models?.length ? (
                            <Space wrap size={4} style={{ marginTop: 6 }}>
                              <span>快捷填入：</span>
                              {matchedChannel.models.map((m) => (
                                <Button
                                  key={m.id}
                                  size="small"
                                  onClick={() =>
                                    form.setFieldValue("model_key", m.id)
                                  }
                                >
                                  {m.label}
                                </Button>
                              ))}
                            </Space>
                          ) : (
                            "供应商侧的公开模型名，不是密钥。"
                          )
                        }
                      >
                        <Input
                          maxLength={128}
                          placeholder={
                            watchedTransport === "cli_oauth"
                              ? "例如 gpt-5.4 或 grok-4"
                              : "例如 deepseek-chat"
                          }
                          autoComplete="off"
                        />
                      </Form.Item>
                      <Form.Item
                        name="purposes"
                        label="适用用途"
                        rules={[
                          {
                            required: true,
                            type: "array",
                            min: 1,
                            message: "至少选择一个用途",
                          },
                        ]}
                      >
                        <Checkbox.Group
                          options={purposes.map((item) => ({
                            label: item.label,
                            value: item.id,
                          }))}
                        />
                      </Form.Item>
                      <Form.Item
                        name="enabled"
                        label="启用此配置"
                        valuePropName="checked"
                        extra="启用后才能被选为某个用途的默认。停用或删除会清掉指向它的默认用途。已经开始的任务不受影响。"
                      >
                        <Switch />
                      </Form.Item>
                      <Button type="primary" htmlType="submit">
                        保存配置
                      </Button>
                    </Form>
                    {selectedRow && (
                      <>
                        <Alert
                          style={{ marginTop: 16 }}
                          type={
                            currentProbe
                              ? currentProbe.ok
                                ? "success"
                                : "warning"
                              : selectedRow.connection?.status ===
                                    "not_configured" ||
                                  selectedRow.connection?.status === "invalid"
                                ? "warning"
                                : "info"
                          }
                          showIcon
                          title={
                            currentProbe?.message ||
                            selectedRow.connection?.message ||
                            "可以检查这项配置或发起在线连通探测"
                          }
                          description={liveProbeMeta || undefined}
                        />
                        <div className="model-actions">
                          <Button
                            loading={checkingMode === "config"}
                            disabled={checkingMode !== ""}
                            onClick={() => check(selectedRow, false)}
                          >
                            检查配置
                          </Button>
                          <Button
                            type="primary"
                            ghost
                            loading={checkingMode === "live"}
                            disabled={checkingMode !== ""}
                            onClick={() => check(selectedRow, true)}
                          >
                            在线探测连通
                          </Button>
                          <Button onClick={() => toggleEnabled(selectedRow)}>
                            {selectedRow.enabled ? "停用此项" : "启用此项"}
                          </Button>
                          <Popconfirm
                            title="删除这个模型配置？"
                            description="已经开始的任务仍使用开始时记下的模型。指向它的默认用途会清空。"
                            okText="删除"
                            cancelText="取消"
                            onConfirm={() => remove(selectedRow)}
                          >
                            <Button danger>删除配置</Button>
                          </Popconfirm>
                        </div>
                      </>
                    )}
                  </Card>
                </div>
              </>
            ),
          },
          {
            key: "defaults",
            label: "默认用途",
            children: (
              <Card>
                <Typography.Paragraph type="secondary">
                  每个用途选择一项已启用、且声明了该用途的配置。选「不设置」后，新任务改用第一个符合的已启用配置；都没有时使用进程环境。第二评价两边都为空则不启用。已经开始的任务不改。
                </Typography.Paragraph>
                {purposes.map((item) => {
                  const options = configurations.filter(
                    (row) => row.enabled && row.purposes.includes(item.id),
                  );
                  const value =
                    binds[item.id] !== undefined
                      ? binds[item.id]
                      : data?.defaults?.[item.id] || "";
                  const effect = data?.effective?.[item.id];
                  const hint = !effect
                    ? ""
                    : effect.model_key
                      ? `${effect.bound ? "已绑定" : "未指定默认"}。新任务使用 ${effect.name}${effect.model_key ? ` · ${effect.model_key}` : ""}`
                      : item.id === "judge_secondary"
                        ? "未启用第二评价。"
                        : "这个用途还没有可用模型。新任务会停在未配置，不会生成演示内容。";
                  return (
                    <div className="model-default" key={item.id}>
                      <b>{item.label}</b>
                      <Select
                        aria-label={item.label}
                        value={value}
                        onChange={(next) =>
                          setBinds((current) => ({
                            ...current,
                            [item.id]: next,
                          }))
                        }
                        options={[
                          { value: "", label: "不设置" },
                          ...options.map((row) => ({
                            value: row.id,
                            label: `${row.name} · ${row.model_key}`,
                          })),
                        ]}
                      />
                      <Button
                        type="primary"
                        onClick={() => saveDefault(item.id)}
                      >
                        保存
                      </Button>
                      <p>{hint}</p>
                    </div>
                  );
                })}
              </Card>
            ),
          },
          {
            key: "subscription",
            label: "本机 CLI OAuth 订阅",
            children: (
              <SubscriptionPanel onBindToModels={handleBindFromSubscription} />
            ),
          },
        ]}
      />
    </div>
  );
}
