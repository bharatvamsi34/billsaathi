"use client";

import qrcode from "qrcode-generator";
import { useMemo, useSyncExternalStore } from "react";
import { t, type Lang } from "@/lib/i18n";

// One SVG path of dark modules, so the code is crisp at any size and uses our ink colour.
function qrPath(text: string): { size: number; d: string } {
  const qr = qrcode(0, "M");
  qr.addData(text);
  qr.make();
  const n = qr.getModuleCount();
  let d = "";
  for (let r = 0; r < n; r++) for (let c = 0; c < n; c++) if (qr.isDark(r, c)) d += `M${c} ${r}h1v1h-1z`;
  return { size: n, d };
}

const noSubscribe = () => () => {};

/** "Best on your phone": a QR code for the page the visitor is on (desktop header only). */
export default function PhoneQR({ lang }: { lang: Lang }) {
  // The page's own address, known only in the browser (empty while pre-rendering).
  const url = useSyncExternalStore(
    noSubscribe,
    () => window.location.origin + window.location.pathname,
    () => "",
  );
  const code = useMemo(() => (url ? qrPath(url) : null), [url]);

  return (
    <div className="flex items-center gap-3">
      <div className="h-[72px] w-[72px] shrink-0 rounded-lg bg-white p-1">
        {code && (
          <svg viewBox={`-1 -1 ${code.size + 2} ${code.size + 2}`} className="h-full w-full" role="img" aria-label={t(lang, "qrAlt")} shapeRendering="crispEdges">
            <path d={code.d} fill="var(--color-ink)" />
          </svg>
        )}
      </div>
      <div className="w-40 min-w-0">
        <p className="font-extrabold leading-snug text-white">{t(lang, "qrTitle")}</p>
        <p className="text-sm leading-snug text-white/75">{t(lang, "qrNote")}</p>
      </div>
    </div>
  );
}
