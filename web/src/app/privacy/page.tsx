import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Privacy policy — BillSaathi",
  description: "What BillSaathi, a sandbox demo, processes when you check a bill or payment message, and who it is sent to.",
};

const CONTACT = "ch.bharat34@gmail.com";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-2">
      <h2 className="text-xl font-extrabold">{title}</h2>
      {children}
    </section>
  );
}

// Plain server-rendered text: it must be readable without JavaScript, including by Meta's app review.
export default function Privacy() {
  return (
    <main className="mx-auto max-w-2xl space-y-6 px-4 py-8 leading-relaxed">
      <header>
        <Link href="/" className="font-bold text-brand underline underline-offset-4">
          BillSaathi
        </Link>
        <h1 className="mt-2 text-3xl font-extrabold">Privacy policy</h1>
        <p className="text-sm text-muted">Last updated: 4 November 2026</p>
      </header>

      <Section title="What BillSaathi is">
        <p>
          BillSaathi is a sandbox demo, built by Bharat Vamsi Chillimunta (Ireesha Infosol Pvt Ltd) for the Meta Global AI Developer
          Hackathon. It checks a bill or payment message for signs of a scam and explains the result. All billers and bills in it are
          synthetic, its bill-payment service (BBPS) is a mock, and no real money ever moves.
        </p>
        <p className="rounded-xl bg-caution-bg p-3 font-semibold text-caution">
          Please do not send real bills or anything with personal details. Use the samples in the app.
        </p>
      </Section>

      <Section title="What is processed">
        <ul className="list-disc space-y-1 pl-5">
          <li>The message text, image or voice recording you send for a check.</li>
          <li>On WhatsApp: your phone number, which is needed to reply to you, and your message.</li>
          <li>Technical data such as your IP address, used for rate limits and security.</li>
        </ul>
      </Section>

      <Section title="Who it is sent to">
        <ul className="list-disc space-y-1 pl-5">
          <li>
            <strong>Meta Model API</strong>, to read and check what you send: Muse Spark (reading, verification and explanations), SAM
            3.1 (finding the bill in a photo), Muse Voice Transcribe (voice), and Muse Image (a warning-card picture, which never
            contains your data).
          </li>
          <li>
            <strong>Privacy Mode</strong> sends it to the open-weight Muse Spark Open model on an external host (Baseten or Fireworks) instead of Meta&apos;s
            Model API. It does not run on your device. Photo cropping is skipped and the warning card has no generated picture on this path.
          </li>
          <li>
            <strong>WhatsApp (Meta)</strong> carries your messages if you use the WhatsApp number, under WhatsApp&apos;s own terms.
          </li>
          <li>
            <strong>Microsoft Azure</strong> (Central India) hosts the service.
          </li>
        </ul>
        <p>
          This demo runs on free developer credits, and content sent through them may be used by Meta to improve its products. That is
          another reason to send only synthetic data.
        </p>
      </Section>

      <Section title="What is stored, and for how long">
        <ul className="list-disc space-y-1 pl-5">
          <li>
            <strong>Images and voice recordings are not stored</strong> by BillSaathi. They are held in memory only while a check runs,
            then discarded. They are sent inline to the model, so no file is kept in a file store there by us.
          </li>
          <li>
            <strong>Check results</strong>, including the text of a message or what was heard in a recording, stay in the server&apos;s
            memory for about 10 minutes, then are removed. They are also lost
            whenever the service restarts.
          </li>
          <li>
            <strong>WhatsApp:</strong> your number is kept in memory only while a check is open, so we can reply. Your language choice is
            kept in memory against a keyed hash of your number. Logs contain only that hash, never the number.
          </li>
          <li>
            <strong>Sandbox payments:</strong> an audit record (masked consumer number, amount, time) is kept in a file on Azure Files in
            Central India, and survives restarts. It holds no real payment: this is a sandbox.
          </li>
          <li>Server logs hold technical records with consumer and phone numbers masked.</li>
        </ul>
        <p>We do not sell your data, use it for advertising, or use it to train models ourselves. There are no accounts and no tracking cookies.</p>
      </Section>

      <Section title="Deleting your data">
        <p>
          Check data disappears by itself as described above. To ask about or delete anything else, email{" "}
          <a href={`mailto:${CONTACT}`} className="font-semibold text-brand underline underline-offset-4">
            {CONTACT}
          </a>
          . Stop using the WhatsApp number at any time by not sending messages to it.
        </p>
      </Section>

      <Section title="Contact">
        <p>
          Bharat Vamsi Chillimunta, Ireesha Infosol Pvt Ltd —{" "}
          <a href={`mailto:${CONTACT}`} className="font-semibold text-brand underline underline-offset-4">
            {CONTACT}
          </a>
        </p>
      </Section>
    </main>
  );
}
