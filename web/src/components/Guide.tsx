"use client";

import { useState, useSyncExternalStore } from "react";
import { t, type Lang } from "@/lib/i18n";

const KEY = "billsaathi.guide-dismissed";
const noSubscribe = () => () => {};

function seenBefore(): boolean {
  try {
    return localStorage.getItem(KEY) === "1";
  } catch {
    return false;
  }
}

/** First visit, desktop: the three steps, with the current one lit. Dismissible, and stays dismissed. */
export default function Guide({ lang, step }: { lang: Lang; step: 1 | 2 | 3 }) {
  const seen = useSyncExternalStore(noSubscribe, seenBefore, () => true); // nothing flashes before hydration
  const [closed, setClosed] = useState(false);
  if (seen || closed) return null;

  const close = () => {
    setClosed(true);
    try {
      localStorage.setItem(KEY, "1");
    } catch {}
  };

  return (
    <div className="hidden items-center gap-4 border-b border-line bg-brand-soft px-[max(2rem,calc(50%-34rem))] py-2.5 lg:flex" role="note">
      <ol className="flex flex-1 items-center gap-3">
        {(["guide1", "guide2", "guide3"] as const).map((key, i) => (
          <li key={key} className={`flex items-center gap-2 font-bold ${step === i + 1 ? "text-brand" : "text-muted"}`}>
            <span className={`flex h-6 w-6 items-center justify-center rounded-full text-sm ${step === i + 1 ? "bg-brand text-white" : "bg-card text-muted"}`}>{i + 1}</span>
            {t(lang, key)}
            {i < 2 && (
              <span aria-hidden="true" className="ml-1 text-muted">
                →
              </span>
            )}
          </li>
        ))}
      </ol>
      <button type="button" onClick={close} className="rounded-lg px-3 py-1 font-bold text-brand underline underline-offset-4">
        {t(lang, "guideClose")}
      </button>
    </div>
  );
}
