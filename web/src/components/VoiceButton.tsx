"use client";

import { useEffect, useRef, useState } from "react";
import { MAX_SECONDS, startRecording, toWav, type Recorder } from "@/lib/audio";
import { t, type Lang } from "@/lib/i18n";
import { MicIcon, Spinner } from "./icons";

/** Tap to speak the message, tap again to check it. */
export default function VoiceButton({ lang, busy, onAudio }: { lang: Lang; busy: boolean; onAudio: (wav: Blob) => void }) {
  const [state, setState] = useState<"idle" | "recording" | "converting">("idle");
  const [seconds, setSeconds] = useState(0);
  const [failed, setFailed] = useState(false);
  const recorder = useRef<Recorder | null>(null);

  useEffect(() => () => recorder.current?.cancel(), []);

  const finish = async () => {
    const active = recorder.current;
    if (!active) return;
    recorder.current = null;
    setState("converting");
    try {
      onAudio(await toWav(await active.stop()));
    } catch {
      setFailed(true);
    }
    setState("idle");
  };

  useEffect(() => {
    if (state !== "recording") return;
    const started = Date.now();
    const timer = setInterval(() => {
      const elapsed = Math.floor((Date.now() - started) / 1000);
      setSeconds(elapsed);
      if (elapsed >= MAX_SECONDS) void finish();
    }, 250);
    return () => clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- finish only uses refs and setters
  }, [state]);

  const begin = async () => {
    setFailed(false);
    setSeconds(0);
    try {
      recorder.current = await startRecording();
      setState("recording");
    } catch {
      setFailed(true);
    }
  };

  const recording = state === "recording";
  return (
    <div>
      <button
        type="button"
        disabled={busy || state === "converting"}
        onClick={recording ? finish : begin}
        aria-pressed={recording}
        className={`flex min-h-14 w-full items-center justify-center gap-3 rounded-xl px-4 text-lg font-bold active:translate-y-px disabled:opacity-60 ${
          recording ? "bg-scam text-white" : "border-2 border-brand bg-card text-brand"
        }`}
      >
        {state === "converting" ? <Spinner className="h-7 w-7" /> : <MicIcon className="h-7 w-7" />}
        {recording ? `${t(lang, "stopVoice")} · ${seconds}s` : t(lang, "speak")}
      </button>
      {failed && (
        <p role="alert" className="mt-1 text-sm font-semibold text-scam">
          {t(lang, "errMic")}
        </p>
      )}
    </div>
  );
}
