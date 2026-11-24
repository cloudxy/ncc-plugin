import { api, scoped, type Json } from "./api";

export type PipelineStage =
  "plan" | "judge_plan" | "write" | "judge" | "revise";

export type CodexGroup = {
  id: string;
  label: string;
  description: string;
  kinds: string[];
  recommended_fields: string[];
};

export type CommonsCategory = {
  id: string;
  label: string;
};

export type CommonsCard = {
  id: string;
  category: string;
  title: string;
  summary: string;
  structure: string[];
  ai_prompt_hint: string;
  pitfalls: string[];
  tags: string[];
};

export type MarketPlaybook = {
  id: string;
  name: string;
  core_hook: string;
  pacing_3_10_30: string;
  hook_mix: string;
  midgame_trap: string;
  poison_list: string[];
  target_words_band: [number, number];
};

export type PipelinePreset = {
  id: string;
  label: string;
  stages: PipelineStage[];
};

export type StudioCatalog = {
  codex_groups: CodexGroup[];
  commons_categories: CommonsCategory[];
  commons_cards: CommonsCard[];
  market_playbooks: MarketPlaybook[];
  pipeline_presets: PipelinePreset[];
};

export type StudioVolume = {
  id: string;
  name: string;
  version: string;
  position: number;
  status: string;
};

export type StudioChapter = {
  id: string;
  name: string;
  version: string;
  position: number;
  book_order?: number;
  parent_id?: string | null;
  status: string;
  key_chapter: boolean;
  pov: string;
  plotline: string;
  hook: string;
  beat_outline: string;
  target_words?: number | null;
  char_count: number;
  non_whitespace_chars?: number;
};

export type StudioOutline = {
  id: string;
  name: string;
  version: string;
  kind: string;
  position: number;
  parent_id?: string | null;
  status: string;
  plotline: string;
  beat_outline: string;
};

export type ForeshadowAlertState =
  "resolved" | "dropped" | "overdue" | "due_soon" | "active" | "planned";

export type StudioForeshadow = {
  id: string;
  name: string;
  version: string;
  kind: string;
  position: number;
  status: string;
  line_type: string;
  planted_chapter?: number | null;
  expected_chapter?: number | null;
  planted?: boolean;
  due_state?: "overdue" | "due_soon" | "none";
  alert_state: ForeshadowAlertState;
};

export type StudioMarketConfig = {
  playbook_id?: string;
  custom_track?: string;
  target_min_words?: number;
  target_max_words?: number;
  poison_notes?: string[];
  direction_note?: string;
};

export type StudioDiagnostics = {
  chapter_count: number;
  total_chars: number;
  avg_chars: number;
  total_non_whitespace_chars?: number;
  char_metric?: string;
  key_chapter_count: number;
  active_hidden_lines: number;
  planned_hidden_lines?: number;
  resolved_hidden_lines?: number;
  dropped_hidden_lines?: number;
  hidden_line_cap_exceeded: boolean;
  overdue_foreshadow_count: number;
  due_soon_foreshadow_count: number;
  planted_overdue_foreshadow_count?: number;
  planted_due_soon_foreshadow_count?: number;
  unplanted_due_foreshadow_count?: number;
  resolved_foreshadow_count?: number;
  dropped_foreshadow_count?: number;
};

export type StudioPagination = {
  total_entities: number;
  structural_count: number;
  returned_structural: number;
  offset: number;
  limit: number;
  truncated: boolean;
  next_offset?: number | null;
};

export type CommonsScopeSummary = {
  id: string;
  name: string;
  kind: string;
  version: number;
};

export type StudioOverview = {
  volumes: StudioVolume[];
  chapters: StudioChapter[];
  outlines: StudioOutline[];
  foreshadows: StudioForeshadow[];
  codex_counts: {
    groups: Array<{ id: string; label: string; count: number }>;
    kinds: Record<string, number>;
  };
  market_config: StudioMarketConfig;
  pagination?: StudioPagination;
  diagnostics: StudioDiagnostics;
  commons_scopes: CommonsScopeSummary[];
};

export type StudioReorderItem = {
  entity_id: string;
  position: number;
  parent_id?: string | null;
  include_parent?: boolean;
};

export type CrossScopeAttachment = {
  scope_id: string;
  entity_id: string;
  title: string;
};

export type BuiltinCommonsAttachment = {
  id: string;
  title: string;
};

export type StudioReturnOrigin = "inbox" | "jobs" | "blueprint";

