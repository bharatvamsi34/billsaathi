// Turns the API's event stream into what the screen shows. Pure, so it is unit-tested.

export type Verdict = "SAFE" | "CAUTION" | "SCAM";

export interface EvidenceItem {
  evidence_id: string;
  code: string;
  summary: string;
  detail?: Record<string, unknown>; // real values for the screen, masked by the API
}

export interface BillerRecord {
  name?: string;
  domains?: string[];
  vpas?: string[];
  phones?: string[];
  amount?: number;
  due_date?: string | null;
}

export interface CheckRow {
  seq: number;
  origin: "mandatory" | "agent";
  tool: string;
  args: Record<string, unknown>; // already masked by the API
  ok: boolean;
  error: string | null;
  evidence: EvidenceItem[];
  record: BillerRecord | null;
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
  floor: Verdict | null;
}

export interface Box {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  w: number;
  h: number;
}

export interface JudgeReason {
  reason: string;
  supported: boolean;
  why: string;
  evidence_ids: string[];
}

export interface Timeline {
  received: boolean;
  input: string | null;
  privacy: boolean;
  times: Partial<Record<string, number>>; // when each event type last happened, by the server's clock (ms)
  skew: number; // browser clock minus server clock, so a running timer can tick on the server's clock
  heard: string | null;
  early: "scam_signals" | "checking" | null;
  isolated: { box: Box | null; cropped: boolean } | null;
  extracted: Extracted | null;
  checks: CheckRow[];
  agentTurns: { turn: number; tool_calls: string[] }[];
  judge: { accepted: boolean; reasons: JudgeReason[] }[];
  refusals: { rule: string; message: string }[];
  question: { field: string; question: string } | null;
  verdict: VerdictView | null;
  explanation: { text: string; source: string; language?: string } | null;
  totalMs: number | null;
  lastSeq: number;
  done: boolean;
}

export const emptyTimeline: Timeline = {
  received: false,
  input: null,
  privacy: false,
  times: {},
  skew: 0,
  heard: null,
  early: null,
  isolated: null,
  extracted: null,
  checks: [],
  agentTurns: [],
  judge: [],
  refusals: [],
  question: null,
  verdict: null,
  explanation: null,
  totalMs: null,
  lastSeq: -1,
  done: false,
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type ApiEvent = { seq: number; type: string } & Record<string, any>;

/**
 * Step times come from the server's stamp, not from when the browser received the event: a
 * proxy can deliver several events at once, which made finished steps show 0.0 s.
 */
function stamp(state: Timeline, e: ApiEvent): Pick<Timeline, "times" | "skew"> {
  const at = typeof e.at === "string" ? Date.parse(e.at) : NaN;
  const when = Number.isNaN(at) ? e.receivedAt : at;
  if (when == null) return { times: state.times, skew: state.skew };
  const firstStamp = Object.keys(state.times).length === 0;
  return {
    times: { ...state.times, [e.type]: when },
    skew: firstStamp && e.receivedAt != null ? e.receivedAt - when : state.skew,
  };
}

export function reduce(state: Timeline, e: ApiEvent): Timeline {
  if (e.seq <= state.lastSeq) return state; // duplicates after a reconnect
  const next = { ...state, lastSeq: e.seq, ...stamp(state, e) };
  switch (e.type) {
    case "received":
      return { ...next, received: true, input: e.input ?? null, privacy: !!e.privacy };
    case "transcribed":
      return { ...next, heard: e.text };
    case "isolated":
      return { ...next, isolated: { box: e.box, cropped: e.cropped } };
    case "extracted":
      return { ...next, extracted: e.fields };
    case "check":
      return {
        ...next,
        checks: [
          ...state.checks,
          { seq: e.seq, origin: e.origin, tool: e.tool, args: e.args ?? {}, ok: e.ok, error: e.error, evidence: e.evidence, record: e.record ?? null },
        ],
      };
    case "early":
      return { ...next, early: e.signal };
    case "agent_turn":
      return { ...next, agentTurns: [...state.agentTurns, { turn: e.turn, tool_calls: e.tool_calls }] };
    case "judge":
      return { ...next, judge: [...state.judge, { accepted: e.accepted, reasons: e.reasons ?? [] }] };
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
        verdict: { verdict: e.verdict, reasons: e.reasons, facts: e.facts, forced: e.forced, forced_reason: e.forced_reason, floor: e.floor ?? null },
      };
    case "explanation":
      return { ...next, explanation: { text: e.text, source: e.source, language: e.language } };
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

export const money = (n: number) => `₹${n.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

/** The biller's record found in this check, if any. */
export function billerRecord(state: Timeline): BillerRecord | null {
  return state.checks.find((c) => c.tool === "lookup_biller" && c.record)?.record ?? null;
}

/** Time spent waiting for the user's answer: it is not the agent's time. */
export function waitMs(state: Timeline): number {
  const { question, answer } = state.times;
  return question != null && answer != null ? Math.max(answer - question, 0) : 0;
}

/** The agent has submitted a verdict and no check has answered it yet. */
export function judgePending(state: Timeline): boolean {
  const submitted = state.agentTurns.filter((turn) => turn.tool_calls.includes("submit_verdict")).length;
  return !state.verdict && submitted > Math.max(state.judge.length, state.refusals.length);
}

/** Models actually used in this run, for the trace footer. */
export function modelsUsed(state: Timeline, warningCard: boolean): string[] {
  if (state.privacy) return ["Muse Spark Open"];
  const used: string[] = [];
  if (state.input === "audio") used.push("Muse Voice Transcribe");
  if (state.isolated) used.push("SAM 3.1");
  used.push("Muse Spark 1.3");
  if (warningCard) used.push("Muse Image");
  return used;
}
