import { Alert, Button, Tag } from "antd";
import {
  CAPABILITY_LABEL_FALLBACK,
  CAPABILITY_ORDER,
  type CapabilityId,
  type CapabilityMeta,
  type EffectiveCapability,
  type EntryKind,
} from "../modelsTypes";

type Props = {
  capabilities: CapabilityMeta[];
  supportedCapabilities: CapabilityId[];
  capabilitySource: "catalog" | "explicit" | "legacy_text_route" | "unknown";
  entryKind?: EntryKind;
  modelKey: string;
  canBind: boolean;
  blockedReason?: string;
  isCurrentDefault: (cap: CapabilityId) => boolean;
  effectiveCapabilities?: Record<CapabilityId, EffectiveCapability>;
  busyCapability: string;
  onSetDefault: (cap: CapabilityId) => Promise<void>;
  onClearDefault: (cap: CapabilityId) => Promise<void>;
};

export function CapabilityDefaultsPanel({
  capabilities,
  supportedCapabilities,
  capabilitySource,
  entryKind = "model",
  modelKey,
  canBind,
  blockedReason,
  isCurrentDefault,
  effectiveCapabilities,
  busyCapability,
  onSetDefault,
  onClearDefault,
}: Props) {
  const orderedMeta: CapabilityMeta[] = capabilities.length
    ? capabilities
    : CAPABILITY_ORDER.map((id) => ({
        id,
        label: CAPABILITY_LABEL_FALLBACK[id],
        description: "",
        runtime_adapter: id === "text" ? "implemented" : "metadata_only",
        runtime_note: "",
      }));

  const supportedSet = new Set(supportedCapabilities);
  const hasSupportedMedia = supportedCapabilities.some((cap) => cap !== "text");

  return (
    <section
      className="capability-panel"
      data-component="capability-defaults-panel"
      aria-label="能力与默认设置"
    >
      <div className="capability-panel-head">
        <div className="capability-panel-title-row">
          <h4>能力与默认设置</h4>
          <code>{modelKey || "未选择"}</code>
          {entryKind === "builtin_tool" && (
            <Tag color="blue">CLI 内置工具 / 能力线索</Tag>
          )}
          {capabilitySource === "unknown" && <Tag color="orange">能力未知</Tag>}
        </div>
        <span className="capability-panel-note">
          切换浏览不改动已设默认；仅按目录或显式声明判定能力。
        </span>
      </div>

      {capabilitySource === "unknown" && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 10 }}
          title="未在渠道目录中登记能力，不能设为默认"
          description="系统不从模型名称或登录态猜测能力。请改选目录内已知模型，或在「API 配置」中显式勾选供应商能力。"
        />
      )}

      {capabilitySource !== "unknown" && blockedReason && (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 10 }}
          title={blockedReason}
        />
      )}

      <div className="capability-list">
        {orderedMeta.map((meta) => {
          const cap = meta.id;
          const supported = supportedSet.has(cap);
          const activeHere = isCurrentDefault(cap);
          const currentGlobal = effectiveCapabilities?.[cap];
          const isBusy = busyCapability === cap;

          return (
            <div
              key={cap}
              className={
                activeHere
                  ? "capability-row is-active"
                  : supported
                    ? "capability-row is-supported"
                    : "capability-row is-unsupported"
              }
              data-capability={cap}
              data-supported={supported ? "true" : "false"}
            >
              <div className="capability-row-label">
                <span>{meta.label}</span>
                {activeHere ? (
                  <Tag color="green">当前默认</Tag>
                ) : supported ? (
                  <Tag color="blue">支持</Tag>
                ) : (
                  <Tag>
                    {capabilitySource === "unknown" ? "未知" : "不支持"}
                  </Tag>
                )}
              </div>

              <div className="capability-row-summary">
                {activeHere
                  ? "已绑定此项"
                  : currentGlobal?.bound
                    ? `现默认：${currentGlobal.source_label} · ${currentGlobal.model_key}`
                    : currentGlobal?.fallback
                      ? `现回退：${currentGlobal.model_key}`
                      : "未设置"}
              </div>

              <div className="capability-row-action">
                {activeHere ? (
                  <Button
                    size="small"
                    danger
                    loading={isBusy}
                    disabled={!!busyCapability && !isBusy}
                    onClick={() => void onClearDefault(cap)}
                  >
                    取消「{meta.label}」默认
                  </Button>
                ) : (
                  <Button
                    size="small"
                    type={supported && canBind ? "primary" : "default"}
                    ghost={supported && canBind}
                    loading={isBusy}
                    disabled={
                      !supported || !canBind || (!!busyCapability && !isBusy)
                    }
                    onClick={() => void onSetDefault(cap)}
                  >
                    {supported
                      ? `设为「${meta.label}」默认`
                      : capabilitySource === "unknown"
                        ? "能力未知"
                        : "不支持"}
                  </Button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {hasSupportedMedia && (
        <p className="capability-media-footnote">
          注：生图、生视频、图生图、图生视频、文生视频当前完成模型登记、能力校验与默认保存，媒体执行适配待后续接入。
        </p>
      )}
    </section>
  );
}