export type StudioHandoff = {
  scopeId: string;
  chapterId?: string;
  jobId?: string;
  returnTo?: StudioReturnOrigin;
  sourceEntity?: { id: string; title: string };
  builtinCommons?: BuiltinCommonsAttachment;
  commonsRef?: CrossScopeAttachment;
};

export type BlueprintCardDraft = {
  baseVersion: string;
  first: string;
  second: string;
};

type BlueprintCardDraftEntry = BlueprintCardDraft & {
  sessionOwner: string;
  scopeId: string;
  actionsStamp: string;
};

let activeSessionOwner: string | null = null;
let pendingHandoff: (StudioHandoff & { sessionOwner: string }) | null = null;
const blueprintDraftCache = new Map<string, BlueprintCardDraftEntry>();

function actionsSignature(actions: readonly string[]): string {
  return actions.slice().sort().join(":");
}

function draftMapKey(
  sessionOwner: string,
  scopeId: string,
  kind: "outline" | "chapter",
  entityId: string,
): string {
  return `${sessionOwner}::${scopeId}::${kind}::${entityId}`;
}

/** Bind in-memory studio drafts & handoff to the active login session; switching or ending session destroys prior drafts. */
export function bindStudioSessionOwner(sessionOwner: string | null): void {
  const normalized = sessionOwner && sessionOwner.trim() ? sessionOwner : null;
  if (normalized === activeSessionOwner) return;
  blueprintDraftCache.clear();
  pendingHandoff = null;
  activeSessionOwner = normalized;
}

/** Destroy all in-memory studio drafts and handoffs (on logout, auth expiry, or login switch). */
export function clearAllStudioSessionDrafts(): void {
  blueprintDraftCache.clear();
  pendingHandoff = null;
  activeSessionOwner = null;
}

/** Destroy in-memory studio drafts and handoffs for a specific scope (on permission change or access revocation). */
export function clearScopeStudioDrafts(scopeId: string): void {
  if (!scopeId) return;
  for (const [key, entry] of blueprintDraftCache.entries()) {
    if (entry.scopeId === scopeId) blueprintDraftCache.delete(key);
  }
  if (pendingHandoff?.scopeId === scopeId) {
    pendingHandoff = null;
  }
}

/** Remove drafts for scopes no longer accessible in the current session's scope list. */
export function pruneStudioDraftScopes(
  allowedScopeIds: Iterable<string>,
): void {
  const allowed = new Set(allowedScopeIds);
  for (const [key, entry] of blueprintDraftCache.entries()) {
    if (!allowed.has(entry.scopeId)) blueprintDraftCache.delete(key);
  }
  if (pendingHandoff && !allowed.has(pendingHandoff.scopeId)) {
    pendingHandoff = null;
  }
}

/** Purge scope drafts if edit capability was lost or scope action set changed. */
export function syncScopeStudioActions(
  scopeId: string,
  actions: readonly string[],
): void {
  if (!actions.includes("edit")) {
    clearScopeStudioDrafts(scopeId);
    return;
  }
  const stamp = actionsSignature(actions);
  for (const [key, entry] of blueprintDraftCache.entries()) {
    if (entry.scopeId === scopeId && entry.actionsStamp !== stamp) {
      blueprintDraftCache.delete(key);
    }
  }
}

export function getBlueprintDraft(
  sessionOwner: string,
  scopeId: string,
  actions: readonly string[],
  kind: "outline" | "chapter",
  entityId: string,
): BlueprintCardDraft | undefined {
  if (
    !sessionOwner ||
    sessionOwner !== activeSessionOwner ||
    !actions.includes("edit")
  ) {
    return undefined;
  }
  const key = draftMapKey(sessionOwner, scopeId, kind, entityId);
  const entry = blueprintDraftCache.get(key);
  if (!entry) return undefined;
  if (
    entry.sessionOwner !== sessionOwner ||
    entry.scopeId !== scopeId ||
    entry.actionsStamp !== actionsSignature(actions)
  ) {
    blueprintDraftCache.delete(key);
    return undefined;
  }
  return {
    baseVersion: entry.baseVersion,
    first: entry.first,
    second: entry.second,
  };
}

export function setBlueprintDraft(
  sessionOwner: string,
  scopeId: string,
  actions: readonly string[],
  kind: "outline" | "chapter",
  entityId: string,
  draft: BlueprintCardDraft,
): void {
  if (!sessionOwner || !actions.includes("edit")) return;
  if (activeSessionOwner !== sessionOwner) {
    bindStudioSessionOwner(sessionOwner);
  }
  const key = draftMapKey(sessionOwner, scopeId, kind, entityId);
  blueprintDraftCache.set(key, {
    ...draft,
    sessionOwner,
    scopeId,
    actionsStamp: actionsSignature(actions),
  });
}

