// Shows which model does each step, so the Meta tools at work are visible on every screen.
const NAMES = {
  spark: "Muse Spark 1.3",
  sam: "SAM 3.1",
  voice: "Voice Transcribe",
  open: "Muse Spark Open",
  image: "Muse Image",
} as const;

export type Model = keyof typeof NAMES;

export default function ModelBadge({ model, code, privacy }: { model?: Model; code?: boolean; privacy?: boolean }) {
  return (
    <span className="inline-flex items-center gap-1 whitespace-nowrap text-xs font-bold">
      {model && (
        <span className="rounded-md bg-ink px-1.5 py-0.5 text-white">{privacy ? NAMES.open : NAMES[model]}</span>
      )}
      {code && <span className="rounded-md border border-muted px-1.5 py-[1px] text-ink-soft">Code</span>}
    </span>
  );
}
