import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import replay from "@/replay.generated.json";
import samples from "@/samples.generated.json";
import { KNOWN_CODES } from "./codes";
import { LANGS, STRINGS } from "./i18n";
import { wrapLines } from "./card";
import { warningText } from "./share";

const ROOT = join(__dirname, "..", "..", "..");

describe("sample gallery", () => {
  const labels = new Map(
    readFileSync(join(ROOT, "data", "synthetic", "labels.jsonl"), "utf8")
      .split("\n")
      .filter((l) => l.trim())
      .map((l) => JSON.parse(l))
      .map((l) => [l.id, l]),
  );

  it("has 4 to 10 samples, each from the DEV split or demo-only (never test items)", () => {
    expect(samples.length).toBeGreaterThanOrEqual(4);
    expect(samples.length).toBeLessThanOrEqual(10);
    for (const s of samples) {
      if ("demoOnly" in s && s.demoOnly) expect(labels.has(s.id), s.id).toBe(false);
      else expect(labels.get(s.id)?.split, s.id).toBe("dev");
    }
  });

  it("the genuine and tampered demo bills are the same account", () => {
    expect(samples.map((s) => s.id)).toEqual(expect.arrayContaining(["photo_genuine_demo", "demo_tampered_same_account", "demo_voice_note"]));
    expect(labels.get("photo_genuine_demo").expected.extracted.consumer_number).toBe("DP-4410-882761");
  });

  it("ships the image and audio files and a title in every language", () => {
    for (const s of samples) {
      if (s.kind !== "text") expect(existsSync(join(__dirname, "..", "..", "public", s.src!)), s.id).toBe(true);
      for (const { code } of LANGS) expect(s.title[code], `${s.id} ${code}`).toBeTruthy();
    }
  });
});

describe("judge-catch replay", () => {
  it("is copied from the recorded run, not written by hand", () => {
    const file = readFileSync(join(ROOT, replay.file), "utf8");
    expect(replay.attempts.length).toBe(2);
    expect(replay.attempts[0].accepted).toBe(false);
    expect(replay.attempts[1].accepted).toBe(true);
    for (const attempt of replay.attempts) for (const r of attempt.reasons) expect(file).toContain(r.reason);
  });
});

describe("wording", () => {
  it("says synthetic, never made-up", () => {
    // Our data is synthetic. ownHelper is an instruction to the user about what they type, BV's wording.
    for (const [key, text] of Object.entries(STRINGS)) if (key !== "ownHelper") expect(text.en, key).not.toMatch(/made[- ]up/i);
    for (const s of samples) expect(s.title.en).not.toMatch(/made[- ]up/i);
  });
});

describe("interface text", () => {
  it("has every string in English, Telugu and Hindi", () => {
    for (const [key, text] of Object.entries(STRINGS)) {
      for (const { code } of LANGS) expect(text[code], `${key} ${code}`).toBeTruthy();
    }
  });

  it("labels every evidence code the API can send", () => {
    const schemas = readFileSync(join(ROOT, "api", "app", "schemas.py"), "utf8");
    const block = schemas.split("class EvidenceCode")[1].split("\nclass ")[0];
    const codes = [...block.matchAll(/^\s+([A-Z_]+) = "/gm)].map((m) => m[1]);
    expect(codes.length).toBeGreaterThan(15);
    expect(codes.filter((c) => !KNOWN_CODES.includes(c))).toEqual([]);
  });
});

describe("warn my family", () => {
  it("is only offered for SCAM and CAUTION", () => {
    expect(warningText("SAFE", "en", "1930")).toBeNull();
    for (const { code } of LANGS) {
      expect(warningText("SCAM", code, "1930")).toContain("1930");
      expect(warningText("CAUTION", code)).toBeTruthy();
    }
  });

  it("never contains personal data: no digits except the checked helpline", () => {
    for (const { code } of LANGS) {
      for (const verdict of ["SCAM", "CAUTION"] as const) {
        const text = warningText(verdict, code, "1930")!;
        expect(text.replaceAll("1930", "")).not.toMatch(/\d/);
        expect(text).not.toMatch(/https?:|@|\.example/);
      }
    }
  });
});

describe("card text wrapping", () => {
  it("keeps every word and respects the width", () => {
    const lines = wrapLines("one two three four five", 9, (s) => s.length);
    expect(lines.join(" ")).toBe("one two three four five");
    for (const line of lines) expect(line.length).toBeLessThanOrEqual(9);
  });
  it("keeps a word longer than the width on its own line", () => {
    expect(wrapLines("a verylongwordindeed b", 5, (s) => s.length)).toEqual(["a", "verylongwordindeed", "b"]);
  });
});
