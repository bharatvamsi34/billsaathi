import { describe, expect, it } from "vitest";
import { compareRows } from "./compare";
import { highlight } from "./highlight";
import { reasonLines } from "./reasons";
import { emptyTimeline, modelsUsed, reduce, type ApiEvent, type Timeline } from "./timeline";

const fields = (over: Record<string, unknown> = {}) => ({
  biller_name: { value: "Demo Power Distribution Co. Ltd", confidence: 0.95 },
  amount: { value: 4240, confidence: 0.95 },
  due_date: { value: "2026-11-05", confidence: 0.95 },
  consumer_number: { value: "**********2761", confidence: 0.95 },
  payment_destinations: { value: [], confidence: 0.95 },
  ...over,
});

const check = (seq: number, tool: string, evidence: object[], extra: object = {}) => ({ seq, type: "check", origin: "mandatory", tool, ok: true, error: null, args: {}, evidence, record: null, ...extra });

const run = (events: object[]): Timeline => (events as ApiEvent[]).reduce(reduce, emptyTimeline);

const tampered = run([
  { seq: 0, type: "received", input: "image" },
  { seq: 1, type: "extracted", fields: fields() },
  check(2, "lookup_biller", [{ evidence_id: "ev_b", code: "BILLER_VERIFIED", summary: "s", detail: {} }], { record: { name: "Demo Power Distribution Co. Ltd", vpas: ["demopower.bill@demobank"], domains: ["demopower.example"], phones: [] } }),
  check(3, "check_payment_destination", [{ evidence_id: "ev_d", code: "DESTINATION_OFFICIAL", summary: "s", detail: {} }], { args: { kind: "upi", value: "demopower.bill@demobank" } }),
  check(4, "fetch_bill", [{ evidence_id: "ev_a", code: "AMOUNT_MISMATCH", summary: "s", detail: { biller_amount: 1240, claimed_amount: 4240 } }], { record: { amount: 1240 }, args: { consumer_number: "**********2761" } }),
  { seq: 5, type: "verdict", verdict: "CAUTION", reasons: [{ text: "x", evidence_ids: ["ev_a", "ev_d"] }], facts: [], forced: false, forced_reason: null },
]);

const scam = run([
  { seq: 0, type: "received", input: "text" },
  { seq: 1, type: "extracted", fields: fields({ biller_name: { value: "Electricity Office", confidence: 0.9 }, amount: { value: 3150, confidence: 0.9 }, consumer_number: { value: null, confidence: 0 } }) },
  check(2, "lookup_biller", [{ evidence_id: "ev_u", code: "UNKNOWN_BILLER", summary: "s", detail: { query: "Electricity Office" } }]),
  check(3, "check_payment_destination", [{ evidence_id: "ev_k", code: "KNOWN_SCAM_DESTINATION", summary: "s", detail: { vpa: "electricityofficer@okdemo" } }], { args: { kind: "upi", value: "electricityofficer@okdemo" } }),
  check(4, "match_scam_patterns", [{ evidence_id: "ev_p", code: "DISCONNECTION_THREAT", summary: "s", detail: { phrases: ["power supply will be cut"] } }]),
  { seq: 5, type: "verdict", verdict: "SCAM", reasons: [{ text: "x", evidence_ids: ["ev_u", "ev_k", "ev_p"] }], facts: [], forced: false, forced_reason: null, floor: "SCAM" },
]);

describe("comparison", () => {
  it("a tampered bill differs in exactly one value", () => {
    const rows = compareRows(tampered);
    expect(rows.filter((r) => r.status === "mismatch").map((r) => r.key)).toEqual(["amount"]);
    const amount = rows.find((r) => r.key === "amount")!;
    expect([amount.says, amount.record]).toEqual(["₹4,240.00", "₹1,240.00"]);
    expect(rows.find((r) => r.key === "consumer")?.says).toBe("**********2761");
  });

  it("an unknown biller shows no record instead of inventing one", () => {
    const rows = compareRows(scam);
    expect(rows.find((r) => r.key === "biller")).toMatchObject({ status: "noRecord", record: null });
    expect(rows.find((r) => r.key === "amount")).toMatchObject({ status: "noRecord", record: null });
    expect(rows.find((r) => r.key === "destination")).toMatchObject({ status: "noRecord", flag: "KNOWN_SCAM_DESTINATION" });
    expect(rows.some((r) => r.key === "consumer")).toBe(false);
  });

  it("is empty when nothing was read", () => {
    expect(compareRows(emptyTimeline)).toEqual([]);
  });
});

describe("why", () => {
  it("quotes real values, most telling first", () => {
    const lines = reasonLines(scam, "en");
    expect(lines[0].text).toBe("“electricityofficer@okdemo” is on the known-scam list");
    expect(lines[1].text).toBe("Phrase: “…power supply will be cut…”");
    expect(lines.map((l) => l.text)).toContain("“Electricity Office” is not in the biller registry");
  });

  it("gives both amounts for a mismatch", () => {
    expect(reasonLines(tampered, "en")[0].text).toBe("Bill says ₹4,240.00 · biller record says ₹1,240.00");
    expect(reasonLines(tampered, "te")[0].text).toContain("₹1,240.00");
    expect(reasonLines(tampered, "hi")[0].text).toContain("₹4,240.00");
  });
});

describe("highlighting", () => {
  it("never changes the text and marks by what the checks found", () => {
    const text = "Pending bill Rs 3,150. Pay to UPI electricityofficer@okdemo or your power supply will be cut.";
    const spans = highlight(text, scam);
    expect(spans.map((s) => s.text).join("")).toBe(text);
    const mark = (t: string) => spans.find((s) => s.text === t)?.mark;
    expect(mark("electricityofficer@okdemo")).toBe("risky");
    expect(mark("power supply will be cut")).toBe("risky");
    expect(mark("Rs 3,150")).toBe("unverified");
  });

  it("matches a masked phone by the digits it keeps", () => {
    const tl = run([check(0, "check_payment_destination", [{ evidence_id: "e", code: "PERSONAL_PHONE_NUMBER", summary: "s" }], { args: { kind: "phone", value: "90******03" } })]);
    expect(highlight("Call 9000000003 now", tl).find((s) => s.mark)).toMatchObject({ text: "9000000003", mark: "risky" });
  });
});

describe("step times", () => {
  it("use the server's stamps, so events delivered together keep their real duration", () => {
    const tl = run([
      { seq: 0, type: "early", signal: "checking", at: "2026-11-04T00:00:01.000Z", receivedAt: 5000 },
      { seq: 1, type: "agent_turn", turn: 1, tool_calls: [], at: "2026-11-04T00:00:06.500Z", receivedAt: 5000 },
    ]);
    expect(tl.times.agent_turn! - tl.times.early!).toBe(5500);
  });
});

describe("models used", () => {
  it("lists only what ran in this check", () => {
    expect(modelsUsed(scam, true)).toEqual(["Muse Spark 1.3", "Muse Image"]);
    expect(modelsUsed({ ...tampered, isolated: { box: null, cropped: false } }, false)).toEqual(["SAM 3.1", "Muse Spark 1.3"]);
    expect(modelsUsed({ ...scam, privacy: true }, true)).toEqual(["Muse Spark Open"]);
  });
});
