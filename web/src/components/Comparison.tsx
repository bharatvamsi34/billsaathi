"use client";

import { codeLabel } from "@/lib/codes";
import { compareRows, isDecisive, orderRows, type CompareRow, type RowStatus } from "@/lib/compare";
import { t, type Key, type Lang } from "@/lib/i18n";
import type { Timeline, Verdict } from "@/lib/timeline";
import { Badge, Soft } from "./ui";

const NOTE: Partial<Record<RowStatus, Key>> = { noRecord: "notInRegistry", notChecked: "notChecked", notFound: "noAccount" };

function label(row: CompareRow, lang: Lang): string {
  if (row.key === "amount" && row.status === "mismatch") return t(lang, "rowAmountDiffers");
  if (row.key === "destination" && row.status === "mismatch") return t(lang, "rowAddressDiffers");
  if (row.key === "consumer" && row.status === "notFound") return t(lang, "rowAccountNotFound");
  if (row.key === "biller") return t(lang, "biller");
  if (row.key === "amount") return t(lang, "amount");
  if (row.key === "consumer") return t(lang, "consumer");
  return t(lang, row.kind === "upi" ? "destUpi" : row.kind === "phone" ? "destPhone" : "destUrl");
}

const wrap = (row: CompareRow) => (row.key === "biller" ? "wrap-words" : "wrap-value");

function Says({ row, lang }: { row: CompareRow; lang: Lang }) {
  const big = isDecisive(row);
  if (!row.says) return <span className="text-muted">{t(lang, "missing")}</span>;
  return (
    <span className={`${wrap(row)} font-semibold ${big ? "text-[18px] leading-snug" : ""} ${row.status === "mismatch" ? "mark-risky" : ""}`}>
      <Soft text={row.says} />
    </span>
  );
}

function Record({ row, lang }: { row: CompareRow; lang: Lang }) {
  const note = NOTE[row.status];
  const big = isDecisive(row);
  return (
    <span className="inline-flex min-w-0 flex-wrap items-center gap-1.5">
      {row.record ? (
        <span className={`${wrap(row)} font-semibold ${big ? "text-[18px] leading-snug" : ""} ${row.status === "mismatch" ? "text-safe" : ""}`}>
          {row.status === "match" && (
            <span aria-hidden="true" className="mr-1 font-bold text-safe">
              ✓
            </span>
          )}
          <Soft text={row.record} />
        </span>
      ) : (
        note && <span className={`font-semibold text-caution ${big ? "text-[18px] leading-snug" : ""}`}>{t(lang, note)}</span>
      )}
      {row.flag && row.status !== "match" && <Badge tone={codeLabel(row.flag, lang).tone}>{codeLabel(row.flag, lang).text}</Badge>}
    </span>
  );
}

/** The centrepiece: what this says against what the demo biller's record says, decisive row first. */
export default function Comparison({ tl, lang, verdict }: { tl: Timeline; lang: Lang; verdict: Verdict }) {
  const rows = orderRows(compareRows(tl));
  if (!rows.length) return null;
  const image = tl.input === "image";
  const says = t(lang, image ? "colBill" : "colMessage");
  const record = t(lang, "colRecord");
  const tint = verdict === "SCAM" ? "bg-scam-bg" : "bg-caution-bg";
  return (
    <section aria-labelledby="compare-title" data-testid="comparison">
      <h3 id="compare-title" className="t-title mb-2">
        {t(lang, image ? "compareTitleBill" : "compareTitle")}
      </h3>
      <div className="overflow-hidden rounded-2xl border border-line">
        {/* Desktop and tablet: a real table. */}
        <table className="hidden w-full table-fixed border-collapse text-left text-[15px] leading-snug sm:table">
          <thead>
            <tr className="bg-paper text-[13px] text-muted">
              <th scope="col" className="w-[20%] px-3 py-2 font-semibold">
                <span className="sr-only">{t(lang, "biller")}</span>
              </th>
              <th scope="col" className="w-[40%] px-3 py-2 font-semibold">
                {says}
              </th>
              <th scope="col" className="w-[40%] px-3 py-2 font-semibold">
                {record}
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => {
              const big = isDecisive(row);
              return (
                <tr key={i} data-status={row.status} data-decisive={big || undefined} className={`border-t border-line align-top ${big ? tint : ""}`}>
                  <th scope="row" className={`wrap-words px-3 text-[13px] ${big ? "py-3 font-bold text-ink" : "py-2.5 font-medium text-muted"}`}>
                    {label(row, lang)}
                  </th>
                  <td className={`px-3 ${big ? "py-3" : "py-2.5"}`}>
                    <Says row={row} lang={lang} />
                  </td>
                  <td className={`px-3 ${big ? "py-3" : "py-2.5"}`}>
                    <Record row={row} lang={lang} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {/* Phone: the decisive rows stacked and large; matching rows on one line, so the main action stays on the first screen. */}
        <dl className="divide-y divide-line text-[15px] leading-snug sm:hidden">
          {rows.map((row, i) => {
            const big = isDecisive(row);
            if (row.status === "match") {
              return (
                <div key={i} data-status={row.status} className="grid grid-cols-[5.5rem_minmax(0,1fr)] gap-x-2 px-3 py-2">
                  <dt className="wrap-words text-[13px] font-medium text-muted">{label(row, lang)}</dt>
                  <dd className="min-w-0">
                    <Record row={row} lang={lang} />
                  </dd>
                </div>
              );
            }
            return (
              <div key={i} data-status={row.status} data-decisive={big || undefined} className={`${big ? `p-3 ${tint}` : "px-3 py-2"}`}>
                <dt className={`wrap-words mb-1 text-[13px] ${big ? "font-bold text-ink" : "font-medium text-muted"}`}>{label(row, lang)}</dt>
                <dd className="grid grid-cols-[4.75rem_minmax(0,1fr)] gap-x-2 gap-y-1">
                  <span className="t-caption text-muted">{says}</span>
                  <Says row={row} lang={lang} />
                  <span className="t-caption text-muted">{t(lang, "colRecordShort")}</span>
                  <Record row={row} lang={lang} />
                </dd>
              </div>
            );
          })}
        </dl>
      </div>
    </section>
  );
}
