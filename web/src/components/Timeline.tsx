"use client";

import { motion } from "motion/react";
import { useEffect, useState } from "react";
import { codeLabel, toolLabel, type Tone } from "@/lib/codes";
import { t, type Key, type Lang } from "@/lib/i18n";
import { evidenceIndex, judgePending, lowConfidence, money, waitMs, type Box, type CheckRow, type Timeline as TL } from "@/lib/timeline";
import { Check, Dot, Spinner } from "./icons";
import ModelBadge, { type Model } from "./ModelBadge";
import { Badge, rise, Skeleton, Soft } from "./ui";

type Stage = "waiting" | "active" | "done";

const MARK: Record<Tone, string> = { good: "✓", bad: "✕", warn: "!", info: "i" };

export function EvidencePill({ code, lang }: { code: string; lang: Lang }) {
  const { tone, text } = codeLabel(code, lang);
  return (
    <Badge tone={tone}>
      <span aria-hidden="true" className="font-bold">
        {MARK[tone]}
      </span>
      {text}
    </Badge>
  );
}

/** Seconds for one step: ticking while it runs, its real duration once it ends. */
function Timer({ start, end, stage, skew }: { start?: number; end?: number; stage: Stage; skew: number }) {
  const [now, setNow] = useState(0);
  const running = stage === "active" && start != null && end == null;
  useEffect(() => {
    if (!running) return;
    const tick = () => setNow(Date.now() - skew); // on the server's clock, like start and end
    const id = setInterval(tick, 100);
    tick();
    return () => clearInterval(id);
  }, [running, skew]);
  const until = end ?? (running ? now : undefined);
  const seconds = start != null && until != null ? Math.max(until - start, 0) / 1000 : null;
  // Code-only steps finish in milliseconds; "0.0 s" read like a step that never ran.
  const text = seconds == null ? "" : end != null && seconds < 0.05 ? "< 0.1 s" : `${seconds.toFixed(1)} s`;
  return <span className="t-caption ml-auto min-w-11 shrink-0 whitespace-nowrap text-right font-semibold tabular-nums text-muted">{text}</span>;
}

/** The running step and the time so far, for the status bar: the active row can be below the fold. */
export function currentStep(tl: TL): Key | null {
  if (!tl.input) return null;
  if (tl.input === "audio" && !tl.heard) return "stepHear";
  if (tl.input === "image" && !tl.isolated && !tl.extracted && !tl.privacy) return "stepIsolate";
  if (!tl.extracted) return tl.input === "image" ? "stepReading" : "stepReadingMsg";
  if (judgePending(tl)) return "stepJudge";
  return tl.early || tl.agentTurns.length ? "stepAgent" : "stepFixed";
}

export function Elapsed({ start, skew, label }: { start?: number; skew: number; label: string }) {
  const [now, setNow] = useState(0);
  useEffect(() => {
    const tick = () => setNow(Date.now() - skew);
    const id = setInterval(tick, 100);
    tick();
    return () => clearInterval(id);
  }, [skew]);
  if (start == null || !now) return null;
  return (
    <span className="shrink-0 text-right text-[17px] tabular-nums" aria-label={label}>
      {(Math.max(now - start, 0) / 1000).toFixed(1)} s
    </span>
  );
}

function StepRow({
  stage,
  title,
  model,
  job,
  code,
  privacy,
  start,
  end,
  skew,
  lang,
  children,
}: {
  stage: Stage;
  title: string;
  model?: Model;
  job?: Key;
  code?: boolean;
  privacy: boolean;
  start?: number;
  end?: number;
  skew: number;
  lang: Lang;
  children?: React.ReactNode;
}) {
  return (
    <motion.li layout="position" transition={{ duration: 0.2, ease: "easeOut" }} className={`rounded-2xl p-3 transition-colors duration-200 ${stage === "active" ? "gradient-ring bg-card" : ""}`}>
      <div className="flex items-start gap-2.5">
        {stage === "done" ? (
          <Check className="h-5 w-5 shrink-0 text-brand" />
        ) : stage === "active" ? (
          <Spinner className="h-5 w-5 shrink-0 text-brand" />
        ) : (
          <Dot className="h-5 w-5 shrink-0 text-[#c5ccd6]" />
        )}
        <div className="min-w-0 flex-1">
          <div className="flex items-start gap-2">
            <h3 className={`wrap-words text-[15px] font-semibold leading-snug ${stage === "waiting" ? "text-muted" : ""}`}>{title}</h3>
            <Timer start={start} end={end} stage={stage} skew={skew} />
          </div>
          <div className="mt-1">
            <ModelBadge model={model} job={job} code={code} privacy={privacy} lang={lang} />
          </div>
        </div>
      </div>
      {children && <div className="mt-2 space-y-2 pl-7">{children}</div>}
    </motion.li>
  );
}

