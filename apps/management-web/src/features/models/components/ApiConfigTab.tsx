import {
  Alert,
  App,
  Button,
  Card,
  Checkbox,
  Form,
  Input,
  Popconfirm,
  Segmented,
  Select,
  Space,
  Switch,
  Tag,
  Typography,
} from "antd";
import { useEffect, useMemo, useRef, useState } from "react";
import { api, type Json } from "../../../shared/api";
import {
  CAPABILITY_ORDER,
  type CapabilityId,
  type Configuration,
  type ModelCatalogItem,
  type PlatformSpec,
  type ProbeState,
  type Purpose,
  type SettingsView,
} from "../modelsTypes";
import { CapabilityDefaultsPanel } from "./CapabilityDefaultsPanel";

type ApiDraft = {
  name: string;
  supplier: string;
  base_url: string;
  auth_ref: string;
  model_key: string;
  capabilities: CapabilityId[];
  purposes: Purpose[];
  enabled: boolean;
};

type Props = {
  data: SettingsView | undefined;
  busyCapability: string;
  onUpdated: (next: SettingsView) => void;
  onBindCapability: (payload: {
    capability: CapabilityId;
    source: "" | "api";
    configuration_id?: string;
    model_key?: string;
  }) => Promise<boolean>;
};

const ALL_PURPOSES: Purpose[] = ["plan", "write", "revise", "judge"];

function normalizePlatformKey(
  row: Configuration,
  knownIds: Set<string>,
): string {
  if (row.platform_id && knownIds.has(row.platform_id)) return row.platform_id;
  return "custom";
}

function emptyDraftForPlatform(platform: PlatformSpec): ApiDraft {
  return {
    name: "",
    supplier: platform.supplier || "兼容接口",
    base_url: platform.base_url || "",
    auth_ref: platform.auth_ref || "NCC_MODEL_KEY",
    model_key: "",
    capabilities: ["text"],
    purposes: [...ALL_PURPOSES],
    enabled: true,
  };
}

function draftFromConfig(row: Configuration): ApiDraft {
  const caps = (
    row.capabilities?.length ? row.capabilities : ["text"]
  ) as CapabilityId[];
  return {
    name: row.name,
    supplier: row.supplier,
    base_url: row.base_url,
    auth_ref: row.auth_ref || "NCC_MODEL_KEY",
    model_key: row.model_key,
    capabilities: caps,
    purposes: caps.includes("text") ? row.purposes : [],
    enabled: row.enabled,
  };
}

function sameStringSet(a: string[] = [], b: string[] = []): boolean {
  if (a.length !== b.length) return false;
  const setB = new Set(b);
  return a.every((item) => setB.has(item));
}

