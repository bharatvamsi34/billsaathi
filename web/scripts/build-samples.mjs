// Builds the "Try a sample" gallery from the labelled synthetic dataset.
// Only DEV-split items are allowed: test-split items are held out for evaluation.
// Run: npm run samples (also runs before every build).
import { copyFileSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const data = join(here, "..", "..", "data", "synthetic");
const outImages = join(here, "..", "public", "samples");
const outJson = join(here, "..", "src", "samples.generated.json");

// Order = order in the gallery. Titles are shown in the user's language.
const SAMPLES = [
  {
    id: "scam_te_known_vpa",
    title: { en: "Telugu SMS: “pay now or power cut”", te: "తెలుగు SMS: “ఇప్పుడే చెల్లించండి, లేకపోతే కరెంట్ కట్”", hi: "तेलुगु SMS: “अभी भुगतान करें, वरना बिजली कटेगी”" },
  },
  {
    id: "scam_hi_kyc_apk",
    title: { en: "Hindi WhatsApp: “update KYC, install app”", te: "హిందీ WhatsApp: “KYC అప్‌డేట్ చేయండి, యాప్ ఇన్‌స్టాల్ చేయండి”", hi: "हिंदी WhatsApp: “KYC अपडेट करें, ऐप डाउनलोड करें”" },
  },
  {
    id: "bill_tampered_demo",
    title: { en: "Electricity bill with a changed amount", te: "మొత్తం మార్చిన కరెంట్ బిల్లు", hi: "बदली हुई राशि वाला बिजली बिल" },
  },
  {
    id: "bill_swapped_vpa_dgas",
    title: { en: "Gas bill with a different UPI ID", te: "వేరే UPI ID ఉన్న గ్యాస్ బిల్లు", hi: "अलग UPI ID वाला गैस बिल" },
  },
  {
    id: "photo_genuine_demo",
    title: { en: "Phone photo of a real-looking bill", te: "ఫోన్‌తో తీసిన బిల్లు ఫోటో", hi: "फ़ोन से खींची बिल की फ़ोटो" },
  },
  {
    id: "reminder_en_dmob_polite_disconnect",
    title: { en: "Polite reminder from the biller", te: "బిల్లర్ నుండి మర్యాదపూర్వక గుర్తుచేత", hi: "बिलर की ओर से विनम्र याद-दिहानी" },
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
const out = SAMPLES.map(({ id, title }) => {
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
console.log(`wrote ${out.length} dev-split samples`);
