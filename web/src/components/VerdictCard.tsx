"use client";

import { motion } from "motion/react";
import { useState } from "react";
import { t, type Lang } from "@/lib/i18n";
import { reasonLines } from "@/lib/reasons";
import type { Timeline, Verdict } from "@/lib/timeline";
import Comparison from "./Comparison";
import Explanation, { ListenButton } from "./Explanation";
import { CautionIcon, PhoneIcon, SafeIcon, ScamIcon } from "./icons";
import SandboxPay from "./SandboxPay";
import { Badge, Button, buttonClass, Card } from "./ui";
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
}: {
  checkId: string | null;
  tl: Timeline;
  lang: Lang;
  onShowEvidence: (seq: number) => void;
  onReset: () => void;
}) {
  const v = tl.verdict!;
  const { band, icon: Icon } = LOOK[v.verdict];
  const helpline = v.facts.find((f) => f.key === "cybercrime_helpline")?.value;
  const [allOpen, setAllOpen] = useState(false);
  const lines = reasonLines(tl, lang);
  const shown = allOpen ? lines : lines.slice(0, 2);
  const headline = t(lang, `headline_${v.verdict}`);
  const explanation = tl.explanation?.text ?? (tl.done ? headline : null);
  const judged = !v.forced && tl.judge.length > 0 && tl.judge[tl.judge.length - 1].accepted;

  return (
    <motion.div initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.25, ease: "easeOut" }} aria-live="polite">
      <Card className={`overflow-hidden ${judged ? "gradient-ring" : ""}`} data-testid="verdict" data-verdict={v.verdict}>
        <div className={`flex items-center gap-3 px-4 py-3.5 ${band}`}>
          <Icon className="h-10 w-10 shrink-0" />
          <div className="min-w-0">
            <div className="text-[1.625rem] font-bold leading-tight tracking-tight">{t(lang, `verdict_${v.verdict}`)}</div>
            <div className="wrap-words text-[15px] font-medium leading-snug">{headline}</div>
          </div>
        </div>

        <div className="space-y-4 p-4">
          {v.forced && <p className="t-caption rounded-xl bg-caution-bg p-2.5 font-semibold text-caution">{t(lang, "forced")}</p>}

          {/* Actions first. */}
          <div className="grid gap-2" data-testid="actions">
            {v.verdict === "SAFE" ? (
              checkId && <SandboxPay checkId={checkId} tl={tl} lang={lang} />
            ) : (
              <div className="grid items-stretch gap-2 sm:grid-cols-2">
                <div className="grid content-start gap-2">
                  <div className={`flex min-h-11 items-center justify-center gap-2 rounded-full px-4 text-[15px] font-bold ${v.verdict === "SCAM" ? "bg-scam-bg text-scam" : "bg-caution-bg text-caution"}`}>
                    <span aria-hidden="true">⛔</span> {t(lang, v.verdict === "SCAM" ? "doNotPay" : "doNotPayYet")}
                  </div>
                  {helpline && (
                    <a href={`tel:${helpline}`} className={buttonClass("danger")}>
                      <PhoneIcon className="h-5 w-5" />
                      {t(lang, "report", { value: helpline })}
                    </a>
                  )}
                  <ListenButton text={explanation} headline={headline} lang={lang} />
                </div>
                <WarnFamily verdict={v.verdict} lang={lang} helpline={helpline} privacy={tl.privacy} />
              </div>
            )}
            {v.verdict === "SAFE" && <ListenButton text={explanation} headline={headline} lang={lang} />}
          </div>

          <Comparison tl={tl} lang={lang} />
          <Explanation text={explanation} lang={lang} />

          {lines.length > 0 && (
            <section aria-labelledby="why-title">
              <h3 id="why-title" className="t-title mb-2">
                {t(lang, "why")}
              </h3>
              <ul className="space-y-1.5" data-testid="why">
                {shown.map((line) => (
                  <li key={line.id}>
                    <button type="button" onClick={() => onShowEvidence(line.seq)} className="flex w-full items-start gap-2 rounded-xl p-1.5 text-left text-[15px] leading-snug transition-colors hover:bg-paper">
                      <span aria-hidden="true" className={`mt-px font-bold ${TONE_TEXT[line.tone]}`}>
                        {MARK[line.tone]}
                      </span>
                      <span className="wrap-value min-w-0 flex-1">{line.text}</span>
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
                  {v.reasons.map((r, i) => (
                    <Badge key={i} tone="neutral" className="block! rounded-xl! px-2.5! py-1.5! font-normal!">
                      {r.text}
                    </Badge>
                  ))}
                </div>
              )}
            </section>
          )}

          <Button variant="ghost" onClick={onReset} className="w-full">
            {t(lang, "checkAnother")}
          </Button>
        </div>
      </Card>
    </motion.div>
  );
}
