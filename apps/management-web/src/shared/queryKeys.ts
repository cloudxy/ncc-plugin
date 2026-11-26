export const queryKeys = {
  me: () => ["me"] as const,
  users: () => ["users"] as const,
  userDirectory: (q = "") => ["users", "directory", q] as const,
  scopesRoot: () => ["scopes"] as const,
  scopes: (userId?: string) =>
    userId !== undefined
      ? (["scopes", userId] as const)
      : (["scopes"] as const),
  allScopes: (userId?: string) =>
    userId !== undefined
      ? (["scopes", "all", userId] as const)
      : (["scopes", "all"] as const),
  studioCatalog: () => ["studio-catalog"] as const,
  modelSettings: () => ["model-settings"] as const,
  subscriptionAuth: () => ["subscription-auth"] as const,
  scopeRoot: (scopeId: string) => ["scope", scopeId] as const,
  scopeInfo: (scopeId: string) => ["scope", scopeId, "info"] as const,
  studioOverview: (
    scopeId: string,
    role: "author" | "writer" | "reader" = "author",
    chapterId?: string,
  ) =>
    role === "author" && !chapterId
      ? (["scope", scopeId, "studio-overview"] as const)
      : ([
          "scope",
          scopeId,
          "studio-overview",
          { role, chapterId: chapterId || null },
        ] as const),
  definitions: (scopeId: string) => ["scope", scopeId, "definitions"] as const,
  members: (scopeId: string) => ["scope", scopeId, "members"] as const,
  tokens: (scopeId: string) => ["scope", scopeId, "tokens"] as const,
  audit: (scopeId: string, filters?: { action?: string; actor_id?: string }) =>
    filters && (filters.action || filters.actor_id)
      ? (["scope", scopeId, "audit", filters] as const)
      : (["scope", scopeId, "audit"] as const),
  attachments: (scopeId: string, purpose = "source") =>
    ["scope", scopeId, "attachments", purpose] as const,
  quality: (scopeId: string) => ["scope", scopeId, "quality"] as const,
  assessments: (scopeId: string) => ["scope", scopeId, "assessments"] as const,
  jobsRoot: (scopeId: string) => ["scope", scopeId, "jobs"] as const,
  jobs: (
    scopeId: string,
    filters?: { kind?: string; state?: string; summary?: boolean },
  ) =>
    filters
      ? (["scope", scopeId, "jobs", filters] as const)
      : (["scope", scopeId, "jobs"] as const),
  operations: (scopeId: string) => ["scope", scopeId, "operations"] as const,
  delegations: (scopeId: string) => ["scope", scopeId, "delegations"] as const,
  entity: (scopeId: string, entityId?: string) =>
    ["scope", scopeId, "entity", entityId] as const,
  entityHistory: (scopeId: string, entityId?: string) =>
    ["scope", scopeId, "history", entityId] as const,
  writingEntities: (scopeId: string) =>
    ["scope", scopeId, "writing-entities"] as const,
  codexSearch: (
    scopeId: string,
    q: string,
    groupId = "全部",
    role: "author" | "writer" | "reader" = "author",
    chapterId?: string,
  ) =>
    [
      "scope",
      scopeId,
      "codex-search",
      { q, groupId, role, chapterId: chapterId || null },
    ] as const,
  materials: (
    scopeId: string,
    params: {
      q: string;
      group: string;
      kind?: string;
      offset: number;
      sortKey: string;
    },
  ) => ["scope", scopeId, "materials", params] as const,
  commonsLibrary: (
    scopeId: string,
    params: { category: string; q: string; offset: number; sortKey: string },
  ) => ["scope", scopeId, "commons-library", params] as const,
  marketWinds: (
    scopeId: string,
    params: { q: string; track?: string; sortKey: string },
  ) => ["scope", scopeId, "market-winds", params] as const,
};
