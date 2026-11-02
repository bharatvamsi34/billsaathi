import type { Metadata } from "next";
import Link from "next/link";
import results from "@/eval.generated.json";

export const metadata: Metadata = {
  title: "Evaluation — BillSaathi",
  description: "Accuracy, false-SAFE rate, latency and cost of BillSaathi on a held-out test set.",
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

function Tile({ value, label, note }: { value: string; label: string; note?: string }) {
  return (
    <div className="rounded-2xl border border-line bg-card p-4 shadow-sm">
      <p className="text-3xl font-extrabold tabular-nums tracking-tight">{value}</p>
      <p className="mt-1 font-bold leading-snug">{label}</p>
      {note && <p className="mt-1 text-sm leading-snug text-muted">{note}</p>}
    </div>
  );
}

function Table({ head, rows, emphasis }: { head: string[]; rows: (string | number)[][]; emphasis?: number }) {
  return (
    <div className="overflow-x-auto rounded-2xl border border-line bg-card shadow-sm">
      <table className="w-full min-w-[34rem] border-collapse text-left text-[15px]">
        <thead>
          <tr className="border-b-2 border-line text-sm text-muted">
            {head.map((h, i) => (
              <th key={h} scope="col" className={`px-3 py-2 font-bold ${i ? "text-right" : ""}`}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, r) => (
            <tr key={r} className={`border-b border-line last:border-0 ${r === emphasis ? "bg-brand-soft font-semibold" : ""}`}>
              {row.map((cell, i) => (
                <td key={i} className={`px-3 py-2 ${i ? "text-right tabular-nums" : ""}`}>
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
    <main className="mx-auto max-w-4xl space-y-8 px-4 py-8 leading-relaxed lg:py-12">
      <header>
        <Link href="/" className="font-bold text-brand underline underline-offset-4">
          ← BillSaathi
        </Link>
        <h1 className="mt-3 text-3xl font-extrabold tracking-tight lg:text-4xl">How well does it work?</h1>
        <p className="mt-2 max-w-2xl text-lg">
          Every number here comes from real runs of the live pipeline over {main.n} made-up test items that were never used to tune it. Prompts and rules were tuned on a separate
          development set.
        </p>
      </header>

      <section aria-label="Headline results" className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Tile value={`${main.correct}/${main.n}`} label="Correct verdicts" note="SAFE, CAUTION or SCAM exactly as labelled" />
        <Tile value={`${main.false_safe}/${main.risky}`} label="False SAFE" note="Risky requests called SAFE: the failure we care about most" />
        <Tile value={`${main.false_alarm}/${main.safe}`} label="False alarms" note="Genuine bills not called SAFE" />
        <Tile value={`${secs(main.latency_p50_s)}`} label="Median time to verdict" note={`p90 ${secs(main.latency_p90_s)}, ${usd(main.cost_per_check_usd)} per check`} />
      </section>

      <section className="rounded-2xl border-2 border-saffron bg-caution-bg p-4">
        <h2 className="font-extrabold text-caution">Read this before trusting the numbers</h2>
        <ul className="mt-1 list-disc space-y-1 pl-5 text-ink">
          <li>
            The test set is small and synthetic, and written by the builder. Zero false SAFE out of {main.risky} still allows a true rate up to about {safeBound}% (95% confidence, rule of
            three). It shows the design works on these cases, not that it is proven in the field.
          </li>
          <li>Real scammers will write messages this set does not contain. Real bills end as CAUTION here by design, because every biller in the demo is a mock.</li>
          <li>Times were measured from a developer machine running three checks at once, not from a phone on a mobile network.</li>
        </ul>
      </section>

      <section className="space-y-3">
        <h2 className="text-2xl font-extrabold">By language and input</h2>
        <Table
          head={HEAD}
          rows={[
            ...Object.entries(main.by_language).map(([k, v]) => row(LANGUAGES[k] ?? k, v)),
            ...Object.entries(main.by_kind).map(([k, v]) => row(KINDS[k] ?? k, v)),
          ]}
        />
      </section>

      <section className="space-y-3">
        <h2 className="text-2xl font-extrabold">Expected verdict vs what we said</h2>
        <Table
          head={["Expected ↓ / Got →", "SAFE", "CAUTION", "SCAM"]}
          rows={Object.entries(main.confusion).map(([expected, got]) => [expected, got.SAFE, got.CAUTION, got.SCAM])}
        />
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

      {sweep.length > 1 && (
        <section className="space-y-3">
          <h2 className="text-2xl font-extrabold">Reasoning effort on Muse Spark 1.3</h2>
          <p>
            The same test set at four effort levels, applied to reading and the agent. Accuracy did not separate them on this set, so speed and cost decide. The independent judge stayed at{" "}
            <code>low</code> in the other rows; the product row uses the shipped judge setting.
          </p>
          <Table
            head={["Effort", "Correct", "False SAFE", "Forced CAUTION", "p50", "p90", "Cost per check"]}
            emphasis={sweep.indexOf("spark-low")}
            rows={sweep.map((k) => {
              const c = configs[k];
              return [c.title, `${c.correct}/${c.n}`, `${c.false_safe}/${c.risky}`, c.forced, secs(c.latency_p50_s), secs(c.latency_p90_s), usd(c.cost_per_check_usd)];
            })}
          />
        </section>
      )}

      {open && (
        <section className="space-y-3">
          <h2 className="text-2xl font-extrabold">Muse Spark 1.3 vs Muse Spark Open (Privacy Mode)</h2>
          <p>
            Privacy Mode runs the whole pipeline on the open-weight model through Baseten. It skips SAM, which is on Meta&apos;s API, so its images are read uncropped. Its cost is an estimate at Spark 1.3
            token rates, because no price is listed for it.
          </p>
          <Table
            head={["Model", "Correct", "False SAFE", "False alarms", "Agent turns", "p50", "p90", "Cost per check"]}
            rows={[main, open].map((c) => [
              c.title,
              `${c.correct}/${c.n}`,
              `${c.false_safe}/${c.risky}`,
              `${c.false_alarm}/${c.safe}`,
              c.turns_median,
              secs(c.latency_p50_s),
              secs(c.latency_p90_s),
              `${c === open ? "~" : ""}${usd(c.cost_per_check_usd)}`,
            ])}
          />
        </section>
      )}

      <section className="space-y-2">
        <h2 className="text-2xl font-extrabold">How this was measured</h2>
        <ul className="list-disc space-y-1 pl-5">
          <li>
            <strong>Held-out split.</strong> {results.n_test} of 60 labelled items, split by scenario before any tuning. Labels were written from intent, and a separate test requires the real tools to
            reproduce every label.
          </li>
          <li>
            <strong>Deterministic graders.</strong> Code compares each verdict with its label; no model does any grading. The graders have their own unit tests.
          </li>
          <li>
            <strong>The real pipeline.</strong> SAM, reading, the milestone check, the fixed checks, the agent, the deterministic checks and the judge, exactly as in the live app. Nobody answers the agent&apos;s
            question, so a question ends as no answer, which means forced CAUTION.
          </li>
          <li>
            <strong>Time</strong> is to the verdict, and the explanation follows it. <strong>Cost</strong> is model spend from token counts at list prices, and includes the explanation (
            {usd(main.explanation_cost_per_check_usd)}) in the product row only.
          </li>
          <li>
            <strong>Results files are in the repo:</strong>{" "}
            <a href={`${REPO}/main/${main.file}`} className="font-semibold text-brand underline underline-offset-4">
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
        <p className="text-sm text-muted">Generated {results.generated}.</p>
      </section>
    </main>
  );
}
