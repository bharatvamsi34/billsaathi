import Link from "next/link";
import results from "@/eval.generated.json";
import { t, type Lang } from "@/lib/i18n";
import ModelBadge, { type Model } from "./ModelBadge";
import PhoneQR from "./PhoneQR";

const SOURCE = "https://www.theweek.in/wire-updates/business/2025/07/22/del23-lsq-cyber-fraud.html";

const MODELS: [Model, "modelSpark" | "modelSam" | "modelVoice" | "modelOpen" | "modelImage"][] = [
  ["spark", "modelSpark"],
  ["sam", "modelSam"],
  ["voice", "modelVoice"],
  ["open", "modelOpen"],
  ["image", "modelImage"],
];

/** Desktop only: the problem, one real number, one big button, and proof it was measured. */
export default function Hero({ lang, busy, onScam, onGenuine }: { lang: Lang; busy: boolean; onScam: () => void; onGenuine: () => void }) {
  const best = (results.configs as Record<string, { correct: number; n: number; false_safe: number; risky: number; latency_p50_s: number; cost_per_check_usd: number }>)["spark-low"];
  return (
    <div className="hidden lg:block">
      <section className="bg-ink px-[max(2rem,calc(50%-34rem))] pb-6 pt-1 text-white">
        <div className="grid grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)] items-start gap-10">
          <div>
            <h1 className="text-[2rem] font-extrabold leading-[1.15] tracking-tight xl:text-[2.5rem]">
              {t(lang, "heroTitle")
                .split(/(?<=[.।])\s+/)
                .map((sentence) => (
                  <span key={sentence} className="block">
                    {sentence}
                  </span>
                ))}
            </h1>
            <p className="mt-2 max-w-2xl leading-snug text-white/85 xl:text-lg">{t(lang, "intro")}</p>
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <button
                type="button"
                disabled={busy}
                onClick={onScam}
                className="min-h-14 rounded-xl bg-saffron px-7 text-lg font-extrabold text-ink shadow-md transition-transform hover:-translate-y-px active:translate-y-px disabled:opacity-60"
              >
                {t(lang, "tryScam")}
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={onGenuine}
                className="min-h-14 rounded-xl border-2 border-white/40 px-5 font-bold text-white transition-colors hover:border-white disabled:opacity-60"
              >
                {t(lang, "tryGenuine")}
              </button>
            </div>
          </div>
          <div className="space-y-3">
            <div className="border-l-4 border-saffron pl-4">
              <p className="text-[1.75rem] font-extrabold leading-none text-saffron xl:text-[2rem]">{t(lang, "statValue")}</p>
              <p className="mt-1 text-[15px] leading-snug text-white/90 xl:text-base">{t(lang, "statLabel")}</p>
              <a href={SOURCE} target="_blank" rel="noreferrer" className="mt-1 inline-block text-sm text-white/70 underline underline-offset-2 hover:text-white">
                {t(lang, "statSource")}
              </a>
            </div>
            {best && (
              <Link href="/eval" className="block rounded-xl bg-ink-soft p-3 transition-colors hover:bg-[#2c4c6e]">
                <span className="grid grid-cols-3 gap-2">
                  <span>
                    <span className="block text-xl font-extrabold tabular-nums">
                      {best.correct}/{best.n}
                    </span>
                    <span className="block text-sm leading-tight text-white/80">{t(lang, "statCorrect")}</span>
                  </span>
                  <span>
                    <span className="block text-xl font-extrabold tabular-nums">
                      {best.false_safe}/{best.risky}
                    </span>
                    <span className="block text-sm leading-tight text-white/80">{t(lang, "statFalseSafe")}</span>
                  </span>
                  <span>
                    <span className="block text-xl font-extrabold tabular-nums">{best.latency_p50_s.toFixed(1)} s</span>
                    <span className="block text-sm leading-tight text-white/80">{t(lang, "statLatency")}</span>
                  </span>
                </span>
                <span className="mt-1.5 block text-sm font-bold leading-snug text-saffron">
                  {t(lang, "statMore", { n: best.n })} →
                </span>
              </Link>
            )}
          </div>
        </div>
      </section>

      <section aria-labelledby="models-title" className="border-b border-line bg-card px-[max(2rem,calc(50%-34rem))] py-2.5">
        <div className="flex items-center gap-5">
          <h2 id="models-title" className="w-24 shrink-0 text-sm font-extrabold leading-tight text-ink">
            {t(lang, "modelsTitle")}
          </h2>
          <ul className="grid flex-1 grid-cols-5 gap-2 xl:gap-3">
            {MODELS.map(([model, job]) => (
              <li key={model}>
                <ModelBadge model={model} />
                <p className="mt-0.5 text-[13px] leading-snug text-muted xl:text-sm">{t(lang, job)}</p>
              </li>
            ))}
          </ul>
          <div className="hidden shrink-0 xl:block">
            <PhoneQR lang={lang} />
          </div>
        </div>
      </section>
    </div>
  );
}
