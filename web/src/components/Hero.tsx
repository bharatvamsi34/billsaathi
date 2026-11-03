"use client";

import Link from "next/link";
import results from "@/eval.generated.json";
import { t, type Lang } from "@/lib/i18n";
import ModelBadge, { type Model } from "./ModelBadge";
import PhoneQR from "./PhoneQR";
import { Button, Chip } from "./ui";

const SOURCE = "https://www.theweek.in/wire-updates/business/2025/07/22/del23-lsq-cyber-fraud.html";

const MODELS: [Model, "modelSpark" | "modelSam" | "modelVoice" | "modelOpen" | "modelImage"][] = [
  ["spark", "modelSpark"],
  ["sam", "modelSam"],
  ["voice", "modelVoice"],
  ["open", "modelOpen"],
  ["image", "modelImage"],
];

export type QuickSample = "scam" | "tampered" | "genuine" | "voice";

function Stat({ lang }: { lang: Lang }) {
  return (
    <div>
      <p className="text-[1.375rem] font-bold leading-tight tracking-tight text-white">{t(lang, "statValue")}</p>
      <p className="mt-1 text-[15px] leading-snug text-white/85">{t(lang, "statLabel")}</p>
      <a href={SOURCE} target="_blank" rel="noreferrer" className="t-caption mt-1 inline-flex min-h-6 items-center text-white/70 underline underline-offset-2 hover:text-white">
        {t(lang, "statSource")}
      </a>
    </div>
  );
}

function EvalProof({ lang }: { lang: Lang }) {
  const best = (results.configs as Record<string, { correct: number; n: number; false_safe: number; risky: number; latency_p50_s: number }>)["spark-low"];
  if (!best) return null;
  return (
    <Link href="/eval" className="block rounded-2xl border border-white/15 bg-white/[0.07] p-3.5 transition-colors duration-150 hover:bg-white/[0.12]">
      <span className="grid grid-cols-3 gap-2">
        {[
          [`${best.correct}/${best.n}`, "statCorrect"],
          [`${best.false_safe}/${best.risky}`, "statFalseSafe"],
          [`${best.latency_p50_s.toFixed(1)} s`, "statLatency"],
        ].map(([value, label]) => (
          <span key={label}>
            <span className="block text-lg font-bold tabular-nums">{value}</span>
            <span className="t-caption block text-white/75">{t(lang, label as "statCorrect")}</span>
          </span>
        ))}
      </span>
      <span className="t-caption mt-2 block font-semibold text-[#9cc3ff]">{t(lang, "statMore", { n: best.n })}&nbsp;→</span>
    </Link>
  );
}

export default function Hero({ lang, busy, onQuick }: { lang: Lang; busy: boolean; onQuick: (s: QuickSample) => void }) {
  return (
    <section className="hero-glow px-4 pb-5 pt-4 text-white lg:px-[max(2rem,calc(50%-38rem))] lg:pb-8 lg:pt-8">
      <div className="lg:grid lg:grid-cols-[minmax(0,1.55fr)_minmax(0,1fr)] lg:items-start lg:gap-12">
        <div>
          <h1 className="t-display">{t(lang, "heroTitle")}</h1>
          <p className="mt-2 max-w-2xl text-[15px] leading-relaxed text-white/85 lg:mt-3 lg:text-lg">{t(lang, "heroBody")}</p>
          <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center lg:mt-5 lg:gap-3">
            <Button variant="onDark" size="lg" disabled={busy} onClick={() => onQuick("scam")} data-testid="cta-scam">
              {t(lang, "tryScam")}
            </Button>
            <span className="hidden lg:contents">
              <Button variant="onDarkGhost" size="lg" disabled={busy} onClick={() => onQuick("genuine")} data-testid="cta-genuine">
                {t(lang, "tryGenuine")}
              </Button>
            </span>
          </div>
          {/* Phone: one tap to every kind of sample, right at the top. */}
          <div className="mt-3 grid grid-cols-2 gap-2 lg:hidden">
            {(
              [
                ["tampered", "chipTampered"],
                ["genuine", "chipGenuine"],
                ["voice", "chipVoice"],
                ["scam", "chipScam"],
              ] as const
            ).map(([sample, label]) => (
              <Chip key={sample} disabled={busy} onClick={() => onQuick(sample)} className="border-white/30! bg-white/10! text-white!">
                {t(lang, label)}
              </Chip>
            ))}
          </div>
          <p className="t-caption mt-3 text-white/70">{t(lang, "heroSim")}</p>
        </div>
        <div className="hidden space-y-4 lg:block">
          <Stat lang={lang} />
          <EvalProof lang={lang} />
        </div>
      </div>
    </section>
  );
}

/** The Meta models at work, and on a phone the stat and the measured results, below the workspace. */
export function ProofStrip({ lang }: { lang: Lang }) {
  return (
    <>
      <section className="hero-glow space-y-4 px-4 py-5 text-white lg:hidden">
        <Stat lang={lang} />
        <EvalProof lang={lang} />
      </section>
      <section aria-labelledby="models-title" className="border-y border-line bg-card px-4 py-4 lg:px-[max(2rem,calc(50%-38rem))]">
        <div className="lg:flex lg:items-center lg:gap-6">
          <h2 id="models-title" className="mb-3 text-sm font-bold leading-tight lg:mb-0 lg:w-24 lg:shrink-0">
            {t(lang, "modelsTitle")}
          </h2>
          <ul className="grid flex-1 grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
            {MODELS.map(([model, job]) => (
              <li key={model}>
                <ModelBadge model={model} lang={lang} />
                <p className="t-caption mt-1 text-muted">{t(lang, job)}</p>
              </li>
            ))}
          </ul>
          <div className="hidden shrink-0 xl:block">
            <PhoneQR lang={lang} />
          </div>
        </div>
      </section>
    </>
  );
}
