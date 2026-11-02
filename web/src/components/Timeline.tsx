"use client";

import { motion } from "motion/react";
import { useEffect, useState } from "react";
import { codeLabel, toolLabel, type Tone } from "@/lib/codes";
import { t, type Key, type Lang } from "@/lib/i18n";
import { lowConfidence, money, type CheckRow, type Timeline as TL } from "@/lib/timeline";
import { Check, Dot, Spinner } from "./icons";
import ModelBadge, { type Model } from "./ModelBadge";

type Stage = "waiting" | "active" | "done";

const TONE: Record<Tone, { cls: string; mark: string }> = {
  good: { cls: "bg-safe-bg text-safe", mark: "✓" },
  bad: { cls: "bg-scam-bg text-scam", mark: "✕" },
  warn: { cls: "bg-caution-bg text-caution", mark: "!" },
  info: { cls: "bg-brand-soft text-brand", mark: "i" },
};

const rise = { initial: { opacity: 0, y: 8 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.25, ease: "easeOut" } } as const;

export function EvidencePill({ code, lang }: { code: string; lang: Lang }) {
  const { tone, text } = codeLabel(code, lang);
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-sm font-semibold ${TONE[tone].cls}`}>
      <span aria-hidden="true" className="font-extrabold">
        {TONE[tone].mark}
      </span>
      {text}
    </span>
  );
}

/** Seconds for one step: ticking while it runs, fixed once it ends. */
function Timer({ start, end, stage }: { start?: number; end?: number; stage: Stage }) {
  const [now, setNow] = useState(0);
  const running = stage === "active" && start != null && end == null;
  useEffect(() => {
    if (!running) return;
    const tick = () => setNow(performance.now());
    const id = setInterval(tick, 100);
    tick();
    return () => clearInterval(id);
  }, [running]);
  const until = end ?? (running ? now : undefined);
  const seconds = start != null && until != null ? Math.max(until - start, 0) / 1000 : null;
  return <span className="ml-auto min-w-11 text-right text-sm font-semibold tabular-nums text-muted">{seconds != null ? `${seconds.toFixed(1)} s` : ""}</span>;
}

function StageHeader({
  stage,
  title,
  model,
  code,
  privacy,
  start,
  end,
}: {
  stage: Stage;
  title: string;
  model?: Model;
  code?: boolean;
  privacy: boolean;
  start?: number;
  end?: number;
}) {
  return (
    <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
      {stage === "done" ? (
        <Check className="h-6 w-6 shrink-0 text-brand" />
      ) : stage === "active" ? (
        <Spinner className="h-6 w-6 shrink-0 text-brand" />
      ) : (
        <Dot className="h-6 w-6 shrink-0 text-line" />
      )}
      <h3 className={`font-bold leading-snug ${stage === "waiting" ? "text-muted" : ""}`}>{title}</h3>
      <ModelBadge model={model} code={code} privacy={privacy} />
      <Timer start={start} end={end} stage={stage} />
    </div>
  );
}

function Skeleton({ lines = 2 }: { lines?: number }) {
  return (
    <div aria-hidden="true" className="space-y-2 rounded-xl border border-line bg-card p-3">
      {Array.from({ length: lines }, (_, i) => (
        <div key={i} className={`h-3 rounded bg-line motion-safe:animate-pulse ${i % 2 ? "w-2/3" : "w-5/6"}`} />
      ))}
    </div>
  );
}

function CheckLine({ row, lang, highlighted }: { row: CheckRow; lang: Lang; highlighted: boolean }) {
  const value = typeof row.args.value === "string" ? row.args.value : typeof row.args.name === "string" ? row.args.name : null;
  return (
    <motion.li {...rise} id={`check-${row.seq}`} className={`rounded-xl border bg-card p-3 ${highlighted ? "border-saffron ring-2 ring-saffron" : "border-line"}`}>
      <div className="text-[15px] font-semibold text-ink-soft">{toolLabel(row.tool, lang)}</div>
      {value && <div className="mt-0.5 break-all font-mono text-[15px]">{value}</div>}
      <div className="mt-2 flex flex-wrap gap-1.5">
        {!row.ok ? (
          <EvidencePill code="DESTINATION_NOT_OFFICIAL" lang={lang} />
        ) : row.evidence.length ? (
          row.evidence.map((e) => <EvidencePill key={e.evidence_id} code={e.code} lang={lang} />)
        ) : (
          <span className="text-sm text-muted">—</span>
        )}
      </div>
      {!row.ok && <p className="mt-1 text-sm text-scam">{row.error}</p>}
    </motion.li>
  );
}

/** The user's own image with SAM's box drawn over it (the server only sends the box). */
function IsolatedImage({ src, tl, lang }: { src: string; tl: TL; lang: Lang }) {
  const found = tl.isolated;
  const box = found?.box;
  const note: Key | null = !found ? null : found.cropped ? "isolatedCrop" : box ? "isolatedFull" : "isolatedNone";
  return (
    <motion.div {...rise} className="flex items-start gap-3 rounded-xl border border-line bg-card p-3">
      <div className="relative w-24 shrink-0 overflow-hidden rounded-lg border border-line">
        {/* eslint-disable-next-line @next/next/no-img-element -- a local blob, not a site asset */}
        <img src={src} alt="" className="block w-full" />
        {box && (
          <motion.span
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            aria-hidden="true"
            className="absolute border-2 border-saffron shadow-[0_0_0_999px_rgba(11,34,57,0.45)]"
            style={{
              left: `${(box.x1 / box.w) * 100}%`,
              top: `${(box.y1 / box.h) * 100}%`,
              width: `${((box.x2 - box.x1) / box.w) * 100}%`,
              height: `${((box.y2 - box.y1) / box.h) * 100}%`,
            }}
          />
        )}
      </div>
      {note && <p className="text-[15px] font-semibold text-ink-soft">{t(lang, note)}</p>}
    </motion.div>
  );
}

export default function Timeline({
  tl,
  lang,
  highlightSeq,
  imageUrl,
  idle = false,
}: {
  tl: TL;
  lang: Lang;
  highlightSeq: number | null;
  imageUrl: string | null;
  idle?: boolean;
}) {
  const fixed = tl.checks.filter((c) => c.origin === "mandatory");
  const extra = tl.checks.filter((c) => c.origin === "agent");
  const when = tl.times;
  const privacy = tl.privacy;
  const reading: Stage = idle ? "waiting" : tl.extracted || tl.verdict ? "done" : "active";
  const fixedStage: Stage = idle || (!tl.extracted && !fixed.length) ? (tl.verdict ? "done" : "waiting") : tl.early || tl.agentTurns.length || tl.verdict ? "done" : "active";
  const agentStage: Stage = tl.verdict || tl.judge.length ? "done" : tl.early || fixed.length ? "active" : "waiting";
  const judgeStage: Stage = tl.verdict ? "done" : tl.agentTurns.length ? "active" : "waiting";
  const explainStage: Stage = tl.explanation || tl.done ? "done" : tl.verdict ? "active" : "waiting";
  const showIsolate = !privacy && (idle || (tl.input === "image" && (tl.isolated != null || !tl.done)));
  const showVoice = idle || tl.input === "audio";
  const f = tl.extracted;

  return (
    <ol className="space-y-5">
      {privacy && <li className="rise rounded-xl bg-ink px-3 py-2 text-[15px] font-bold text-white">{t(lang, "privacyActive")}</li>}
      {showVoice && !idle && (
        <li className="space-y-2">
          <StageHeader stage={tl.heard || tl.verdict ? "done" : "active"} title={t(lang, "stepHear")} model="voice" privacy={privacy} start={when.received} end={when.transcribed} />
          {tl.heard ? (
            <motion.blockquote {...rise} lang={lang} className="rounded-xl border border-line bg-card p-3 text-[15px]">
              <span className="font-semibold text-muted">{t(lang, "heard")}: </span>
              {tl.heard}
            </motion.blockquote>
          ) : (
            !tl.verdict && <Skeleton lines={1} />
          )}
        </li>
      )}
      {showIsolate && (
        <li className="space-y-2">
          <StageHeader
            stage={idle ? "waiting" : tl.isolated || tl.extracted || tl.verdict ? "done" : "active"}
            title={t(lang, "stepIsolate")}
            model="sam"
            privacy={false}
            start={when.received}
            end={when.isolated}
          />
          {imageUrl && <IsolatedImage src={imageUrl} tl={tl} lang={lang} />}
        </li>
      )}
      <li className="space-y-2">
        <StageHeader stage={reading} title={t(lang, "stepReading")} model="spark" privacy={privacy} start={when.isolated ?? when.transcribed ?? when.received} end={when.extracted} />
        {f ? (
          <motion.dl {...rise} className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 rounded-xl border border-line bg-card p-3 text-[15px]">
            {[
              ["biller", f.biller_name.value, lowConfidence(f.biller_name)],
              ["amount", f.amount.value != null ? money(f.amount.value) : null, lowConfidence(f.amount)],
              ["dueDate", f.due_date.value, lowConfidence(f.due_date)],
              ["consumer", f.consumer_number.value, lowConfidence(f.consumer_number)],
            ]
              .filter(([, v]) => v)
              .map(([key, value, low]) => (
                <div key={key as string} className="contents">
                  <dt className="text-muted">{t(lang, key as "biller")}</dt>
                  <dd className="font-semibold">
                    {value as string}
                    {low ? <span className="ml-2 rounded bg-caution-bg px-1.5 text-xs font-bold text-caution">{t(lang, "unclear")}</span> : null}
                  </dd>
                </div>
              ))}
          </motion.dl>
        ) : (
          reading === "active" && <Skeleton />
        )}
      </li>

      <li className="space-y-2">
        <StageHeader stage={fixedStage} title={t(lang, "stepFixed")} code privacy={privacy} start={when.extracted} end={when.early} />
        {fixed.length > 0 ? (
          <ul className="space-y-2 border-l-4 border-brand-soft pl-3">
            {fixed.map((row) => (
              <CheckLine key={row.seq} row={row} lang={lang} highlighted={row.seq === highlightSeq} />
            ))}
          </ul>
        ) : (
          fixedStage === "active" && <Skeleton />
        )}
      </li>

      <li className="space-y-2">
        <StageHeader stage={agentStage} title={t(lang, "stepAgent")} model="spark" privacy={privacy} start={when.early} end={when.agent_turn} />
        {tl.agentTurns.length > 0 && <p className="rise text-[15px] text-ink-soft">{t(lang, "agentDecided")}</p>}
        {extra.length > 0 && (
          <ul className="space-y-2">
            {extra.map((row) => (
              <CheckLine key={row.seq} row={row} lang={lang} highlighted={row.seq === highlightSeq} />
            ))}
          </ul>
        )}
        {tl.refusals.map((r, i) => (
          <p key={i} className="rise rounded-xl bg-caution-bg p-3 text-[15px] text-caution">
            <strong>{t(lang, "refused")}.</strong> {r.message}
          </p>
        ))}
      </li>

      <li className="space-y-2">
        <StageHeader stage={judgeStage} title={t(lang, "stepJudge")} model="spark" code privacy={privacy} start={when.agent_turn} end={when.verdict} />
        {tl.judge.map((j, i) => (
          <p key={i} className={`rise text-[15px] font-semibold ${j.accepted ? "text-safe" : "text-caution"}`}>
            {j.accepted ? `✓ ${t(lang, "judgeOk")}` : `! ${t(lang, "judgeRefused")}`}
          </p>
        ))}
      </li>

      <li>
        <StageHeader stage={explainStage} title={t(lang, "stepExplain")} model="spark" privacy={privacy} start={when.verdict} end={when.explanation} />
      </li>
    </ol>
  );
}
