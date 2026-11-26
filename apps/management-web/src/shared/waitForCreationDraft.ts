import { api, scoped, type Json } from "./api";
import { selectedCandidate } from "../features/creation/jobCandidate";

const TERMINAL_STATES = new Set([
  "failed",
  "cancelled",
  "waiting",
  "qualified",
  "succeeded",
  "applied",
]);

export async function waitForCreationDraft(
  scopeId: string,
  jobId: string,
  signal: AbortSignal,
  failureMessage: string,
): Promise<string> {
  for (let attempt = 0; attempt < 30; attempt += 1) {
    const job = await api<Json>(
      scoped(scopeId, `/jobs/${jobId}`),
      "GET",
      undefined,
      signal,
    );
    const text = selectedCandidate(job)?.text;
    if (typeof text === "string" && text.trim()) return text;
    if (TERMINAL_STATES.has(String(job.state || ""))) {
      throw new Error(failureMessage);
    }
    await new Promise<void>((resolve, reject) => {
      const timer = window.setTimeout(resolve, 2000);
      signal.addEventListener(
        "abort",
        () => {
          window.clearTimeout(timer);
          reject(new DOMException("aborted", "AbortError"));
        },
        { once: true },
      );
    });
  }
  throw new Error(failureMessage);
}
