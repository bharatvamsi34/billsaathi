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
    en: "Synthetic examples, one tap each",
    te: "సింథటిక్ ఉదాహరణలు — ఒక్క ట్యాప్ చాలు",
    hi: "सिंथेटिक उदाहरण — बस एक टैप",
  },
  or: { en: "or", te: "లేదా", hi: "या" },
  checking: {
    en: "Reading your request and checking payment details…",
    te: "మీ అభ్యర్థనను చదివి, చెల్లింపు వివరాలు తనిఖీ చేస్తోంది…",
    hi: "आपका अनुरोध पढ़कर भुगतान का ब्योरा जाँच रहे हैं…",
  },
  stepReading: {
    en: "Reading the bill photo",
    te: "బిల్లు ఫోటోను చదువుతోంది",
    hi: "बिल की फ़ोटो पढ़ रहे हैं",
  },
  stepReadingMsg: { en: "Reading the message", te: "సందేశాన్ని చదువుతోంది", hi: "संदेश पढ़ रहे हैं" },
  replaySource: { en: "Source", te: "మూలం", hi: "स्रोत" },
  statusElapsed: { en: "Time so far", te: "ఇప్పటివరకు సమయం", hi: "अब तक का समय" },
  stepFixed: { en: "Fixed checks — always run", te: "తప్పనిసరి తనిఖీలు — ఎప్పుడూ జరుగుతాయి", hi: "ज़रूरी जाँचें — हमेशा होती हैं" },
  stepAgent: { en: "Agent review", te: "ఏజెంట్ సమీక్ష", hi: "एजेंट की समीक्षा" },
  stepJudge: {
    en: "Second AI check",
    te: "రెండో AI తనిఖీ",
    hi: "दूसरी AI जाँच",
  },
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
    en: "Verified against the demo biller record",
    te: "డెమో బిల్లర్ రికార్డుతో సరిచూశాం",
    hi: "डेमो बिलर रिकॉर्ड से जाँचा गया",
  },
  headline_CAUTION: {
    en: "Not verified. Don't pay yet.",
    te: "నిర్ధారణ కాలేదు. ఇప్పుడే చెల్లించవద్దు.",
    hi: "पुष्टि नहीं हुई। अभी भुगतान न करें।",
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
    en: "Simulate payment (sandbox — no real money)",
    te: "చెల్లింపును అనుకరించండి (శాండ్‌బాక్స్ — నిజమైన డబ్బు కాదు)",
    hi: "भुगतान का सिमुलेशन (सैंडबॉक्स — असली पैसा नहीं)",
  },
  sandboxLabel: {
    en: "Sandbox: no real money moves",
    te: "డెమో: నిజమైన డబ్బు కదలదు",
    hi: "डेमो: कोई असली पैसा नहीं जाता",
  },
  confirmTitle: {
    en: "Confirm demo payment",
    te: "డెమో చెల్లింపును నిర్ధారించండి",
    hi: "डेमो भुगतान की पुष्टि करें",
  },
  confirmPay: {
    en: "Confirm simulation",
    te: "డెమో చెల్లింపు పూర్తి చేయండి",
    hi: "सिमुलेशन की पुष्टि करें",
  },
  cancel: { en: "Cancel", te: "రద్దు చేయండి", hi: "रद्द करें" },
  receiptTitle: { en: "Sandbox receipt", te: "డెమో రసీదు", hi: "डेमो रसीद" },
  receiptNumber: { en: "Receipt no.", te: "రసీదు సంఖ్య", hi: "रसीद संख्या" },
  auditEntry: { en: "Audit entry", te: "ఆడిట్ నమోదు", hi: "ऑडिट प्रविष्टि" },
  paidAt: {
    en: "Simulation time",
    te: "డెమో సమయం",
    hi: "सिमुलेशन का समय",
  },
  errPay: {
    en: "Could not finish the sandbox payment. Nothing was paid twice; please try again.",
    te: "డెమో చెల్లింపు పూర్తి కాలేదు. రెండుసార్లు చెల్లింపు జరగదు; మళ్లీ ప్రయత్నించండి.",
    hi: "डेमो भुगतान पूरा नहीं हुआ। दो बार भुगतान नहीं होगा; फिर कोशिश करें।",
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
    en: "Pick a sample to watch each step live, with the Meta model doing it and how long it took.",
    te: "ఒక నమూనా ఎంచుకోండి: ప్రతి దశను ప్రత్యక్షంగా చూడండి, ఏ Meta మోడల్ చేసిందో, ఎంత సమయం పట్టిందో సహా.",
    hi: "कोई नमूना चुनें और हर चरण लाइव देखें: कौन सा Meta मॉडल कर रहा है और कितना समय लगा।",
  },
  howToTest: { en: "How to test", te: "ఎలా పరీక్షించాలి", hi: "कैसे परखें" },
  testGuide: { en: "Full test guide", te: "పూర్తి పరీక్ష గైడ్", hi: "पूरी परीक्षण गाइड" },
  speak: { en: "Speak the message", te: "సందేశాన్ని చెప్పండి", hi: "संदेश बोलकर बताएँ" },
  stopVoice: { en: "Stop and check", te: "ఆపి తనిఖీ చేయండి", hi: "रोकें और जाँचें" },
  errMic: {
    en: "Could not use the microphone. Allow it in your browser, or type the message.",
    te: "మైక్రోఫోన్ వాడలేకపోయాం. బ్రౌజర్‌లో అనుమతించండి, లేదా సందేశాన్ని టైప్ చేయండి.",
    hi: "माइक्रोफ़ोन नहीं चला। ब्राउज़र में अनुमति दें, या संदेश टाइप करें।",
  },
  heard: { en: "We heard", te: "మేము విన్నది", hi: "हमने सुना" },
  stepIsolate: { en: "Finding the bill in the photo", te: "ఫోటోలో బిల్లును గుర్తిస్తోంది", hi: "फ़ोटो में बिल ढूँढ रहे हैं" },
  isolatedCrop: { en: "Bill found and cropped", te: "బిల్లు గుర్తించి కత్తిరించాం", hi: "बिल मिला और काटा गया" },
  isolatedFull: { en: "The bill fills the image", te: "చిత్రం మొత్తం బిల్లే", hi: "पूरा चित्र ही बिल है" },
  isolatedNone: { en: "Using the whole image", te: "మొత్తం చిత్రాన్ని వాడుతున్నాం", hi: "पूरा चित्र इस्तेमाल कर रहे हैं" },
  privacy: { en: "Privacy", te: "ప్రైవసీ", hi: "प्राइवेसी" },
  privacyToggle: { en: "Privacy Mode", te: "ప్రైవసీ మోడ్", hi: "प्राइवेसी मोड" },
  privacyHelp: {
    en: "Runs the whole check on the open-weight Muse Spark Open model, on an external host.",
    te: "మొత్తం తనిఖీ ఓపెన్-వెయిట్ Muse Spark Open మోడల్‌పై, బయటి హోస్ట్‌లో జరుగుతుంది.",
    hi: "पूरी जाँच ओपन-वेट Muse Spark Open मॉडल पर, बाहरी होस्ट पर चलती है।",
  },
  privacyActive: {
    en: "Privacy Mode: Muse Spark Open · open weights (hosted on Baseten / Fireworks)",
    te: "ప్రైవసీ మోడ్: Muse Spark Open · ఓపెన్ వెయిట్స్ (Baseten / Fireworks లో హోస్ట్)",
    hi: "प्राइवेसी मोड: Muse Spark Open · ओपन वेट्स (Baseten / Fireworks पर होस्ट)",
  },
  errPrivacy: {
    en: "Privacy Mode is not available right now. Nothing was sent.",
    te: "ప్రైవసీ మోడ్ ఇప్పుడు అందుబాటులో లేదు. ఏదీ పంపలేదు.",
    hi: "प्राइवेसी मोड अभी उपलब्ध नहीं है। कुछ भी नहीं भेजा गया।",
  },
  cardMaking: { en: "Making the warning card…", te: "హెచ్చరిక కార్డ్ తయారవుతోంది…", hi: "चेतावनी कार्ड बन रहा है…" },
  cardSaved: {
    en: "Card saved, and the warning copied. Send them on WhatsApp.",
    te: "కార్డ్ సేవ్ అయింది, హెచ్చరిక కాపీ అయింది. WhatsApp లో పంపండి.",
    hi: "कार्ड सेव हुआ और चेतावनी कॉपी हुई। WhatsApp पर भेजें।",
  },
  cardFailed: {
    en: "Could not share the card.",
    te: "కార్డ్ షేర్ చేయలేకపోయాం.",
    hi: "कार्ड साझा नहीं हो सका।",
  },
  earlyScam: {
    en: "Possible scam signs found. Checking the evidence…",
    te: "మోసం సూచనలు కనిపించాయి. ఆధారాలు తనిఖీ చేస్తోంది…",
    hi: "धोखे के संकेत मिले। सबूत जाँच रहे हैं…",
  },
  earlyChecking: {
    en: "Comparing with the biller record…",
    te: "బిల్లర్ రికార్డుతో పోలుస్తోంది…",
    hi: "बिलर के रिकॉर्ड से मिला रहे हैं…",
  },
  heroTitle: {
    en: "Check a bill before you pay.",
    te: "చెల్లించే ముందు బిల్లును తనిఖీ చేయండి.",
    hi: "भुगतान से पहले बिल जाँचें।",
  },
  tryScam: {
    en: "Watch BillSaathi catch a scam",
    te: "BillSaathi మోసాన్ని పట్టుకోవడం చూడండి",
    hi: "BillSaathi को धोखा पकड़ते देखें",
  },
  tryGenuine: {
    en: "or try a genuine demo bill →",
    te: "లేదా నిజమైన డెమో బిల్లు ప్రయత్నించండి →",
    hi: "या असली डेमो बिल आज़माएँ →",
  },
  statValue: {
    en: "₹22,845 crore (~US$2.7 billion)",
    te: "₹22,845 కోట్లు (~US$2.7 బిలియన్లు)",
    hi: "₹22,845 करोड़ (~US$2.7 अरब)",
  },
  statLabel: {
    en: "lost to cyber fraud in India in 2024 — all cyber fraud, not only bill scams",
    te: "2024లో భారతదేశంలో సైబర్ మోసాల్లో నష్టం — అన్ని సైబర్ మోసాలు, బిల్లు మోసాలే కాదు",
    hi: "2024 में भारत में साइबर धोखाधड़ी से नुकसान — सभी साइबर धोखाधड़ी, सिर्फ़ बिल वाली नहीं",
  },
  statSource: {
    en: "Ministry of Home Affairs, reply in the Lok Sabha, July 2025",
    te: "హోం మంత్రిత్వ శాఖ, లోక్‌సభలో సమాధానం, జులై 2025",
    hi: "गृह मंत्रालय, लोकसभा में उत्तर, जुलाई 2025",
  },
  statCorrect: { en: "correct verdicts", te: "సరైన తీర్పులు", hi: "सही फ़ैसले" },
  statBlocked: {
    en: "risky cases flagged, none marked SAFE",
    te: "ప్రమాదకర కేసులు గుర్తించాం, ఏదీ సురక్షితం అనలేదు",
    hi: "जोखिम वाले मामले पकड़े, कोई भी सुरक्षित नहीं बताया",
  },
  statLatency: {
    en: "median to verdict",
    te: "తీర్పుకు మధ్యస్థ సమయం",
    hi: "फ़ैसले का मध्यक समय",
  },
  statMore: {
    en: "{n} synthetic, held-out test items · How we measured",
    te: "{n} సింథటిక్, పక్కన ఉంచిన పరీక్షలపై · ఎలా కొలిచాం",
    hi: "{n} सिंथेटिक, अलग रखे परीक्षणों पर · कैसे मापा",
  },
  evalLink: { en: "Evaluation", te: "మూల్యాంకనం", hi: "मूल्यांकन" },
  modelsTitle: { en: "Meta models at work", te: "పనిలో ఉన్న Meta మోడళ్లు", hi: "काम पर Meta मॉडल" },
  modelSpark: {
    en: "reads, decides, explains",
    te: "చదువుతుంది, నిర్ణయిస్తుంది, వివరిస్తుంది",
    hi: "पढ़ता है, फ़ैसला करता है, समझाता है",
  },
  modelSam: { en: "crops the bill out of a photo", te: "ఫోటో నుండి బిల్లును కత్తిరిస్తుంది", hi: "फ़ोटो से बिल अलग करता है" },
  modelVoice: { en: "hears voice messages", te: "వాయిస్ సందేశాలను వింటుంది", hi: "वॉइस संदेश सुनता है" },
  modelOpen: { en: "open weights, for Privacy Mode", te: "ఓపెన్ వెయిట్స్, ప్రైవసీ మోడ్ కోసం", hi: "ओपन वेट्स, प्राइवेसी मोड के लिए" },
  modelImage: { en: "paints the warning card", te: "హెచ్చరిక కార్డ్ చిత్రం గీస్తుంది", hi: "चेतावनी कार्ड का चित्र बनाता है" },
  guide1: { en: "Pick a sample", te: "నమూనా ఎంచుకోండి", hi: "नमूना चुनें" },
  guide2: { en: "Watch the agent verify", te: "ఏజెంట్ నిర్ధారించడం చూడండి", hi: "एजेंट की जाँच देखें" },
  guide3: { en: "See the verdict", te: "తీర్పు చూడండి", hi: "फ़ैसला देखें" },
  guideClose: { en: "Got it", te: "సరే", hi: "समझ गया" },
  stepHear: { en: "Hearing your message", te: "మీ సందేశాన్ని వింటోంది", hi: "आपका संदेश सुन रहे हैं" },
  stepExplain: { en: "Explaining the verdict", te: "తీర్పును వివరిస్తోంది", hi: "फ़ैसला समझा रहे हैं" },
  explaining: { en: "Writing the explanation…", te: "వివరణ రాస్తోంది…", hi: "समझा रहे हैं…" },
  listen: { en: "Listen", te: "వినండి", hi: "सुनें" },
  stopListening: { en: "Stop", te: "ఆపండి", hi: "रोकें" },
  noVoice: {
    en: "This device has no voice for this language.",
    te: "ఈ పరికరంలో ఈ భాషకు వాయిస్ లేదు.",
    hi: "इस डिवाइस में इस भाषा की आवाज़ नहीं है।",
  },
  forced: {
    en: "Some checks could not be completed.",
    te: "కొన్ని తనిఖీలు పూర్తి కాలేదు.",
    hi: "कुछ जाँचें पूरी नहीं हो सकीं।",
  },
  openWeights: {
    en: "open weights",
    te: "ఓపెన్ వెయిట్స్",
    hi: "ओपन वेट्स",
  },
  codeBadge: {
    en: "Code",
    te: "కోడ్",
    hi: "कोड",
  },
  jobVision: {
    en: "vision extraction",
    te: "చిత్రం చదవడం",
    hi: "चित्र से पढ़ना",
  },
  jobAgent: {
    en: "tool-calling agent",
    te: "టూల్స్ వాడే ఏజెంట్",
    hi: "टूल चलाने वाला एजेंट",
  },
  jobJudge: {
    en: "checks claims",
    te: "వాదనలను తనిఖీ చేస్తుంది",
    hi: "दावे जाँचता है",
  },
  jobExplain: {
    en: "multilingual explanation",
    te: "బహుభాషా వివరణ",
    hi: "बहुभाषी व्याख्या",
  },
  jobCrop: {
    en: "photo cropping",
    te: "ఫోటో కత్తిరింపు",
    hi: "फ़ोटो क्रॉपिंग",
  },
  sandboxBadge: {
    en: "Sandbox · simulated biller records",
    te: "శాండ్‌బాక్స్ · అనుకరించిన బిల్లర్ రికార్డులు",
    hi: "सैंडबॉक्स · सिमुलेटेड बिलर रिकॉर्ड",
  },
  heroBody: {
    en: "BillSaathi compares the amount and payment address with the biller's record and shows you exactly what doesn't match.",
    te: "BillSaathi మొత్తాన్ని, చెల్లింపు చిరునామాను బిల్లర్ రికార్డుతో పోల్చి, ఏది సరిపోలడం లేదో స్పష్టంగా చూపిస్తుంది.",
    hi: "BillSaathi राशि और भुगतान के पते को बिलर के रिकॉर्ड से मिलाता है और दिखाता है कि ठीक-ठीक क्या मेल नहीं खाता।",
  },
  heroSim: {
    en: "This demo uses simulated biller records, not the live BBPS network (India's national bill-payment network).",
    te: "ఈ డెమో అనుకరించిన బిల్లర్ రికార్డులను వాడుతుంది, నిజమైన BBPS నెట్‌వర్క్‌ను కాదు (భారత జాతీయ బిల్లు చెల్లింపు నెట్‌వర్క్).",
    hi: "यह डेमो सिमुलेटेड बिलर रिकॉर्ड इस्तेमाल करता है, असली BBPS नेटवर्क नहीं (भारत का राष्ट्रीय बिल भुगतान नेटवर्क)।",
  },
  tabSamples: {
    en: "Try a sample",
    te: "నమూనా ప్రయత్నించండి",
    hi: "नमूना आज़माएँ",
  },
  tabOwn: {
    en: "Check your own",
    te: "మీది తనిఖీ చేయండి",
    hi: "अपना जाँचें",
  },
  ownHelper: {
    en: "Your own real bill will usually show CAUTION — scam checks run on anything, but the registry holds only 8 synthetic demo billers.",
    te: "మీ నిజమైన బిల్లుకు సాధారణంగా జాగ్రత్త (CAUTION) వస్తుంది — మోసం తనిఖీలు దేనిపైనైనా జరుగుతాయి, కానీ రిజిస్ట్రీలో 8 సింథటిక్ డెమో బిల్లర్లు మాత్రమే ఉన్నారు.",
    hi: "आपके असली बिल पर आमतौर पर सावधान (CAUTION) आएगा — धोखे की जाँच हर चीज़ पर होती है, पर रजिस्ट्री में सिर्फ़ 8 सिंथेटिक डेमो बिलर हैं।",
  },
  noRealData: {
    en: "Please don't send anything with real personal details.",
    te: "నిజమైన వ్యక్తిగత వివరాలు ఉన్నవి పంపవద్దు.",
    hi: "असली निजी जानकारी वाली कोई चीज़ न भेजें।",
  },
  uploadShort: {
    en: "Upload",
    te: "అప్‌లోడ్",
    hi: "अपलोड",
  },
  cameraShort: {
    en: "Camera",
    te: "కెమెరా",
    hi: "कैमरा",
  },
  speakShort: {
    en: "Speak",
    te: "మాట్లాడండి",
    hi: "बोलें",
  },
  uploadLong: {
    en: "Upload screenshot or photo",
    te: "స్క్రీన్‌షాట్ లేదా ఫోటో అప్‌లోడ్ చేయండి",
    hi: "स्क्रीनशॉट या फ़ोटो अपलोड करें",
  },
  chipScam: {
    en: "Scam SMS",
    te: "మోసం SMS",
    hi: "धोखे का SMS",
  },
  chipTampered: {
    en: "Tampered bill",
    te: "మార్చిన బిల్లు",
    hi: "बदला हुआ बिल",
  },
  chipGenuine: {
    en: "Genuine bill",
    te: "నిజమైన బిల్లు",
    hi: "असली बिल",
  },
  chipVoice: {
    en: "Voice note",
    te: "వాయిస్ నోట్",
    hi: "वॉइस नोट",
  },
  inputTitle: {
    en: "Input under review",
    te: "పరిశీలనలో ఉన్నది",
    hi: "जाँच में",
  },
  legendRisky: {
    en: "risky",
    te: "ప్రమాదకరం",
    hi: "जोखिम",
  },
  legendUnverified: {
    en: "not verified",
    te: "నిర్ధారణ కాలేదు",
    hi: "पुष्टि नहीं",
  },
  legendOk: {
    en: "confirmed",
    te: "నిర్ధారణ అయింది",
    hi: "पुष्टि हुई",
  },
  compareTitle: {
    en: "What the message says vs. the demo biller record",
    te: "సందేశంలో ఉన్నది, డెమో బిల్లర్ రికార్డులో ఉన్నది",
    hi: "संदेश में क्या है और डेमो बिलर रिकॉर्ड में क्या है",
  },
  colMessage: {
    en: "Message says",
    te: "సందేశంలో",
    hi: "संदेश में",
  },
  colBill: {
    en: "Bill says",
    te: "బిల్లులో",
    hi: "बिल में",
  },
  colRecord: {
    en: "Demo biller record",
    te: "డెమో బిల్లర్ రికార్డు",
    hi: "डेमो बिलर रिकॉर्ड",
  },
  destUpi: {
    en: "UPI ID (bank payment address)",
    te: "UPI ID (బ్యాంక్ చెల్లింపు చిరునామా)",
    hi: "UPI ID (बैंक भुगतान पता)",
  },
  destUrl: {
    en: "Payment link",
    te: "చెల్లింపు లింక్",
    hi: "भुगतान लिंक",
  },
  destPhone: {
    en: "Phone number",
    te: "ఫోన్ నంబర్",
    hi: "फ़ोन नंबर",
  },
  notInRegistry: {
    en: "not in registry",
    te: "రిజిస్ట్రీలో లేదు",
    hi: "रजिस्ट्री में नहीं",
  },
  notChecked: {
    en: "not checked",
    te: "తనిఖీ కాలేదు",
    hi: "जाँच नहीं हुई",
  },
  noAccount: {
    en: "no such account",
    te: "అలాంటి ఖాతా లేదు",
    hi: "ऐसा खाता नहीं",
  },
  missing: {
    en: "not given",
    te: "ఇవ్వలేదు",
    hi: "नहीं दिया",
  },
  viewAll: {
    en: "Show all {n} findings",
    te: "మొత్తం {n} అంశాలు చూపించండి",
    hi: "सभी {n} निष्कर्ष दिखाएँ",
  },
  hideAll: {
    en: "Show less",
    te: "తక్కువ చూపించండి",
    hi: "कम दिखाएँ",
  },
  doNotPay: {
    en: "Do not pay",
    te: "చెల్లించవద్దు",
    hi: "भुगतान न करें",
  },
  doNotPayYet: {
    en: "Do not pay yet",
    te: "ఇప్పుడే చెల్లించవద్దు",
    hi: "अभी भुगतान न करें",
  },
  traceChecks: {
    en: "{n} checks",
    te: "{n} తనిఖీలు",
    hi: "{n} जाँचें",
  },
  noneFound: {
    en: "Nothing found",
    te: "ఏమీ కనబడలేదు",
    hi: "कुछ नहीं मिला",
  },
  traceTurn: {
    en: "{n} agent turn",
    te: "{n} ఏజెంట్ మలుపు",
    hi: "{n} एजेंट टर्न",
  },
  colRecordShort: {
    en: "Record says",
    te: "రికార్డులో",
    hi: "रिकॉर्ड में",
  },
  traceTurns: {
    en: "{n} agent turns",
    te: "{n} ఏజెంట్ మలుపులు",
    hi: "{n} एजेंट टर्न",
  },
  traceJudge: {
    en: "Second AI check: {a}/{b} claims verified",
    te: "రెండో AI తనిఖీ: {a}/{b} వాదనలు ధృవీకరించబడ్డాయి",
    hi: "दूसरी AI जाँच: {a}/{b} दावे सत्यापित",
  },
  viewTrace: {
    en: "See verification steps",
    te: "తనిఖీ దశలు చూడండి",
    hi: "जाँच के चरण देखें",
  },
  hideTrace: {
    en: "Hide verification steps",
    te: "తనిఖీ దశలు దాచండి",
    hi: "जाँच के चरण छिपाएँ",
  },
  modelsInRun: {
    en: "Meta models in this check",
    te: "ఈ తనిఖీలోని Meta మోడళ్లు",
    hi: "इस जाँच के Meta मॉडल",
  },
  judgeSubtitle: {
    en: "A second Muse Spark call checks every claim against the evidence.",
    te: "రెండో Muse Spark కాల్ ప్రతి వాదనను ఆధారంతో సరిచూస్తుంది.",
    hi: "दूसरी Muse Spark कॉल हर दावे को सबूत से मिलाती है।",
  },
  judgeSubtitleOpen: {
    en: "A second Muse Spark Open call checks every claim against the evidence.",
    te: "రెండో Muse Spark Open కాల్ ప్రతి వాదనను ఆధారంతో సరిచూస్తుంది.",
    hi: "दूसरी Muse Spark Open कॉल हर दावे को सबूत से मिलाती है।",
  },
  floorEnforced: {
    en: "Floor check: {v} enforced",
    te: "కనీస స్థాయి తనిఖీ: {v} అమలైంది",
    hi: "न्यूनतम स्तर जाँच: {v} लागू",
  },
  noInvented: {
    en: "0 invented links or numbers",
    te: "కల్పించిన లింక్‌లు లేదా నంబర్లు: 0",
    hi: "गढ़े गए लिंक या नंबर: 0",
  },
  checkedAgainst: {
    en: "checked against",
    te: "దీనితో సరిచూశారు",
    hi: "इससे मिलाया",
  },
  photoCropSkipped: {
    en: "Photo cropping skipped: SAM 3.1 runs on Meta's API.",
    te: "ఫోటో కత్తిరింపు వదిలేశాం: SAM 3.1 Meta API పై నడుస్తుంది.",
    hi: "फ़ोटो क्रॉपिंग छोड़ी गई: SAM 3.1 Meta API पर चलता है।",
  },
  fillValid: {
    en: "Fill demo consumer number",
    te: "డెమో వినియోగదారు సంఖ్య నింపండి",
    hi: "डेमो उपभोक्ता संख्या भरें",
  },
  fillWrong: {
    en: "Fill a wrong number",
    te: "తప్పు సంఖ్య నింపండి",
    hi: "गलत संख्या भरें",
  },
  retry: {
    en: "Try again",
    te: "మళ్లీ ప్రయత్నించండి",
    hi: "फिर कोशिश करें",
  },
  replayTitle: {
    en: "Replay: a second AI catches an unsupported claim",
    te: "రీప్లే: ఆధారం లేని వాదనను రెండో AI పట్టుకుంది",
    hi: "रीप्ले: दूसरी AI ने बिना सबूत का दावा पकड़ा",
  },
  replayLabel: {
    en: "Replay of a real run (recorded {date})",
    te: "నిజమైన రన్ రీప్లే (నమోదు: {date})",
    hi: "असली रन का रीप्ले (रिकॉर्ड: {date})",
  },
  replayIntro: {
    en: "The agent's first answer said more than its evidence showed. The second AI check sent it back, and the agent corrected it.",
    te: "ఏజెంట్ మొదటి సమాధానం ఆధారానికి మించి చెప్పింది. రెండో AI తనిఖీ దాన్ని వెనక్కి పంపింది, ఏజెంట్ సరిదిద్దింది.",
    hi: "एजेंट के पहले जवाब ने सबूत से ज़्यादा कहा। दूसरी AI जाँच ने उसे वापस भेजा और एजेंट ने सुधारा।",
  },
  replayAttempt1: {
    en: "First answer",
    te: "మొదటి సమాధానం",
    hi: "पहला जवाब",
  },
  replayAttempt2: {
    en: "After correction",
    te: "సరిదిద్దిన తర్వాత",
    hi: "सुधार के बाद",
  },
  replayRefused: {
    en: "Sent back by the second AI check",
    te: "రెండో AI తనిఖీ వెనక్కి పంపింది",
    hi: "दूसरी AI जाँच ने वापस भेजा",
  },
  replayAccepted: {
    en: "Accepted by the second AI check",
    te: "రెండో AI తనిఖీ ఆమోదించింది",
    hi: "दूसरी AI जाँच ने स्वीकार किया",
  },
  replayFinal: {
    en: "Final verdict in that run",
    te: "ఆ రన్‌లో తుది తీర్పు",
    hi: "उस रन का अंतिम फ़ैसला",
  },
  back: {
    en: "Check another",
    te: "మరొకటి తనిఖీ చేయండి",
    hi: "दूसरा जाँचें",
  },
  playSample: {
    en: "Play the voice note",
    te: "వాయిస్ నోట్ వినండి",
    hi: "वॉइस नोट सुनें",
  },
  thumbAlt: {
    en: "The image being checked",
    te: "తనిఖీ అవుతున్న చిత్రం",
    hi: "जाँचा जा रहा चित्र",
  },
  foundBill: {
    en: "The bill SAM 3.1 found",
    te: "SAM 3.1 గుర్తించిన బిల్లు",
    hi: "SAM 3.1 को मिला बिल",
  },
  heroModels: {
    en: "An AI agent on Meta's Muse Spark 1.3 · SAM 3.1 · Muse Voice Transcribe · Muse Image. A second AI call checks every claim.",
    te: "Meta Muse Spark 1.3 · SAM 3.1 · Muse Voice Transcribe · Muse Image పై నడిచే AI ఏజెంట్. రెండో AI కాల్ ప్రతి వాదనను తనిఖీ చేస్తుంది.",
    hi: "Meta के Muse Spark 1.3 · SAM 3.1 · Muse Voice Transcribe · Muse Image पर चलने वाला AI एजेंट। दूसरी AI कॉल हर दावे को जाँचती है।",
  },
  statsLabel: {
    en: "{n} synthetic test cases",
    te: "{n} సింథటిక్ పరీక్షలు",
    hi: "{n} सिंथेटिक परीक्षण",
  },
  statHow: {
    en: "How we measured",
    te: "ఎలా కొలిచాం",
    hi: "कैसे मापा",
  },
  tagPhotoOnly: {
    en: "Photo only",
    te: "ఫోటోకు మాత్రమే",
    hi: "सिर्फ़ फ़ोटो",
  },
  tagVoiceOnly: {
    en: "Voice only",
    te: "వాయిస్‌కు మాత్రమే",
    hi: "सिर्फ़ आवाज़",
  },
  stepReadingVoice: {
    en: "Reading the transcript",
    te: "విన్న మాటలను చదువుతోంది",
    hi: "सुनी गई बात पढ़ रहे हैं",
  },
  jobText: {
    en: "reads text",
    te: "సందేశం చదువుతుంది",
    hi: "टेक्स्ट पढ़ता है",
  },
  compareTitleBill: {
    en: "What the bill says vs. the demo biller record",
    te: "బిల్లులో ఉన్నది, డెమో బిల్లర్ రికార్డులో ఉన్నది",
    hi: "बिल में क्या है और डेमो बिलर रिकॉर्ड में क्या है",
  },
  rowAmountDiffers: {
    en: "Amount differs",
    te: "మొత్తం తేడా ఉంది",
    hi: "राशि अलग है",
  },
  rowAddressDiffers: {
    en: "Payment address differs",
    te: "చెల్లింపు చిరునామా తేడా ఉంది",
    hi: "भुगतान का पता अलग है",
  },
  rowAccountNotFound: {
    en: "Account not found",
    te: "ఖాతా కనబడలేదు",
    hi: "खाता नहीं मिला",
  },
  plainCard: {
    en: "Plain card: no image model in Privacy Mode",
    te: "సాధారణ కార్డ్: ప్రైవసీ మోడ్‌లో ఇమేజ్ మోడల్ లేదు",
    hi: "सादा कार्ड: प्राइवेसी मोड में इमेज मॉडल नहीं",
  },
  exclReply: {
    en: "excl. your reply",
    te: "మీ సమాధాన సమయం మినహా",
    hi: "आपके जवाब का समय छोड़कर",
  },
  sandboxBadgeShort: {
    en: "Demo · mock billers · no real money",
    te: "డెమో · నమూనా బిల్లర్లు · నిజమైన డబ్బు కాదు",
    hi: "डेमो बिलर · असली पैसा नहीं",
  },
  replayWhy: {
    en: "The message says 'tonight', but the check the agent cited recorded only a power-cut threat, not when. Every claim needs evidence, so the second AI refused it.",
    te: "సందేశంలో 'ఈ రాత్రి' అని ఉంది, కానీ ఏజెంట్ చూపిన తనిఖీలో కరెంట్ కట్ బెదిరింపు మాత్రమే నమోదైంది, ఎప్పుడో కాదు. ప్రతి వాదనకు ఆధారం ఉండాలి, అందుకే రెండో AI తిరస్కరించింది.",
    hi: "संदेश में 'आज रात' लिखा है, पर एजेंट की बताई जाँच में सिर्फ़ बिजली कटने की धमकी दर्ज थी, समय नहीं। हर दावे का सबूत ज़रूरी है, इसलिए दूसरी AI ने उसे ठुकरा दिया।",
  },
  noRealMoney: {
    en: "No real money will move",
    te: "నిజమైన డబ్బు కదలదు",
    hi: "कोई असली पैसा नहीं जाएगा",
  },
  cautionLine: {
    en: "Confirm with the biller's official app, or a bill you already trust.",
    te: "బిల్లర్ అధికారిక యాప్‌లో లేదా మీరు నమ్మే బిల్లుతో సరిచూసుకోండి.",
    hi: "बिलर के आधिकारिक ऐप या अपने भरोसेमंद बिल से पुष्टि करें।",
  },
} satisfies Record<string, Text>;

export type Key = keyof typeof STRINGS;

export function t(lang: Lang, key: Key, vars: Record<string, string | number> = {}): string {
  let text: string = STRINGS[key][lang];
  for (const [name, value] of Object.entries(vars)) text = text.replace(`{${name}}`, String(value));
  return text;
}
