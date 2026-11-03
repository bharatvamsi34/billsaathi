"use client";

import { highlight, type Mark } from "@/lib/highlight";
import { t, type Lang } from "@/lib/i18n";
import { money, type Timeline } from "@/lib/timeline";
import { Badge, Card } from "./ui";

export type ReviewInput = { kind: "text"; text: string } | { kind: "image"; url: string } | { kind: "audio"; url?: string } | null;

const CLASS: Record<Mark, string> = { risky: "mark-risky", unverified: "mark-unverified", ok: "mark-ok" };

function Marked({ text, tl }: { text: string; tl: Timeline }) {
  return (
    <>
      {highlight(text, tl).map((span, i) =>
        span.mark ? (
          <mark key={i} className={CLASS[span.mark]}>
            {span.text}
          </mark>
        ) : (
          <span key={i}>{span.text}</span>
        ),
      )}
    </>
  );
}

function Bubble({ text, tl }: { text: string; tl: Timeline }) {
  return (
    <div className="wrap-words max-w-full rounded-2xl rounded-tl-md bg-[#eef1f5] px-3.5 py-2.5 text-[15px] leading-relaxed lg:max-w-[92%]">
      <Marked text={text} tl={tl} />
    </div>
  );
}

/** What is being checked, at the top of the results, with its risky values marked in place. */
export default function InputReview({ input, tl, lang }: { input: ReviewInput; tl: Timeline; lang: Lang }) {
  const f = tl.extracted;
  if (!input) return null;
  const entities = f
    ? [
        ...(f.amount.value != null ? [money(f.amount.value)] : []),
        ...f.payment_destinations.value.map((d) => d.value),
      ]
    : [];
  return (
    <Card className="p-3.5 scroll-mt-[calc(var(--topbar-h)+0.75rem)]" id="results-top">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
        <h2 className="t-caption font-semibold uppercase tracking-wide text-muted">{t(lang, "inputTitle")}</h2>
        {tl.checks.length > 0 && (
          <div className="flex flex-wrap gap-1" aria-hidden="true">
            <Badge tone="bad" className="text-[11px]">
              {t(lang, "legendRisky")}
            </Badge>
            <Badge tone="warn" className="text-[11px]">
              {t(lang, "legendUnverified")}
            </Badge>
            <Badge tone="good" className="text-[11px]">
              {t(lang, "legendOk")}
            </Badge>
          </div>
        )}
      </div>
      {input.kind === "text" && <Bubble text={input.text} tl={tl} />}
      {input.kind === "audio" &&
        (tl.heard ? (
          <Bubble text={tl.heard} tl={tl} />
        ) : (
          input.url && <audio controls src={input.url} className="h-9 w-full" />
        ))}
      {input.kind === "image" && (
        <div className="flex items-start gap-3">
          {/* eslint-disable-next-line @next/next/no-img-element -- a local blob made in this browser */}
          <img src={input.url} alt={t(lang, "thumbAlt")} className="h-20 w-20 shrink-0 rounded-xl border border-line object-cover object-top" />
          <div className="flex min-w-0 flex-wrap gap-1.5">
            {entities.map((value) => (
              <span key={value} className="wrap-value text-[13px] leading-relaxed">
                <Marked text={value} tl={tl} />
              </span>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}