function CheckLine({ row, lang, highlighted }: { row: CheckRow; lang: Lang; highlighted: boolean }) {
  const value = typeof row.args.value === "string" ? row.args.value : typeof row.args.name === "string" ? row.args.name : null;
  return (
    <motion.li {...rise} id={`check-${row.seq}`} className={`rounded-xl border bg-card p-2.5 scroll-mt-[calc(var(--topbar-h)+1rem)] ${highlighted ? "border-brand ring-2 ring-brand-soft" : "border-line"}`}>
      <div className="t-caption font-semibold text-ink-soft">{toolLabel(row.tool, lang)}</div>
      {value && (
        <div className="wrap-value mt-0.5 font-mono text-[13px]">
          <Soft text={value} />
        </div>
      )}
      <div className="mt-1.5 flex flex-wrap gap-1">
        {!row.ok ? (
          <Badge tone="warn">! {t(lang, "notChecked")}</Badge>
        ) : row.evidence.length ? (
          row.evidence.map((e) => <EvidencePill key={e.evidence_id} code={e.code} lang={lang} />)
        ) : (
          <span className="t-caption text-muted">{t(lang, "noneFound")}</span>
        )}
      </div>
    </motion.li>
  );
}

function boxStyle(box: Box) {
  return {
    left: `${(box.x1 / box.w) * 100}%`,
    top: `${(box.y1 / box.h) * 100}%`,
    width: `${((box.x2 - box.x1) / box.w) * 100}%`,
    height: `${((box.y2 - box.y1) / box.h) * 100}%`,
  };
}

/** Original photo -> SAM's box over it -> the cropped bill. The server only sends the box. */
function IsolatedImage({ src, tl, lang }: { src: string; tl: TL; lang: Lang }) {
  const found = tl.isolated;
  const box = found?.box;
  const note: Key | null = !found ? null : found.cropped ? "isolatedCrop" : box ? "isolatedFull" : "isolatedNone";
  const cropAspect = box ? (box.x2 - box.x1) / (box.y2 - box.y1) : 1;
  return (
    <motion.div {...rise} className="rounded-xl border border-line bg-card p-2.5">
      <div className="flex items-center gap-2.5">
        <div className="relative w-24 shrink-0 overflow-hidden rounded-lg border border-line">
          {/* eslint-disable-next-line @next/next/no-img-element -- a local blob, not a site asset */}
          <img src={src} alt={t(lang, "thumbAlt")} className="block w-full" />
          {box && (
            <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} aria-hidden="true" className="absolute border-2 border-brand-bright shadow-[0_0_0_999px_rgba(10,22,51,0.45)]" style={boxStyle(box)} />
          )}
        </div>
        {box && found?.cropped && (
          <>
            <span aria-hidden="true" className="text-muted">
              →
            </span>
            <motion.div {...rise} className="relative h-20 shrink-0 overflow-hidden rounded-lg border border-brand-bright" style={{ aspectRatio: `${cropAspect}` }} role="img" aria-label={t(lang, "foundBill")}>
              {/* eslint-disable-next-line @next/next/no-img-element -- a local blob, not a site asset */}
              <img
                src={src}
                alt=""
                className="absolute max-w-none"
                style={{
                  width: `${(box.w / (box.x2 - box.x1)) * 100}%`,
                  left: `${(-box.x1 / (box.x2 - box.x1)) * 100}%`,
                  top: `${(-box.y1 / (box.y2 - box.y1)) * 100}%`,
                }}
              />
            </motion.div>
          </>
        )}
      </div>
      {note && <p className="t-caption mt-2 font-semibold text-ink-soft">{t(lang, note)}</p>}
    </motion.div>
  );
}

