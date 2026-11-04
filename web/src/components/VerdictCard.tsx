"use client";

import { motion } from "motion/react";
import { useState } from "react";
import { LANGS, t, type Lang } from "@/lib/i18n";
import { reasonLines } from "@/lib/reasons";
import type { Timeline, Verdict } from "@/lib/timeline";
import Comparison from "./Comparison";
import Explanation, { ListenButton } from "./Explanation";
import { CautionIcon, ListCheckIcon, PhoneIcon, SafeIcon, ScamIcon } from "./icons";
import SandboxPay from "./SandboxPay";
import { Badge, Button, buttonClass, Card, Soft } from "./ui";
import WarnFamily from "./WarnFamily";

const LOOK: Record<Verdict, { band: string; icon: typeof SafeIcon }> = {
  SAFE: { band: "bg-safe text-white", icon: SafeIcon },
  CAUTION: { band: "bg-caution text-white", icon: CautionIcon },
  SCAM: { band: "bg-scam text-white", icon: ScamIcon },
};

const MARK = { good: "✓", bad: "✕", warn: "!", info: "i" } as const;
const TONE_TEXT = { good: "text-safe", bad: "text-scam", warn: "text-caution", info: "text-brand" } as const;

export default function VerdictCard({
  checkId,
  tl,
  lang,
  onShowEvidence,
  onReset,
  onCardPicture,
}: {
  checkId: string | null;
  tl: Timeline;
  lang: Lang;
  onShowEvidence: (seq: number) => void;
  onReset: () => void;
  onCardPicture: (loaded: boolean) => void;
}) {
  const v = tl.verdict!;
  const { band, icon: Icon } = LOOK[v.verdict];
  const helpline = v.facts.find((f) => f.key === "cybercrime_helpline")?.value;
  const [allOpen, setAllOpen] = useState(false);
  const lines = reasonLines(tl, lang);
  const shown = allOpen ? lines : lines.slice(0, 2);
  const headline = t(lang, `headline_${v.verdict}`);
  // A check keeps the language it ran in, even if the page language changes afterwards.
  const textLang = LANGS.find((l) => l.code === tl.explanation?.language)?.code ?? lang;
  const spokenHeadline = t(textLang, `headline_${v.verdict}`);
  const fallback = v.verdict === "CAUTION" ? `${headline} ${t(lang, "cautionLine")}` : headline;
  const explanation = tl.explanation?.text ?? (tl.done ? fallback : null);
  const last = tl.judge[tl.judge.length - 1];
  const judged = !v.forced && !!last?.accepted;

  return (
    <motion.div initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.25, ease: "easeOut" }} style={{ transformOrigin: "top" }} aria-live="polite" id="verdict-top" className="scroll-mt-[calc(var(--topbar-h)+0.25rem)]">
      <Card className={`overflow-hidden ${judged ? "gradient-ring" : ""}`} data-testid="verdict" data-verdict={v.verdict}>
        <div className={`flex flex-wrap items-center gap-x-3 gap-y-1.5 px-4 py-2.5 ${band}`}>
          <Icon className="h-10 w-10 shrink-0" />
          <div className="min-w-0 flex-1 basis-56">
            <div className="text-[1.625rem] font-bold leading-tight tracking-tight">{t(lang, `verdict_${v.verdict}`)}</div>
            <div className="wrap-words text-[15px] font-semibold leading-snug" data-testid="instruction">
              {headline}
            </div>
            {v.verdict === "CAUTION" && <div className="wrap-words mt-0.5 text-[14px] leading-snug text-white/90">{t(lang, "cautionLine")}</div>}
          </div>
          <div className="ml-auto flex flex-col items-end gap-0.5">
            {judged && (
              <span className="inline-flex items-center gap-1 rounded-full bg-white/15 px-2.5 py-1 text-[13px] font-semibold leading-tight" data-testid="second-check">
                <span aria-hidden="true">✓</span>
                {t(lang, "traceJudge", { a: last.reasons.filter((r) => r.supported).length, b: last.reasons.length })}
              </span>
            )}
            <button type="button" onClick={onReset} className="hidden min-h-7 whitespace-nowrap rounded-full px-1 text-[14px] font-semibold underline underline-offset-4 lg:block" data-testid="check-another-top">
              {t(lang, "checkAnother")}
            </button>
          </div>
        </div>

        <div className="space-y-3 p-3.5">
          {v.forced && <p className="t-caption rounded-xl bg-caution-bg p-2.5 font-semibold text-caution">{t(lang, "forced")}</p>}

          <Comparison tl={tl} lang={lang} verdict={v.verdict} />

          <div className="grid gap-2" data-testid="actions">
            {v.verdict === "SAFE" ? (
              <>
                {checkId && <SandboxPay checkId={checkId} tl={tl} lang={lang} />}
                <ListenButton text={explanation} headline={spokenHeadline} lang={lang} textLang={textLang} />
              </>
            ) : (
              <>
                {helpline && (
                  <a href={`tel:${helpline}`} className={buttonClass("danger", "md", "w-full")}>
                    <PhoneIcon className="h-5 w-5 shrink-0" />
                    {t(lang, "report", { value: helpline })}
                  </a>
                )}
                <div className="grid items-center gap-2 sm:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
                  <ListenButton text={explanation} headline={spokenHeadline} lang={lang} textLang={textLang} />
                  <WarnFamily verdict={v.verdict} lang={lang} helpline={helpline} privacy={tl.privacy} onPicture={onCardPicture} />
                </div>
              </>
            )}
          </div>

          <Explanation text={explanation} lang={lang} textLang={textLang} />

          {lines.length > 0 && (
            <section aria-labelledby="why-title">
              <h3 id="why-title" className="t-title mb-2">
                {t(lang, "why")}
              </h3>
              <ul className="space-y-1.5" data-testid="why">
                {shown.map((line) => (
                  <li key={line.id}>
                    <button type="button" onClick={() => onShowEvidence(line.seq)} className="flex w-full items-start gap-2 rounded-xl p-1.5 text-left text-[15px] leading-snug transition-colors hover:bg-paper">
                      <span aria-hidden="true" className={`mt-px w-4 shrink-0 text-center font-bold ${TONE_TEXT[line.tone]}`}>
                        {MARK[line.tone]}
                      </span>
                      <span className="wrap-value min-w-0 flex-1">
                        <Soft text={line.text} />
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
              {lines.length > 2 && (
                <button type="button" onClick={() => setAllOpen(!allOpen)} className="mt-1 min-h-10 rounded-full px-1.5 text-[15px] font-semibold text-brand hover:underline">
                  {allOpen ? t(lang, "hideAll") : t(lang, "viewAll", { n: lines.length })}
                </button>
              )}
              {allOpen && lang === "en" && v.reasons.length > 0 && (
                <div className="rise mt-2 space-y-1">
                  <p className="t-caption mb-1.5 flex items-center gap-1.5 font-semibold text-ink-soft">
                    <ListCheckIcon className="h-4 w-4 shrink-0 text-navy" />
                    The agent&apos;s findings, each checked by the second AI
                  </p>
                  {v.reasons.map((r, i) => (
                    <Badge key={i} tone="neutral" className="block! rounded-xl! px-2.5! py-1.5! font-normal!">
                      {r.text}
                    </Badge>
                  ))}
                </div>
              )}
            </section>
          )}

          <Button variant="ghost" onClick={onReset} className="w-full lg:hidden">
            {t(lang, "checkAnother")}
          </Button>
        </div>
      </Card>
    </motion.div>
  );
}
