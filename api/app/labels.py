"""Plain-language text shared by every channel, in English, Telugu and Hindi.

Evidence labels mirror web/src/lib/codes.ts. Telugu reviewed by BV; Hindi approximate.
"""

from typing import Literal

Lang = Literal["en", "te", "hi"]
LANGS: tuple[Lang, ...] = ("en", "te", "hi")

HEADLINES: dict[str, dict[Lang, str]] = {
    "SAFE": {
        "en": "Checks passed. Pay only after you confirm.",
        "te": "తనిఖీలు సరిపోయాయి. మీరు నిర్ధారించిన తర్వాతే చెల్లించండి.",
        "hi": "जाँचें सही रहीं। अपनी पुष्टि के बाद ही भुगतान करें।",
    },
    "CAUTION": {
        "en": "We could not confirm this. Do not pay yet.",
        "te": "దీన్ని నిర్ధారించలేకపోయాం. ఇప్పుడే చెల్లించవద్దు.",
        "hi": "इसकी पुष्टि नहीं हो सकी। अभी भुगतान न करें।",
    },
    "SCAM": {
        "en": "This looks like a scam. Do not pay.",
        "te": "ఇది మోసంలా ఉంది. చెల్లించవద్దు.",
        "hi": "यह धोखाधड़ी लगती है। भुगतान न करें।",
    },
}

CODE_LABELS: dict[str, dict[Lang, str]] = {
    "BILLER_VERIFIED": {"en": "Registered biller", "te": "నమోదైన బిల్లర్", "hi": "पंजीकृत बिलर"},
    "UNKNOWN_BILLER": {"en": "Biller not found in the registry", "te": "బిల్లర్ రిజిస్ట్రీలో లేరు", "hi": "बिलर रजिस्ट्री में नहीं मिला"},
    "AMOUNT_MATCHES_BILLER": {"en": "Amount matches the biller's records", "te": "మొత్తం బిల్లర్ రికార్డుతో సరిపోతోంది", "hi": "राशि बिलर के रिकॉर्ड से मेल खाती है"},
    "AMOUNT_MISMATCH": {"en": "Amount is different from the biller's records", "te": "మొత్తం బిల్లర్ రికార్డుకు భిన్నంగా ఉంది", "hi": "राशि बिलर के रिकॉर्ड से अलग है"},
    "CONSUMER_NOT_FOUND": {"en": "Consumer number not found", "te": "వినియోగదారు సంఖ్య కనబడలేదు", "hi": "उपभोक्ता संख्या नहीं मिली"},
    "AMOUNT_WITHIN_HISTORY": {"en": "Amount is normal for this account", "te": "ఈ ఖాతాకు మొత్తం సాధారణంగా ఉంది", "hi": "इस खाते के लिए राशि सामान्य है"},
    "AMOUNT_SPIKE": {"en": "Amount is much higher than usual", "te": "మొత్తం సాధారణం కంటే చాలా ఎక్కువ", "hi": "राशि सामान्य से बहुत ज़्यादा है"},
    "DESTINATION_OFFICIAL": {"en": "Official payment channel", "te": "అధికారిక చెల్లింపు మార్గం", "hi": "आधिकारिक भुगतान माध्यम"},
    "DESTINATION_NOT_OFFICIAL": {"en": "Not an official payment channel", "te": "అధికారిక చెల్లింపు మార్గం కాదు", "hi": "आधिकारिक भुगतान माध्यम नहीं"},
    "LOOKALIKE_DOMAIN": {"en": "Fake website that imitates the real one", "te": "నిజమైన దాన్ని అనుకరించే నకిలీ వెబ్‌సైట్", "hi": "असली जैसी दिखने वाली नकली वेबसाइट"},
    "LOOKALIKE_VPA": {"en": "Fake UPI ID that imitates the real one", "te": "నిజమైన దాన్ని అనుకరించే నకిలీ UPI ID", "hi": "असली जैसी दिखने वाली नकली UPI ID"},
    "KNOWN_SCAM_DESTINATION": {"en": "On the known-scam list", "te": "తెలిసిన మోసాల జాబితాలో ఉంది", "hi": "ज्ञात धोखाधड़ी सूची में है"},
    "PERSONAL_PHONE_NUMBER": {"en": "Personal mobile number, not the biller's", "te": "వ్యక్తిగత మొబైల్ నంబర్, బిల్లర్‌ది కాదు", "hi": "निजी मोबाइल नंबर, बिलर का नहीं"},
    "APK_LINK": {"en": "Asks you to install an app file (.apk)", "te": "యాప్ ఫైల్ (.apk) ఇన్‌స్టాల్ చేయమంటోంది", "hi": "ऐप फ़ाइल (.apk) डाउनलोड करने को कहता है"},
    "SHORT_URL": {"en": "Link is hidden behind a short link", "te": "లింక్ షార్ట్ లింక్ వెనుక దాచబడింది", "hi": "लिंक छोटे लिंक के पीछे छिपा है"},
    "DISCONNECTION_THREAT": {"en": "Threatens to cut your connection", "te": "కనెక్షన్ కట్ చేస్తామని బెదిరిస్తోంది", "hi": "कनेक्शन काटने की धमकी"},
    "KYC_UPDATE_LURE": {"en": "Asks you to update KYC", "te": "KYC అప్‌డేట్ చేయమంటోంది", "hi": "KYC अपडेट करने को कहता है"},
    "REFUND_LURE": {"en": "Promises a refund or cashback", "te": "రీఫండ్ లేదా క్యాష్‌బ్యాక్ వాగ్దానం", "hi": "रिफंड या कैशबैक का वादा"},
    "URGENCY_PRESSURE": {"en": "Pressures you to act right now", "te": "వెంటనే చేయమని ఒత్తిడి చేస్తోంది", "hi": "तुरंत करने का दबाव"},
    "MISSED_BY_EXTRACTION": {"en": "Found an extra link or number in the image", "te": "చిత్రంలో అదనపు లింక్ లేదా నంబర్ కనబడింది", "hi": "चित्र में एक और लिंक या नंबर मिला"},
}  # fmt: skip
