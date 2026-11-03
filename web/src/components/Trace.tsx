"use client";

import { AnimatePresence, motion } from "motion/react";
import { t, type Lang } from "@/lib/i18n";
import { modelsUsed, type Timeline as TL } from "@/lib/timeline";
import { Card } from "./ui";
import Timeline from "./Timeline";

/** After the verdict the steps fold into one line, and open again on request. */
export default function Trace({ tl, lang, open, onToggle, highlightSeq, imageUrl }: { tl: TL; lang: Lang; open: boolean; onToggle: () => void; highlightSeq: number | null; imageUrl: string | null }) {
  const last = tl.judge[tl.judge.length - 1];
  const claims = last?.reasons.length ?? 0;
  const verified = last?.reasons.filter((r) => r.supported).length ?? 0;
  const pieces = [
    t(lang, "traceChecks", { n: tl.checks.length }),
    t(lang, tl.agentTurns.length === 1 ? "traceTurn" : "traceTurns", { n: tl.agentTurns.length }),
    ...(last ? [t(lang, "traceJudge", { a: verified, b: claims })] : []),
    ...(tl.totalMs != null ? [`${(tl.totalMs / 1000).toFixed(1)} s`] : []),
  ];
  const warningCard = !!tl.verdict && tl.verdict.verdict !== "SAFE";
  return (
    <Card className="overflow-hidden" data-testid="trace">
      <button type="button" onClick={onToggle} aria-expanded={open} className="flex w-full flex-wrap items-center gap-x-2 gap-y-1 p-3.5 text-left text-[14px] leading-snug transition-colors hover:bg-paper">
        <span aria-hidden="true" className="font-bold text-safe">
          ✓
        </span>
        <span className="min-w-0 flex-1 font-medium text-ink-soft">{pieces.join(" · ")}</span>
        <span className="font-semibold text-brand">
          {t(lang, open ? "hideTrace" : "viewTrace")} {open ? "▴" : "▾"}
        </span>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.2, ease: "easeOut" }} className="overflow-hidden">
            <div className="border-t border-line p-2">
              <Timeline tl={tl} lang={lang} highlightSeq={highlightSeq} imageUrl={imageUrl} />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      <div className="t-caption border-t border-line bg-paper px-3.5 py-2 text-muted" data-testid="models-used">
        <span className="font-semibold">{t(lang, "modelsInRun")}:</span> {modelsUsed(tl, warningCard).join(" · ")}
      </div>
    </Card>
  );
}
