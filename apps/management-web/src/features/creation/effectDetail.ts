import { ApiError } from "../../shared/api";

export function effectDetail(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof TypeError) return "网络连接失败。恢复连接后可重试。";
  if (error instanceof Error && error.message) return error.message;
  return "网络连接失败。恢复连接后可重试。";
}
