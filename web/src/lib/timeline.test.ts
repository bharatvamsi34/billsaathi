import { describe, expect, it } from "vitest";
import { emptyTimeline, evidenceIndex, reduce, type ApiEvent, type Timeline } from "./timeline";

const ev = (seq: number, type: string, extra: Record<string, unknown> = {}): ApiEvent => ({ seq, type, ...extra });

const check = (seq: number, origin: string, tool: string, code: string, id: string) =>
  ev(seq, "check", {
    origin,
    tool,
    ok: true,
    error: null,
    args: { value: "demopower.example" },
    evidence: [{ evidence_id: id, code, summary: "s" }],
  });

const run = (events: ApiEvent[], start: Timeline = emptyTimeline) => events.reduce(reduce, start);

describe("timeline", () => {
  it("follows a check from upload to verdict", () => {
    const tl = run([
      ev(0, "received", { input: "image" }),
      ev(1, "extracted", { fields: { biller_name: { value: "Demo Power", confidence: 0.95 } } }),
      ev(2, "verification_started"),
      check(3, "mandatory", "lookup_biller", "BILLER_VERIFIED", "ev_a"),
      check(4, "mandatory", "check_payment_destination", "LOOKALIKE_DOMAIN", "ev_b"),
      ev(5, "agent_turn", { turn: 1, tool_calls: ["submit_verdict"] }),
      ev(6, "judge", { accepted: true }),
      ev(7, "verdict", { verdict: "SCAM", reasons: [{ text: "Fake site.", evidence_ids: ["ev_b"] }], facts: [], forced: false, forced_reason: null }),
      ev(8, "complete", { timings_ms: { total: 12400 } }),
    ]);
    expect(tl.received).toBe(true);
    expect(tl.extracted?.biller_name.value).toBe("Demo Power");
    expect(tl.checks.map((c) => [c.origin, c.tool])).toEqual([
      ["mandatory", "lookup_biller"],
      ["mandatory", "check_payment_destination"],
    ]);
    expect(tl.checks[1].args.value).toBe("demopower.example");
    expect(tl.verdict?.verdict).toBe("SCAM");
    expect(tl.totalMs).toBe(12400);
    expect(tl.done).toBe(true);
    expect(evidenceIndex(tl).get("ev_b")).toMatchObject({ code: "LOOKALIKE_DOMAIN", seq: 4 });
  });

  it("ignores events already seen after a reconnect", () => {
    const once = run([check(3, "mandatory", "lookup_biller", "BILLER_VERIFIED", "ev_a")]);
    const twice = run([check(3, "mandatory", "lookup_biller", "BILLER_VERIFIED", "ev_a")], once);
    expect(twice.checks).toHaveLength(1);
  });

  it("shows the agent's question until it is answered", () => {
    const asked = run([ev(5, "agent_turn", { turn: 1, tool_calls: ["ask_user"] }), ev(6, "question", { field: "consumer_number", question: "Consumer number?" })]);
    expect(asked.question?.field).toBe("consumer_number");
    const answered = run([ev(7, "answer", { field: "consumer_number", answered: true })], asked);
    expect(answered.question).toBeNull();
  });

  it("keeps refusals and judge results in order", () => {
    const tl = run([
      ev(5, "judge", { accepted: false }),
      ev(6, "refusal", { rule: "claims_check", message: "Reason 1 says tonight." }),
      ev(7, "judge", { accepted: true }),
    ]);
    expect(tl.judge.map((j) => j.accepted)).toEqual([false, true]);
    expect(tl.refusals[0].rule).toBe("claims_check");
  });
});