export function deleteBlueprintDraft(
  sessionOwner: string,
  scopeId: string,
  kind: "outline" | "chapter",
  entityId: string,
): void {
  if (!sessionOwner) return;
  blueprintDraftCache.delete(
    draftMapKey(sessionOwner, scopeId, kind, entityId),
  );
}

export function countBlueprintDrafts(
  sessionOwner: string,
  scopeId: string,
  actions: readonly string[],
): number {
  if (
    !sessionOwner ||
    sessionOwner !== activeSessionOwner ||
    !actions.includes("edit")
  ) {
    return 0;
  }
  const stamp = actionsSignature(actions);
  let count = 0;
  for (const [key, entry] of blueprintDraftCache.entries()) {
    if (entry.scopeId !== scopeId) continue;
    if (entry.sessionOwner !== sessionOwner || entry.actionsStamp !== stamp) {
      blueprintDraftCache.delete(key);
      continue;
    }
    count += 1;
  }
  return count;
}

/** Store in-memory cross-route studio handoff bound to the current login session without writing novel data to localStorage. */
export function setStudioHandoff(next: StudioHandoff) {
  if (!activeSessionOwner) {
    pendingHandoff = null;
    return;
  }
  pendingHandoff = { ...next, sessionOwner: activeSessionOwner };
}

export function consumeStudioHandoff(scopeId: string): StudioHandoff | null {
  if (!pendingHandoff) return null;
  if (
    !activeSessionOwner ||
    pendingHandoff.sessionOwner !== activeSessionOwner
  ) {
    pendingHandoff = null;
    return null;
  }
  if (pendingHandoff.scopeId !== scopeId) return null;
  const { sessionOwner: _owner, ...taken } = pendingHandoff;
  pendingHandoff = null;
  return taken;
}

export function buildWorkTaskPath(
  scopeId: string,
  job: Json,
  from: "inbox" | "jobs",
): string {
  const params = new URLSearchParams();
  params.set("scope", scopeId);
  const entityId =
    typeof job.payload?.entity_id === "string" && job.payload.entity_id
      ? job.payload.entity_id
      : undefined;
  if (entityId) params.set("entity", entityId);
  if (job.id) params.set("job", String(job.id));
  params.set("from", from);
  return `/work?${params.toString()}`;
}

export function buildJobsTaskPath(
  scopeId: string,
  jobId: string,
  from: "inbox" | "work" = "inbox",
): string {
  const params = new URLSearchParams();
  params.set("scope", scopeId);
  if (jobId) params.set("job", jobId);
  params.set("from", from);
  return `/admin/jobs?${params.toString()}`;
}

const HAN_REGEX = /\p{Script=Han}/gu;

/** Count CJK Unified Ideographs only, excluding punctuation and whitespace. */
export function countHanChars(text: string): number {
  if (!text) return 0;
  const matches = text.match(HAN_REGEX);
  return matches ? matches.length : 0;
}

export const STAGE_LABELS: Record<PipelineStage, string> = {
  plan: "细纲推演",
  judge_plan: "结构审",
  write: "正文起草",
  judge: "质量审评",
  revise: "定向返修",
};

const CANONICAL_STAGE_ORDER: PipelineStage[] = [
  "plan",
  "judge_plan",
  "write",
  "judge",
  "revise",
];

const REVISE_WITHOUT_WRITE_ORDER: PipelineStage[] = [
  "plan",
  "judge_plan",
  "revise",
  "judge",
];

/**
 * Normalize selected composable stages to valid backend execution order.
 * When revising existing text without drafting (`revise` without `write`),
 * `plan`/`judge_plan` stay ahead of `revise`, and `revise` runs before `judge`.
 */
export function normalizeStages(stages: PipelineStage[]): PipelineStage[] {
  const unique = new Set(stages);
  if (!unique.has("write")) {
    return REVISE_WITHOUT_WRITE_ORDER.filter((s) => unique.has(s));
  }
  return CANONICAL_STAGE_ORDER.filter((s) => unique.has(s));
}

