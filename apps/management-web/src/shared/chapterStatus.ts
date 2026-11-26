export type ChapterStatus = "planned" | "draft" | "review" | "done";

export const CHAPTER_STATUS_OPTIONS: {
  value: ChapterStatus;
  label: string;
}[] = [
  { value: "planned", label: "规划中" },
  { value: "draft", label: "草稿" },
  { value: "review", label: "待审" },
  { value: "done", label: "已定稿" },
];

export function normalizeChapterStatus(raw?: string | null): ChapterStatus {
  const value = (raw || "").trim().toLowerCase();
  if (value === "planned" || value === "pending" || value === "规划中") {
    return "planned";
  }
  if (
    value === "review" ||
    value === "checking" ||
    value === "reviewing" ||
    value === "revising" ||
    value === "待审"
  ) {
    return "review";
  }
  if (value === "done" || value === "已定稿") {
    return "done";
  }
  return "draft";
}

export function chapterStatusFilterKey(raw?: string | null): string {
  const value = (raw || "").trim().toLowerCase();
  if (value === "failed" || value === "待修") {
    return "failed";
  }
  return normalizeChapterStatus(raw);
}

export function chapterStatusLabel(raw?: string | null): string {
  const trimmed = (raw || "").trim();
  if (!trimmed) return "草稿";
  const lower = trimmed.toLowerCase();
  if (lower === "planned" || lower === "pending" || trimmed === "规划中") {
    return "规划中";
  }
  if (
    lower === "draft" ||
    lower === "drafted" ||
    lower === "drafting" ||
    trimmed === "草稿"
  ) {
    return "草稿";
  }
  if (
    lower === "review" ||
    lower === "checking" ||
    lower === "reviewing" ||
    lower === "revising" ||
    trimmed === "待审"
  ) {
    return "待审";
  }
  if (lower === "done" || trimmed === "已定稿") {
    return "已定稿";
  }
  if (lower === "failed" || trimmed === "待修") {
    return "待修";
  }
  if (/[^\u0000-\u007f]/.test(trimmed)) {
    return trimmed;
  }
  return "草稿";
}

export function chapterStatusTagColor(raw?: string | null): string | undefined {
  const key = chapterStatusFilterKey(raw);
  if (key === "done") return "success";
  if (key === "review") return "processing";
  if (key === "failed") return "error";
  if (key === "planned") return "default";
  return "gold";
}
