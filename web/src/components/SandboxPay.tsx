"use client";

import { useState } from "react";
import { paySandbox, type Receipt } from "@/lib/api";
import { t, type Lang } from "@/lib/i18n";
import { money, type Timeline } from "@/lib/timeline";
import { SafeIcon } from "./icons";
import { Button } from "./ui";

// Names wrap between words; only long codes with no spaces may wrap anywhere.
function Row({ label, value, code }: { label: string; value: string; code?: boolean }) {
  return (
    <div className="contents">
      <dt className="wrap-words text-muted">{label}</dt>
      <dd className={`min-w-0 font-semibold ${code ? "wrap-value" : "wrap-words"}`}>{value}</dd>
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

  const label = <p className="t-caption rounded-xl bg-caution-bg px-3 py-2 text-center font-semibold text-caution">{t(lang, "sandboxLabel")}</p>;
  const grid = "grid grid-cols-[minmax(6rem,auto)_minmax(0,1fr)] gap-x-3 gap-y-1 text-[15px]";

  if (receipt) {
    return (
      <section className="rise rounded-2xl border border-safe bg-safe-bg p-4" data-testid="receipt">
        <h3 className="t-title flex items-center gap-2 text-safe">
          <SafeIcon className="h-5 w-5" />
          {t(lang, "receiptTitle")}
        </h3>
        <dl className={`mt-2 ${grid}`}>
          <Row label={t(lang, "receiptNumber")} value={receipt.receipt_id} code />
          <Row label={t(lang, "biller")} value={receipt.biller_name} />
          <Row label={t(lang, "consumer")} value={receipt.consumer_masked} code />
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
      <Button variant="safe" size="lg" onClick={() => setStep("confirm")} className="w-full" data-testid="pay">
        {t(lang, "pay")}
      </Button>
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
    <section className="rise space-y-3 rounded-2xl border border-safe p-4" data-testid="pay-confirm">
      <h3 className="t-title">{t(lang, "confirmTitle")}</h3>
      <dl className={grid}>
        {f?.biller_name.value && <Row label={t(lang, "biller")} value={f.biller_name.value} />}
        {f?.consumer_number.value && <Row label={t(lang, "consumer")} value={f.consumer_number.value} code />}
        <Row label={t(lang, "amount")} value={money(amount)} />
      </dl>
      {label}
      {failed && (
        <p role="alert" className="t-caption font-semibold text-scam">
          {t(lang, "errPay")}
        </p>
      )}
      <div className="grid grid-cols-2 gap-2">
        <Button variant="safe" disabled={step === "paying"} onClick={confirm} data-testid="pay-yes">
          {t(lang, "confirmPay")}
        </Button>
        <Button variant="secondary" disabled={step === "paying"} onClick={() => setStep("idle")}>
          {t(lang, "cancel")}
        </Button>
      </div>
    </section>
  );
}
