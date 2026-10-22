import type {
  Agreement,
  BridgeMetrics,
  IssueAnalysis,
  Issue,
  Participant,
  SessionDetails,
  SessionProgress,
} from "./types";

const configuredBase = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";
export const API_BASE_URL = configuredBase.replace(/\/$/, "");

export class ApiError extends Error {
  status: number;
  details?: unknown;

  constructor(message: string, status: number, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body) headers.set("Content-Type", "application/json");

  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 20_000);
  const externalSignal = init.signal;
  const abortFromCaller = () => controller.abort();
  externalSignal?.addEventListener("abort", abortFromCaller, { once: true });

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers,
      signal: controller.signal,
    });
  } catch (error) {
    if (externalSignal?.aborted) throw error;
    if (controller.signal.aborted) {
      throw new ApiError("Request timed out. Please retry.", 408);
    }
    throw new ApiError(
      "Backend se connection nahi ho paaya. Server aur API URL check karein.",
      0,
    );
  } finally {
    window.clearTimeout(timeout);
    externalSignal?.removeEventListener("abort", abortFromCaller);
  }

  const contentType = response.headers.get("content-type") || "";
  const body = contentType.includes("application/json")
    ? await response.json().catch(() => null)
    : await response.text().catch(() => "");

  if (!response.ok) {
    const message =
      (body && typeof body === "object" &&
        (String((body as Record<string, unknown>).detail || "") ||
          String((body as Record<string, unknown>).message || ""))) ||
      `Request failed (${response.status})`;
    throw new ApiError(message, response.status, body);
  }

  return body as T;
}

export const api = {
  createSession: (payload: { title: string; description: string; context?: string }) =>
    request<{ id: string; join_code: string; status: string }>("/sessions", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  joinSession: (payload: { join_code: string; display_name: string }) =>
    request<{ session_id: string; participant_id: string; status: string }>(
      "/sessions/join",
      { method: "POST", body: JSON.stringify(payload) },
    ),

  getSession: (sessionId: string, signal?: AbortSignal) =>
    request<SessionDetails>(`/sessions/${sessionId}`, { signal }),

  getParticipants: async (sessionId: string, signal?: AbortSignal) => {
    const data = await request<Participant[] | { participants: Participant[] }>(
      `/sessions/${sessionId}/participants`,
      { signal },
    );
    return Array.isArray(data) ? data : data.participants || [];
  },

  getStatus: (sessionId: string, signal?: AbortSignal) =>
    request<SessionProgress>(`/sessions/${sessionId}/status`, { signal }),

  submitInterpretation: (
    sessionId: string,
    payload: {
      participant_id: string;
      response_text: string;
      assumptions: string[];
      success_criteria: string[];
    },
  ) =>
    request<{ interpretation_id: string; submitted: boolean }>(
      `/sessions/${sessionId}/interpretations`,
      { method: "POST", body: JSON.stringify(payload) },
    ),

  startAnalysis: (sessionId: string) =>
    request<{ analysis_id: string; status: string; issue_count?: number }>(
      `/sessions/${sessionId}/analyze`,
      { method: "POST" },
    ),

  getIssues: async (sessionId: string, signal?: AbortSignal): Promise<IssueAnalysis> => {
    const data = await request<Issue[] | IssueAnalysis>(
      `/sessions/${sessionId}/issues`,
      { signal },
    );
    return Array.isArray(data)
      ? {
          session_id: sessionId,
          issues: data,
          complementary_perspectives: [],
        }
      : {
          ...data,
          issues: data.issues || [],
          complementary_perspectives: data.complementary_perspectives || [],
        };
  },

  updateIssue: (
    issueId: string,
    payload: { status: "resolved" | "dismissed"; resolution_text?: string },
  ) =>
    request<Issue>(`/issues/${issueId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  generateAgreement: (sessionId: string) =>
    request<Agreement>(`/sessions/${sessionId}/agreement`, { method: "POST" }),

  confirmAgreement: (
    agreementId: string,
    payload: { participant_id: string; confirmed: boolean; comment: string | null },
  ) =>
    request<{
      agreement_id: string;
      participant_confirmed: boolean;
      agreement_status: string;
    }>(`/agreements/${agreementId}/confirm`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getBridgeMetrics: (sessionId: string, signal?: AbortSignal) =>
    request<BridgeMetrics>(`/sessions/${sessionId}/bridge-test`, { signal }),
};

export function messageFromError(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong. Please try again.";
}
