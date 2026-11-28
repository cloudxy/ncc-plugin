export type Purpose = "plan" | "write" | "revise" | "judge" | "judge_secondary";

export type CapabilityId =
  | "text"
  | "text_to_image"
  | "video"
  | "image_to_image"
  | "image_to_video"
  | "text_to_video";

export type ModelCategory = "text" | "image" | "video";
export type EntryKind = "model" | "builtin_tool";
export type TransportMode = "http" | "cli_oauth";
export type CliProvider = "" | "grok" | "codex" | "agy";

export type ModelCatalogItem = {
  id: string;
  label: string;
  category?: ModelCategory;
  capabilities?: CapabilityId[];
  entry_kind?: EntryKind;
  capability_source?: "catalog" | "explicit" | "unknown";
};

export type PlatformSpec = {
  id: string;
  name: string;
  supplier: string;
  base_url: string;
  auth_ref: string;
  models: ModelCatalogItem[];
};

export type Configuration = {
  id: string;
  name: string;
  supplier: string;
  platform_id?: string;
  transport?: TransportMode;
  cli_provider?: CliProvider;
  base_url: string;
  auth_ref: string;
  model_key: string;
  capabilities?: CapabilityId[];
  capability_source?: "catalog" | "explicit" | "legacy_text_route";
  purposes: Purpose[];
  enabled: boolean;
  deprecated_notice?: string;
  connection?: { status: string; credential: string; message: string };
};

export type CapabilityMeta = {
  id: CapabilityId;
  label: string;
  description: string;
  runtime_adapter: "implemented" | "metadata_only";
  runtime_note: string;
};

export type CapabilityDefaultSlot = {
  source: "api" | "subscription";
  configuration_id?: string;
  provider?: "grok" | "codex" | "agy";
  model_key: string;
} | null;

export type EffectiveCapability = CapabilityMeta & {
  bound: boolean;
  fallback: boolean;
  fallback_from: string;
  fallback_blocked_reason: string;
  source: "" | "api" | "subscription" | "environment";
  source_label: string;
  platform_id: string;
  platform_label: string;
  configuration_id: string;
  provider: string;
  name: string;
  model_key: string;
  entry_kind?: EntryKind;
  status:
    "ready" | "unverified" | "needs_auth" | "cli_missing" | "invalid" | "unset";
  status_label: string;
  status_message: string;
  verified: boolean;
};

export type CapabilityCandidate = {
  value: string;
  source: "api" | "subscription";
  configuration_id: string;
  provider: string;
  platform_id: string;
  platform_label: string;
  name: string;
  model_key: string;
  entry_kind?: EntryKind;
  verified: boolean;
  status_label: string;
};

export type SettingsView = {
  configurations: Configuration[];
  defaults: Record<string, string>;
  purposes: { id: Purpose; label: string }[];
  presets: Array<Record<string, unknown> & { id: string; name: string }>;
  platforms: PlatformSpec[];
  capabilities: CapabilityMeta[];
  capability_defaults: Record<CapabilityId, CapabilityDefaultSlot>;
  effective_capabilities: Record<CapabilityId, EffectiveCapability>;
  capability_candidates: Record<CapabilityId, CapabilityCandidate[]>;
  source: string;
  effective: Record<
    string,
    {
      label: string;
      configuration_id: string;
      name: string;
      model_key: string;
      bound: boolean;
      source_kind?: string;
    }
  >;
  saved_id?: string;
};

export type ChannelStatus = {
  ready: boolean;
  status: string;
  cli_installed: boolean;
  account: string | null;
  message: string;
  verified: boolean;
};

export type ActiveSessionSummary = {
  provider: string;
  session_id: string;
  mode: "device_auth" | "manual";
  state: "pending";
  expires_in?: number | null;
};

export type LoginSession = {
  provider: string;
  started?: boolean;
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

export type Channel = {
  id: "grok" | "codex" | "agy" | string;
  title: string;
  path_label: string;
  login_command: string;
  login_label: string;
  verify_label: string;
  note: string;
  text_models?: ModelCatalogItem[];
  image_models?: ModelCatalogItem[];
  video_models?: ModelCatalogItem[];
  text_model?: string;
  image_model?: string;
  models: ModelCatalogItem[];
  model: string;
  status: ChannelStatus;
  verified?: boolean;
  active_session?: ActiveSessionSummary | null;
};

export type SubscriptionView = {
  channels: Channel[];
  ready_count: number;
};

export type ProbeState = {
  configId: string;
  mode: "config" | "live";
  ok: boolean;
  message: string;
  statusCode?: number | null;
  modelFound?: boolean | null;
  elapsedMs?: number;
};

export const CAPABILITY_ORDER: CapabilityId[] = [
  "text",
  "text_to_image",
  "video",
  "image_to_image",
  "image_to_video",
  "text_to_video",
];

export const CAPABILITY_LABEL_FALLBACK: Record<CapabilityId, string> = {
  text: "文本",
  text_to_image: "生图",
  video: "生视频",
  image_to_image: "图生图",
  image_to_video: "图生视频",
  text_to_video: "文生视频",
};

export function statusTagColor(status: EffectiveCapability["status"]): string {
  switch (status) {
    case "ready":
      return "green";
    case "unverified":
      return "blue";
    case "needs_auth":
    case "cli_missing":
    case "invalid":
      return "orange";
    default:
      return "default";
  }
}
