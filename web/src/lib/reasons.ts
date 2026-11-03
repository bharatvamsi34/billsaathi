// "Why": sentences with the real values from the evidence, never a restatement of the badge.
// Amounts, links and UPI IDs come from this run's evidence; consumer and phone numbers are masked
// by the API before they get here.
import { codeLabel, type Tone } from "./codes";
import type { Lang } from "./i18n";
import { evidenceIndex, money, type CheckRow, type EvidenceItem, type Timeline } from "./timeline";

export interface ReasonLine {
  id: string;
  seq: number;
  code: string;
  tone: Tone;
  text: string;
}

type Vars = { v: string; other: string; says: string; record: string; usual: string; ratio: string; name: string };
type Template = Record<Lang, (x: Vars) => string>;

const TEMPLATES: Record<string, Template> = {
  KNOWN_SCAM_DESTINATION: {
    en: (x) => `“${x.v}” is on the known-scam list`,
    te: (x) => `“${x.v}” తెలిసిన మోసాల జాబితాలో ఉంది`,
    hi: (x) => `“${x.v}” ज्ञात धोखाधड़ी सूची में है`,
  },
  LOOKALIKE_VPA: {
    en: (x) => `UPI ID “${x.v}” imitates the official “${x.other}”`,
    te: (x) => `UPI ID “${x.v}” అధికారిక “${x.other}” ను అనుకరిస్తోంది`,
    hi: (x) => `UPI ID “${x.v}” आधिकारिक “${x.other}” की नकल करती है`,
  },
  LOOKALIKE_DOMAIN: {
    en: (x) => `Website “${x.v}” imitates the official “${x.other}”`,
    te: (x) => `వెబ్‌సైట్ “${x.v}” అధికారిక “${x.other}” ను అనుకరిస్తోంది`,
    hi: (x) => `वेबसाइट “${x.v}” आधिकारिक “${x.other}” की नकल करती है`,
  },
  APK_LINK: {
    en: (x) => `Link “${x.v}” installs an app file (.apk)`,
    te: (x) => `లింక్ “${x.v}” యాప్ ఫైల్ (.apk) ఇన్‌స్టాల్ చేయిస్తుంది`,
    hi: (x) => `लिंक “${x.v}” ऐप फ़ाइल (.apk) इंस्टॉल कराता है`,
  },
  SHORT_URL: {
    en: (x) => `Link “${x.v}” hides where it goes behind a link shortener`,
    te: (x) => `లింక్ “${x.v}” అసలు చిరునామాను షార్ట్ లింక్ వెనుక దాచింది`,
    hi: (x) => `लिंक “${x.v}” असली पता छोटे लिंक के पीछे छिपाता है`,
  },
  PERSONAL_PHONE_NUMBER: {
    en: (x) => `Number “${x.v}” is a personal mobile, not the biller's`,
    te: (x) => `నంబర్ “${x.v}” వ్యక్తిగత మొబైల్, బిల్లర్‌ది కాదు`,
    hi: (x) => `नंबर “${x.v}” निजी मोबाइल है, बिलर का नहीं`,
  },
  DESTINATION_NOT_OFFICIAL: {
    en: (x) => `“${x.v}” is not an official payment channel`,
    te: (x) => `“${x.v}” అధికారిక చెల్లింపు మార్గం కాదు`,
    hi: (x) => `“${x.v}” आधिकारिक भुगतान माध्यम नहीं है`,
  },
  DESTINATION_OFFICIAL: {
    en: (x) => `“${x.v}” is an official channel of this biller`,
    te: (x) => `“${x.v}” ఈ బిల్లర్ అధికారిక మార్గం`,
    hi: (x) => `“${x.v}” इस बिलर का आधिकारिक माध्यम है`,
  },
  AMOUNT_MISMATCH: {
    en: (x) => `${x.says} · biller record says ${x.record}`,
    te: (x) => `${x.says} · బిల్లర్ రికార్డు ప్రకారం ${x.record}`,
    hi: (x) => `${x.says} · बिलर के रिकॉर्ड में ${x.record}`,
  },
  AMOUNT_MATCHES_BILLER: {
    en: (x) => `${x.record} matches the biller record`,
    te: (x) => `${x.record} బిల్లర్ రికార్డుతో సరిపోతోంది`,
    hi: (x) => `${x.record} बिलर के रिकॉर्ड से मेल खाती है`,
  },
  AMOUNT_SPIKE: {
    en: (x) => `${x.says} is ${x.ratio}× this account's usual ${x.usual}`,
    te: (x) => `${x.says} ఈ ఖాతా సాధారణ మొత్తం ${x.usual} కు ${x.ratio} రెట్లు`,
    hi: (x) => `${x.says} इस खाते की सामान्य राशि ${x.usual} का ${x.ratio} गुना है`,
  },
  AMOUNT_WITHIN_HISTORY: {
    en: (x) => `${x.says} is normal for this account (usually ${x.usual})`,
    te: (x) => `${x.says} ఈ ఖాతాకు సాధారణమే (సాధారణంగా ${x.usual})`,
    hi: (x) => `${x.says} इस खाते के लिए सामान्य है (आमतौर पर ${x.usual})`,
  },
  UNKNOWN_BILLER: {
    en: (x) => (x.name ? `“${x.name}” is not in the biller registry` : "No biller name that the registry knows"),
    te: (x) => (x.name ? `“${x.name}” బిల్లర్ రిజిస్ట్రీలో లేదు` : "రిజిస్ట్రీకి తెలిసిన బిల్లర్ పేరు లేదు"),
    hi: (x) => (x.name ? `“${x.name}” बिलर रजिस्ट्री में नहीं है` : "रजिस्ट्री में मौजूद बिलर का नाम नहीं मिला"),
  },
  BILLER_VERIFIED: {
    en: (x) => `“${x.name}” is in the demo biller registry`,
    te: (x) => `“${x.name}” డెమో బిల్లర్ రిజిస్ట్రీలో ఉంది`,
    hi: (x) => `“${x.name}” डेमो बिलर रजिस्ट्री में है`,
  },
  PHRASE: {
    en: (x) => `Phrase: “…${x.v}…”`,
    te: (x) => `పదబంధం: “…${x.v}…”`,
    hi: (x) => `वाक्यांश: “…${x.v}…”`,
  },
};

