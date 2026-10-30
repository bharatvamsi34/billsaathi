import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import samples from "@/samples.generated.json";
import { KNOWN_CODES } from "./codes";
import { LANGS, STRINGS } from "./i18n";
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

  it("has 4 to 6 samples, all from the DEV split (never test items)", () => {
    expect(samples.length).toBeGreaterThanOrEqual(4);
    expect(samples.length).toBeLessThanOrEqual(6);
    for (const s of samples) expect(labels.get(s.id)?.split, s.id).toBe("dev");
  });

  it("ships the image files and a title in every language", () => {
    for (const s of samples) {
      if (s.kind === "image") expect(existsSync(join(__dirname, "..", "..", "public", s.src!)), s.id).toBe(true);
      for (const { code } of LANGS) expect(s.title[code], `${s.id} ${code}`).toBeTruthy();
    }
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
