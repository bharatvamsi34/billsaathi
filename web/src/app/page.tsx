"use client";

import { useEffect, useRef, useState } from "react";
import { MotionConfig } from "motion/react";
import Link from "next/link";
import Capture, { sampleInput, type CaptureInput } from "@/components/Capture";
import Guide from "@/components/Guide";
import Hero, { ProofStrip, type QuickSample } from "@/components/Hero";
import InputReview, { type ReviewInput } from "@/components/InputReview";
import QuestionBox from "@/components/QuestionBox";
import Replay from "@/components/Replay";
import Timeline from "@/components/Timeline";
import TopBar from "@/components/TopBar";
import Trace from "@/components/Trace";
import { Button, Card } from "@/components/ui";
import VerdictCard from "@/components/VerdictCard";
import samples from "@/samples.generated.json";
import { ApiError, followEvents, sendAnswer, startCheck } from "@/lib/api";
import { scrollBehavior, useDemoMode } from "@/lib/demo";
import { t, type Key } from "@/lib/i18n";
import { prepareImage } from "@/lib/image";
import { useLang } from "@/lib/useLang";
import { emptyTimeline, reduce, type Timeline as TL } from "@/lib/timeline";

const GUTTER = "lg:px-[max(2rem,calc(50%-38rem))]";
const STALL_MS = 90_000;
const TEST_GUIDE = "https://github.com/bharatvamsi34/billsaathi/blob/main/docs/TESTING.md";

const ERRORS: Record<string, Key> = {
  rate_limited: "errRate",
  privacy_unavailable: "errPrivacy",
  service_busy: "errBusy",
  unsupported_image: "errImage",
  image_too_large: "errImage",
};

function scrollToResults() {
  requestAnimationFrame(() => document.getElementById("results-top")?.scrollIntoView({ behavior: scrollBehavior(), block: "start" }));
}