/** Each claim of the last judged answer, and the tool result it was checked against. */
function JudgeDetail({ tl, lang }: { tl: TL; lang: Lang }) {
  const index = evidenceIndex(tl);
  const rows = new Map(tl.checks.map((c) => [c.seq, c]));
  const last = tl.judge[tl.judge.length - 1];
  const v = tl.verdict;
  return (
    <>
      <p className="t-caption text-muted">{t(lang, tl.privacy ? "judgeSubtitleOpen" : "judgeSubtitle")}</p>
      {tl.judge
        .filter((j) => !j.accepted)
        .map((j, i) => (
          <p key={i} className="t-caption rise rounded-xl bg-caution-bg p-2 font-semibold text-caution">
            ! {t(lang, "judgeRefused")}
          </p>
        ))}
      {last && (
        <ul className="space-y-1.5">
          {last.reasons.map((r, i) => {
            const cited = (r.evidence_ids ?? []).map((id) => index.get(id)).filter((e) => !!e);
            return (
              <motion.li {...rise} key={i} lang="en" className="rounded-xl border border-line bg-card p-2.5">
                <p className="wrap-words text-[13px] font-semibold leading-snug">
                  <span className={r.supported ? "text-safe" : "text-caution"} aria-hidden="true">
                    {r.supported ? "✓ " : "! "}
                  </span>
                  {r.reason}
                </p>
                {cited.length > 0 && (
                  <p className="t-caption mt-1 text-muted">
                    → {t(lang, "checkedAgainst")}:{" "}
                    {[...new Set(cited.map((e) => `${toolLabel(rows.get(e.seq)?.tool ?? "", lang)} ${codeLabel(e.code, lang).text}`))].join(" · ")}
                  </p>
                )}
              </motion.li>
            );
          })}
        </ul>
      )}
      {v && !v.forced && (
        <div className="flex flex-wrap gap-1">
          {v.floor && v.floor !== "SAFE" && <Badge tone="info">{t(lang, "floorEnforced", { v: t(lang, `verdict_${v.floor}`) })}</Badge>}
          <Badge tone="good">{t(lang, "noInvented")}</Badge>
        </div>
      )}
    </>
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
  const skew = tl.skew;
  const reading: Stage = idle ? "waiting" : tl.extracted || tl.verdict ? "done" : "active";
  const fixedStage: Stage = idle || (!tl.extracted && !fixed.length) ? (tl.verdict ? "done" : "waiting") : tl.early || tl.agentTurns.length || tl.verdict ? "done" : "active";
  const checking = judgePending(tl);
  const agentStage: Stage = tl.verdict || checking ? "done" : tl.early || fixed.length ? "active" : "waiting";
  const judgeStage: Stage = checking ? "active" : tl.verdict || tl.judge.length ? "done" : "waiting";
  const explainStage: Stage = tl.explanation || tl.done ? "done" : tl.verdict ? "active" : "waiting";
  const showIsolate = !privacy && (idle || (tl.input === "image" && (tl.isolated != null || !tl.done)));
  const showVoice = idle || tl.input === "audio";
  const f = tl.extracted;
  const common = { privacy, skew, lang };

  return (
    <ol className="space-y-1">
      {showVoice && (
        <StepRow {...common} stage={idle ? "waiting" : tl.heard || tl.verdict ? "done" : "active"} title={t(lang, "stepHear")} model="voice" start={when.received} end={when.transcribed}>
          {!idle &&
            (tl.heard ? (
              <motion.blockquote {...rise} lang={lang} className="wrap-words rounded-xl border border-line bg-card p-2.5 text-[15px]">
                <span className="font-semibold text-muted">{t(lang, "heard")}: </span>
                {tl.heard}
              </motion.blockquote>
            ) : (
              !tl.verdict && <Skeleton lines={1} />
            ))}
        </StepRow>
      )}
      {showIsolate && (
        <StepRow {...common} privacy={false} stage={idle ? "waiting" : tl.isolated || tl.extracted || tl.verdict ? "done" : "active"} title={t(lang, "stepIsolate")} model="sam" job="jobCrop" start={when.received} end={when.isolated}>
          {imageUrl && <IsolatedImage src={imageUrl} tl={tl} lang={lang} />}
        </StepRow>
      )}
      <StepRow {...common} stage={reading} title={t(lang, idle || tl.input === "image" ? "stepReading" : "stepReadingMsg")} model="spark" job={idle || tl.input === "image" ? "jobVision" : undefined} start={when.isolated ?? when.transcribed ?? when.received} end={when.extracted}>
        {f ? (
          <motion.dl {...rise} className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-0.5 rounded-xl border border-line bg-card p-2.5 text-[13px]">
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
                  <dd className="wrap-words font-semibold">
                    {value as string}
                    {low ? (
                      <Badge tone="warn" className="ml-1.5 text-[11px]">
                        {t(lang, "unclear")}
                      </Badge>
                    ) : null}
                  </dd>
                </div>
              ))}
          </motion.dl>
        ) : (
          reading === "active" && <Skeleton />
        )}
      </StepRow>

      <StepRow {...common} stage={fixedStage} title={t(lang, "stepFixed")} code start={when.extracted} end={when.early}>
        {fixed.length > 0 ? (
          <ul className="space-y-1.5">
            {fixed.map((row) => (
              <CheckLine key={row.seq} row={row} lang={lang} highlighted={row.seq === highlightSeq} />
            ))}
          </ul>
        ) : (
          fixedStage === "active" && <Skeleton />
        )}
      </StepRow>

      <StepRow {...common} stage={agentStage} title={t(lang, "stepAgent")} model="spark" job="jobAgent" start={when.early != null ? when.early + waitMs(tl) : undefined} end={agentStage === "done" ? when.agent_turn : undefined}>
        {tl.agentTurns.length > 0 && <p className="t-caption rise text-ink-soft">{t(lang, "agentDecided")}</p>}
        {extra.length > 0 && (
          <ul className="space-y-1.5">
            {extra.map((row) => (
              <CheckLine key={row.seq} row={row} lang={lang} highlighted={row.seq === highlightSeq} />
            ))}
          </ul>
        )}
      </StepRow>

      <StepRow {...common} stage={judgeStage} title={t(lang, "stepJudge")} model="spark" job="jobJudge" code start={when.agent_turn} end={when.verdict}>
        {judgeStage !== "waiting" && <JudgeDetail tl={tl} lang={lang} />}
      </StepRow>

      <StepRow {...common} stage={explainStage} title={t(lang, "stepExplain")} model="spark" job="jobExplain" start={when.verdict} end={when.explanation} />
    </ol>
  );
}
