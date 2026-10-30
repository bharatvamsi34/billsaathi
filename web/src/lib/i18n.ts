// Interface text in English, Telugu and Hindi. Simple words for first-time users.
// Telugu reviewed by BV (native speaker); Hindi approximate.

export type Lang = "en" | "te" | "hi";
export const LANGS: { code: Lang; name: string }[] = [
  { code: "en", name: "English" },
  { code: "te", name: "తెలుగు" },
  { code: "hi", name: "हिंदी" },
];

type Text = Record<Lang, string>;

export const STRINGS = {
  tagline: {
    en: "Check a bill or payment message before you pay.",
    te: "చెల్లించే ముందు బిల్లు లేదా చెల్లింపు సందేశాన్ని తనిఖీ చేయండి.",
    hi: "भुगतान से पहले बिल या भुगतान संदेश जाँचें।",
  },
  banner: {
    en: "Sandbox demo — no real payment. All bills and billers here are made up; BBPS is a mock.",
    te: "ఇది డెమో మాత్రమే — నిజమైన చెల్లింపు జరగదు. ఇక్కడి బిల్లులు, బిల్లర్లు అన్నీ కల్పితం; BBPS నమూనా మాత్రమే.",
    hi: "यह सिर्फ़ डेमो है — कोई असली भुगतान नहीं होता। यहाँ के सभी बिल और बिलर काल्पनिक हैं; BBPS एक नमूना है।",
  },
  language: { en: "Language", te: "భాష", hi: "भाषा" },
  takePhoto: { en: "Take a photo of the bill", te: "బిల్లు ఫోటో తీయండి", hi: "बिल की फ़ोटो लें" },
  upload: { en: "Choose a screenshot or photo", te: "స్క్రీన్‌షాట్ లేదా ఫోటో ఎంచుకోండి", hi: "स्क्रीनशॉट या फ़ोटो चुनें" },
  pasteLabel: {
    en: "Or paste the SMS / WhatsApp message",
    te: "లేదా SMS / WhatsApp సందేశాన్ని ఇక్కడ పేస్ట్ చేయండి",
    hi: "या SMS / WhatsApp संदेश यहाँ चिपकाएँ",
  },
  pastePlaceholder: { en: "Paste the message here…", te: "సందేశాన్ని ఇక్కడ పేస్ట్ చేయండి…", hi: "संदेश यहाँ चिपकाएँ…" },
  checkMessage: { en: "Check this message", te: "ఈ సందేశాన్ని తనిఖీ చేయండి", hi: "यह संदेश जाँचें" },
  samplesTitle: { en: "Try a sample", te: "ఒక నమూనాతో ప్రయత్నించండి", hi: "एक नमूना आज़माएँ" },
  noBill: {
    en: "No bill at hand? Try a sample",
    te: "బిల్లు దగ్గర లేదా? నమూనాతో ప్రయత్నించండి",
    hi: "बिल पास में नहीं? एक नमूना आज़माएँ",
  },
  samplesNote: {
    en: "Made-up examples, one tap each",
    te: "కల్పిత ఉదాహరణలు — ఒక్క ట్యాప్ చాలు",
    hi: "काल्पनिक उदाहरण — बस एक टैप",
  },
  or: { en: "or", te: "లేదా", hi: "या" },
  checking: { en: "Checking…", te: "తనిఖీ చేస్తోంది…", hi: "जाँच हो रही है…" },
  stepReading: { en: "Reading the bill", te: "బిల్లును చదువుతోంది", hi: "बिल पढ़ रहे हैं" },
  stepFixed: { en: "Fixed checks — always run", te: "తప్పనిసరి తనిఖీలు — ఎప్పుడూ జరుగుతాయి", hi: "ज़रूरी जाँचें — हमेशा होती हैं" },
  stepAgent: { en: "Agent review", te: "ఏజెంట్ సమీక్ష", hi: "एजेंट की समीक्षा" },
  stepJudge: { en: "Independent check of the reasons", te: "కారణాల స్వతంత్ర తనిఖీ", hi: "कारणों की स्वतंत्र जाँच" },
  agentDecided: { en: "The agent reviewed the evidence", te: "ఏజెంట్ ఆధారాలను పరిశీలించింది", hi: "एजेंट ने सबूत देखे" },
  agentExtra: { en: "Extra check requested", te: "అదనపు తనిఖీ కోరింది", hi: "अतिरिक्त जाँच माँगी" },
  judgeOk: {
    en: "Every reason matches its evidence",
    te: "ప్రతి కారణం దాని ఆధారంతో సరిపోతోంది",
    hi: "हर कारण अपने सबूत से मेल खाता है",
  },
  judgeRefused: {
    en: "Sent back: a reason said more than the evidence shows",
    te: "వెనక్కి పంపబడింది: ఒక కారణం ఆధారానికి మించి చెప్పింది",
    hi: "वापस भेजा: एक कारण ने सबूत से ज़्यादा कहा",
  },
  refused: { en: "Answer sent back by the safety checks", te: "భద్రతా తనిఖీలు సమాధానాన్ని వెనక్కి పంపాయి", hi: "सुरक्षा जाँच ने जवाब वापस भेजा" },
  unclear: { en: "unclear", te: "స్పష్టంగా లేదు", hi: "साफ़ नहीं" },
  biller: { en: "Biller", te: "బిల్లర్", hi: "बिलर" },
  amount: { en: "Amount", te: "మొత్తం", hi: "राशि" },
  dueDate: { en: "Due date", te: "గడువు తేదీ", hi: "अंतिम तिथि" },
  consumer: { en: "Consumer no.", te: "వినియోగదారు సంఖ్య", hi: "उपभोक्ता संख्या" },
  payTo: { en: "Pay to", te: "చెల్లించాల్సిన చోటు", hi: "भुगतान कहाँ" },
  verdict_SAFE: { en: "SAFE", te: "సురక్షితం", hi: "सुरक्षित" },
  verdict_CAUTION: { en: "CAUTION", te: "జాగ్రత్త", hi: "सावधान" },
  verdict_SCAM: { en: "SCAM", te: "మోసం", hi: "धोखा" },
  headline_SAFE: {
    en: "Checks passed. Pay only after you confirm.",
    te: "తనిఖీలు సరిపోయాయి. మీరు నిర్ధారించిన తర్వాతే చెల్లించండి.",
    hi: "जाँचें सही रहीं। अपनी पुष्टि के बाद ही भुगतान करें।",
  },
  headline_CAUTION: {
    en: "We could not confirm this. Do not pay yet.",
    te: "దీన్ని నిర్ధారించలేకపోయాం. ఇప్పుడే చెల్లించవద్దు.",
    hi: "इसकी पुष्टि नहीं हो सकी। अभी भुगतान न करें।",
  },
  headline_SCAM: {
    en: "This looks like a scam. Do not pay.",
    te: "ఇది మోసంలా ఉంది. చెల్లించవద్దు.",
    hi: "यह धोखाधड़ी लगती है। भुगतान न करें।",
  },
  checkedIn: { en: "Checked in {s} s", te: "{s} సెకన్లలో తనిఖీ పూర్తి", hi: "{s} सेकंड में जाँच पूरी" },
  why: { en: "Why", te: "ఎందుకు", hi: "क्यों" },
  howChecked: { en: "How we checked", te: "మేము ఎలా తనిఖీ చేశాం", hi: "हमने कैसे जाँचा" },
  pay: {
    en: "Pay via BBPS (sandbox) — coming soon",
    te: "BBPS ద్వారా చెల్లించండి (డెమో) — త్వరలో",
    hi: "BBPS से भुगतान (डेमो) — जल्द ही",
  },
  payNote: {
    en: "You always confirm before any payment.",
    te: "ఏ చెల్లింపుకైనా ముందు మీరే నిర్ధారిస్తారు.",
    hi: "हर भुगतान से पहले आप ही पुष्टि करते हैं।",
  },
  report: { en: "Report fraud: call {value}", te: "మోసాన్ని ఫిర్యాదు చేయండి: {value} కు కాల్ చేయండి", hi: "धोखाधड़ी की शिकायत: {value} पर कॉल करें" },
  warnFamily: { en: "Warn my family", te: "నా కుటుంబాన్ని హెచ్చరించండి", hi: "परिवार को सावधान करें" },
  copied: {
    en: "Warning copied. Paste it in WhatsApp.",
    te: "హెచ్చరిక కాపీ అయింది. WhatsApp లో పేస్ట్ చేయండి.",
    hi: "चेतावनी कॉपी हो गई। WhatsApp में चिपकाएँ।",
  },
  checkAnother: { en: "Check another", te: "మరొకటి తనిఖీ చేయండి", hi: "दूसरा जाँचें" },
  questionTitle: { en: "One quick question", te: "ఒక చిన్న ప్రశ్న", hi: "एक छोटा सा सवाल" },
  send: { en: "Send", te: "పంపండి", hi: "भेजें" },
  skip: { en: "I don't know", te: "నాకు తెలియదు", hi: "मुझे नहीं पता" },
  errRate: {
    en: "Too many checks. Please wait a minute and try again.",
    te: "చాలా ఎక్కువ తనిఖీలు. ఒక నిమిషం ఆగి మళ్లీ ప్రయత్నించండి.",
    hi: "बहुत सारी जाँचें। एक मिनट रुककर फिर कोशिश करें।",
  },
  errBusy: {
    en: "BillSaathi is busy right now. Please try again later.",
    te: "BillSaathi ఇప్పుడు బిజీగా ఉంది. తర్వాత మళ్లీ ప్రయత్నించండి.",
    hi: "BillSaathi अभी व्यस्त है। बाद में फिर कोशिश करें।",
  },
  errImage: {
    en: "Please send a photo or screenshot (PNG, JPEG or WebP).",
    te: "దయచేసి ఫోటో లేదా స్క్రీన్‌షాట్ పంపండి (PNG, JPEG లేదా WebP).",
    hi: "कृपया फ़ोटो या स्क्रीनशॉट भेजें (PNG, JPEG या WebP)।",
  },
  errNetwork: {
    en: "Could not reach BillSaathi. Check your internet and try again.",
    te: "BillSaathi ని చేరుకోలేకపోయాం. ఇంటర్నెట్ చూసి మళ్లీ ప్రయత్నించండి.",
    hi: "BillSaathi तक नहीं पहुँच सके। इंटरनेट जाँचकर फिर कोशिश करें।",
  },
  intro: {
    en: "BillSaathi is an AI agent that checks a bill or payment message against the biller's own records, catches scams before money moves, and explains why.",
    te: "BillSaathi ఒక AI ఏజెంట్: బిల్లు లేదా చెల్లింపు సందేశాన్ని బిల్లర్ రికార్డులతో పోల్చి, డబ్బు కదలకముందే మోసాన్ని పట్టుకుని, కారణం చెబుతుంది.",
    hi: "BillSaathi एक AI एजेंट है: बिल या भुगतान संदेश को बिलर के अपने रिकॉर्ड से मिलाता है, पैसा जाने से पहले धोखा पकड़ता है, और वजह बताता है।",
  },
  howItWorks: { en: "How it works", te: "ఇది ఎలా పనిచేస్తుంది", hi: "यह कैसे काम करता है" },
  how1Title: { en: "Read", te: "చదవడం", hi: "पढ़ना" },
  how1Body: {
    en: "Muse Spark reads the bill or message: biller, amount, where to pay.",
    te: "Muse Spark బిల్లు లేదా సందేశాన్ని చదువుతుంది: బిల్లర్, మొత్తం, ఎక్కడ చెల్లించాలి.",
    hi: "Muse Spark बिल या संदेश पढ़ता है: बिलर, राशि, कहाँ भुगतान करना है।",
  },
  how2Title: { en: "Verify", te: "నిర్ధారణ", hi: "जाँच" },
  how2Body: {
    en: "Fixed checks always run on the biller, every link and UPI ID; then the agent investigates and decides.",
    te: "బిల్లర్, ప్రతి లింక్, UPI ID పై తప్పనిసరి తనిఖీలు ఎప్పుడూ జరుగుతాయి; తర్వాత ఏజెంట్ పరిశీలించి నిర్ణయిస్తుంది.",
    hi: "बिलर, हर लिंक और UPI ID पर ज़रूरी जाँचें हमेशा होती हैं; फिर एजेंट पड़ताल करके फ़ैसला करता है।",
  },
  how3Title: { en: "Independent check", te: "స్వతంత్ర తనిఖీ", hi: "स्वतंत्र जाँच" },
  how3Body: {
    en: "Code and a second model check every reason against its evidence. Nothing can turn a risk into SAFE.",
    te: "కోడ్, రెండో మోడల్ ప్రతి కారణాన్ని దాని ఆధారంతో సరిచూస్తాయి. ఏ ప్రమాదాన్నీ సురక్షితంగా మార్చలేరు.",
    hi: "कोड और दूसरा मॉडल हर कारण को उसके सबूत से मिलाते हैं। कोई भी जोखिम सुरक्षित नहीं बन सकता।",
  },
  qrTitle: { en: "Best on your phone", te: "ఫోన్‌లో ఉత్తమంగా పనిచేస్తుంది", hi: "फ़ोन पर सबसे अच्छा" },
  qrNote: {
    en: "Scan to open this page and photograph a bill with your camera.",
    te: "ఈ పేజీని తెరవడానికి స్కాన్ చేసి, కెమెరాతో బిల్లు ఫోటో తీయండి.",
    hi: "यह पेज खोलने के लिए स्कैन करें और कैमरे से बिल की फ़ोटो लें।",
  },
  qrAlt: { en: "QR code for this page", te: "ఈ పేజీ QR కోడ్", hi: "इस पेज का QR कोड" },
  watchTitle: { en: "Watch the agent work", te: "ఏజెంట్ పనిని చూడండి", hi: "एजेंट को काम करते देखें" },
  watchBody: {
    en: "Pick a sample on the left. Each check appears here as it happens, then the verdict with its evidence.",
    te: "ఎడమవైపు ఒక నమూనాను ఎంచుకోండి. ప్రతి తనిఖీ జరిగేటప్పుడే ఇక్కడ కనిపిస్తుంది, తర్వాత ఆధారాలతో తీర్పు.",
    hi: "बाईं ओर एक नमूना चुनें। हर जाँच होते ही यहाँ दिखेगी, फिर सबूत के साथ फ़ैसला।",
  },
  howToTest: { en: "How to test", te: "ఎలా పరీక్షించాలి", hi: "कैसे परखें" },
  testGuide: { en: "Full test guide", te: "పూర్తి పరీక్ష గైడ్", hi: "पूरी परीक्षण गाइड" },
  forced: {
    en: "Some checks could not be completed.",
    te: "కొన్ని తనిఖీలు పూర్తి కాలేదు.",
    hi: "कुछ जाँचें पूरी नहीं हो सकीं।",
  },
} satisfies Record<string, Text>;

export type Key = keyof typeof STRINGS;

export function t(lang: Lang, key: Key, vars: Record<string, string | number> = {}): string {
  let text: string = STRINGS[key][lang];
  for (const [name, value] of Object.entries(vars)) text = text.replace(`{${name}}`, String(value));
  return text;
}