export default function Home() {
  const [lang, setLang] = useLang();
  const demo = useDemoMode();
  const [checkId, setCheckId] = useState<string | null>(null);
  const [tl, setTl] = useState<TL>(emptyTimeline);
  const [error, setError] = useState<Key | null>(null);
  const [busy, setBusy] = useState(false);
  const [highlight, setHighlight] = useState<number | null>(null);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [review, setReview] = useState<ReviewInput>(null);
  const [privacy, setPrivacy] = useState(false);
  const [replaying, setReplaying] = useState(false);
  const [traceOpen, setTraceOpen] = useState(false);
  const [lastInput, setLastInput] = useState<CaptureInput | null>(null);
  const stop = useRef<(() => void) | null>(null);
  const lastSeq = useRef(-1);
  const lastEventAt = useRef(0);

  useEffect(() => {
    document.documentElement.lang = lang; // right fonts and line height for Telugu / Hindi
  }, [lang]);

  useEffect(() => {
    if (demo) document.documentElement.dataset.demo = "1";
  }, [demo]);

  // The verdict is the moment to read: bring it into view, under the sticky bar.
  const hasVerdict = !!tl.verdict;
  useEffect(() => {
    if (hasVerdict) scrollToResults();
  }, [hasVerdict]);

  // A slow or lost connection must not leave a spinner forever: after this long with no event,
  // show the friendly error with a retry. A check normally takes well under a minute.
  useEffect(() => {
    if (!busy || !checkId) return;
    const id = setInterval(() => {
      if (Date.now() - lastEventAt.current > STALL_MS) {
        stop.current?.();
        setError("errNetwork");
        setBusy(false);
      }
    }, 2000);
    return () => clearInterval(id);
  }, [busy, checkId]);

  const follow = (id: string, after: number) => {
    stop.current?.();
    lastEventAt.current = Date.now();
    stop.current = followEvents(
      id,
      after,
      (e) => {
        lastEventAt.current = Date.now();
        lastSeq.current = Math.max(lastSeq.current, e.seq);
        const receivedAt = Date.now();
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
    let url: string | null = null;
    setImageUrl((old) => {
      if (old) URL.revokeObjectURL(old);
      url = image ? URL.createObjectURL(image) : null;
      return url;
    });
    return () => url;
  };

  const submit = async (input: CaptureInput) => {
    setError(null);
    setBusy(true);
    setReplaying(false);
    setTraceOpen(false);
    setHighlight(null);
    setTl(emptyTimeline);
    setCheckId(null);
    setLastInput(input);
    lastSeq.current = -1;
    const url = "image" in input ? URL.createObjectURL(input.image) : null;
    setImageUrl((old) => {
      if (old) URL.revokeObjectURL(old);
      return url;
    });
    setReview("text" in input ? { kind: "text", text: input.text } : "image" in input ? { kind: "image", url: url! } : { kind: "audio", url: input.audioUrl });
    scrollToResults();
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
    setReview(null);
    setReplaying(false);
    setTraceOpen(false);
    setLastInput(null);
    showImage(null);
    window.scrollTo({ top: 0, behavior: scrollBehavior() });
  };

  const showEvidence = (seq: number) => {
    setHighlight(seq);
    setTraceOpen(true);
    // After the trace has opened.
    setTimeout(() => document.getElementById(`check-${seq}`)?.scrollIntoView({ behavior: scrollBehavior(), block: "center" }), 260);
  };

  const startReplay = () => {
    stop.current?.();
    setBusy(false);
    setCheckId(null);
    setTl(emptyTimeline);
    setReview(null);
    setError(null);
    setReplaying(true);
    scrollToResults();
  };

  const checking = review !== null;
  const showResults = checking || replaying || !!error;
  const runSample = async (id: string) => {
    const sample = samples.find((s) => s.id === id);
    if (sample) void submit(await sampleInput(sample));
  };
  const scamSample = lang === "te" ? "scam_te_known_vpa" : lang === "hi" ? "scam_hi_kyc_apk" : "scam_en_known_vpa";
  const quick = (s: QuickSample) => {
    const ids: Record<QuickSample, string> = { scam: scamSample, tampered: "demo_tampered_same_account", genuine: "photo_genuine_demo", voice: "demo_voice_note" };
    void runSample(ids[s]);
  };

  return (
    <MotionConfig reducedMotion="user">
      <TopBar lang={lang} onLang={setLang} privacy={privacy} onPrivacy={setPrivacy} busy={busy} onBack={showResults ? reset : null} />

      {/* Phone: while a check runs the hero steps aside, so the result fits the first screen. */}
      <div className={showResults ? "hidden lg:block" : undefined}>
        <Hero lang={lang} busy={busy} onQuick={quick} />
        {!demo && <Guide lang={lang} step={tl.verdict ? 3 : checking ? 2 : 1} />}
      </div>

      <main id="workspace" className={`flex flex-col gap-4 px-4 py-4 lg:grid lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:items-start lg:gap-8 lg:py-6 ${GUTTER}`}>
        <div className={`lg:sticky lg:top-[calc(var(--topbar-h)+1rem)] ${showResults ? "hidden lg:block" : ""}`}>
          <Capture lang={lang} busy={busy} onSubmit={submit} onReplay={startReplay} />
        </div>

        <div className="min-w-0 space-y-3">
          {!showResults && (
            <Card className="hidden p-4 lg:block">
              <h2 className="t-title">{t(lang, "watchTitle")}</h2>
              <p className="mb-2 mt-1 text-[15px] text-muted">{t(lang, "watchBody")}</p>
              <Timeline tl={emptyTimeline} lang={lang} highlightSeq={null} imageUrl={null} idle />
            </Card>
          )}

          {replaying && <Replay lang={lang} onClose={reset} />}

          {checking && <InputReview input={review} tl={tl} lang={lang} />}

          {error && (
            <div role="alert" id={checking ? undefined : "results-top"} className="rise rounded-2xl border border-scam/30 bg-scam-bg p-4">
              <p className="font-semibold text-scam">{t(lang, error)}</p>
              {lastInput && (
                <Button variant="secondary" className="mt-3" onClick={() => void submit(lastInput)} data-testid="retry">
                  {t(lang, "retry")}
                </Button>
              )}
            </div>
          )}

          {checking && tl.privacy && (
            <div className="t-caption rise space-y-0.5 rounded-2xl bg-navy px-3.5 py-2.5 font-semibold text-white" data-testid="privacy-bar">
              <p>{t(lang, "privacyActive")}</p>
              {tl.input === "image" && <p className="font-normal text-white/80">{t(lang, "photoCropSkipped")}</p>}
            </div>
          )}

          {checking && !error && (
            <>
              {tl.verdict && <VerdictCard key={checkId ?? "verdict"} checkId={checkId} tl={tl} lang={lang} onShowEvidence={showEvidence} onReset={reset} />}
              {tl.question && !tl.verdict && <QuestionBox question={tl.question.question} field={tl.question.field} biller={tl.extracted?.biller_name.value} lang={lang} onAnswer={answer} />}
              {!tl.verdict && !tl.question && (
                <div
                  data-testid="status"
                  data-step={tl.early ?? undefined}
                  aria-live="polite"
                  className={`flex min-h-16 items-center gap-2 rounded-2xl px-4 py-3 text-[17px] font-semibold shadow-soft transition-colors duration-200 ${
                    tl.early === "scam_signals" ? "border border-caution-line bg-caution-bg text-caution" : "bg-navy text-white"
                  }`}
                >
                  {tl.early === "scam_signals" && <span aria-hidden="true">⚠️</span>}
                  {t(lang, tl.early === "scam_signals" ? "earlyScam" : tl.early ? "earlyChecking" : "checking")}
                </div>
              )}
              {tl.verdict ? (
                <Trace tl={tl} lang={lang} open={traceOpen} onToggle={() => setTraceOpen(!traceOpen)} highlightSeq={highlight} imageUrl={imageUrl} />
              ) : (
                <Card className="p-2">
                  <Timeline tl={tl} lang={lang} highlightSeq={highlight} imageUrl={imageUrl} />
                </Card>
              )}
            </>
          )}
        </div>
      </main>

      <ProofStrip lang={lang} />

      <footer className={`t-caption px-4 py-6 text-center text-muted ${GUTTER}`}>
        BillSaathi · Meta Global AI Developer Hackathon 2026 ·{" "}
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
    </MotionConfig>
  );
}
