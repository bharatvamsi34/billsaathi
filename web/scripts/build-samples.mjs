// Builds the "Try a sample" gallery and the judge-catch replay.
// Dataset samples must be DEV-split items: test-split items are held out for evaluation.
// Demo-only samples come from data/generators/make_demo_samples.py and are in no split.
// Run: npm run samples (also runs before every build).
import { copyFileSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..", "..");
const data = join(root, "data", "synthetic");
const outImages = join(here, "..", "public", "samples");
const outJson = join(here, "..", "src", "samples.generated.json");
const outReplay = join(here, "..", "src", "replay.generated.json");

// Order = order in the gallery. Titles are shown in the user's language.
const SAMPLES = [
  {
    id: "scam_en_known_vpa",
    title: { en: "Scam SMS: “pay now or power cut”", te: "మోసం SMS: “ఇప్పుడే చెల్లించండి, లేకపోతే కరెంట్ కట్” (ఇంగ్లీష్)", hi: "धोखे का SMS: “अभी भुगतान करें, वरना बिजली कटेगी” (अंग्रेज़ी)" },
  },
  {
    id: "demo_tampered_same_account",
    demo: { kind: "image", src: "/samples/demo_tampered_same_account.jpg", language: "en" },
    title: { en: "Tampered bill: one amount changed", te: "మార్చిన బిల్లు: ఒక్క మొత్తం మారింది", hi: "बदला हुआ बिल: सिर्फ़ राशि बदली" },
  },
  {
    id: "photo_genuine_demo",
    title: { en: "Genuine demo bill: same account", te: "నిజమైన డెమో బిల్లు: అదే ఖాతా, ఫోన్ ఫోటో", hi: "असली डेमो बिल: वही खाता, फ़ोन फ़ोटो" },
  },
  {
    id: "demo_voice_note",
    demo: { kind: "audio", src: "/samples/demo_voice_note.wav", language: "en" },
    title: { en: "Voice note: power-cut threat (synthetic English voice)", te: "వాయిస్ నోట్: కరెంట్ కట్ బెదిరింపు (సింథటిక్ ఇంగ్లీష్ వాయిస్)", hi: "वॉइस नोट: बिजली कटने की धमकी (सिंथेटिक अंग्रेज़ी आवाज़)" },
  },
  {
    id: "scam_te_known_vpa",
    title: { en: "Telugu SMS: “pay now or power cut”", te: "తెలుగు SMS: “ఇప్పుడే చెల్లించండి, లేకపోతే కరెంట్ కట్”", hi: "तेलुगु SMS: “अभी भुगतान करें, वरना बिजली कटेगी”" },
  },
  {
    id: "scam_hi_kyc_apk",
    title: { en: "Hindi WhatsApp: “update KYC, install app”", te: "హిందీ WhatsApp: “KYC అప్‌డేట్ చేయండి, యాప్ ఇన్‌స్టాల్ చేయండి”", hi: "हिंदी WhatsApp: “KYC अपडेट करें, ऐप डाउनलोड करें”" },
  },
  {
    id: "bill_swapped_vpa_dgas",
    title: { en: "Gas bill with a different UPI ID", te: "వేరే UPI ID ఉన్న గ్యాస్ బిల్లు", hi: "अलग UPI ID वाला गैस बिल" },
  },
  {
    id: "demo_missing_account",
    demo: { kind: "text", language: "en", text: "SkyDemo: Your DTH recharge of Rs 599 is due on 01-Nov-2026. Recharge at skydemo.example/pay or UPI skydemo.recharge@demobank." },
    title: { en: "No account number: the agent may ask you", te: "ఖాతా సంఖ్య లేని గుర్తుచేత: ఏజెంట్ మిమ్మల్ని అడగవచ్చు", hi: "बिना खाता संख्या की याद-दिहानी: एजेंट आपसे पूछ सकता है" },
  },
];

const labels = new Map(
  readFileSync(join(data, "labels.jsonl"), "utf8")
    .split("\n")
    .filter((line) => line.trim())
    .map((line) => JSON.parse(line))
    .map((label) => [label.id, label]),
);

mkdirSync(outImages, { recursive: true });
const out = SAMPLES.map(({ id, title, demo }) => {
  if (demo) {
    if (labels.has(id)) throw new Error(`demo sample ${id} must not be in labels.jsonl`);
    return { id, title, ...demo, demoOnly: true };
  }
  const label = labels.get(id);
  if (!label) throw new Error(`sample ${id} is not in labels.jsonl`);
  if (label.split !== "dev") throw new Error(`sample ${id} is in the ${label.split} split; only dev items may be samples`);
  const sample = { id, title, language: label.expected.extracted.languages[0] };
  if (label.input.kind === "image") {
    const file = label.input.path.split("/").pop();
    copyFileSync(join(data, label.input.path), join(outImages, file));
    return { ...sample, kind: "image", src: `/samples/${file}` };
  }
  return { ...sample, kind: "text", text: label.input.text };
});
writeFileSync(outJson, JSON.stringify(out, null, 2) + "\n");
console.log(`wrote ${out.length} samples`);

// The judge-catch replay: copied from a real recorded run, never written by hand.
const REPLAY_FILE = "eval/results/agent_live_2026-10-29_2355.jsonl";
const run = readFileSync(join(root, REPLAY_FILE), "utf8")
  .split("\n")
  .filter((line) => line.trim())
  .map((line) => JSON.parse(line))
  .find((r) => r.id === "scam_te_known_vpa" && r.refusals?.includes("claims_check"));
if (!run) throw new Error("the recorded judge refusal is missing");
const replay = {
  file: REPLAY_FILE,
  date: "2026-10-29",
  id: run.id,
  verdict: run.got,
  message: labels.get(run.id).input.text,
  attempts: run.judge.map((j) => ({
    accepted: j.accepted,
    reasons: j.reasons.map((r) => ({ reason: r.reason, supported: r.supported, why: r.why })),
  })),
};
writeFileSync(outReplay, JSON.stringify(replay, null, 2) + "\n");
console.log(`wrote the replay of ${run.id}`);
