// Plain-language labels for evidence codes, and whether each one is good, bad or neutral.
import type { Lang } from "./i18n";

export type Tone = "good" | "bad" | "warn" | "info";

const LABELS: Record<string, { tone: Tone; text: Record<Lang, string> }> = {
  BILLER_VERIFIED: { tone: "good", text: { en: "Registered biller", te: "నమోదైన బిల్లర్", hi: "पंजीकृत बिलर" } },
  UNKNOWN_BILLER: { tone: "bad", text: { en: "Biller not found in the registry", te: "బిల్లర్ రిజిస్ట్రీలో లేరు", hi: "बिलर रजिस्ट्री में नहीं मिला" } },
  AMOUNT_MATCHES_BILLER: { tone: "good", text: { en: "Amount matches the biller's records", te: "మొత్తం బిల్లర్ రికార్డుతో సరిపోతోంది", hi: "राशि बिलर के रिकॉर्ड से मेल खाती है" } },
  AMOUNT_MISMATCH: { tone: "bad", text: { en: "Amount is different from the biller's records", te: "మొత్తం బిల్లర్ రికార్డుకు భిన్నంగా ఉంది", hi: "राशि बिलर के रिकॉर्ड से अलग है" } },
  CONSUMER_NOT_FOUND: { tone: "bad", text: { en: "Consumer number not found", te: "వినియోగదారు సంఖ్య కనబడలేదు", hi: "उपभोक्ता संख्या नहीं मिली" } },
  AMOUNT_WITHIN_HISTORY: { tone: "good", text: { en: "Amount is normal for this account", te: "ఈ ఖాతాకు మొత్తం సాధారణంగా ఉంది", hi: "इस खाते के लिए राशि सामान्य है" } },
  AMOUNT_SPIKE: { tone: "warn", text: { en: "Amount is much higher than usual", te: "మొత్తం సాధారణం కంటే చాలా ఎక్కువ", hi: "राशि सामान्य से बहुत ज़्यादा है" } },
  DESTINATION_OFFICIAL: { tone: "good", text: { en: "Official payment channel", te: "అధికారిక చెల్లింపు మార్గం", hi: "आधिकारिक भुगतान माध्यम" } },
  DESTINATION_NOT_OFFICIAL: { tone: "bad", text: { en: "Not an official payment channel", te: "అధికారిక చెల్లింపు మార్గం కాదు", hi: "आधिकारिक भुगतान माध्यम नहीं" } },
  LOOKALIKE_DOMAIN: { tone: "bad", text: { en: "Fake website that imitates the real one", te: "నిజమైన దాన్ని అనుకరించే నకిలీ వెబ్‌సైట్", hi: "असली जैसी दिखने वाली नकली वेबसाइट" } },
  LOOKALIKE_VPA: { tone: "bad", text: { en: "Fake UPI ID that imitates the real one", te: "నిజమైన దాన్ని అనుకరించే నకిలీ UPI ID", hi: "असली जैसी दिखने वाली नकली UPI ID" } },
  KNOWN_SCAM_DESTINATION: { tone: "bad", text: { en: "On the known-scam list", te: "తెలిసిన మోసాల జాబితాలో ఉంది", hi: "ज्ञात धोखाधड़ी सूची में है" } },
  PERSONAL_PHONE_NUMBER: { tone: "bad", text: { en: "Personal mobile number, not the biller's", te: "వ్యక్తిగత మొబైల్ నంబర్, బిల్లర్‌ది కాదు", hi: "निजी मोबाइल नंबर, बिलर का नहीं" } },
  APK_LINK: { tone: "bad", text: { en: "Asks you to install an app file (.apk)", te: "యాప్ ఫైల్ (.apk) ఇన్‌స్టాల్ చేయమంటోంది", hi: "ऐप फ़ाइल (.apk) डाउनलोड करने को कहता है" } },
  SHORT_URL: { tone: "warn", text: { en: "Link is hidden behind a short link", te: "లింక్ షార్ట్ లింక్ వెనుక దాచబడింది", hi: "लिंक छोटे लिंक के पीछे छिपा है" } },
  DISCONNECTION_THREAT: { tone: "warn", text: { en: "Threatens to cut your connection", te: "కనెక్షన్ కట్ చేస్తామని బెదిరిస్తోంది", hi: "कनेक्शन काटने की धमकी" } },
  KYC_UPDATE_LURE: { tone: "warn", text: { en: "Asks you to update KYC", te: "KYC అప్‌డేట్ చేయమంటోంది", hi: "KYC अपडेट करने को कहता है" } },
  REFUND_LURE: { tone: "warn", text: { en: "Promises a refund or cashback", te: "రీఫండ్ లేదా క్యాష్‌బ్యాక్ వాగ్దానం", hi: "रिफंड या कैशबैक का वादा" } },
  URGENCY_PRESSURE: { tone: "warn", text: { en: "Pressures you to act right now", te: "వెంటనే చేయమని ఒత్తిడి చేస్తోంది", hi: "तुरंत करने का दबाव" } },
  MISSED_BY_EXTRACTION: { tone: "info", text: { en: "Found an extra link or number in the image", te: "చిత్రంలో అదనపు లింక్ లేదా నంబర్ కనబడింది", hi: "चित्र में एक और लिंक या नंबर मिला" } },
};

const TOOLS: Record<string, Record<Lang, string>> = {
  lookup_biller: { en: "Is the biller registered?", te: "బిల్లర్ నమోదై ఉన్నారా?", hi: "क्या बिलर पंजीकृत है?" },
  check_payment_destination: { en: "Is this where you should pay?", te: "ఇక్కడే చెల్లించాలా?", hi: "क्या भुगतान यहीं करना है?" },
  match_scam_patterns: { en: "Known scam wording?", te: "తెలిసిన మోసపు మాటలు ఉన్నాయా?", hi: "क्या धोखाधड़ी वाले शब्द हैं?" },
  fetch_bill: { en: "What does the biller say you owe?", te: "బిల్లర్ ప్రకారం ఎంత బాకీ?", hi: "बिलर के अनुसार कितना बकाया?" },
  get_bill_history: { en: "Is the amount normal?", te: "మొత్తం సాధారణంగా ఉందా?", hi: "क्या राशि सामान्य है?" },
  milestone_check: { en: "Anything the reading missed?", te: "చదవడంలో ఏదైనా తప్పిపోయిందా?", hi: "पढ़ते समय कुछ छूटा?" },
};

export function codeLabel(code: string, lang: Lang): { tone: Tone; text: string } {
  const entry = LABELS[code];
  return entry ? { tone: entry.tone, text: entry.text[lang] } : { tone: "info", text: code };
}

export function toolLabel(tool: string, lang: Lang): string {
  return TOOLS[tool]?.[lang] ?? tool;
}

export const KNOWN_CODES = Object.keys(LABELS);
