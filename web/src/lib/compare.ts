// The comparison panel: what the message says against what the demo biller's record says.
// Every value comes from the extraction and the tool results of this run; nothing is typed here.
import { billerRecord, money, type BillerRecord, type Timeline } from "./timeline";

export type RowStatus = "match" | "mismatch" | "noRecord" | "notChecked" | "notFound";
export type RowKey = "biller" | "amount" | "destination" | "consumer";

export interface CompareRow {
  key: RowKey;
  kind?: string; // destination rows: upi, url or phone
  says: string | null;
  record: string | null;
  status: RowStatus;
  flag?: string; // the evidence code that makes a destination risky
  entered?: boolean; // the value came from the user's answer, not from the bill or message
}

const BAD_DESTINATION = ["KNOWN_SCAM_DESTINATION", "LOOKALIKE_VPA", "LOOKALIKE_DOMAIN", "APK_LINK", "SHORT_URL", "PERSONAL_PHONE_NUMBER", "DESTINATION_NOT_OFFICIAL"];

function official(record: BillerRecord | null, kind: string): string | null {
  if (!record) return null;
  const list = kind === "upi" ? record.vpas : kind === "phone" ? record.phones : record.domains;
  return list?.[0] ?? null;
}

/** The row that decides the verdict: it gets the big type and the tint. */
export function isDecisive(row: CompareRow): boolean {
  return row.status === "mismatch" || (!!row.flag && row.status !== "match") || (row.key === "consumer" && row.status === "notFound");
}

/** Display order only: what is wrong first, then what could not be verified, then what matches. */
export function orderRows(rows: CompareRow[]): CompareRow[] {
  const rank = (row: CompareRow) => (isDecisive(row) ? 0 : row.status === "match" ? 2 : 1);
  const within = (row: CompareRow) => (row.key === "amount" ? 0 : 1);
  return rows
    .map((row, i) => ({ row, i }))
    .sort((a, b) => rank(a.row) - rank(b.row) || within(a.row) - within(b.row) || a.i - b.i)
    .map(({ row }) => row);
}

export function compareRows(tl: Timeline): CompareRow[] {
  const f = tl.extracted;
  if (!f) return [];
  const rows: CompareRow[] = [];
  const record = billerRecord(tl);
  const lookup = tl.checks.find((c) => c.tool === "lookup_biller");
  const fetch = [...tl.checks].reverse().find((c) => c.tool === "fetch_bill");
  const fetchCodes = new Set(fetch?.evidence.map((e) => e.code));

  rows.push({
    key: "biller",
    says: f.biller_name.value,
    record: record?.name ?? null,
    status: record ? "match" : lookup ? "noRecord" : "notChecked",
  });

  const says = f.amount.value != null ? money(f.amount.value) : null;
  const billed = fetch?.record?.amount;
  if (says || billed != null) {
    let status: RowStatus = record ? "notChecked" : "noRecord";
    if (fetchCodes.has("AMOUNT_MISMATCH")) status = "mismatch";
    else if (fetchCodes.has("AMOUNT_MATCHES_BILLER")) status = "match";
    else if (fetchCodes.has("CONSUMER_NOT_FOUND")) status = "notFound";
    rows.push({ key: "amount", says, record: billed != null ? money(billed) : null, status });
  }

  for (const c of tl.checks) {
    if (c.tool !== "check_payment_destination" || typeof c.args.value !== "string") continue;
    const kind = String(c.args.kind ?? "url");
    const codes = c.evidence.map((e) => e.code);
    if (rows.some((r) => r.key === "destination" && r.says === c.args.value)) continue;
    const isOfficial = codes.includes("DESTINATION_OFFICIAL");
    const expected = official(record, kind);
    rows.push({
      key: "destination",
      kind,
      says: c.args.value === "-" ? null : c.args.value,
      record: isOfficial ? c.args.value : expected,
      status: isOfficial ? "match" : !c.ok ? "notChecked" : expected ? "mismatch" : "noRecord",
      flag: BAD_DESTINATION.find((code) => codes.includes(code)),
    });
  }

  const consumer = f.consumer_number.value ?? (typeof fetch?.args.consumer_number === "string" ? fetch.args.consumer_number : null);
  if (consumer) {
    const found = !!fetch?.record;
    rows.push({
      key: "consumer",
      says: consumer,
      record: found ? consumer : null,
      status: found ? "match" : fetchCodes.has("CONSUMER_NOT_FOUND") ? "notFound" : record ? "notChecked" : "noRecord",
      entered: f.consumer_number.value == null,
    });
  }
  return rows;
}
