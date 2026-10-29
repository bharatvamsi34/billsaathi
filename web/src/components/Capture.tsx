"use client";

import { useRef, useState } from "react";
import samples from "@/samples.generated.json";
import { t, type Lang } from "@/lib/i18n";
import { BillIcon, CameraIcon, ImageIcon, MessageIcon } from "./icons";

export type CaptureInput = { image: Blob; imageName: string } | { text: string };

type Sample = (typeof samples)[number];

export default function Capture({ lang, busy, onSubmit }: { lang: Lang; busy: boolean; onSubmit: (input: CaptureInput) => void }) {
  const camera = useRef<HTMLInputElement>(null);
  const upload = useRef<HTMLInputElement>(null);
  const [text, setText] = useState("");

  const pick = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (file) onSubmit({ image: file, imageName: file.name });
  };

  const trySample = async (s: Sample) => {
    if (s.kind === "text") return onSubmit({ text: s.text! });
    const blob = await (await fetch(s.src!)).blob();
    onSubmit({ image: blob, imageName: s.src!.split("/").pop()! });
  };

  return (
    <div className="space-y-5">
      <a
        href="#samples"
        className="flex min-h-12 items-center justify-center gap-2 rounded-xl bg-brand-soft px-4 font-bold text-brand underline-offset-4 hover:underline"
      >
        {t(lang, "noBill")} ↓
      </a>
      <section className="rounded-2xl border border-line bg-card p-4 shadow-sm">
        <div className="grid gap-3">
          <button
            type="button"
            disabled={busy}
            onClick={() => camera.current?.click()}
            className="flex min-h-14 items-center justify-center gap-3 rounded-xl bg-brand px-4 text-lg font-bold text-white shadow-sm active:translate-y-px disabled:opacity-60"
          >
            <CameraIcon className="h-7 w-7" />
            {t(lang, "takePhoto")}
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => upload.current?.click()}
            className="flex min-h-14 items-center justify-center gap-3 rounded-xl border-2 border-brand bg-card px-4 text-lg font-bold text-brand active:translate-y-px disabled:opacity-60"
          >
            <ImageIcon className="h-7 w-7" />
            {t(lang, "upload")}
          </button>
          <input ref={camera} type="file" accept="image/*" capture="environment" className="hidden" onChange={pick} />
          <input ref={upload} type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={pick} />
        </div>

        <div className="my-4 flex items-center gap-3 text-sm font-semibold uppercase tracking-wide text-muted">
          <span className="h-px flex-1 bg-line" />
          {t(lang, "or")}
          <span className="h-px flex-1 bg-line" />
        </div>

        <label htmlFor="message" className="mb-2 block font-semibold">
          {t(lang, "pasteLabel")}
        </label>
        <textarea
          id="message"
          rows={4}
          value={text}
          maxLength={4000}
          onChange={(e) => setText(e.target.value)}
          placeholder={t(lang, "pastePlaceholder")}
          className="w-full resize-y rounded-xl border-2 border-line bg-paper p-3 text-base leading-relaxed focus:border-brand"
        />
        <button
          type="button"
          disabled={busy || !text.trim()}
          onClick={() => onSubmit({ text: text.trim() })}
          className="mt-3 flex min-h-14 w-full items-center justify-center gap-2 rounded-xl bg-ink px-4 text-lg font-bold text-white active:translate-y-px disabled:opacity-40"
        >
          <MessageIcon className="h-6 w-6" />
          {t(lang, "checkMessage")}
        </button>
      </section>

      <section>
        <div className="mb-2 px-1">
          <h2 id="samples" className="scroll-mt-20 text-xl font-extrabold">
            {t(lang, "samplesTitle")}
          </h2>
          <p className="text-sm text-muted">{t(lang, "samplesNote")}</p>
        </div>
        <ul className="grid gap-2">
          {samples.map((s) => (
            <li key={s.id}>
              <button
                type="button"
                disabled={busy}
                onClick={() => trySample(s)}
                className="flex w-full items-center gap-3 rounded-xl border border-line bg-card p-3 text-left shadow-sm active:translate-y-px disabled:opacity-60"
              >
                {s.kind === "image" ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={s.src} alt="" className="h-14 w-14 shrink-0 rounded-lg border border-line object-cover object-top" />
                ) : (
                  <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-lg bg-brand-soft text-brand">
                    <MessageIcon className="h-7 w-7" />
                  </span>
                )}
                <span className="flex-1 font-semibold leading-snug">{s.title[lang]}</span>
                <span className="shrink-0 rounded-md bg-paper px-2 py-1 text-xs font-bold uppercase text-muted">
                  {s.kind === "image" ? <BillIcon className="h-4 w-4" /> : s.language}
                </span>
              </button>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
