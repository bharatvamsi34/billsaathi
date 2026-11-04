"use client";

import { useEffect, useState } from "react";
import { LANGS, t, type Lang } from "@/lib/i18n";
import { speak, speechSupported, stopSpeaking } from "@/lib/speech";
import { SpeakerIcon, Spinner } from "./icons";
import { Button, Skeleton } from "./ui";

/** Read the explanation aloud, in the actions row. */
export function ListenButton({ text, headline, lang, textLang }: { text: string | null; headline: string; lang: Lang; textLang: Lang }) {
  const [playing, setPlaying] = useState(false);
  const [noVoice, setNoVoice] = useState(false);
  useEffect(() => stopSpeaking, []); // stop reading when the card goes away
  if (!speechSupported()) return null;
  const listen = () => {
    if (!text) return;
    if (playing) {
      stopSpeaking();
      setPlaying(false);
      return;
    }
    // The template explanation already starts with the headline.
    const spoken = text.startsWith(headline) ? text.replaceAll(" · ", ". ") : `${headline} ${text}`;
    const started = speak(spoken, textLang, () => setPlaying(false)); // the voice follows the text, not the UI
    setPlaying(started);
    setNoVoice(!started);
  };
  return (
    <div className="min-w-0">
      <Button variant="secondary" disabled={!text} onClick={listen} aria-pressed={playing} className="w-full">
        {text ? <SpeakerIcon className="h-5 w-5" /> : <Spinner className="h-5 w-5" />}
        {t(lang, !text ? "explaining" : playing ? "stopListening" : "listen")}
      </Button>
      {noVoice && <p className="t-caption mt-1 text-muted">{t(lang, "noVoice")}</p>}
    </div>
  );
}

/** The verdict explained in the user's language. Its height is reserved so nothing jumps. */
export default function Explanation({ text, lang, textLang }: { text: string | null; lang: Lang; textLang: Lang }) {
  return (
    <div className="min-h-[6.25rem] rounded-2xl bg-brand-soft/60 p-3.5" aria-live="polite" data-testid="explanation">
      {text ? (
        <>
          {textLang !== lang && (
            <p className="t-caption mb-1 font-semibold text-brand" data-testid="explanation-language">
              {t(lang, "explainFrom", { lang: LANGS.find((l) => l.code === textLang)?.name ?? textLang })}
            </p>
          )}
          <p lang={textLang} className="wrap-words rise text-[15px] leading-relaxed">
            {text}
          </p>
        </>
      ) : (
        <>
          <p className="t-caption mb-2 font-semibold text-brand">{t(lang, "explaining")}</p>
          <Skeleton lines={3} />
        </>
      )}
    </div>
  );
}
