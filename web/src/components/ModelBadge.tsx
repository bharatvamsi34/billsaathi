// Shows which model does each step, so the Meta models at work are visible at the moment their
// output appears. In Privacy Mode every model badge names the open-weight model instead.
import { t, type Key, type Lang } from "@/lib/i18n";

export const MODEL_NAMES = {
  spark: "Muse Spark 1.3",
  sam: "SAM 3.1",
  voice: "Muse Voice Transcribe",
  open: "Muse Spark Open",
  image: "Muse Image",
} as const;

export type Model = keyof typeof MODEL_NAMES;

export default function ModelBadge({ model, job, code, privacy, lang = "en" }: { model?: Model; job?: Key; code?: boolean; privacy?: boolean; lang?: Lang }) {
  const name = model && (privacy ? MODEL_NAMES.open : MODEL_NAMES[model]);
  return (
    <span className="inline-flex max-w-full flex-wrap items-center gap-1 text-[13px] font-medium leading-tight">
      {name && (
        <span className="inline-flex items-center gap-1.5 rounded-full border border-[#d5e3fb] bg-brand-soft px-2 py-0.5 text-[#0a4fb0]">
          <span aria-hidden="true" className="h-1.5 w-1.5 shrink-0 rounded-full" style={{ background: "var(--accent-gradient)" }} />
          <span>
            {name}
            {job ? ` · ${t(lang, job)}` : ""}
          </span>
        </span>
      )}
      {code && <span className="rounded-full border border-line bg-card px-2 py-0.5 text-ink-soft">{t(lang, "codeBadge")}</span>}
    </span>
  );
}
