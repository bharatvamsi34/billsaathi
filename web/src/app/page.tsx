"use client";

import { useEffect, useRef, useState } from "react";
import { MotionConfig } from "motion/react";
import Link from "next/link";
import Capture, { sampleInput, type CaptureInput } from "@/components/Capture";
import Guide from "@/components/Guide";
import Hero from "@/components/Hero";
import QuestionBox from "@/components/QuestionBox";
import Timeline from "@/components/Timeline";
import VerdictCard from "@/components/VerdictCard";
import { ShieldMark } from "@/components/icons";
import samples from "@/samples.generated.json";
import { ApiError, followEvents, sendAnswer, startCheck } from "@/lib/api";
import { LANGS, t, type Key } from "@/lib/i18n";
import { prepareImage } from "@/lib/image";
import { useLang } from "@/lib/useLang";
import { emptyTimeline, reduce, type Timeline as TL } from "@/lib/timeline";

const GUTTER = "lg:px-[max(2rem,calc(50%-34rem))]";
const TEST_GUIDE = "https://github.com/bharatvamsi34/billsaathi/blob/main/docs/TESTING.md";

const ERRORS: Record<string, Key> = {
  rate_limited: "errRate",
  privacy_unavailable: "errPrivacy",
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
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [privacy, setPrivacy] = useState(false);
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
        const receivedAt = performance.now();
        setTl((prev) => reduce(prev, { ...e, receivedAt }));
        if (e.type === "complete" || e.type === "question") setBusy(false);
      },
      () => {
        setError("errNetwork");
        setBusy(false);
      },
    );
  };

  const showImage = (image: Blob | null) => {
    setImageUrl((old) => {
      if (old) URL.revokeObjectURL(old);
      return image ? URL.createObjectURL(image) : null;
    });
  };

  const submit = async (input: CaptureInput) => {
    setError(null);
    setBusy(true);
    setTl(emptyTimeline);
    lastSeq.current = -1;
    if (window.matchMedia("(min-width: 1024px)").matches) {
      document.getElementById("workspace")?.scrollIntoView({ behavior: "smooth", block: "start" });
    } else {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
    showImage("image" in input ? input.image : null);
    try {
      const id =
        "text" in input
          ? await startCheck({ text: input.text, language: lang, privacy })
          : "audio" in input
            ? await startCheck({ audio: input.audio, language: lang, privacy })
            : await startCheck({ image: await prepareImage(input.image), imageName: input.imageName, language: lang, privacy });
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
    showImage(null);
  };

  const showEvidence = (seq: number) => {
    setHighlight(seq);
    document.getElementById(`check-${seq}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  const checking = checkId !== null;
  const runSample = async (id: string) => {
    const sample = samples.find((s) => s.id === id);
    if (sample) void submit(await sampleInput(sample));
  };
  const scamSample = lang === "te" ? "scam_te_known_vpa" : lang === "hi" ? "scam_hi_kyc_apk" : "scam_en_known_vpa";

  // "How to test" opens the sample gallery; after a finished check it first goes back to capture.
  const goToSamples = (e: React.MouseEvent) => {
    e.preventDefault();
    if (checking && !busy) reset();
    requestAnimationFrame(() => document.getElementById("samples")?.scrollIntoView({ behavior: "smooth", block: "start" }));
  };

  return (
    <MotionConfig reducedMotion="user">
      <div className="mx-auto max-w-xl lg:max-w-none">
        <div className={`sticky top-0 z-10 bg-caution-bg px-4 py-2 text-[14px] font-semibold leading-snug text-caution shadow-sm ${GUTTER}`} role="note">
          {t(lang, "banner")}
        </div>

        <header className={`bg-ink px-4 pb-5 pt-4 text-white lg:flex lg:items-center lg:gap-6 lg:py-3 ${GUTTER}`}>
          <div className="flex items-center gap-2">
            <ShieldMark className="h-9 w-9" />
            <span className="text-2xl font-extrabold tracking-tight">BillSaathi</span>
            <a href="#samples" onClick={goToSamples} className="ml-auto whitespace-nowrap rounded-lg px-2 py-1 text-base font-bold text-saffron underline underline-offset-4 lg:ml-4">
              {t(lang, "howToTest")}
            </a>
            <Link href="/eval" className="hidden whitespace-nowrap rounded-lg px-2 py-1 text-base font-bold text-saffron underline underline-offset-4 lg:inline">
              {t(lang, "evalLink")}
            </Link>
          </div>
          <p className="mt-2 text-lg leading-snug text-white/90 lg:hidden">{t(lang, "tagline")}</p>
          <div role="group" aria-label={t(lang, "language")} className="mt-4 grid grid-cols-3 gap-1 rounded-xl bg-ink-soft p-1 lg:ml-auto lg:mt-0 lg:w-80 lg:shrink-0">
            {LANGS.map((l) => (
              <button
                key={l.code}
                type="button"
                lang={l.code}
                aria-pressed={lang === l.code}
                onClick={() => setLang(l.code)}
                className={`min-h-11 rounded-lg px-2 text-base font-bold transition-colors lg:min-h-9 ${lang === l.code ? "bg-white text-ink" : "text-white/85"}`}
              >
                {l.name}
              </button>
            ))}
          </div>
        </header>

        <Hero lang={lang} busy={busy} onScam={() => runSample(scamSample)} onGenuine={() => runSample("photo_genuine_demo")} />
        <Guide lang={lang} step={tl.verdict ? 3 : checking ? 2 : 1} />

        {/* Phone: one column; the wrappers are display:contents, so order and spacing stay simple.
            Desktop (lg): samples and capture on the left, the live check on the right. */}
        <main id="workspace" className={`flex scroll-mt-10 flex-col gap-5 px-4 py-5 lg:grid lg:grid-cols-2 lg:items-start lg:gap-8 lg:py-6 ${GUTTER}`}>
          <div className={checking ? "hidden lg:block" : undefined}>
            <Capture lang={lang} busy={busy} privacy={privacy} onPrivacy={setPrivacy} onSubmit={submit} />
          </div>

          <div className="contents lg:sticky lg:top-11 lg:block lg:max-h-[calc(100dvh-3.5rem)] lg:space-y-5 lg:overflow-y-auto lg:p-1">
            {error && (
              <p role="alert" className="order-first rounded-xl bg-scam-bg p-3 font-semibold text-scam lg:order-none">
                {t(lang, error)}
              </p>
            )}

            {!checking && (
              <section className="hidden rounded-2xl border border-line bg-paper p-4 lg:block">
                <h2 className="text-xl font-extrabold">{t(lang, "watchTitle")}</h2>
                <p className="mb-4 mt-1 text-muted">{t(lang, "watchBody")}</p>
                <Timeline tl={emptyTimeline} lang={lang} highlightSeq={null} imageUrl={null} idle />
              </section>
            )}

            {checking && (
              <>
                {tl.verdict && <VerdictCard key={checkId} checkId={checkId} tl={tl} lang={lang} onShowEvidence={showEvidence} onReset={reset} />}
                {tl.question && !tl.verdict && <QuestionBox question={tl.question.question} lang={lang} onAnswer={answer} />}
                {!tl.verdict && !tl.question && (
                  <div
                    data-step={tl.early ? "early" : undefined}
                    className={`rounded-2xl px-4 py-5 text-xl font-extrabold text-white shadow-md transition-colors duration-300 ${tl.early === "scam_signals" ? "bg-scam" : "bg-ink"}`}
                    aria-live="polite"
                  >
                    {t(lang, tl.early === "scam_signals" ? "earlyScam" : tl.early ? "earlyChecking" : "checking")}
                  </div>
                )}
                <section className="rounded-2xl border border-line bg-paper p-3">
                  {tl.verdict && <h2 className="pb-3 text-xl font-extrabold">{t(lang, "howChecked")}</h2>}
                  <Timeline tl={tl} lang={lang} highlightSeq={highlight} imageUrl={imageUrl} />
                </section>
              </>
            )}
          </div>
        </main>

        <footer className="px-4 pb-8 pt-2 text-center text-sm text-muted">
          BillSaathi · Meta AI Developer Hackathon 2026 ·{" "}
          <Link href="/eval" className="font-semibold text-brand underline underline-offset-4">
            {t(lang, "evalLink")}
          </Link>{" "}
          ·{" "}
          <a href={TEST_GUIDE} className="font-semibold text-brand underline underline-offset-4">
            {t(lang, "testGuide")}
          </a>{" "}
          ·{" "}
          <Link href="/privacy" className="font-semibold text-brand underline underline-offset-4">
            {t(lang, "privacy")}
          </Link>
        </footer>
      </div>
    </MotionConfig>
  );
}
