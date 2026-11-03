"use client";

import { useState } from "react";
import { demoConsumer, WRONG_CONSUMER } from "@/lib/demo";
import { t, type Lang } from "@/lib/i18n";
import { Button, Card, Chip } from "./ui";

export default function QuestionBox({
  question,
  field,
  biller,
  lang,
  onAnswer,
}: {
  question: string;
  field: string;
  biller: string | null | undefined;
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
    <Card className="gradient-ring rise p-4" data-testid="question">
      <h2 className="t-title">{t(lang, "questionTitle")}</h2>
      <p className="wrap-words mt-1 text-[15px]">{question}</p>
      <input
        value={answer}
        maxLength={200}
        aria-label={question}
        onChange={(e) => setAnswer(e.target.value)}
        className="mt-3 w-full rounded-2xl border border-line bg-paper p-3 text-[15px] transition-colors focus:border-brand focus:bg-card"
        autoFocus
      />
      {field === "consumer_number" && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          <Chip disabled={sent} onClick={() => setAnswer(demoConsumer(biller))} data-testid="fill-valid">
            {t(lang, "fillValid")}
          </Chip>
          <Chip disabled={sent} onClick={() => setAnswer(WRONG_CONSUMER)} data-testid="fill-wrong">
            {t(lang, "fillWrong")}
          </Chip>
        </div>
      )}
      <div className="mt-3 grid grid-cols-2 gap-2">
        <Button variant="primary" disabled={sent || !answer.trim()} onClick={() => send(answer.trim())} data-testid="send-answer">
          {t(lang, "send")}
        </Button>
        <Button variant="secondary" disabled={sent} onClick={() => send("")}>
          {t(lang, "skip")}
        </Button>
      </div>
    </Card>
  );
}
