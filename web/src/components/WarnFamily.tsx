"use client";

import { useEffect, useRef, useState } from "react";
import { canvasToFile, drawCard, fetchBackground, shareCard } from "@/lib/card";
import { t, type Lang } from "@/lib/i18n";
import { warningText } from "@/lib/share";
import { ShareIcon, Spinner } from "./icons";

const ACCENT = { SCAM: "#e5484d", CAUTION: "#f2a33a" };

/** "Warn my family": a picture card with our vetted warning, ready to forward. */
export default function WarnFamily({ verdict, lang, helpline }: { verdict: "SCAM" | "CAUTION"; lang: Lang; helpline?: string }) {
  const [preview, setPreview] = useState<string | null>(null);
  const [making, setMaking] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const file = useRef<File | null>(null);
  const background = useRef<ReturnType<typeof fetchBackground> | null>(null);

  // Start early: the first picture of the day takes ~15 s, so it is ready by the time of the tap.
  useEffect(() => {
    background.current = fetchBackground(verdict);
  }, [verdict]);
  useEffect(() => () => void (preview && URL.revokeObjectURL(preview)), [preview]);

  const message = warningText(verdict, lang, helpline) ?? "";

  const share = async () => {
    setNote(null);
    if (!file.current) {
      setMaking(true);
      const bitmap = await (background.current ?? fetchBackground(verdict));
      await document.fonts.ready;
      const canvas = drawCard(bitmap, {
        title: t(lang, `verdict_${verdict}`),
        message,
        footer: `BillSaathi · ${t(lang, "sandboxLabel")}`,
        accent: ACCENT[verdict],
        lang,
      });
      file.current = await canvasToFile(canvas);
      setPreview(URL.createObjectURL(file.current));
      setMaking(false);
    }
    const result = await shareCard(file.current, message);
    if (result === "downloaded") setNote(t(lang, "cardSaved"));
    if (result === "failed") setNote(t(lang, "cardFailed"));
  };

  return (
    <div className="grid gap-2">
      <button
        type="button"
        disabled={making}
        onClick={share}
        className="flex min-h-14 items-center justify-center gap-2 rounded-xl bg-ink px-4 text-lg font-bold text-white active:translate-y-px disabled:opacity-70"
      >
        {making ? <Spinner className="h-6 w-6" /> : <ShareIcon className="h-6 w-6" />}
        {t(lang, making ? "cardMaking" : "warnFamily")}
      </button>
      {preview && (
        // eslint-disable-next-line @next/next/no-img-element -- a local blob made in this browser
        <img src={preview} alt={message} className="rise w-full rounded-xl border border-line" />
      )}
      {note && <p className="text-center text-sm font-semibold text-safe">{note}</p>}
    </div>
  );
}
