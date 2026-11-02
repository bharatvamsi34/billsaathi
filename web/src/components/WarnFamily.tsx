"use client";

import { useEffect, useState } from "react";
import { canvasToFile, drawCard, fetchBackground, shareCard } from "@/lib/card";
import { t, type Lang } from "@/lib/i18n";
import { warningText } from "@/lib/share";
import { ShareIcon, Spinner } from "./icons";
import ModelBadge from "./ModelBadge";

const ACCENT = { SCAM: "#e5484d", CAUTION: "#f2a33a" };

/** "Warn my family": a picture card with our vetted warning, ready to forward. */
export default function WarnFamily({ verdict, lang, helpline }: { verdict: "SCAM" | "CAUTION"; lang: Lang; helpline?: string }) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const message = warningText(verdict, lang, helpline) ?? "";

  // The card is made before the tap: browsers only allow sharing right after a tap, and the first
  // picture of the day takes ~15 s.
  useEffect(() => {
    let alive = true;
    let url: string | null = null;
    void (async () => {
      const bitmap = await fetchBackground(verdict);
      await document.fonts.ready;
      const made = await canvasToFile(
        drawCard(bitmap, { title: t(lang, `verdict_${verdict}`), message, footer: `BillSaathi · ${t(lang, "sandboxLabel")}`, accent: ACCENT[verdict], lang }),
      );
      if (!alive) return;
      url = URL.createObjectURL(made);
      setFile(made);
      setPreview(url);
    })();
    return () => {
      alive = false;
      if (url) URL.revokeObjectURL(url);
    };
  }, [verdict, lang, message]);

  const share = async () => {
    if (!file) return;
    setNote(null);
    const result = await shareCard(file, message);
    if (result === "downloaded") setNote(t(lang, "cardSaved"));
    if (result === "failed") setNote(t(lang, "cardFailed"));
  };

  return (
    <div className="grid gap-2">
      <button
        type="button"
        disabled={!file}
        onClick={share}
        className="flex min-h-14 items-center justify-center gap-2 rounded-xl bg-ink px-4 text-lg font-bold text-white active:translate-y-px disabled:opacity-70"
      >
        {file ? <ShareIcon className="h-6 w-6" /> : <Spinner className="h-6 w-6" />}
        {t(lang, file ? "warnFamily" : "cardMaking")}
      </button>
      <div className="flex justify-end">
        <ModelBadge model="image" />
      </div>
      {preview && (
        // eslint-disable-next-line @next/next/no-img-element -- a local blob made in this browser
        <img src={preview} alt={message} className="rise w-full rounded-xl border border-line" />
      )}
      {note && <p className="text-center text-sm font-semibold text-safe">{note}</p>}
    </div>
  );
}
