"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";
import { LANGS, t, type Lang } from "@/lib/i18n";
import { ShieldMark } from "./icons";
import { Badge, Switch } from "./ui";

/** Sticky frosted bar: logo, language, Privacy Mode and the sandbox badge. */
export default function TopBar({
  lang,
  onLang,
  privacy,
  onPrivacy,
  busy,
  onBack,
}: {
  lang: Lang;
  onLang: (l: Lang) => void;
  privacy: boolean;
  onPrivacy: (on: boolean) => void;
  busy: boolean;
  onBack: (() => void) | null;
}) {
  // Scrolling and the sticky column use the bar's real height: it can take two rows.
  const bar = useRef<HTMLElement>(null);
  useEffect(() => {
    const el = bar.current;
    if (!el) return;
    const measure = () => document.documentElement.style.setProperty("--topbar-h", `${el.offsetHeight}px`);
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    measure();
    return () => observer.disconnect();
  }, []);
  return (
    <header ref={bar} className="topbar glass sticky top-0 z-20 flex flex-col justify-center gap-1 border-b border-line px-4 py-1.5 lg:min-h-15 lg:flex-row lg:items-center lg:justify-start lg:gap-4 lg:px-[max(2rem,calc(50%-38rem))]">
      <div className="topbar-row flex items-center gap-2 lg:contents">
        {onBack ? (
          <button type="button" onClick={onBack} className="-ml-1 min-h-10 rounded-full px-2 text-[15px] font-semibold text-brand lg:hidden">
            ← {t(lang, "back")}
          </button>
        ) : null}
        <Link href="/" className={`items-center gap-2 lg:flex ${onBack ? "hidden" : "flex"}`} aria-label="BillSaathi">
          <ShieldMark className="h-7 w-7" />
          <span className="text-lg font-bold tracking-tight">BillSaathi</span>
        </Link>
        <Link href="/eval" className="hidden min-h-9 items-center rounded-full px-3 text-[15px] font-semibold text-ink-soft transition-colors hover:bg-brand-soft hover:text-brand lg:ml-2 lg:inline-flex">
          {t(lang, "evalLink")}
        </Link>
        <div role="group" aria-label={t(lang, "language")} className="topbar-langs ml-auto flex gap-0.5 rounded-full bg-[#e9edf2] p-0.5 lg:order-last lg:ml-0">
          {LANGS.map((l) => (
            <button
              key={l.code}
              type="button"
              lang={l.code}
              aria-pressed={lang === l.code}
              onClick={() => onLang(l.code)}
              className={`min-h-9 rounded-full px-3 text-[13px] font-semibold transition-colors duration-150 lg:min-h-8 ${lang === l.code ? "bg-card text-ink shadow-soft" : "text-muted hover:text-ink"}`}
            >
              {l.code === "en" ? "EN" : l.name}
            </button>
          ))}
        </div>
      </div>
      <div className="topbar-row2 flex items-center justify-between gap-2 lg:ml-auto lg:justify-end lg:gap-3">
        <Badge tone="warn" className="min-w-0 px-2! text-[12px] lg:text-[13px]">
          <span className="sm:hidden">{t(lang, "sandboxBadgeShort")}</span>
          <span className="hidden sm:inline">{t(lang, "sandboxBadge")}</span>
        </Badge>
        <Switch checked={privacy} onChange={onPrivacy} label={t(lang, "privacyToggle")} disabled={busy} />
      </div>
    </header>
  );
}
