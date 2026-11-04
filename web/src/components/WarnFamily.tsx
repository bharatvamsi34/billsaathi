"use client";

import { useEffect, useState } from "react";
import { canvasToFile, drawCard, fetchBackground, shareCard } from "@/lib/card";
import { t, type Lang } from "@/lib/i18n";
import { warningText } from "@/lib/share";
import { ShareIcon, Spinner } from "./icons";
import ModelBadge from "./ModelBadge";
import { Button, Toast } from "./ui";

const ACCENT = { SCAM: "#e5484d", CAUTION: "#f2a33a" };

/**
 * "Warn my family": a picture card with our vetted warning, ready to forward. In Privacy Mode no
 * picture is requested (it comes from Muse Image on Meta's API), so the card is a plain gradient.
 */
export default function WarnFamily({ verdict, lang, helpline, privacy, onPicture }: { verdict: "SCAM" | "CAUTION"; lang: Lang; helpline?: string; privacy: boolean; onPicture: (loaded: boolean) => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [picture, setPicture] = useState(false);
  const message = warningText(verdict, lang, helpline) ?? "";

  // The card is made before the tap: browsers only allow sharing right after a tap, and the first
  // picture of the day takes ~15 s.
  useEffect(() => {
    let alive = true;
    let url: string | null = null;
    void (async () => {
      const bitmap = privacy ? null : await fetchBackground(verdict);
      await document.fonts.ready;
      const made = await canvasToFile(
        drawCard(bitmap, { title: t(lang, `verdict_${verdict}`), message, footer: `BillSaathi · ${t(lang, "sandboxLabel")}`, accent: ACCENT[verdict], lang }),
      );
      if (!alive) return;
      url = URL.createObjectURL(made);
      setFile(made);
      setPicture(!!bitmap);
      onPicture(!!bitmap); // Muse Image gets credit only when its picture is really on the card
      setPreview(url);
    })();
    return () => {
      alive = false;
      if (url) URL.revokeObjectURL(url);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- onPicture is a setter from the page
  }, [verdict, lang, message, privacy]);

  useEffect(() => {
    if (!note) return;
    const id = setTimeout(() => setNote(null), 4000);
    return () => clearTimeout(id);
  }, [note]);

  const share = async () => {
    if (!file) return;
    setNote(null);
    const result = await shareCard(file, message);
    if (result === "downloaded") setNote(t(lang, "cardSaved"));
    if (result === "failed") setNote(t(lang, "cardFailed"));
  };

  return (
    <div className="flex h-full flex-wrap items-center gap-2.5 rounded-2xl border border-line p-2.5">
      <div className="h-16 w-16 shrink-0 overflow-hidden rounded-xl border border-line">
        {preview ? (
          // eslint-disable-next-line @next/next/no-img-element -- a local blob made in this browser
          <img src={preview} alt={message} className="rise block h-full w-full object-cover" />
        ) : (
          <div className="skeleton h-full w-full" aria-hidden="true" />
        )}
      </div>
      <div className="min-w-fit flex-1 space-y-1.5">
        <Button variant="primary" disabled={!file} onClick={share} className="w-full whitespace-nowrap px-4!">
          {file ? <ShareIcon className="h-5 w-5" /> : <Spinner className="h-5 w-5" />}
          {t(lang, file ? "warnFamily" : "cardMaking")}
        </Button>
        {picture && (
          <div className="whitespace-nowrap">
            <ModelBadge model="image" lang={lang} />
          </div>
        )}
        {privacy && file && <p className="t-caption w-0 min-w-full text-muted">{t(lang, "plainCard")}</p>}
        {note && (
          <p role="status" className="t-caption rise hidden w-0 min-w-full rounded-lg bg-safe-bg px-2 py-1 font-semibold text-safe lg:block" data-testid="card-note">
            {note}
          </p>
        )}
      </div>
      <div className="lg:hidden">
        <Toast message={note} />
      </div>
    </div>
  );
}