// Most telling first: the top two are always shown.
const ORDER = [
  "KNOWN_SCAM_DESTINATION",
  "LOOKALIKE_VPA",
  "LOOKALIKE_DOMAIN",
  "APK_LINK",
  "AMOUNT_MISMATCH",
  "PERSONAL_PHONE_NUMBER",
  "SHORT_URL",
  "DISCONNECTION_THREAT",
  "KYC_UPDATE_LURE",
  "REFUND_LURE",
  "DESTINATION_NOT_OFFICIAL",
  "UNKNOWN_BILLER",
  "CONSUMER_NOT_FOUND",
  "AMOUNT_SPIKE",
  "URGENCY_PRESSURE",
  "MISSED_BY_EXTRACTION",
  "AMOUNT_MATCHES_BILLER",
  "DESTINATION_OFFICIAL",
  "BILLER_VERIFIED",
  "AMOUNT_WITHIN_HISTORY",
];

const SAYS: Record<"bill" | "message", Record<Lang, (a: string) => string>> = {
  bill: { en: (a) => `Bill says ${a}`, te: (a) => `బిల్లులో ${a}`, hi: (a) => `बिल में ${a}` },
  message: { en: (a) => `Message says ${a}`, te: (a) => `సందేశంలో ${a}`, hi: (a) => `संदेश में ${a}` },
};

const num = (v: unknown) => (typeof v === "number" ? money(v) : "");

function sentence(ev: EvidenceItem, row: CheckRow | undefined, lang: Lang, kind: "bill" | "message", biller: string): string {
  const d = ev.detail ?? {};
  const v = String(row?.args.value ?? d.vpa ?? d.host ?? d.phone_masked ?? "");
  const phrases = Array.isArray(d.phrases) ? (d.phrases as string[]) : [];
  if (phrases.length) return TEMPLATES.PHRASE[lang]({ v: phrases[0] } as Vars);
  const template = TEMPLATES[ev.code];
  // A number spoken as words has no masked value to quote.
  if (!template || (v === "-" && !d.vpa && !d.host)) return codeLabel(ev.code, lang).text;
  const claimed = num(d.claimed_amount ?? d.current_amount);
  const text = template[lang]({
    v,
    other: String(d.lookalike_of ?? ""),
    says: ev.code === "AMOUNT_MISMATCH" ? SAYS[kind][lang](claimed) : claimed,
    record: num(d.biller_amount),
    usual: num(d.usual_amount),
    ratio: typeof d.ratio === "number" ? d.ratio.toFixed(1) : "",
    name: String(d.query ?? biller ?? ""),
  });
  return text;
}

/** The evidence the verdict cites, as sentences, most telling first. */
export function reasonLines(tl: Timeline, lang: Lang): ReasonLine[] {
  const index = evidenceIndex(tl);
  const rows = new Map(tl.checks.map((c) => [c.seq, c]));
  const cited = new Set((tl.verdict?.reasons ?? []).flatMap((r) => r.evidence_ids));
  let items = [...index.values()].filter((e) => cited.has(e.evidence_id));
  // A forced verdict may cite nothing; the risky findings are still worth showing.
  if (!items.length) items = [...index.values()].filter((e) => ["bad", "warn"].includes(codeLabel(e.code, lang).tone));
  const rank = (code: string) => {
    const i = ORDER.indexOf(code);
    return i < 0 ? ORDER.length : i;
  };
  const kind = tl.input === "image" ? "bill" : "message";
  const biller = tl.extracted?.biller_name.value ?? "";
  const seen = new Set<string>();
  return items
    .sort((a, b) => rank(a.code) - rank(b.code))
    .map((e) => ({ id: e.evidence_id, seq: e.seq, code: e.code, tone: codeLabel(e.code, lang).tone, text: sentence(e, rows.get(e.seq), lang, kind, biller) }))
    .filter((line) => !seen.has(line.text) && !!seen.add(line.text));
}