export function validateStudioStages(
  stages: PipelineStage[] | null,
  options: {
    hasOutline: boolean;
    hasCurrent: boolean;
    hasSavedTarget?: boolean;
    hasDelegation?: boolean;
  },
): string | null {
  if (options.hasDelegation && stages !== null) {
    return "自动定稿托管须执行默认完整审评流程，不能与显式拆分工序同时使用";
  }
  if (stages === null) return null;
  if (stages.length === 0) return "先选择至少一道工序";
  const index = new Map<PipelineStage, number>();
  for (let i = 0; i < stages.length; i += 1) {
    if (index.has(stages[i])) return "创作工序不能重复";
    index.set(stages[i], i);
  }
  if (
    index.has("plan") &&
    index.has("judge_plan") &&
    index.get("plan")! > index.get("judge_plan")!
  ) {
    return "结构审必须排在细纲推演之后";
  }
  if (
    index.has("plan") &&
    index.has("write") &&
    index.get("plan")! > index.get("write")!
  ) {
    return "正文起草必须排在细纲推演之后";
  }
  if (
    index.has("plan") &&
    index.has("revise") &&
    index.get("plan")! > index.get("revise")!
  ) {
    return "定向返修必须排在细纲推演之后";
  }
  if (
    index.has("judge_plan") &&
    index.has("write") &&
    index.get("judge_plan")! > index.get("write")!
  ) {
    return "正文起草必须排在结构审之后";
  }
  if (
    index.has("judge_plan") &&
    index.has("revise") &&
    index.get("judge_plan")! > index.get("revise")!
  ) {
    return "定向返修必须排在结构审之后";
  }
  if (index.has("write") && index.has("revise")) {
    if (!index.has("judge")) {
      return "起草后自动返修需要先勾选质量审评，以便按审评意见返修";
    }
    if (
      index.get("write")! > index.get("judge")! ||
      index.get("judge")! > index.get("revise")!
    ) {
      return "起草后自动返修须按「正文起草 → 质量审评 → 定向返修」顺序执行";
    }
  }
  if (index.has("judge") && index.has("revise") && !index.has("write")) {
    if (index.get("revise")! > index.get("judge")!) {
      return "不经过起草时，质量审评须排在定向返修之后做复评";
    }
  }
  if (
    index.has("judge") &&
    !(stages.length === 1 && stages[0] === "judge") &&
    !index.has("write") &&
    !index.has("revise")
  ) {
    return "质量审评需要搭配「正文起草」或「定向返修」，或只勾选「质量审评」单独评分";
  }
  if (
    index.has("judge_plan") &&
    !index.has("plan") &&
    !options.hasOutline &&
    !options.hasCurrent
  ) {
    return "单独结构审需要先填写本章细纲或选择已有内容对象";
  }
  if (
    stages.length === 1 &&
    stages[0] === "judge" &&
    !(options.hasSavedTarget ?? options.hasCurrent)
  ) {
    return "仅质量审评需要先选择已保存的内容对象";
  }
  if (index.has("revise") && !index.has("write") && !options.hasCurrent) {
    return "不经过正文起草的定向返修需要已有正文内容";
  }
  return null;
}

export function fetchStudioCatalog() {
  return api<StudioCatalog>("/studio/catalog");
}

export function fetchStudioOverview(
  scopeId: string,
  params?: {
    role?: "author" | "writer" | "reader";
    chapterId?: string;
    offset?: number;
    limit?: number;
  },
) {
  const query = new URLSearchParams();
  if (params?.role) query.set("role", params.role);
  if (params?.chapterId) query.set("chapter_id", params.chapterId);
  if (params?.offset !== undefined) query.set("offset", String(params.offset));
  if (params?.limit !== undefined) query.set("limit", String(params.limit));
  const suffix = query.toString();
  return api<StudioOverview>(
    scoped(scopeId, `/studio/overview${suffix ? `?${suffix}` : ""}`),
  );
}

export function reorderStudioEntities(
  scopeId: string,
  baseVersion: number,
  items: StudioReorderItem[],
) {
  return api<Json>(scoped(scopeId, "/studio/reorder"), "POST", {
    base_version: baseVersion,
    items,
  });
}

export function saveStudioMarketConfig(
  scopeId: string,
  config: Required<
    Pick<
      StudioMarketConfig,
      | "playbook_id"
      | "custom_track"
      | "target_min_words"
      | "target_max_words"
      | "poison_notes"
      | "direction_note"
    >
  >,
) {
  return api<{
    market_config: StudioMarketConfig;
    diagnostics: StudioDiagnostics;
  }>(scoped(scopeId, "/studio/market-config"), "PUT", config);
}
