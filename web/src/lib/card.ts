// The "Warn my family" card: Muse Image's picture behind our own vetted text, drawn in the browser
// so Telugu and Hindi stay exact. If the picture is not available the card is a plain gradient.
import { API_BASE } from "./api";
import type { Lang } from "./i18n";

const SIZE = 1080;
const PAD = 84;

/** Words on lines that fit `width`, using any measure function (pure, so it is unit-tested). */
export function wrapLines(text: string, width: number, measure: (s: string) => number): string[] {
  const lines: string[] = [];
  let line = "";
  for (const word of text.split(/\s+/).filter(Boolean)) {
    const next = line ? `${line} ${word}` : word;
    if (line && measure(next) > width) {
      lines.push(line);
      line = word;
    } else {
      line = next;
    }
  }
  if (line) lines.push(line);
  return lines;
}

export async function fetchBackground(verdict: "SCAM" | "CAUTION"): Promise<ImageBitmap | null> {
  try {
    const r = await fetch(`${API_BASE}/api/v1/share-card/background?verdict=${verdict}`);
    return r.ok ? await createImageBitmap(await r.blob()) : null;
  } catch {
    return null;
  }
}

export function drawCard(background: ImageBitmap | null, opts: { title: string; message: string; footer: string; accent: string; lang: Lang }): HTMLCanvasElement {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = SIZE;
  const ctx = canvas.getContext("2d")!;
  ctx.fillStyle = "#0b2239";
  ctx.fillRect(0, 0, SIZE, SIZE);
  if (background) {
    const scale = Math.max(SIZE / background.width, SIZE / background.height);
    const w = background.width * scale;
    const h = background.height * scale;
    ctx.drawImage(background, (SIZE - w) / 2, (SIZE - h) / 2, w, h);
  }
  // A dark wash keeps the text readable on any picture.
  const wash = ctx.createLinearGradient(0, 0, 0, SIZE);
  wash.addColorStop(0, "rgba(11,34,57,0.45)");
  wash.addColorStop(0.35, "rgba(11,34,57,0.74)");
  wash.addColorStop(1, "rgba(11,34,57,0.92)");
  ctx.fillStyle = wash;
  ctx.fillRect(0, 0, SIZE, SIZE);

  const family = getComputedStyle(document.body).fontFamily;
  ctx.textBaseline = "top";
  ctx.fillStyle = opts.accent;
  ctx.fillRect(PAD, PAD, 16, 96);
  ctx.fillStyle = "#ffffff";
  ctx.font = `800 84px ${family}`;
  ctx.fillText(opts.title, PAD + 40, PAD + 2, SIZE - PAD * 2 - 40);

  // The biggest size at which the whole message fits above the footer.
  let size = 56;
  let lines: string[] = [];
  const top = PAD + 150;
  const room = SIZE - top - PAD - 110;
  for (; size >= 28; size -= 2) {
    ctx.font = `600 ${size}px ${family}`;
    lines = wrapLines(opts.message, SIZE - PAD * 2, (s) => ctx.measureText(s).width);
    if (lines.length * size * 1.45 <= room) break;
  }
  lines.forEach((line, i) => ctx.fillText(line, PAD, top + i * size * 1.45));

  ctx.fillStyle = "rgba(255,255,255,0.8)";
  ctx.font = `600 30px ${family}`;
  ctx.fillText(opts.footer, PAD, SIZE - PAD - 30, SIZE - PAD * 2);
  return canvas;
}

export function canvasToFile(canvas: HTMLCanvasElement): Promise<File> {
  return new Promise((resolve, reject) =>
    canvas.toBlob((blob) => (blob ? resolve(new File([blob], "billsaathi-warning.png", { type: "image/png" })) : reject(new Error("no image"))), "image/png"),
  );
}

function download(file: File): void {
  const url = URL.createObjectURL(file);
  const a = document.createElement("a");
  a.href = url;
  a.download = file.name;
  a.click();
  URL.revokeObjectURL(url);
}

/** Share the picture if this device can; otherwise, or if sharing is refused, download it. */
export async function shareCard(file: File, text: string): Promise<"shared" | "downloaded" | "cancelled" | "failed"> {
  try {
    if (navigator.canShare?.({ files: [file] })) {
      await navigator.share({ files: [file], text });
      return "shared";
    }
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") return "cancelled"; // the user changed their mind
  }
  try {
    download(file);
    await navigator.clipboard?.writeText(text).catch(() => undefined);
    return "downloaded";
  } catch {
    return "failed";
  }
}
