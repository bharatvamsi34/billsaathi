"use client";

import { useState } from "react";
import { t, type Lang } from "@/lib/i18n";

export default function QuestionBox({
  question,
  lang,
  onAnswer,
}: {
  question: string;
  lang: Lang;
  onAnswer: (answer: string) => void;
}) {
  const [answer, setAnswer] = useState("");
  const [sent, setSent] = useState(false);
  const send = (value: string) => {
    setSent(true);
    onAnswer(value);
  };
  return (
    <section className="rise rounded-2xl border-2 border-saffron bg-card p-4 shadow-md">
      <h2 className="text-lg font-extrabold">{t(lang, "questionTitle")}</h2>
      <p className="mt-1 text-lg">{question}</p>
      <input
        value={answer}
        maxLength={200}
        onChange={(e) => setAnswer(e.target.value)}
        className="mt-3 w-full rounded-xl border-2 border-line bg-paper p-3 text-lg focus:border-brand"
        autoFocus
      />
      <div className="mt-3 grid grid-cols-2 gap-2">
        <button
          type="button"
          disabled={sent || !answer.trim()}
          onClick={() => send(answer.trim())}
          className="min-h-14 rounded-xl bg-brand px-4 text-lg font-bold text-white disabled:opacity-40"
        >
          {t(lang, "send")}
        </button>
        <button type="button" disabled={sent} onClick={() => send("")} className="min-h-14 rounded-xl border-2 border-line px-4 font-bold">
          {t(lang, "skip")}
        </button>
      </div>
    </section>
  );
}
