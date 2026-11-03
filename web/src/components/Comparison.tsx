"use client";

import { codeLabel } from "@/lib/codes";
import { compareRows, type CompareRow, type RowStatus } from "@/lib/compare";
import { t, type Key, type Lang } from "@/lib/i18n";
import type { Timeline } from "@/lib/timeline";
import { Badge } from "./ui";

const NOTE: Partial<Record<RowStatus, Key>> = { noRecord: "notInRegistry", notChecked: "notChecked", notFound: "noAccount" };

function label(row: CompareRow, lang: Lang): string {
  if (row.key === "biller") return t(lang, "biller");
  if (row.key === "amount") return t(lang, "amount");
  if (row.key === "consumer") return t(lang, "consumer");
  return t(lang, row.kind === "upi" ? "destUpi" : row.kind === "phone" ? "destPhone" : "destUrl");
}

function Says({ row, lang }: { row: CompareRow; lang: Lang }) {
  const bad = row.status === "mismatch";
  if (!row.says) return <span className="text-muted">{t(lang, "missing")}</span>;
  return <span className={`${row.key === "biller" ? "wrap-words" : "wrap-value"} font-semibold ${bad ? "mark-risky" : ""}`}>{row.says}</span>;
}

function Record({ row, lang }: { row: CompareRow; lang: Lang }) {
  const note = NOTE[row.status];
  return (
    <span className="inline-flex min-w-0 flex-wrap items-center gap-1.5">
      {row.record ? (
        <span className={`${row.key === "biller" ? "wrap-words" : "wrap-value"} font-semibold ${row.status === "mismatch" ? "text-safe" : ""}`}>
          {row.status === "match" && (
            <span aria-hidden="true" className="mr-1 font-bold text-safe">
              ✓
            </span>
          )}
          {row.record}
        </span>
      ) : (
        note && <span className="font-semibold text-caution">{t(lang, note)}</span>
      )}
      {row.flag && row.status !== "match" && <Badge tone={codeLabel(row.flag, lang).tone}>{codeLabel(row.flag, lang).text}</Badge>}
    </span>
  );
}

/** The centrepiece: what this says against what the demo biller's record says. */
export default function Comparison({ tl, lang }: { tl: Timeline; lang: Lang }) {
  const rows = compareRows(tl);
  if (!rows.length) return null;
  const says = t(lang, tl.input === "image" ? "colBill" : "colMessage");
  const record = t(lang, "colRecord");
  return (
    <section aria-labelledby="compare-title" data-testid="comparison">
      <h3 id="compare-title" className="t-title mb-2">
        {t(lang, "compareTitle")}
      </h3>
      <div className="overflow-hidden rounded-2xl border border-line">
        {/* Desktop and tablet: a real table. */}
        <table className="hidden w-full table-fixed border-collapse text-left text-[14px] leading-snug sm:table">
          <thead>
            <tr className="bg-paper text-[13px] text-muted">
              <th scope="col" className="w-[24%] px-3 py-2 font-semibold">
                <span className="sr-only">{t(lang, "biller")}</span>
              </th>
              <th scope="col" className="w-[38%] px-3 py-2 font-semibold">
                {says}
              </th>
              <th scope="col" className="w-[38%] px-3 py-2 font-semibold">
                {record}
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} data-status={row.status} className={`border-t border-line align-top ${row.status === "mismatch" ? "bg-scam-bg/40" : ""}`}>
                <th scope="row" className="wrap-words px-3 py-2.5 text-[13px] font-medium text-muted">
                  {label(row, lang)}
                </th>
                <td className="px-3 py-2.5">
                  <Says row={row} lang={lang} />
                </td>
                <td className="px-3 py-2.5">
                  <Record row={row} lang={lang} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {/* Phone: stacked rows, same data; a three-column table would not fit. */}
        <dl className="divide-y divide-line text-[14px] leading-snug sm:hidden">
          {rows.map((row, i) => (
            <div key={i} data-status={row.status} className={`p-3 ${row.status === "mismatch" ? "bg-scam-bg/40" : ""}`}>
              <dt className="wrap-words mb-1 text-[13px] font-medium text-muted">{label(row, lang)}</dt>
              <dd className="grid grid-cols-[4.75rem_minmax(0,1fr)] gap-x-2 gap-y-1">
                <span className="t-caption text-muted">{says}</span>
                <Says row={row} lang={lang} />
                <span className="t-caption text-muted">{t(lang, "colRecordShort")}</span>
                <Record row={row} lang={lang} />
              </dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  );
}
