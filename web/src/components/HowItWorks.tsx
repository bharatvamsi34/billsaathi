import { t, type Key, type Lang } from "@/lib/i18n";

const STEPS: [Key, Key][] = [
  ["how1Title", "how1Body"],
  ["how2Title", "how2Body"],
  ["how3Title", "how3Body"],
];

/** Desktop intro for judges: one line on what BillSaathi is, and the three stages of a check. */
export default function HowItWorks({ lang }: { lang: Lang }) {
  return (
    <section aria-labelledby="how-title" className="space-y-4">
      <p className="text-xl font-semibold leading-snug">{t(lang, "intro")}</p>
      <div>
        <h2 id="how-title" className="mb-2 text-sm font-bold uppercase tracking-wide text-muted">
          {t(lang, "howItWorks")}
        </h2>
        <ol className="grid grid-cols-3 gap-2">
          {STEPS.map(([title, body], i) => (
            <li key={title} className="relative rounded-xl border border-line bg-card p-3 shadow-sm">
              <span className="flex h-7 w-7 items-center justify-center rounded-full bg-brand text-sm font-extrabold text-white">
                {i + 1}
              </span>
              <p className="mt-2 font-extrabold leading-tight">{t(lang, title)}</p>
              <p className="mt-1 text-sm leading-snug text-muted">{t(lang, body)}</p>
              {i < STEPS.length - 1 && (
                <span aria-hidden="true" className="absolute -right-2 top-1/2 z-[1] -translate-y-1/2 text-lg font-extrabold text-saffron">
                  →
                </span>
              )}
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
