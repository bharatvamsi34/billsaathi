"use client";

import { useRef, useState } from "react";
import samples from "@/samples.generated.json";
import { t, type Lang } from "@/lib/i18n";
import { CameraIcon, ImageIcon, MessageIcon, MicIcon } from "./icons";
import { Button, Card, Tabs } from "./ui";
import VoiceButton from "./VoiceButton";

export type CaptureInput = { image: Blob; imageName: string } | { text: string } | { audio: Blob; audioUrl?: string };

export type Sample = (typeof samples)[number];

export async function sampleInput(s: Sample): Promise<CaptureInput> {
  if (s.kind === "text") return { text: s.text! };
  const blob = await (await fetch(s.src!)).blob();
  if (s.kind === "audio") return { audio: blob, audioUrl: s.src! };
  return { image: blob, imageName: s.src!.split("/").pop()! };
}

function SampleCard({ s, lang, busy, onRun }: { s: Sample; lang: Lang; busy: boolean; onRun: () => void }) {
  return (
    <li className={s.kind === "audio" ? "lg:col-span-2 lg:first:col-span-2" : "lg:first:col-span-2"}>
      <Card className="h-full overflow-hidden transition-[border-color,box-shadow,transform] duration-150 hover:-translate-y-px hover:border-brand hover:shadow-lift">
        <button type="button" disabled={busy} onClick={onRun} data-sample={s.id} className="flex w-full items-center gap-3 p-2.5 text-left disabled:opacity-60">
          {s.kind === "image" ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={s.src} alt="" className="h-12 w-12 shrink-0 rounded-xl border border-line object-cover object-top" />
          ) : (
            <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-brand-soft text-brand">
              {s.kind === "audio" ? <MicIcon className="h-6 w-6" /> : <MessageIcon className="h-6 w-6" />}
            </span>
          )}
          <span className="wrap-words flex-1 text-[15px] font-semibold leading-snug">{s.title[lang]}</span>
        </button>
        {s.kind === "audio" && (
          <div className="px-2.5 pb-2.5">
            <audio controls preload="none" src={s.src} aria-label={t(lang, "playSample")} className="h-9 w-full" />
          </div>
        )}
      </Card>
    </li>
  );
}

export default function Capture({
  lang,
  busy,
  onSubmit,
  onReplay,
  extra,
}: {
  lang: Lang;
  busy: boolean;
  onSubmit: (input: CaptureInput) => void;
  onReplay: () => void;
  extra?: React.ReactNode;
}) {
  const camera = useRef<HTMLInputElement>(null);
  const upload = useRef<HTMLInputElement>(null);
  const [text, setText] = useState("");
  const [tab, setTab] = useState<"samples" | "own">("samples");

  const pick = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (file) onSubmit({ image: file, imageName: file.name });
  };

  return (
    <div className="flex flex-col gap-3">
      <div id="samples" className="scroll-mt-[calc(var(--topbar-h)+0.75rem)]">
        <Tabs
          id="capture"
          label={t(lang, "samplesTitle")}
          value={tab}
          onChange={setTab}
          tabs={[
            { value: "samples", label: t(lang, "tabSamples") },
            { value: "own", label: t(lang, "tabOwn") },
          ]}
        />
      </div>

      {tab === "samples" ? (
        <section className="rise">
          <p className="t-caption mb-2 px-1 text-muted">{t(lang, "samplesNote")}</p>
          <ul className="grid gap-2 lg:grid-cols-2">
            {samples.map((s) => (
              <SampleCard key={s.id} s={s} lang={lang} busy={busy} onRun={async () => onSubmit(await sampleInput(s))} />
            ))}
            <li className="lg:col-span-2">
              <Card className="overflow-hidden transition-[border-color,box-shadow,transform] duration-150 hover:-translate-y-px hover:border-brand hover:shadow-lift">
                <button type="button" disabled={busy} onClick={onReplay} data-sample="replay" className="flex w-full items-center gap-3 p-2.5 text-left disabled:opacity-60">
                  <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl text-sm font-bold text-white" style={{ background: "var(--accent-gradient)" }} aria-hidden="true">
                    ↺
                  </span>
                  <span className="wrap-words flex-1 text-[15px] font-semibold leading-snug">{t(lang, "replayTitle")}</span>
                </button>
              </Card>
            </li>
          </ul>
        </section>
      ) : (
        <Card className="rise p-4">
          <p className="t-caption rounded-xl bg-caution-bg p-3 text-caution">
            {t(lang, "ownHelper")} {t(lang, "noRealData")}
          </p>

          {/* Desktop: upload and paste lead; camera and voice are secondary. Phone: all three in one row. */}
          <div className="mt-3 grid grid-cols-3 gap-2 lg:hidden">
            <Button variant="secondary" size="sm" disabled={busy} onClick={() => camera.current?.click()} className="flex-col gap-0.5! rounded-2xl! py-2">
              <CameraIcon className="h-5 w-5" />
              {t(lang, "cameraShort")}
            </Button>
            <Button variant="secondary" size="sm" disabled={busy} onClick={() => upload.current?.click()} className="flex-col gap-0.5! rounded-2xl! py-2">
              <ImageIcon className="h-5 w-5" />
              {t(lang, "uploadShort")}
            </Button>
            <VoiceButton lang={lang} busy={busy} compact onAudio={(audio) => onSubmit({ audio })} />
          </div>
          <div className="mt-3 hidden lg:block">
            <Button variant="primary" size="lg" disabled={busy} onClick={() => upload.current?.click()} className="w-full">
              <ImageIcon className="h-5 w-5" />
              {t(lang, "uploadLong")}
            </Button>
          </div>
          <input ref={camera} type="file" accept="image/*" capture="environment" className="hidden" onChange={pick} />
          <input ref={upload} type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={pick} />

          <label htmlFor="message" className="mb-1.5 mt-4 block text-[15px] font-semibold">
            {t(lang, "pasteLabel")}
          </label>
          <textarea
            id="message"
            rows={4}
            value={text}
            maxLength={4000}
            onChange={(e) => setText(e.target.value)}
            placeholder={t(lang, "pastePlaceholder")}
            className="w-full resize-y rounded-2xl border border-line bg-paper p-3 text-[15px] leading-relaxed transition-colors focus:border-brand focus:bg-card"
          />
          <Button variant="primary" size="lg" disabled={busy || !text.trim()} onClick={() => onSubmit({ text: text.trim() })} className="mt-2 w-full" data-testid="check-message">
            <MessageIcon className="h-5 w-5" />
            {t(lang, "checkMessage")}
          </Button>

          <div className="mt-3 hidden grid-cols-2 gap-2 lg:grid">
            <Button variant="secondary" disabled={busy} onClick={() => camera.current?.click()}>
              <CameraIcon className="h-5 w-5" />
              {t(lang, "cameraShort")}
            </Button>
            <VoiceButton lang={lang} busy={busy} onAudio={(audio) => onSubmit({ audio })} />
          </div>
        </Card>
      )}
      {extra}
    </div>
  );
}