export function ApiConfigTab({
  data,
  busyCapability,
  onUpdated,
  onBindCapability,
}: Props) {
  const { message } = App.useApp();
  const [form] = Form.useForm<ApiDraft>();

  const platforms = useMemo<PlatformSpec[]>(
    () => data?.platforms || [],
    [data?.platforms],
  );
  const knownPlatformIds = useMemo(
    () => new Set(platforms.map((p) => p.id)),
    [platforms],
  );

  // Pure HTTP API configurations only (legacy cli_oauth configs are managed under SubscriptionPanel)
  const httpConfigs = useMemo(
    () =>
      (data?.configurations || []).filter(
        (row) => (row.transport || "http") === "http",
      ),
    [data?.configurations],
  );

  const [selectedPlatformId, setSelectedPlatformId] =
    useState<string>("openai");
  const [selectedConfigId, setSelectedConfigId] = useState<string | null>(null);
  const [modelFilter, setModelFilter] = useState<
    "all" | "text" | "image" | "video"
  >("all");
  const [sessionProbes, setSessionProbes] = useState<
    Record<string, ProbeState>
  >({});
  const [saving, setSaving] = useState(false);
  const [checkingMode, setCheckingMode] = useState<"" | "config" | "live">("");
  const probeSeqRef = useRef(0);

  const activePlatform: PlatformSpec = platforms.find(
    (p) => p.id === selectedPlatformId,
  ) ||
    platforms[0] || {
      id: "custom",
      name: "自定义兼容接口",
      supplier: "兼容接口",
      base_url: "",
      auth_ref: "NCC_MODEL_KEY",
      models: [],
    };

  const platformConfigs = useMemo(
    () =>
      httpConfigs.filter(
        (row) =>
          normalizePlatformKey(row, knownPlatformIds) === activePlatform.id,
      ),
    [httpConfigs, knownPlatformIds, activePlatform.id],
  );

  const selectedRow =
    platformConfigs.find((row) => row.id === selectedConfigId) || null;

  useEffect(() => {
    if (!platforms.length) return;
    if (!platforms.some((p) => p.id === selectedPlatformId)) {
      setSelectedPlatformId(platforms[0].id);
    }
  }, [platforms, selectedPlatformId]);

  useEffect(() => {
    if (selectedConfigId && selectedRow) {
      form.setFieldsValue(draftFromConfig(selectedRow));
      return;
    }
    if (!selectedConfigId && platformConfigs.length > 0) {
      const first = platformConfigs[0];
      setSelectedConfigId(first.id);
      form.setFieldsValue(draftFromConfig(first));
      return;
    }
    if (!selectedRow) {
      form.setFieldsValue(emptyDraftForPlatform(activePlatform));
    }
  }, [activePlatform.id]);

  const watchedModelKey = Form.useWatch("model_key", form) || "";
  const watchedCapabilities = (Form.useWatch("capabilities", form) ||
    []) as CapabilityId[];
  const watchedEnabled = Form.useWatch("enabled", form);
  const watchedName = Form.useWatch("name", form) || "";
  const watchedSupplier = Form.useWatch("supplier", form) || "";
  const watchedBaseUrl = Form.useWatch("base_url", form) || "";
  const watchedAuthRef = Form.useWatch("auth_ref", form) || "";
  const watchedPurposes = (Form.useWatch("purposes", form) || []) as Purpose[];

  const catalogModels = activePlatform.models || [];
  const filteredCatalog = useMemo(() => {
    if (modelFilter === "all") return catalogModels;
    return catalogModels.filter((m) => m.category === modelFilter);
  }, [catalogModels, modelFilter]);

  const matchedCatalogItem: ModelCatalogItem | undefined = catalogModels.find(
    (m) => m.id === watchedModelKey.trim(),
  );

  const hasUnsavedChanges = useMemo(() => {
    if (!selectedRow) return true;
    const saved = draftFromConfig(selectedRow);
    return (
      watchedName.trim() !== saved.name.trim() ||
      watchedSupplier.trim() !== saved.supplier.trim() ||
      watchedBaseUrl.trim().replace(/\/+$/, "") !==
        saved.base_url.trim().replace(/\/+$/, "") ||
      watchedAuthRef.trim() !== saved.auth_ref.trim() ||
      watchedModelKey.trim() !== saved.model_key.trim() ||
      Boolean(watchedEnabled) !== saved.enabled ||
      !sameStringSet(watchedCapabilities, saved.capabilities) ||
      !sameStringSet(watchedPurposes, saved.purposes)
    );
  }, [
    selectedRow,
    watchedName,
    watchedSupplier,
    watchedBaseUrl,
    watchedAuthRef,
    watchedModelKey,
    watchedEnabled,
    watchedCapabilities,
    watchedPurposes,
  ]);

  function selectPlatform(platform: PlatformSpec) {
    probeSeqRef.current += 1;
    setSelectedPlatformId(platform.id);
    setModelFilter("all");
    const nextRows = httpConfigs.filter(
      (row) => normalizePlatformKey(row, knownPlatformIds) === platform.id,
    );
    if (nextRows.length > 0) {
      setSelectedConfigId(nextRows[0].id);
      form.setFieldsValue(draftFromConfig(nextRows[0]));
    } else {
      setSelectedConfigId(null);
      form.setFieldsValue(emptyDraftForPlatform(platform));
    }
  }

  function startNewConfig() {
    probeSeqRef.current += 1;
    setSelectedConfigId(null);
    form.setFieldsValue(emptyDraftForPlatform(activePlatform));
  }

  function selectConfig(row: Configuration) {
    probeSeqRef.current += 1;
    setSelectedConfigId(row.id);
    form.setFieldsValue(draftFromConfig(row));
  }

  function handleSelectCatalogModel(modelId: string) {
    if (!modelId || modelId === "__custom__") {
      form.setFieldValue("model_key", "");
      return;
    }
    const found = catalogModels.find((item) => item.id === modelId);
    const nextCaps = (found?.capabilities || ["text"]) as CapabilityId[];
    const currentName = (form.getFieldValue("name") || "").trim();
    form.setFieldsValue({
      model_key: modelId,
      capabilities: nextCaps,
      purposes: nextCaps.includes("text") ? [...ALL_PURPOSES] : [],
      ...(!currentName && !selectedRow
        ? { name: `${activePlatform.name} · ${modelId}` }
        : {}),
    });
  }

  async function saveDraft(values: ApiDraft) {
    const caps = (values.capabilities || []) as CapabilityId[];
    if (!caps.length) {
      message.error("请至少选择一项模型能力");
      return;
    }
    const purposes = caps.includes("text")
      ? values.purposes?.length
        ? values.purposes
        : [...ALL_PURPOSES]
      : [];
    const payload = {
      ...(selectedRow ? { id: selectedRow.id } : {}),
      name: values.name,
      supplier: values.supplier || activePlatform.supplier || "兼容接口",
      platform_id: activePlatform.id,
      transport: "http",
      cli_provider: "",
      base_url: values.base_url || "",
      auth_ref: values.auth_ref || "NCC_MODEL_KEY",
      model_key: values.model_key || "",
      capabilities: caps,
      purposes,
      enabled: Boolean(values.enabled),
    };
    setSaving(true);
    try {
      const saved = await api<SettingsView>(
        "/model-settings/configurations",
        "POST",
        payload,
      );
      onUpdated(saved);
      const savedId = saved.saved_id || selectedRow?.id || null;
      const updatedRow =
        saved.configurations.find((item) => item.id === savedId) || null;
      setSelectedConfigId(savedId);
      if (savedId) {
        setSessionProbes((prev) => {
          const next = { ...prev };
          delete next[savedId];
          return next;
        });
      }
      if (updatedRow) {
        form.setFieldsValue(draftFromConfig(updatedRow));
      }
      message.success("API 模型配置已保存");
    } catch (error) {
      message.error((error as Error).message);
    } finally {
      setSaving(false);
    }
  }

  async function toggleEnabled(row: Configuration) {
    try {
      const saved = await api<SettingsView>(
        `/model-settings/configurations/${encodeURIComponent(row.id)}/enabled`,
        "POST",
        { enabled: !row.enabled },
      );
      onUpdated(saved);
      const next = saved.configurations.find((item) => item.id === row.id);
      if (next) form.setFieldsValue(draftFromConfig(next));
      message.success(row.enabled ? "已停用（关联默认已清理）" : "已启用");
    } catch (error) {
      message.error((error as Error).message);
    }
  }

  async function removeConfig(row: Configuration) {
    try {
      const saved = await api<SettingsView>(
        `/model-settings/configurations/${encodeURIComponent(row.id)}`,
        "DELETE",
      );
      onUpdated(saved);
      const remaining = saved.configurations.filter(
        (item) =>
          (item.transport || "http") === "http" &&
          normalizePlatformKey(item, knownPlatformIds) === activePlatform.id,
      );
      if (remaining.length > 0) {
        setSelectedConfigId(remaining[0].id);
        form.setFieldsValue(draftFromConfig(remaining[0]));
      } else {
        startNewConfig();
      }
      message.success("已删除配置（关联默认已清理）");
    } catch (error) {
      message.error((error as Error).message);
    }
  }

  async function checkConfig(row: Configuration, live = false) {
    if (checkingMode) return;
    const seq = ++probeSeqRef.current;
    const mode = live ? "live" : "config";
    setCheckingMode(mode);
    const startedAt = performance.now();
    try {
      const suffix = live ? "?live=true" : "";
      const value = await api<Json>(
        `/model-settings/configurations/${encodeURIComponent(row.id)}/check${suffix}`,
        "POST",
      );
      if (probeSeqRef.current !== seq) return;
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
      setSessionProbes((prev) => ({
        ...prev,
        [row.id]: {
          configId: row.id,
          mode,
          ok,
          message: msg,
          statusCode:
            typeof value?.status_code === "number" ? value.status_code : null,
          modelFound:
            typeof value?.model_found === "boolean" ? value.model_found : null,
          elapsedMs,
        },
      }));
      if (live) {
        if (ok) message.success(msg);
        else message.warning(msg);
      } else {
        message.info(msg);
      }
    } catch (error) {
      if (probeSeqRef.current === seq) {
        message.error((error as Error).message);
      }
    } finally {
      if (probeSeqRef.current === seq) {
        setCheckingMode("");
      }
    }
  }

  const currentProbe = selectedRow
    ? sessionProbes[selectedRow.id] || null
    : null;
  const liveProbeMeta =
    currentProbe?.mode === "live"
      ? [
          currentProbe.statusCode != null
            ? `HTTP ${currentProbe.statusCode}`
            : null,
          currentProbe.modelFound === true
            ? "远端模型列表包含该模型"
            : currentProbe.modelFound === false
              ? "接口连通，但远端列表未见该模型"
              : null,
          currentProbe.elapsedMs != null
            ? `耗时 ${currentProbe.elapsedMs} ms`
            : null,
        ]
          .filter(Boolean)
          .join(" · ")
      : undefined;

  const canBindApiDefault = Boolean(
    selectedRow && selectedRow.enabled && !hasUnsavedChanges,
  );
  const apiBlockedReason = !selectedRow
    ? "请先点击「保存配置」并启用后再设为默认。"
    : hasUnsavedChanges
      ? "表单有未保存改动，请先点击「保存配置」后再设为默认。"
      : !selectedRow.enabled
        ? "该配置当前已停用，启用后才可设为默认。"
        : undefined;

  const capabilityOptions = (data?.capabilities || []).map((item) => ({
    value: item.id,
    label: item.label,
  }));
  const purposes = data?.purposes || [];

  return (
    <div className="platform-layout" data-component="api-config-tab">
      <aside
        className="platform-rail"
        aria-label="API 平台列表"
        data-rail="api-platforms"
      >
        <div className="platform-rail-title">API 平台</div>
        {platforms.map((platform) => {
          const rows = httpConfigs.filter(
            (row) =>
              normalizePlatformKey(row, knownPlatformIds) === platform.id,
          );
          const enabledCount = rows.filter((r) => r.enabled).length;
          const active = platform.id === activePlatform.id;
          return (
            <button
              type="button"
              key={platform.id}
              className={
                active ? "platform-rail-item selected" : "platform-rail-item"
              }
              aria-current={active ? "true" : undefined}
              onClick={() => selectPlatform(platform)}
            >
              <strong>{platform.name}</strong>
              <small>
                已登记 {rows.length} 项
                {enabledCount > 0 ? ` · 启用 ${enabledCount}` : ""}
              </small>
            </button>
          );
        })}
      </aside>

      <div className="platform-detail">
        <Card size="small">
          <div className="platform-detail-header">
            <div>
              <h3>{activePlatform.name}</h3>
              <Typography.Paragraph
                type="secondary"
                style={{ marginBottom: 0, fontSize: 12 }}
              >
                {activePlatform.base_url
                  ? `网关 ${activePlatform.base_url} · 环境变量 ${activePlatform.auth_ref}`
                  : "兼容 HTTP 网关，密钥仅通过服务端环境变量引用。"}
              </Typography.Paragraph>
            </div>
            <Button size="small" onClick={startNewConfig}>
              新建此平台配置
            </Button>
          </div>

          <div className="platform-config-strip" aria-label="本平台已登记模型">
            {platformConfigs.length === 0 ? (
              <p className="model-empty">
                当前平台尚未登记配置。请在下方选择目录模型或填写公开模型标识并保存。
              </p>
            ) : (
              platformConfigs.map((row) => {
                const probeRes = sessionProbes[row.id];
                const selected = row.id === selectedRow?.id;
                return (
                  <button
                    type="button"
                    key={row.id}
                    className={
                      selected
                        ? "platform-config-chip selected"
                        : "platform-config-chip"
                    }
                    aria-current={selected ? "true" : undefined}
                    onClick={() => selectConfig(row)}
                  >
                    <div className="platform-config-chip-head">
                      <strong>{row.name}</strong>
                      <Tag color={row.enabled ? "green" : "default"}>
                        {row.enabled ? "启用" : "停用"}
                      </Tag>
                    </div>
                    <small>
                      <code>{row.model_key || "未填"}</code>
                    </small>
                    <div className="platform-config-chip-tags">
                      <Tag
                        color={
                          probeRes?.mode === "live"
                            ? probeRes.ok
                              ? "green"
                              : "red"
                            : "blue"
                        }
                      >
                        {probeRes?.mode === "live"
                          ? probeRes.ok
                            ? "本次探测通过"
                            : "本次探测未通过"
                          : "已保存 · 未在线探测"}
                      </Tag>
                      {row.deprecated_notice && (
                        <Tag color="orange">历史已停用标识</Tag>
                      )}
                      {(row.capabilities || ["text"]).map((cap) => (
                        <Tag key={cap}>
                          {data?.capabilities?.find((c) => c.id === cap)
                            ?.label || cap}
                        </Tag>
                      ))}
                    </div>
                  </button>
                );
              })
            )}
          </div>

          {selectedRow?.deprecated_notice && (
            <Alert
              type="warning"
              showIcon
              style={{ marginBottom: 12 }}
              title={selectedRow.deprecated_notice}
            />
          )}

          <Form
            form={form}
            layout="vertical"
            size="middle"
            initialValues={emptyDraftForPlatform(activePlatform)}
            onFinish={(values) => void saveDraft(values)}
          >
            <div className="api-form-two-col">
              <Form.Item
                name="name"
                label="配置名称"
                rules={[{ required: true, message: "填写配置名称" }]}
              >
                <Input
                  maxLength={80}
                  placeholder={`例如 ${activePlatform.name} · 主力模型`}
                />
              </Form.Item>
              <Form.Item name="supplier" label="供应商名称">
                <Input maxLength={64} placeholder="兼容接口" />
              </Form.Item>
            </div>

            <div className="api-form-two-col">
              <Form.Item
                name="base_url"
                label="网关地址"
                extra="仅保留到主机和路径，勿填密钥。"
              >
                <Input
                  maxLength={512}
                  placeholder="https://api.openai.com/v1"
                  autoComplete="off"
                />
              </Form.Item>
              <Form.Item
                name="auth_ref"
                label="凭证环境变量名"
                extra="只填变量名（如 OPENAI_API_KEY），绝不传明文密钥。"
              >
                <Input
                  maxLength={128}
                  placeholder="NCC_MODEL_KEY"
                  autoComplete="off"
                />
              </Form.Item>
            </div>

            {catalogModels.length > 0 && (
              <div className="api-catalog-picker">
                <div className="api-catalog-picker-head">
                  <span className="api-catalog-picker-label">目录模型快选</span>
                  <Segmented
                    size="small"
                    aria-label="API 模型类别筛选"
                    value={modelFilter}
                    onChange={(val) =>
                      setModelFilter(val as "all" | "text" | "image" | "video")
                    }
                    options={[
                      { value: "all", label: "全部" },
                      { value: "text", label: "文本" },
                      { value: "image", label: "图片" },
                      { value: "video", label: "视频" },
                    ]}
                  />
                </div>
                <Select
                  showSearch
                  allowClear
                  optionFilterProp="label"
                  aria-label="API 目录模型选择"
                  style={{ width: "100%" }}
                  placeholder="搜索并选择该平台 API 目录模型，或直接在下方输入公开标识"
                  value={matchedCatalogItem ? matchedCatalogItem.id : undefined}
                  options={[
                    ...filteredCatalog.map((item) => ({
                      value: item.id,
                      label: item.label,
                    })),
                    {
                      value: "__custom__",
                      label: "清空并手填其他公开模型标识",
                    },
                  ]}
                  onChange={(val) => handleSelectCatalogModel(val || "")}
                />
              </div>
            )}

            <Form.Item
              name="model_key"
              label="模型标识"
              rules={[{ required: true, message: "填写或选择公开模型标识" }]}
            >
              <Input
                maxLength={128}
                placeholder="例如 gpt-5、grok-4、gpt-image-1.5 或 doubao-seedance-1-0-pro-250528"
                autoComplete="off"
              />
            </Form.Item>

            <Form.Item
              name="capabilities"
              label="支持的能力"
              rules={[
                {
                  required: true,
                  type: "array",
                  min: 1,
                  message: "至少勾选一项支持的能力",
                },
              ]}
              extra="图生视频与文生视频为独立输入能力，按供应商文档如实勾选。"
            >
              <Checkbox.Group
                options={
                  capabilityOptions.length
                    ? capabilityOptions
                    : CAPABILITY_ORDER.map((id) => ({ value: id, label: id }))
                }
                onChange={(vals) => {
                  const nextCaps = vals as CapabilityId[];
                  if (!nextCaps.includes("text")) {
                    form.setFieldValue("purposes", []);
                  } else if (!(form.getFieldValue("purposes") || []).length) {
                    form.setFieldValue("purposes", [...ALL_PURPOSES]);
                  }
                }}
              />
            </Form.Item>

            {watchedCapabilities.includes("text") && (
              <Form.Item name="purposes" label="小说进阶用途">
                <Checkbox.Group
                  options={purposes.map((item) => ({
                    label: item.label,
                    value: item.id,
                  }))}
                />
              </Form.Item>
            )}

            <Form.Item
              name="enabled"
              label="启用此配置"
              valuePropName="checked"
              extra="停用或删除会立即清理指向此项的默认；已开始的任务不受影响。"
            >
              <Switch />
            </Form.Item>

            <Space wrap>
              <Button type="primary" htmlType="submit" loading={saving}>
                保存配置
              </Button>
              {selectedRow && (
                <>
                  <Button
                    loading={checkingMode === "config"}
                    disabled={checkingMode !== ""}
                    onClick={() => void checkConfig(selectedRow, false)}
                  >
                    检查配置
                  </Button>
                  <Button
                    type="primary"
                    ghost
                    loading={checkingMode === "live"}
                    disabled={checkingMode !== ""}
                    onClick={() => void checkConfig(selectedRow, true)}
                  >
                    在线探测连通
                  </Button>
                  <Button onClick={() => void toggleEnabled(selectedRow)}>
                    {selectedRow.enabled ? "停用此项" : "启用此项"}
                  </Button>
                  <Popconfirm
                    title="删除这个模型配置？"
                    description="已开始的任务保持原快照；指向此项的默认将立即清理。"
                    okText="删除"
                    cancelText="取消"
                    onConfirm={() => void removeConfig(selectedRow)}
                  >
                    <Button danger>删除配置</Button>
                  </Popconfirm>
                </>
              )}
            </Space>
          </Form>

          {selectedRow && currentProbe && (
            <Alert
              style={{ marginTop: 12 }}
              type={currentProbe.ok ? "success" : "warning"}
              showIcon
              title={currentProbe.message}
              description={liveProbeMeta || undefined}
            />
          )}

          <CapabilityDefaultsPanel
            capabilities={data?.capabilities || []}
            supportedCapabilities={watchedCapabilities}
            capabilitySource={
              matchedCatalogItem &&
              sameStringSet(
                matchedCatalogItem.capabilities || [],
                watchedCapabilities,
              )
                ? "catalog"
                : "explicit"
            }
            entryKind="model"
            modelKey={watchedModelKey.trim()}
            canBind={canBindApiDefault}
            blockedReason={apiBlockedReason}
            isCurrentDefault={(cap) => {
              const slot = data?.capability_defaults?.[cap];
              return Boolean(
                selectedRow &&
                slot &&
                slot.source === "api" &&
                slot.configuration_id === selectedRow.id &&
                slot.model_key === selectedRow.model_key,
              );
            }}
            effectiveCapabilities={data?.effective_capabilities}
            busyCapability={busyCapability}
            onSetDefault={async (cap) => {
              if (!selectedRow) return;
              await onBindCapability({
                capability: cap,
                source: "api",
                configuration_id: selectedRow.id,
                model_key: selectedRow.model_key,
              });
            }}
            onClearDefault={async (cap) => {
              await onBindCapability({ capability: cap, source: "" });
            }}
          />
        </Card>
      </div>
    </div>
  );
}
