"use client";

import { useEffect, useRef, useState } from "react";
import { MAX_SECONDS, startRecording, toWav, type Recorder } from "@/lib/audio";
import { t, type Lang } from "@/lib/i18n";
import { MicIcon, Spinner } from "./icons";
import { Button } from "./ui";

/** Tap to speak the message, tap again to check it. */
export default function VoiceButton({ lang, busy, compact, onAudio }: { lang: Lang; busy: boolean; compact?: boolean; onAudio: (wav: Blob) => void }) {
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
    <div className="min-w-0">
      <Button
        variant={recording ? "danger" : "secondary"}
        size={compact ? "sm" : "md"}
        disabled={busy || state === "converting"}
        onClick={recording ? finish : begin}
        aria-pressed={recording}
        className={compact ? "h-full w-full flex-col gap-0.5! rounded-2xl! py-2" : "w-full"}
      >
        {state === "converting" ? <Spinner className="h-5 w-5" /> : <MicIcon className="h-5 w-5" />}
        {recording ? `${compact ? "■" : t(lang, "stopVoice")} · ${seconds}s` : t(lang, compact ? "speakShort" : "speak")}
      </Button>
      {failed && (
        <p role="alert" className="t-caption mt-1 font-semibold text-scam">
          {t(lang, "errMic")}
        </p>
      )}
    </div>
  );
}
