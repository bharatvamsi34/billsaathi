// "Warn my family": a short warning in the user's language. No personal data: no amounts,
// consumer numbers, links, UPI IDs or phone numbers from the message are ever included.
import type { Lang } from "./i18n";
import type { Verdict } from "./timeline";

const TEXT: Record<"SCAM" | "CAUTION", Record<Lang, string>> = {
  SCAM: {
    en: "⚠️ Scam warning: I got a bill-payment message that BillSaathi flagged as a SCAM. Never pay through links, UPI IDs or phone numbers sent in messages. Pay bills only through the biller's official app or website.",
    te: "⚠️ మోసం హెచ్చరిక: నాకు వచ్చిన బిల్లు చెల్లింపు సందేశాన్ని BillSaathi మోసంగా గుర్తించింది. సందేశాల్లో వచ్చే లింక్‌లు, UPI IDలు, ఫోన్ నంబర్ల ద్వారా ఎప్పుడూ చెల్లించవద్దు. బిల్లులను బిల్లర్ అధికారిక యాప్ లేదా వెబ్‌సైట్‌లోనే చెల్లించండి.",
    hi: "⚠️ धोखाधड़ी की चेतावनी: मुझे मिले बिल भुगतान संदेश को BillSaathi ने धोखा बताया। संदेशों में भेजे गए लिंक, UPI ID या फ़ोन नंबर से कभी भुगतान न करें। बिल सिर्फ़ बिलर के आधिकारिक ऐप या वेबसाइट से भरें।",
  },
  CAUTION: {
    en: "⚠️ Be careful: BillSaathi could not confirm a bill-payment request I received. Before paying any bill, check it in the biller's official app or website.",
    te: "⚠️ జాగ్రత్త: నాకు వచ్చిన బిల్లు చెల్లింపు అభ్యర్థనను BillSaathi నిర్ధారించలేకపోయింది. ఏ బిల్లు చెల్లించే ముందైనా బిల్లర్ అధికారిక యాప్ లేదా వెబ్‌సైట్‌లో తనిఖీ చేయండి.",
    hi: "⚠️ सावधान: मुझे मिले बिल भुगतान अनुरोध की BillSaathi पुष्टि नहीं कर सका। कोई भी बिल भरने से पहले बिलर के आधिकारिक ऐप या वेबसाइट पर जाँचें।",
  },
};

const REPORT: Record<Lang, string> = {
  en: "Report fraud: call {value}.",
  te: "మోసాన్ని ఫిర్యాదు చేయండి: {value} కు కాల్ చేయండి.",
  hi: "धोखाधड़ी की शिकायत: {value} पर कॉल करें।",
};

export function warningText(verdict: Verdict, lang: Lang, helpline?: string): string | null {
  if (verdict === "SAFE") return null;
  const parts = [TEXT[verdict][lang]];
  if (helpline) parts.push(REPORT[lang].replace("{value}", helpline));
  return parts.join(" ");
}

/** Share with the Web Share API, or copy to the clipboard. Returns what happened. */
export async function shareWarning(text: string): Promise<"shared" | "copied" | "failed"> {
  try {
    if (typeof navigator !== "undefined" && navigator.share) {
      await navigator.share({ text });
      return "shared";
    }
    await navigator.clipboard.writeText(text);
    return "copied";
  } catch {
    return "failed";
  }
}
