import type { Json } from "../../shared/api";

export function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

export function selectedCandidate(job: Json | undefined): Json | undefined {
  const candidates = job?.result?.candidates;
  if (!Array.isArray(candidates) || candidates.length === 0) return undefined;
  const index = job?.result?.selected ?? candidates.length - 1;
  const candidate = candidates[index];
  return candidate && typeof candidate === "object" ? candidate : undefined;
}

export function chapterCreationJobs(
  list: Json[] | undefined,
  entityId: string | undefined,
): Json[] {
  if (!list) return [];
  return list.filter((job) => {
    if (job.kind !== "creation" || job.state === "applied") return false;
    const target =
      typeof job.payload?.entity_id === "string" && job.payload.entity_id
        ? job.payload.entity_id
        : undefined;
    return target === entityId;
  });
}

export function currentCreationJob(
  list: Json[] | undefined,
  submittedId: string | undefined,
  entityId: string | undefined,
): Json | undefined {
  if (!list) return undefined;
  if (submittedId) {
    const exact = list.find((job) => job.id === submittedId);
    if (exact) return exact;
  }
  return chapterCreationJobs(list, entityId)[0];
}

export function usageSource(kind: unknown): string | undefined {
  if (kind === undefined || kind === null || kind === "") return undefined;
  if (kind === "conservative_estimate") return "预算估算";
  return "服务端用量记录";
}
