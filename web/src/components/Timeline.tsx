"use client";

import { codeLabel, toolLabel, type Tone } from "@/lib/codes";
import { t, type Lang } from "@/lib/i18n";
import { lowConfidence, type CheckRow, type Timeline as TL } from "@/lib/timeline";
import { Check, Dot, Spinner } from "./icons";

type Stage = "waiting" | "active" | "done";

const TONE: Record<Tone, { cls: string; mark: string }> = {
  good: { cls: "bg-safe-bg text-safe", mark: "✓" },
  bad: { cls: "bg-scam-bg text-scam", mark: "✕" },
  warn: { cls: "bg-caution-bg text-caution", mark: "!" },
  info: { cls: "bg-brand-soft text-brand", mark: "i" },
};

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

function StageHeader({ stage, title, highlight }: { stage: Stage; title: string; highlight?: boolean }) {
  return (
    <div className="flex items-center gap-2">
      {stage === "done" ? (
        <Check className="h-6 w-6 text-brand" />
      ) : stage === "active" ? (
        <Spinner className="h-6 w-6 text-brand" />
      ) : (
        <Dot className="h-6 w-6 text-line" />
      )}
      <h3 className={`font-bold ${stage === "waiting" ? "text-muted" : ""} ${highlight ? "text-brand" : ""}`}>{title}</h3>
    </div>
  );
}

function CheckLine({ row, lang, highlighted }: { row: CheckRow; lang: Lang; highlighted: boolean }) {
  const value = typeof row.args.value === "string" ? row.args.value : typeof row.args.name === "string" ? row.args.name : null;
  return (
    <li id={`check-${row.seq}`} className={`rise rounded-xl border bg-card p-3 ${highlighted ? "border-saffron ring-2 ring-saffron" : "border-line"}`}>
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
    </li>
  );
}

const money = (n: number) => `₹${n.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export default function Timeline({ tl, lang, highlightSeq }: { tl: TL; lang: Lang; highlightSeq: number | null }) {
  const fixed = tl.checks.filter((c) => c.origin === "mandatory");
  const extra = tl.checks.filter((c) => c.origin === "agent");
  const reading: Stage = tl.extracted || tl.verdict ? "done" : "active";
  const fixedStage: Stage = !tl.extracted && !fixed.length ? "waiting" : tl.agentTurns.length || tl.verdict ? "done" : "active";
  const agentStage: Stage = !fixed.length && !tl.verdict ? "waiting" : tl.judge.length || tl.verdict ? "done" : "active";
  const judgeStage: Stage = tl.verdict ? "done" : tl.agentTurns.length ? "active" : "waiting";
  const f = tl.extracted;

  return (
    <ol className="space-y-5">
      <li className="space-y-2">
        <StageHeader stage={reading} title={t(lang, "stepReading")} />
        {f && (
          <dl className="rise grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 rounded-xl border border-line bg-card p-3 text-[15px]">
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
          </dl>
        )}
      </li>

      <li className="space-y-2">
        <StageHeader stage={fixedStage} title={t(lang, "stepFixed")} highlight />
        {fixed.length > 0 && (
          <ul className="space-y-2 border-l-4 border-brand-soft pl-3">
            {fixed.map((row) => (
              <CheckLine key={row.seq} row={row} lang={lang} highlighted={row.seq === highlightSeq} />
            ))}
          </ul>
        )}
      </li>

      <li className="space-y-2">
        <StageHeader stage={agentStage} title={t(lang, "stepAgent")} />
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
        <StageHeader stage={judgeStage} title={t(lang, "stepJudge")} />
        {tl.judge.map((j, i) => (
          <p key={i} className={`rise text-[15px] font-semibold ${j.accepted ? "text-safe" : "text-caution"}`}>
            {j.accepted ? `✓ ${t(lang, "judgeOk")}` : `! ${t(lang, "judgeRefused")}`}
          </p>
        ))}
      </li>
    </ol>
  );
}
