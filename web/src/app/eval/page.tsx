import type { Metadata } from "next";
import Link from "next/link";
import { ShieldMark } from "@/components/icons";
import results from "@/eval.generated.json";
import CountUp from "./CountUp";

export const metadata: Metadata = {
  title: "Evaluation — BillSaathi",
  description: "Accuracy, false-SAFE rate, latency and cost of BillSaathi on a small synthetic held-out test set.",
};

type Summary = {
  n: number;
  correct: number;
  accuracy: number;
  false_safe: number;
  risky: number;
  false_alarm: number;
  safe: number;
  scam_downgraded: number;
  evidence_found: number;
  latency_p50_s: number;
  latency_p90_s: number;
  cost_per_check_usd: number;
};
type Config = Summary & {
  title: string;
  file: string;
  date: string;
  turns_median: number;
  forced: number;
  asked_user: number;
  by_language: Record<string, Summary>;
  by_kind: Record<string, Summary>;
  by_expected: Record<string, Summary>;
  confusion: Record<string, Record<string, number>>;
  misses: { id: string; lang: string; kind: string; expected: string; got: string }[];
  explanation_cost_per_check_usd: number;
};

const configs = results.configs as unknown as Record<string, Config>;
const SWEEP = ["spark-minimal", "spark-low", "spark-medium", "spark-high"];
const LANGUAGES: Record<string, string> = { en: "English", te: "Telugu", hi: "Hindi" };
const KINDS: Record<string, string> = { text: "Text message", image: "Image" };
const REPO = "https://github.com/bharatvamsi34/billsaathi/blob";

const usd = (n: number) => `$${n.toFixed(3)}`;
const secs = (n: number) => `${n.toFixed(1)} s`;

function Tile({ value, total, suffix, label, note, wide }: { value: number; total?: number; suffix?: string; label: string; note?: string; wide?: boolean }) {
  return (
    <div className={`rounded-[18px] border border-line bg-card p-4 shadow-soft ${wide ? "col-span-2 lg:col-span-1" : ""}`}>
      <p className="text-[1.75rem] font-bold tabular-nums leading-tight tracking-tight">
        <CountUp value={value} decimals={suffix ? 1 : 0} />
        {total != null && `/${total}`}
        {suffix}
      </p>
      <p className="mt-1 text-[15px] font-semibold leading-snug">{label}</p>
      {note && <p className="t-caption mt-1 text-muted">{note}</p>}
    </div>
  );
}

function SplitTag({ split }: { split: "test" | "dev" }) {
  return <span className={`inline-flex rounded-full px-2.5 py-0.5 text-[12px] font-semibold ${split === "test" ? "bg-brand-soft text-brand" : "bg-[#efeafe] text-[#5236c9]"}`}>{split === "test" ? "Test split · 21 items" : "Dev split · 39 items"}</span>;
}

