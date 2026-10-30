// Turns the API's event stream into what the screen shows. Pure, so it is unit-tested.

export type Verdict = "SAFE" | "CAUTION" | "SCAM";

export interface EvidenceItem {
  evidence_id: string;
  code: string;
  summary: string;
}

export interface CheckRow {
  seq: number;
  origin: "mandatory" | "agent";
  tool: string;
  args: Record<string, unknown>; // already masked by the API
  ok: boolean;
  error: string | null;
  evidence: EvidenceItem[];
}

export interface Field<T> {
  value: T;
  confidence: number;
}

export interface Extracted {
  biller_name: Field<string | null>;
  amount: Field<number | null>;
  due_date: Field<string | null>;
  consumer_number: Field<string | null>;
  payment_destinations: Field<{ kind: string; value: string }[]>;
}

export interface VerdictView {
  verdict: Verdict;
  reasons: { text: string; evidence_ids: string[] }[];
  facts: { key: string; label: string; value: string; source: string }[];
  forced: boolean;
  forced_reason: string | null;
}

export interface Timeline {
  received: boolean;
  extracted: Extracted | null;
  checks: CheckRow[];
  agentTurns: { turn: number; tool_calls: string[] }[];
  judge: { accepted: boolean }[];
  refusals: { rule: string; message: string }[];
  question: { field: string; question: string } | null;
  verdict: VerdictView | null;
  totalMs: number | null;
  lastSeq: number;
  done: boolean;
}

export const emptyTimeline: Timeline = {
  received: false,
  extracted: null,
  checks: [],
  agentTurns: [],
  judge: [],
  refusals: [],
  question: null,
  verdict: null,
  totalMs: null,
  lastSeq: -1,
  done: false,
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type ApiEvent = { seq: number; type: string } & Record<string, any>;

export function reduce(state: Timeline, e: ApiEvent): Timeline {
  if (e.seq <= state.lastSeq) return state; // duplicates after a reconnect
  const next = { ...state, lastSeq: e.seq };
  switch (e.type) {
    case "received":
      return { ...next, received: true };
    case "extracted":
      return { ...next, extracted: e.fields };
    case "check":
      return {
        ...next,
        checks: [
          ...state.checks,
          { seq: e.seq, origin: e.origin, tool: e.tool, args: e.args ?? {}, ok: e.ok, error: e.error, evidence: e.evidence },
        ],
      };
    case "agent_turn":
      return { ...next, agentTurns: [...state.agentTurns, { turn: e.turn, tool_calls: e.tool_calls }] };
    case "judge":
      return { ...next, judge: [...state.judge, { accepted: e.accepted }] };
    case "refusal":
      return { ...next, refusals: [...state.refusals, { rule: e.rule, message: e.message }] };
    case "question":
      return { ...next, question: { field: e.field, question: e.question } };
    case "answer":
      return { ...next, question: null };
    case "verdict":
      return {
        ...next,
        question: null,
        verdict: { verdict: e.verdict, reasons: e.reasons, facts: e.facts, forced: e.forced, forced_reason: e.forced_reason },
      };
    case "complete":
      return { ...next, done: true, totalMs: e.timings_ms?.total ?? null };
    default:
      return next;
  }
}

/** Evidence by id, for the chips on the verdict card. */
export function evidenceIndex(state: Timeline): Map<string, EvidenceItem & { seq: number }> {
  const index = new Map<string, EvidenceItem & { seq: number }>();
  for (const row of state.checks) for (const ev of row.evidence) index.set(ev.evidence_id, { ...ev, seq: row.seq });
  return index;
}

export function lowConfidence(field: Field<unknown> | undefined): boolean {
  return !!field && field.confidence < 0.8;
}
