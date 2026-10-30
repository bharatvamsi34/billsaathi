"use client";

import { useEffect, useRef, useState } from "react";
import Capture, { type CaptureInput } from "@/components/Capture";
import HowItWorks from "@/components/HowItWorks";
import PhoneQR from "@/components/PhoneQR";
import QuestionBox from "@/components/QuestionBox";
import Timeline from "@/components/Timeline";
import VerdictCard from "@/components/VerdictCard";
import { Dot, ShieldMark } from "@/components/icons";
import { ApiError, followEvents, sendAnswer, startCheck } from "@/lib/api";
import { LANGS, t, type Key } from "@/lib/i18n";
import { prepareImage } from "@/lib/image";
import { useLang } from "@/lib/useLang";
import { emptyTimeline, reduce, type Timeline as TL } from "@/lib/timeline";

const TEST_GUIDE = "https://github.com/bharatvamsi34/billsaathi/blob/main/docs/TESTING.md";

const ERRORS: Record<string, Key> = {
  rate_limited: "errRate",
  service_busy: "errBusy",
  unsupported_image: "errImage",
  image_too_large: "errImage",
};

export default function Home() {
  const [lang, setLang] = useLang();
  const [checkId, setCheckId] = useState<string | null>(null);
  const [tl, setTl] = useState<TL>(emptyTimeline);
  const [error, setError] = useState<Key | null>(null);
  const [busy, setBusy] = useState(false);
  const [highlight, setHighlight] = useState<number | null>(null);
  const stop = useRef<(() => void) | null>(null);
  const lastSeq = useRef(-1);

  useEffect(() => {
    document.documentElement.lang = lang; // right fonts and line height for Telugu / Hindi
  }, [lang]);

  const follow = (id: string, after: number) => {
    stop.current?.();
    stop.current = followEvents(
      id,
      after,
      (e) => {
        lastSeq.current = Math.max(lastSeq.current, e.seq);
        setTl((prev) => reduce(prev, e));
        if (e.type === "complete" || e.type === "question") setBusy(false);
      },
      () => {
        setError("errNetwork");
        setBusy(false);
      },
    );
  };

  const submit = async (input: CaptureInput) => {
    setError(null);
    setBusy(true);
    setTl(emptyTimeline);
    lastSeq.current = -1;
    window.scrollTo({ top: 0, behavior: "smooth" });
    try {
      const id =
        "text" in input
          ? await startCheck({ text: input.text, language: lang })
          : await startCheck({ image: await prepareImage(input.image), imageName: input.imageName, language: lang });
      setCheckId(id);
      follow(id, -1);
    } catch (e) {
      setError(e instanceof ApiError ? (ERRORS[e.code] ?? "errNetwork") : "errImage");
      setBusy(false);
    }
  };

  const answer = async (value: string) => {
    if (!checkId) return;
    setBusy(true);
    try {
      await sendAnswer(checkId, value);
      follow(checkId, lastSeq.current);
    } catch {
      setError("errNetwork");
      setBusy(false);
    }
  };

  const reset = () => {
    stop.current?.();
    setCheckId(null);
    setTl(emptyTimeline);
    setError(null);
    setBusy(false);
    setHighlight(null);
  };

  const showEvidence = (seq: number) => {
    setHighlight(seq);
    document.getElementById(`check-${seq}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  const checking = checkId !== null;

  // "How to test" opens the sample gallery; after a finished check it first goes back to capture.
  const goToSamples = (e: React.MouseEvent) => {
    e.preventDefault();
    if (checking && !busy) reset();
    requestAnimationFrame(() => document.getElementById("samples")?.scrollIntoView({ behavior: "smooth", block: "start" }));
  };

  return (
    <div className="mx-auto max-w-xl lg:max-w-none">
      <div className="sticky top-0 z-10 bg-caution-bg px-4 py-2 text-[14px] font-semibold leading-snug text-caution shadow-sm lg:px-[max(2rem,calc(50%-34rem))]" role="note">
        {t(lang, "banner")}
      </div>

      <header className="bg-ink px-4 pb-5 pt-4 text-white lg:flex lg:items-center lg:justify-between lg:gap-8 lg:px-[max(2rem,calc(50%-34rem))] lg:py-5">
        <div>
          <div className="flex items-center gap-2">
            <ShieldMark className="h-9 w-9" />
            <span className="text-2xl font-extrabold tracking-tight">BillSaathi</span>
            <a
              href="#samples"
              onClick={goToSamples}
              className="ml-auto whitespace-nowrap rounded-lg px-2 py-1 text-base font-bold text-saffron underline underline-offset-4 lg:ml-4"
            >
              {t(lang, "howToTest")}
            </a>
          </div>
          <p className="mt-2 text-lg leading-snug text-white/90">{t(lang, "tagline")}</p>
        </div>
        <div className="hidden lg:block">
          <PhoneQR lang={lang} />
        </div>
        <div role="group" aria-label={t(lang, "language")} className="mt-4 grid grid-cols-3 gap-1 rounded-xl bg-ink-soft p-1 lg:mt-0 lg:w-72 lg:shrink-0 xl:w-96">
          {LANGS.map((l) => (
            <button
              key={l.code}
              type="button"
              lang={l.code}
              aria-pressed={lang === l.code}
              onClick={() => setLang(l.code)}
              className={`min-h-11 rounded-lg px-2 text-base font-bold ${lang === l.code ? "bg-white text-ink" : "text-white/85"}`}
            >
              {l.name}
            </button>
          ))}
        </div>
      </header>

      {/* Phone: one column, wrappers are display:contents so the order and spacing stay as before.
          Desktop (lg): capture and samples on the left, the live check on the right, side by side. */}
      <main className="flex flex-col gap-5 px-4 py-5 lg:grid lg:grid-cols-2 lg:items-start lg:gap-8 lg:px-[max(2rem,calc(50%-34rem))] lg:py-8">
        <div className="contents lg:block lg:space-y-5">
          <div className="hidden lg:block">
            <HowItWorks lang={lang} />
          </div>
          <div className={checking ? "hidden lg:block" : undefined}>
            <Capture lang={lang} busy={busy} onSubmit={submit} />
          </div>
        </div>

        <div className="contents lg:sticky lg:top-14 lg:block lg:max-h-[calc(100dvh-4.5rem)] lg:space-y-5 lg:overflow-y-auto lg:p-1">
          {error && (
            <p role="alert" className="order-first rounded-xl bg-scam-bg p-3 font-semibold text-scam lg:order-none">
              {t(lang, error)}
            </p>
          )}

          {!checking && (
            <section className="hidden rounded-2xl border-2 border-dashed border-line p-6 lg:block">
              <h2 className="text-xl font-extrabold">{t(lang, "watchTitle")}</h2>
              <p className="mt-1 text-muted">{t(lang, "watchBody")}</p>
              <ol className="mt-5 space-y-3" aria-hidden="true">
                {(["stepReading", "stepFixed", "stepAgent", "stepJudge"] as const).map((k) => (
                  <li key={k} className="flex items-center gap-3 font-semibold text-muted">
                    <Dot className="h-6 w-6 shrink-0 text-line" />
                    {t(lang, k)}
                  </li>
                ))}
              </ol>
            </section>
          )}

          {checking && (
            <>
              {tl.verdict && <VerdictCard tl={tl} lang={lang} onShowEvidence={showEvidence} onReset={reset} />}
              {tl.question && !tl.verdict && <QuestionBox question={tl.question.question} lang={lang} onAnswer={answer} />}
              {!tl.verdict && (
                <p className="flex items-center gap-2 text-xl font-extrabold text-brand" aria-live="polite">
                  {t(lang, "checking")}
                </p>
              )}
              <section className="rounded-2xl border border-line bg-paper">
                {tl.verdict && <h2 className="px-1 pb-3 text-xl font-extrabold">{t(lang, "howChecked")}</h2>}
                <Timeline tl={tl} lang={lang} highlightSeq={highlight} />
              </section>
            </>
          )}
        </div>
      </main>

      <footer className="px-4 pb-8 pt-2 text-center text-sm text-muted">
        BillSaathi · Meta AI Developer Hackathon 2026 · Muse Spark on the Meta Model API ·{" "}
        <a href={TEST_GUIDE} className="font-semibold text-brand underline underline-offset-4">
          {t(lang, "testGuide")}
        </a>
      </footer>
    </div>
  );
}