function Table({ head, rows, emphasis, caption }: { head: string[]; rows: (string | number)[][]; emphasis?: number; caption?: string }) {
  return (
    <div className="overflow-x-auto rounded-[18px] border border-line bg-card shadow-soft" tabIndex={0} role="region" aria-label={caption ?? head.join(", ")}>
      <table className="w-full min-w-[32rem] border-collapse text-left text-[14px]">
        <thead>
          <tr className="border-b border-line bg-paper text-[13px] text-muted">
            {head.map((h, i) => (
              <th key={h || i} scope="col" className={`px-3 py-2 font-semibold ${i ? "text-right" : ""}`}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, r) => (
            <tr key={r} className={`border-b border-line last:border-0 ${r === emphasis ? "bg-brand-soft font-semibold" : ""}`}>
              {row.map((cell, i) => (
                <td key={i} className={`px-3 py-2 ${i ? "whitespace-nowrap text-right tabular-nums" : ""}`}>
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const row = (name: string, s: Summary) => [
  name,
  s.n,
  `${s.correct}/${s.n}`,
  s.risky ? `${s.false_safe}/${s.risky}` : "—",
  s.safe ? `${s.false_alarm}/${s.safe}` : "—",
  secs(s.latency_p50_s),
  secs(s.latency_p90_s),
];
const HEAD = ["", "Items", "Correct", "False SAFE", "False alarms", "p50", "p90"];

export default function Eval() {
  const main = configs["spark-low"];
  const open = configs["open"];
  const sweep = SWEEP.filter((k) => configs[k]);
  if (!main) return <p className="p-8">No evaluation results yet.</p>;
  // "Rule of three": with 0 failures in n trials the 95% upper bound on the true rate is about 3/n.
  const safeBound = Math.round((3 / main.risky) * 100);

  return (
    <>
      <header className="glass sticky top-0 z-20 flex h-14 items-center gap-3 border-b border-line px-4 lg:px-[max(2rem,calc(50%-34rem))]">
        <Link href="/" className="flex items-center gap-2" aria-label="BillSaathi home">
          <ShieldMark className="h-7 w-7" />
          <span className="text-lg font-bold tracking-tight">BillSaathi</span>
        </Link>
        <Link href="/" className="ml-auto inline-flex min-h-10 items-center rounded-full px-3 text-[15px] font-semibold text-brand hover:bg-brand-soft">
          ← Back to the app
        </Link>
      </header>

      <section className="hero-glow px-4 py-7 text-white lg:px-[max(2rem,calc(50%-34rem))] lg:py-9">
        <h1 className="t-display">
          {main.correct}/{main.n} correct on a small synthetic held-out set
        </h1>
        <p className="mt-2 max-w-3xl text-[15px] leading-relaxed text-white/85 lg:text-base">
          A good sign, not proof: the {main.n} items were written by the builder, and 0 false SAFE out of {main.risky} still allows a true rate up to about {safeBound}% (95% confidence, rule of three).
        </p>
      </section>

      <main className="mx-auto max-w-[68rem] space-y-7 px-4 py-6">
        <section aria-label="Headline results on the test split" className="space-y-2">
          <SplitTag split="test" />
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
            <Tile value={main.correct} total={main.n} label="Verdict correct" note="SAFE, CAUTION or SCAM exactly as labelled" />
            <Tile value={main.evidence_found} total={main.n} label="All expected findings present" note="On the rest the verdict held on the remaining evidence" />
            <Tile value={main.false_safe} total={main.risky} label="False SAFE" note="Risky called SAFE: the failure we care about most" />
            <Tile value={main.false_alarm} total={main.safe} label="False alarms" note="Genuine bills not called SAFE" />
            <Tile wide value={main.latency_p50_s} suffix=" s" label="Median to verdict" note={`p90 ${secs(main.latency_p90_s)}, ${usd(main.cost_per_check_usd)} per check`} />
          </div>
        </section>

        <div className="grid gap-5 lg:grid-cols-2">
          {sweep.length > 1 && (
            <section className="space-y-2">
              <h2 className="t-title">Reasoning effort on Muse Spark 1.3</h2>
              <SplitTag split="test" />
              <Table
                caption="Reasoning effort sweep"
                head={["Effort", "Correct", "False SAFE", "p50", "Cost"]}
                emphasis={sweep.indexOf("spark-low")}
                rows={sweep.map((k) => {
                  const c = configs[k];
                  return [c.title.replace("Spark 1.3, ", ""), `${c.correct}/${c.n}`, `${c.false_safe}/${c.risky}`, secs(c.latency_p50_s), usd(c.cost_per_check_usd)];
                })}
              />
              <div className="t-caption space-y-1.5 text-ink-soft">
                <p>Accuracy did not separate the levels on this set. Effort applied to reading and the agent; the highlighted product row uses the shipped judge setting (minimal), the others used low.</p>
                <p className="flex flex-wrap items-center gap-1.5">
                  <SplitTag split="dev" />
                  <span>Why minimal was not adopted: all-minimal scored 38/39 with one false alarm and was not faster (p50 13.8 s); the product scored 39/39 (p50 10.6 s). Those runs were hours apart, so the speed gap is weak evidence.</span>
                </p>
              </div>
            </section>
          )}

          {open && (
            <section className="space-y-2">
              <h2 className="t-title">Muse Spark 1.3 vs Muse Spark Open (Privacy Mode)</h2>
              <SplitTag split="test" />
              <Table
                caption="Muse Spark 1.3 compared with Muse Spark Open"
                head={["Model", "Correct", "False SAFE", "Turns", "p50", "Cost"]}
                rows={[main, open].map((c) => [c === open ? "Muse Spark Open" : "Muse Spark 1.3", `${c.correct}/${c.n}`, `${c.false_safe}/${c.risky}`, c.turns_median, secs(c.latency_p50_s), `${c === open ? "~" : ""}${usd(c.cost_per_check_usd)}`])}
              />
              <p className="t-caption text-ink-soft">
                Privacy Mode runs the whole pipeline on the open-weight model on an external host (Baseten; a Fireworks fallback is built but untested live). It is not offline. It skips SAM, which is on Meta&apos;s API, so images are read uncropped. Its cost is an estimate at Spark 1.3 token rates, because no price is listed.
              </p>
            </section>
          )}
        </div>

        <section className="rounded-[18px] border border-caution-line bg-caution-bg p-4">
          <h2 className="t-title text-caution">Read this before trusting the numbers</h2>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-[15px]">
            <li>The set is small and synthetic. It shows the design works on these cases, not that it is proven in the field.</li>
            <li>Real scammers will write messages this set does not contain. Real bills end as CAUTION here by design, because every biller in the demo is simulated.</li>
            <li>Times were measured from a developer machine running three checks at once, not from a phone on a mobile network, and they vary by time of day.</li>
          </ul>
        </section>

        <details className="group rounded-[18px] border border-line bg-card shadow-soft">
          <summary className="flex min-h-12 cursor-pointer list-none items-center justify-between gap-2 px-4 py-3 font-semibold">
            Full methodology and breakdowns
            <span aria-hidden="true" className="text-brand transition-transform duration-200 group-open:rotate-180">
              ▾
            </span>
          </summary>
          <div className="space-y-6 border-t border-line p-4">
            <section className="space-y-2">
              <h2 className="t-title">By language and input (test split)</h2>
              <Table
                caption="Results by language and input"
                head={HEAD}
                rows={[...Object.entries(main.by_language).map(([k, v]) => row(LANGUAGES[k] ?? k, v)), ...Object.entries(main.by_kind).map(([k, v]) => row(KINDS[k] ?? k, v))]}
              />
            </section>

            <section className="space-y-2">
              <h2 className="t-title">Expected verdict vs what we said (test split)</h2>
              <Table caption="Confusion table" head={["Expected ↓ / Got →", "SAFE", "CAUTION", "SCAM"]} rows={Object.entries(main.confusion).map(([expected, got]) => [expected, got.SAFE, got.CAUTION, got.SCAM])} />
              {main.misses.length > 0 && (
                <ul className="list-disc pl-5">
                  {main.misses.map((m) => (
                    <li key={m.id}>
                      <code>{m.id}</code> ({LANGUAGES[m.lang]}): expected {m.expected}, got {m.got}
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="space-y-2">
              <h2 className="t-title">How this was measured</h2>
              <ul className="list-disc space-y-1 pl-5 text-[15px]">
                <li>
                  <strong>Held-out split.</strong> {results.n_test} of 60 labelled synthetic items, split by scenario before any tuning. Prompts and rules were tuned on the 39 dev items only. Labels were written from intent, and a separate test requires the real tools to reproduce every label.
                </li>
                <li>
                  <strong>Deterministic graders.</strong> Code compares each verdict with its label; no model does any grading. The graders have their own unit tests.
                </li>
                <li>
                  <strong>The real pipeline.</strong> SAM, reading, the milestone check, the fixed checks, the agent, the deterministic checks and the judge, as in the live app. Nobody answers the agent&apos;s question, so a question ends as no answer, which means forced CAUTION.
                </li>
                <li>
                  <strong>Time</strong> is to the verdict; the explanation follows it. <strong>Cost</strong> is model spend from token counts at list prices, and includes the explanation ({usd(main.explanation_cost_per_check_usd)}) in the product row only.
                </li>
                <li>
                  <strong>Results files are in the repo:</strong>{" "}
                  <a href={`${REPO}/main/${main.file}`} className="wrap-value font-semibold text-brand underline underline-offset-4">
                    {main.file.split("/").pop()}
                  </a>
                  , one row per item, with the{" "}
                  <a href={`${REPO}/main/eval/metrics.py`} className="font-semibold text-brand underline underline-offset-4">
                    graders
                  </a>{" "}
                  and{" "}
                  <a href={`${REPO}/main/eval/run_eval.py`} className="font-semibold text-brand underline underline-offset-4">
                    harness
                  </a>
                  .
                </li>
              </ul>
              <p className="t-caption text-muted">Generated {results.generated}.</p>
            </section>
          </div>
        </details>
      </main>
    </>
  );
}
