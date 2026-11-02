"use client";

import { useEffect, useState } from "react";
import { t, type Lang } from "@/lib/i18n";
import { speak, speechSupported, stopSpeaking } from "@/lib/speech";
import { SpeakerIcon, Spinner } from "./icons";

/** The verdict explained in the user's language, with a "Listen" button. */
export default function Explanation({ text, headline, lang }: { text: string | null; headline: string; lang: Lang }) {
  const [playing, setPlaying] = useState(false);
  const [noVoice, setNoVoice] = useState(false);

  useEffect(() => stopSpeaking, []); // stop reading when the card goes away

  if (!text) {
    return (
      <p className="flex items-center gap-2 rounded-xl bg-brand-soft p-3 font-semibold text-brand" aria-live="polite">
        <Spinner className="h-5 w-5" />
        {t(lang, "explaining")}
      </p>
    );
  }

  const listen = () => {
    if (playing) {
      stopSpeaking();
      setPlaying(false);
      return;
    }
    // The template explanation already starts with the headline.
    const spoken = text.startsWith(headline) ? text.replaceAll(" · ", ". ") : `${headline} ${text}`;
    const started = speak(spoken, lang, () => setPlaying(false));
    setPlaying(started);
    setNoVoice(!started);
  };

  return (
    <div className="rise rounded-xl bg-brand-soft p-3">
      <p lang={lang} className="text-[17px] leading-relaxed">
        {text}
      </p>
      {speechSupported() && (
        <button
          type="button"
          onClick={listen}
          aria-pressed={playing}
          className="mt-2 inline-flex min-h-11 items-center gap-2 rounded-lg border-2 border-brand bg-card px-3 font-bold text-brand active:translate-y-px"
        >
          <SpeakerIcon className="h-5 w-5" />
          {t(lang, playing ? "stopListening" : "listen")}
        </button>
      )}
      {noVoice && <p className="mt-1 text-sm text-muted">{t(lang, "noVoice")}</p>}
    </div>
  );
}
