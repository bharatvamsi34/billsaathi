"use client";

import { motion } from "motion/react";
import { useEffect, useState } from "react";
import replay from "@/replay.generated.json";
import { t, type Lang } from "@/lib/i18n";
import ModelBadge from "./ModelBadge";
import { Badge, Button, Card, rise } from "./ui";

type Attempt = (typeof replay.attempts)[number];

function Claims({ attempt, title, lang }: { attempt: Attempt; title: string; lang: Lang }) {
  return (
    <motion.section {...rise} className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="t-title">{title}</h3>
        <Badge tone={attempt.accepted ? "good" : "warn"}>{t(lang, attempt.accepted ? "replayAccepted" : "replayRefused")}</Badge>
      </div>
      <ul className="space-y-1.5" lang="en">
        {attempt.reasons.map((r, i) => (
          <li key={i} className={`rounded-xl border p-2.5 ${r.supported ? "border-line bg-card" : "border-caution-line bg-caution-bg"}`}>
            <p className="wrap-words text-[14px] font-semibold leading-snug">
              <span aria-hidden="true" className={r.supported ? "text-safe" : "text-caution"}>
                {r.supported ? "✓ " : "! "}
              </span>
              {r.reason}
            </p>
            {!r.supported && <p className="wrap-words t-caption mt-1 text-caution">{r.why}</p>}
          </li>
        ))}
      </ul>
    </motion.section>
  );
}

/**
 * Replays a real recorded run, step by step, from eval/results (built into replay.generated.json
 * at build time). Nothing here is written by hand and no model is called.
 */
export default function Replay({ lang, onClose }: { lang: Lang; onClose: () => void }) {
  const [shown, setShown] = useState(1);
  useEffect(() => {
    if (shown >= replay.attempts.length + 1) return;
    const id = setTimeout(() => setShown((n) => n + 1), 1800);
    return () => clearTimeout(id);
  }, [shown]);
  return (
    <Card className="space-y-4 p-4 scroll-mt-[calc(var(--topbar-h)+0.75rem)]" data-testid="replay" id="results-top">
      <div>
        <Badge tone="info">{t(lang, "replayLabel", { date: replay.date })}</Badge>
        <h2 className="t-title mt-2">{t(lang, "replayTitle")}</h2>
        <p className="mt-1 text-[15px] text-ink-soft">{t(lang, "replayIntro")}</p>
        <div className="mt-2">
          <ModelBadge model="spark" job="jobJudge" lang={lang} />
        </div>
      </div>
      <div lang="te" className="wrap-words rounded-2xl rounded-tl-md bg-[#eef1f5] px-3.5 py-2.5 text-[15px] leading-relaxed">
        {replay.message}
      </div>
      {replay.attempts.slice(0, shown).map((attempt, i) => (
        <Claims key={i} attempt={attempt} lang={lang} title={t(lang, i === 0 ? "replayAttempt1" : "replayAttempt2")} />
      ))}
      {shown > replay.attempts.length && (
        <motion.p {...rise} className="text-[15px] font-semibold">
          {t(lang, "replayFinal")}: <span className="text-scam">⛔ {t(lang, `verdict_${replay.verdict as "SCAM"}`)}</span>
        </motion.p>
      )}
      <p className="t-caption text-muted">
        {t(lang, "replaySource")}: <code className="wrap-value">{replay.file}</code>
      </p>
      <Button variant="ghost" onClick={onClose} className="w-full">
        {t(lang, "checkAnother")}
      </Button>
    </Card>
  );
}
