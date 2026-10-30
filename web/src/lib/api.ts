// BillSaathi API client: start a check, follow its live events, answer the agent's question.
import type { ApiEvent } from "./timeline";
import type { Lang } from "./i18n";

export const API_BASE = (process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
  }
}

export async function startCheck(input: { image?: Blob; imageName?: string; text?: string; language: Lang }): Promise<string> {
  const form = new FormData();
  form.set("language", input.language);
  if (input.image) form.set("image", input.image, input.imageName ?? "image.jpg");
  if (input.text) form.set("text", input.text);
  let r: Response;
  try {
    r = await fetch(`${API_BASE}/api/v1/checks`, { method: "POST", body: form });
  } catch {
    throw new ApiError(0, "network", "network error");
  }
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw new ApiError(r.status, body.error ?? body.detail?.error ?? "error", body.message ?? "request failed");
  return body.check_id;
}

export async function sendAnswer(checkId: string, answer: string): Promise<void> {
  const r = await fetch(`${API_BASE}/api/v1/checks/${checkId}/answer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answer }),
  });
  if (!r.ok) throw new ApiError(r.status, "answer_failed", "could not send the answer");
}

/**
 * Follow the live event stream from `after`. The server closes the stream when the check is
 * complete or waiting for an answer; we close our side too, so the browser does not reconnect.
 */
export function followEvents(checkId: string, after: number, onEvent: (e: ApiEvent) => void, onError: () => void): () => void {
  const source = new EventSource(`${API_BASE}/api/v1/checks/${checkId}/events?after=${after}`);
  let finished = false;
  const handle = (msg: MessageEvent) => {
    const event = JSON.parse(msg.data) as ApiEvent;
    onEvent(event);
    if (event.type === "complete" || event.type === "question") {
      finished = true;
      source.close();
    }
  };
  for (const type of ["received", "extracted", "verification_started", "check", "agent_turn", "refusal", "judge", "question", "answer", "verdict", "complete"]) {
    source.addEventListener(type, handle as EventListener);
  }
  source.onerror = () => {
    if (!finished && source.readyState === EventSource.CLOSED) onError();
  };
  return () => source.close();
}
