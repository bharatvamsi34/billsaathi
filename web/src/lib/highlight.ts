// Finds the money, links, UPI IDs and phone numbers in the message under review, and colours each
// by what the checks found: red if risky, amber if unverified, green if the checks confirmed it.
import type { Timeline } from "./timeline";

export type Mark = "risky" | "unverified" | "ok";
export interface Span {
  text: string;
  mark: Mark | null;
}

const ENTITY =
  /(?:₹|Rs\.?\s?|INR\s?)\d[\d,]*(?:\.\d+)?|[A-Za-z0-9._-]+@[A-Za-z0-9]+|(?:https?:\/\/)?[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.(?:example|com|in|org|net|co|ly|me|info|xyz)(?:\/[^\s,]*)?|(?<![\d-])(?:\+?91[\s-]?)?[6-9]\d{9}(?![\d-])/gi;

const RISKY = new Set(["KNOWN_SCAM_DESTINATION", "LOOKALIKE_VPA", "LOOKALIKE_DOMAIN", "APK_LINK", "SHORT_URL", "PERSONAL_PHONE_NUMBER", "DESTINATION_NOT_OFFICIAL"]);

const digits = (s: string) => s.replace(/\D/g, "");

function sameDestination(token: string, value: string): boolean {
  if (value.includes("*")) {
    // A masked phone: compare the digits the mask keeps, and the length.
    const a = digits(token).slice(-10);
    return a.length === value.replace(/[^\d*]/g, "").length && a.slice(0, 2) === value.slice(0, 2) && a.slice(-2) === value.slice(-2);
  }
  const clean = (s: string) => s.toLowerCase().replace(/^https?:\/\//, "").replace(/[/.]+$/, "");
  return clean(token) === clean(value) || clean(token).startsWith(`${clean(value)}/`);
}

function classify(token: string, tl: Timeline): Mark {
  if (/^(?:₹|Rs|INR)/i.test(token)) {
    const codes = tl.checks.filter((c) => c.tool === "fetch_bill").flatMap((c) => c.evidence.map((e) => e.code));
    if (codes.includes("AMOUNT_MISMATCH")) return "risky";
    return codes.includes("AMOUNT_MATCHES_BILLER") ? "ok" : "unverified";
  }
  const row = tl.checks.find((c) => c.tool === "check_payment_destination" && typeof c.args.value === "string" && sameDestination(token, c.args.value));
  if (!row) return "unverified";
  const codes = row.evidence.map((e) => e.code);
  if (codes.some((c) => RISKY.has(c))) return "risky";
  return codes.includes("DESTINATION_OFFICIAL") ? "ok" : "unverified";
}

/** The message split into plain text and marked pieces. The text itself is never changed. */
export function highlight(text: string, tl: Timeline): Span[] {
  const phrases = tl.checks
    .filter((c) => c.tool === "match_scam_patterns")
    .flatMap((c) => c.evidence.flatMap((e) => (Array.isArray(e.detail?.phrases) ? (e.detail.phrases as string[]) : [])))
    .filter((p) => p && text.includes(p));
  const hits: { start: number; end: number; mark: Mark }[] = [];
  for (const m of text.matchAll(ENTITY)) hits.push({ start: m.index, end: m.index + m[0].length, mark: classify(m[0], tl) });
  for (const p of phrases) {
    const start = text.indexOf(p);
    hits.push({ start, end: start + p.length, mark: "risky" });
  }
  hits.sort((a, b) => a.start - b.start);
  const spans: Span[] = [];
  let at = 0;
  for (const hit of hits) {
    if (hit.start < at) continue; // overlaps a piece already marked
    if (hit.start > at) spans.push({ text: text.slice(at, hit.start), mark: null });
    spans.push({ text: text.slice(hit.start, hit.end), mark: hit.mark });
    at = hit.end;
  }
  if (at < text.length) spans.push({ text: text.slice(at), mark: null });
  return spans;
}
