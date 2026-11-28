import { Button, Card, Select, Space, Tag, Typography } from "antd";
import { useState } from "react";
import {
  CAPABILITY_ORDER,
  statusTagColor,
  type CapabilityCandidate,
  type CapabilityId,
  type Purpose,
  type SettingsView,
} from "../modelsTypes";

type Props = {
  data: SettingsView | undefined;
  busyKey: string;
  onBindCapability: (payload: {
    capability: CapabilityId;
    source: "" | "api" | "subscription";
    configuration_id?: string;
    provider?: string;
    model_key?: string;
  }) => Promise<boolean>;
  onBindPurpose: (purpose: Purpose, configurationId: string) => Promise<void>;
  onJumpTab: (tab: "api" | "subscription") => void;
};

function currentSelectValue(
  slot: SettingsView["capability_defaults"][CapabilityId],
): string {
  if (!slot) return "";
  if (slot.source === "api" && slot.configuration_id) {
    return `api:${slot.configuration_id}`;
  }
  if (slot.source === "subscription" && slot.provider && slot.model_key) {
    return `subscription:${slot.provider}:${slot.model_key}`;
  }
  return "";
}

function buildGroupedOptions(candidates: CapabilityCandidate[]) {
  const apiItems = candidates.filter((item) => item.source === "api");
  const subItems = candidates.filter((item) => item.source === "subscription");
  const groups: Array<{
    label: string;
    options: Array<{ value: string; label: string }>;
  }> = [];
  if (apiItems.length) {
    groups.push({
      label: "API 配置",
      options: apiItems.map((item) => ({
        value: item.value,
        label: `[API] ${item.platform_label} · ${item.name}（${item.model_key}）`,
      })),
    });
  }
  if (subItems.length) {
    groups.push({
      label: "订阅配置",
      options: subItems.map((item) => ({
        value: item.value,
        label: `[订阅] ${item.platform_label} · ${item.model_key}${item.entry_kind === "builtin_tool" ? "（内置工具）" : ""}`,
      })),
    });
  }
  return [{ value: "", label: "不设置（清除默认）" }, ...groups];
}

