"use client";

import { useState } from "react";
import { paySandbox, type Receipt } from "@/lib/api";
import { t, type Lang } from "@/lib/i18n";
import { money, type Timeline } from "@/lib/timeline";
import { SafeIcon } from "./icons";

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="contents">
      <dt className="text-muted">{label}</dt>
      <dd className="break-all font-semibold">{value}</dd>
    </div>
  );
}

/** SAFE only: pay button -> explicit confirmation -> sandbox receipt. */
export default function SandboxPay({ checkId, tl, lang }: { checkId: string; tl: Timeline; lang: Lang }) {
  const [step, setStep] = useState<"idle" | "confirm" | "paying">("idle");
  const [receipt, setReceipt] = useState<Receipt | null>(null);
  const [failed, setFailed] = useState(false);
  const [key] = useState(() => crypto.randomUUID()); // one key per check: a retry can never pay twice

  const f = tl.extracted;
  const amount = f?.amount.value;
  if (amount == null) return null;

  const label = (
    <p className="rounded-lg bg-caution-bg px-3 py-2 text-center text-[15px] font-bold text-caution">{t(lang, "sandboxLabel")}</p>
  );

  if (receipt) {
    return (
      <section className="rise rounded-xl border-2 border-safe bg-safe-bg p-4">
        <h3 className="flex items-center gap-2 text-lg font-extrabold text-safe">
          <SafeIcon className="h-6 w-6" />
          {t(lang, "receiptTitle")}
        </h3>
        <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-[15px]">
          <Row label={t(lang, "receiptNumber")} value={receipt.receipt_id} />
          <Row label={t(lang, "biller")} value={receipt.biller_name} />
          <Row label={t(lang, "consumer")} value={receipt.consumer_masked} />
          <Row label={t(lang, "amount")} value={money(receipt.amount)} />
          <Row label={t(lang, "paidAt")} value={new Date(receipt.paid_at).toLocaleString("en-IN")} />
          <Row label={t(lang, "auditEntry")} value={`#${receipt.audit_id}`} />
        </dl>
        <div className="mt-3">{label}</div>
      </section>
    );
  }

  if (step === "idle") {
    return (
      <button
        type="button"
        onClick={() => setStep("confirm")}
        className="min-h-14 rounded-xl bg-safe px-4 text-lg font-bold text-white active:translate-y-px"
      >
        {t(lang, "pay", { amount: money(amount) })}
      </button>
    );
  }

  const confirm = async () => {
    setStep("paying");
    setFailed(false);
    try {
      setReceipt(await paySandbox(checkId, key));
    } catch {
      setFailed(true);
      setStep("confirm");
    }
  };

  return (
    <section className="rise space-y-3 rounded-xl border-2 border-safe p-4">
      <h3 className="text-lg font-extrabold">{t(lang, "confirmTitle")}</h3>
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-[15px]">
        {f?.biller_name.value && <Row label={t(lang, "biller")} value={f.biller_name.value} />}
        {f?.consumer_number.value && <Row label={t(lang, "consumer")} value={f.consumer_number.value} />}
        <Row label={t(lang, "amount")} value={money(amount)} />
      </dl>
      {label}
      {failed && (
        <p role="alert" className="text-sm font-semibold text-scam">
          {t(lang, "errPay")}
        </p>
      )}
      <div className="grid grid-cols-2 gap-2">
        <button
          type="button"
          disabled={step === "paying"}
          onClick={confirm}
          className="min-h-14 rounded-xl bg-safe px-3 font-bold text-white disabled:opacity-60"
        >
          {t(lang, "confirmPay")}
        </button>
        <button
          type="button"
          disabled={step === "paying"}
          onClick={() => setStep("idle")}
          className="min-h-14 rounded-xl border-2 border-line px-3 font-bold"
        >
          {t(lang, "cancel")}
        </button>
      </div>
    </section>
  );
}
