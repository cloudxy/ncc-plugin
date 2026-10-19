export type Json = Record<string, any>;
export type Scope = {
  id: string;
  name: string;
  kind: string;
  version: number;
  actions: string[];
  config: Json;
  base_id?: string;
};
export type Entity = {
  id: string;
  name: string;
  kind: string;
  version: string;
  revision: string;
  content_hash: string;
  data: Json;
  text: string;
  secret: boolean;
  definition_id: string;
  definition_spec?: Definition["spec"];
  text_preview?: string;
};
export type Definition = {
  id: string;
  key: string;
  version: number;
  spec: {
    label: string;
    domain?: string;
    properties?: Record<string, Json>;
    required?: string[];
    relation?: boolean;
    exclusive_target?: boolean;
    acyclic?: boolean;
  };
};
let csrf = "";
export function setCSRF(value: string) {
  csrf = value;
}
export class ApiError extends Error {
  constructor(
    public status: number,
    public problem: Json,
  ) {
    super(problem.detail || problem.title || "请求失败");
  }
}
export async function api<T = any>(
  path: string,
  method = "GET",
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  const headers: Record<string, string> = { "x-ncc-client": "console" };
  if (method !== "GET" && method !== "HEAD") {
    headers["x-csrf-token"] = csrf;
    headers["idempotency-key"] = crypto.randomUUID();
  }
  if (body !== undefined && !(body instanceof FormData))
    headers["content-type"] = "application/json";
  const response = await fetch("/api/v1" + path, {
    method,
    credentials: "same-origin",
    headers,
    body:
      body instanceof FormData
        ? body
        : body !== undefined
          ? JSON.stringify(body)
          : method !== "GET" && method !== "HEAD"
            ? "{}"
            : undefined,
    signal,
  });
  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: `服务返回 ${response.status}` }));
    if (response.status === 401)
      window.dispatchEvent(new Event("ncc-auth-expired"));
    throw new ApiError(response.status, error);
  }
  return response.json();
}
export const scoped = (scope: string, path: string) =>
  `/scopes/${scope}${path}`;
export async function adopt(scope: Scope, operations: Json[], title: string) {
  const fresh = await api<Scope>(scoped(scope.id, ""));
  const change = await api<Json>(scoped(scope.id, "/changes"), "POST", {
    title,
    base_version: fresh.version,
    operations,
  });
  return api(scoped(scope.id, `/changes/${change.id}/adopt`), "POST");
}
export async function download(
  scope: string,
  id: string,
  name = "ncc-export.json",
) {
  const response = await fetch(
    "/api/v1" + scoped(scope, `/attachments/${id}`),
    { credentials: "same-origin" },
  );
  if (!response.ok) throw new Error("下载失败或权限已变化");
  const url = URL.createObjectURL(await response.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