export function DefaultsTab({
  data,
  busyKey,
  onBindCapability,
  onBindPurpose,
  onJumpTab,
}: Props) {
  const [draftSelection, setDraftSelection] = useState<Record<string, string>>(
    {},
  );
  const [purposeDraft, setPurposeDraft] = useState<Record<string, string>>({});

  const capabilities = data?.capabilities || [];
  const effectiveCaps = data?.effective_capabilities;
  const rawDefaults = data?.capability_defaults;
  const candidatesByCap = data?.capability_candidates;
  const configurations = data?.configurations || [];
  const purposes = data?.purposes || [];

  async function saveCapability(cap: CapabilityId) {
    const savedVal = currentSelectValue(rawDefaults?.[cap] ?? null);
    const chosen =
      draftSelection[cap] !== undefined ? draftSelection[cap] : savedVal;
    let ok = false;
    if (!chosen) {
      ok = await onBindCapability({ capability: cap, source: "" });
    } else if (chosen.startsWith("api:")) {
      const cid = chosen.slice(4);
      const match = (candidatesByCap?.[cap] || []).find(
        (item) => item.value === chosen,
      );
      ok = await onBindCapability({
        capability: cap,
        source: "api",
        configuration_id: cid,
        model_key: match?.model_key || "",
      });
    } else if (chosen.startsWith("subscription:")) {
      const rest = chosen.slice("subscription:".length);
      const sep = rest.indexOf(":");
      const provider = sep >= 0 ? rest.slice(0, sep) : "";
      const modelKey = sep >= 0 ? rest.slice(sep + 1) : "";
      ok = await onBindCapability({
        capability: cap,
        source: "subscription",
        provider,
        model_key: modelKey,
      });
    }
    if (ok) {
      setDraftSelection((prev) => {
        const next = { ...prev };
        delete next[cap];
        return next;
      });
    }
  }

  async function clearCapability(cap: CapabilityId) {
    const ok = await onBindCapability({ capability: cap, source: "" });
    if (ok) {
      setDraftSelection((prev) => {
        const next = { ...prev };
        delete next[cap];
        return next;
      });
    }
  }

  const orderedIds = capabilities.length
    ? capabilities.map((item) => item.id)
    : CAPABILITY_ORDER;

  return (
    <div className="defaults-tab" data-component="defaults-tab">
      <Card
        size="small"
        className="defaults-summary-card"
        title="六类默认模型"
        extra={
          <Space size={8}>
            <Button size="small" onClick={() => onJumpTab("api")}>
              管理 API
            </Button>
            <Button size="small" onClick={() => onJumpTab("subscription")}>
              管理订阅
            </Button>
          </Space>
        }
      >
        <div className="defaults-rows">
          {orderedIds.map((capId) => {
            const item = effectiveCaps?.[capId];
            const meta = capabilities.find((m) => m.id === capId);
            const candidates = candidatesByCap?.[capId] || [];
            const savedVal = currentSelectValue(rawDefaults?.[capId] ?? null);
            const selectedVal =
              draftSelection[capId] !== undefined
                ? draftSelection[capId]
                : savedVal;
            const isBusy = busyKey === `cap:${capId}`;

            return (
              <div
                key={capId}
                className={
                  capId === "text"
                    ? "default-row default-row-primary"
                    : "default-row"
                }
                data-default-capability={capId}
              >
                <div className="default-row-info">
                  <div className="default-row-title">
                    <strong>{item?.label || meta?.label || capId}</strong>
                    {capId === "text" && <Tag color="green">小说主能力</Tag>}
                    <Tag color={statusTagColor(item?.status || "unset")}>
                      {item?.status_label || "未设置"}
                    </Tag>
                    {item?.entry_kind === "builtin_tool" && (
                      <Tag color="blue">内置工具</Tag>
                    )}
                  </div>
                  <div className="default-row-meta">
                    <span>{item?.source_label || "未设置"}</span>
                    {item?.platform_label && (
                      <span>· {item.platform_label}</span>
                    )}
                    <span>
                      · <code>{item?.model_key || "未指定"}</code>
                    </span>
                  </div>
                  {item?.fallback && (
                    <p className="default-cap-note">
                      {item.fallback_from === "video"
                        ? `按输入能力匹配沿用「生视频」默认（${item.model_key}）。`
                        : item.status_message}
                    </p>
                  )}
                  {item?.fallback_blocked_reason && (
                    <p className="default-cap-warn">
                      {item.fallback_blocked_reason}
                    </p>
                  )}
                </div>

                <div className="default-row-controls">
                  <Select
                    showSearch
                    optionFilterProp="label"
                    aria-label={`${item?.label || capId}默认模型`}
                    className="default-row-select"
                    value={selectedVal}
                    options={buildGroupedOptions(candidates)}
                    onChange={(value) =>
                      setDraftSelection((prev) => ({
                        ...prev,
                        [capId]: value || "",
                      }))
                    }
                  />
                  <Space size={6}>
                    <Button
                      size="small"
                      type="primary"
                      loading={isBusy}
                      disabled={!!busyKey && !isBusy}
                      onClick={() => void saveCapability(capId)}
                    >
                      保存
                    </Button>
                    <Button
                      size="small"
                      disabled={!item?.bound || (!!busyKey && !isBusy)}
                      onClick={() => void clearCapability(capId)}
                    >
                      清除
                    </Button>
                  </Space>
                </div>
              </div>
            );
          })}
        </div>
        <p className="defaults-media-footnote">
          说明：「文本」已接入小说写作与审评路由；生图、生视频、图生图、图生视频、文生视频当前提供模型登记、能力校验与默认持久化，媒体执行适配器待后续接入。
        </p>
      </Card>

      <Card
        size="small"
        title="小说进阶设置（按写作工序独立指定）"
        className="novel-advanced-card"
        data-section="novel-advanced-defaults"
      >
        <Typography.Paragraph
          type="secondary"
          style={{ marginBottom: 8, fontSize: 12 }}
        >
          未单独覆盖时，前四项沿用上方「文本」默认；第二评价默认不启用。正在运行的任务保持启动快照不变。
        </Typography.Paragraph>
        {purposes.map((item) => {
          const options = configurations.filter(
            (row) =>
              row.enabled &&
              (row.capabilities || ["text"]).includes("text") &&
              row.purposes.includes(item.id),
          );
          const value =
            purposeDraft[item.id] !== undefined
              ? purposeDraft[item.id]
              : data?.defaults?.[item.id] || "";
          const effect = data?.effective?.[item.id];
          const isBusy = busyKey === `purpose:${item.id}`;
          const hint = !effect
            ? ""
            : effect.model_key
              ? effect.source_kind === "explicit_purpose"
                ? `独立指定：${effect.name} · ${effect.model_key}`
                : effect.source_kind === "global_text"
                  ? `沿用文本默认：${effect.name} · ${effect.model_key}`
                  : effect.source_kind === "environment"
                    ? `进程环境：${effect.model_key}`
                    : `自动匹配：${effect.name} · ${effect.model_key}`
              : item.id === "judge_secondary"
                ? "未启用第二评价。"
                : "暂无可用文本模型。";

          return (
            <div className="model-default" key={item.id}>
              <b>{item.label}</b>
              <Select
                size="small"
                aria-label={`小说进阶-${item.label}`}
                value={value}
                onChange={(next) =>
                  setPurposeDraft((current) => ({
                    ...current,
                    [item.id]: next,
                  }))
                }
                options={[
                  {
                    value: "",
                    label:
                      item.id === "judge_secondary"
                        ? "不启用（留空）"
                        : "不单独覆盖（沿用文本默认）",
                  },
                  ...options.map((row) => ({
                    value: row.id,
                    label: `${row.name} · ${row.model_key}${row.transport === "cli_oauth" ? "（旧 CLI 登记）" : ""}`,
                  })),
                ]}
              />
              <Button
                size="small"
                type="primary"
                ghost
                loading={isBusy}
                disabled={!!busyKey && !isBusy}
                onClick={() => void onBindPurpose(item.id, value)}
              >
                保存
              </Button>
              <p>{hint}</p>
            </div>
          );
        })}
      </Card>
    </div>
  );
}
