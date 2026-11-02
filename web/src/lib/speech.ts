// "Listen": read the verdict aloud with the browser's own speech synthesis (no server, no cost).
import type { Lang } from "./i18n";

const BCP47: Record<Lang, string> = { en: "en-IN", te: "te-IN", hi: "hi-IN" };

/** Best voice for a language: exact locale first, then the same language in any region. */
export function pickVoice<V extends { lang: string }>(voices: V[], lang: Lang): V | null {
  const want = BCP47[lang].toLowerCase();
  const norm = (v: V) => v.lang.replace("_", "-").toLowerCase();
  return voices.find((v) => norm(v) === want) ?? voices.find((v) => norm(v).split("-")[0] === lang) ?? null;
}

export function speechSupported(): boolean {
  return typeof window !== "undefined" && "speechSynthesis" in window;
}

export function stopSpeaking(): void {
  if (speechSupported()) window.speechSynthesis.cancel();
}

/** Speak the text. Returns false when this device has no voice for the language. */
export function speak(text: string, lang: Lang, onEnd: () => void): boolean {
  if (!speechSupported()) return false;
  const voices = window.speechSynthesis.getVoices();
  const voice = pickVoice(voices, lang);
  if (voices.length > 0 && !voice) return false;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = BCP47[lang];
  if (voice) utterance.voice = voice;
  utterance.rate = 0.95;
  utterance.onend = onEnd;
  utterance.onerror = onEnd;
  window.speechSynthesis.speak(utterance);
  return true;
}
