"use client";

import { t, type Lang } from "@/lib/i18n";
import { evidenceIndex, type Timeline, type Verdict } from "@/lib/timeline";
import { CautionIcon, PhoneIcon, SafeIcon, ScamIcon } from "./icons";
import Explanation from "./Explanation";
import SandboxPay from "./SandboxPay";
import WarnFamily from "./WarnFamily";
import { EvidencePill } from "./Timeline";

const LOOK: Record<Verdict, { band: string; icon: typeof SafeIcon }> = {
  SAFE: { band: "bg-safe text-white", icon: SafeIcon },
  CAUTION: { band: "bg-caution text-white", icon: CautionIcon },
  SCAM: { band: "bg-scam text-white", icon: ScamIcon },
};

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
  const index = evidenceIndex(tl);
  const helpline = v.facts.find((f) => f.key === "cybercrime_helpline")?.value;

  return (
    <section className="rise overflow-hidden rounded-2xl border border-line bg-card shadow-md" aria-live="polite">
      <div className={`flex items-center gap-3 px-4 py-4 ${band}`}>
        <Icon className="h-12 w-12 shrink-0" />
        <div>
          <div className="text-3xl font-extrabold tracking-wide">{t(lang, `verdict_${v.verdict}`)}</div>
          <div className="text-lg font-semibold leading-snug">{t(lang, `headline_${v.verdict}`)}</div>
        </div>
      </div>

      <div className="space-y-4 p-4">
        {tl.totalMs != null && <p className="text-sm font-semibold text-muted">{t(lang, "checkedIn", { s: (tl.totalMs / 1000).toFixed(1) })}</p>}
        {v.forced && <p className="rounded-lg bg-caution-bg p-2 text-[15px] text-caution">{t(lang, "forced")}</p>}

        <Explanation text={tl.explanation?.text ?? (tl.done ? t(lang, `headline_${v.verdict}`) : null)} headline={t(lang, `headline_${v.verdict}`)} lang={lang} />

        <div>
          <h3 className="mb-2 text-lg font-extrabold">{t(lang, "why")}</h3>
          <ul className="space-y-3">
            {v.reasons.map((r, i) => (
              <li key={i} className="space-y-1.5">
                <div className="flex flex-wrap gap-1.5">
                  {r.evidence_ids
                    .map((id) => index.get(id))
                    .filter((e) => !!e)
                    .map((e) => (
                      <button key={e.evidence_id} type="button" onClick={() => onShowEvidence(e.seq)} className="text-left">
                        <EvidencePill code={e.code} lang={lang} />
                      </button>
                    ))}
                </div>
                {lang === "en" && <p className="text-[15px] text-ink-soft">{r.text}</p>}
              </li>
            ))}
          </ul>
        </div>

        <div className="grid gap-2">
          {v.verdict === "SAFE" ? (
            <>
              {checkId && <SandboxPay checkId={checkId} tl={tl} lang={lang} />}
              <p className="text-center text-sm text-muted">{t(lang, "payNote")}</p>
            </>
          ) : (
            <>
              <WarnFamily verdict={v.verdict} lang={lang} helpline={helpline} />
              {helpline && (
                <a
                  href={`tel:${helpline}`}
                  className="flex min-h-14 items-center justify-center gap-2 rounded-xl border-2 border-scam px-4 text-lg font-bold text-scam"
                >
                  <PhoneIcon className="h-6 w-6" />
                  {t(lang, "report", { value: helpline })}
                </a>
              )}
            </>
          )}
          <button type="button" onClick={onReset} className="min-h-12 rounded-xl px-4 font-bold text-brand underline underline-offset-4">
            {t(lang, "checkAnother")}
          </button>
        </div>
      </div>
    </section>
  );
}
