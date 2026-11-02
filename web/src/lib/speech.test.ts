import { describe, expect, it } from "vitest";
import { pickVoice } from "./speech";

describe("pickVoice", () => {
  const voices = [{ lang: "en-US" }, { lang: "hi_IN" }, { lang: "te-IN" }, { lang: "en-IN" }];
  it("prefers the Indian locale", () => {
    expect(pickVoice(voices, "en")?.lang).toBe("en-IN");
    expect(pickVoice(voices, "te")?.lang).toBe("te-IN");
  });
  it("handles underscores and other regions", () => {
    expect(pickVoice(voices, "hi")?.lang).toBe("hi_IN");
    expect(pickVoice([{ lang: "en-GB" }], "en")?.lang).toBe("en-GB");
  });
  it("returns null when there is no voice", () => {
    expect(pickVoice([{ lang: "fr-FR" }], "te")).toBeNull();
  });
});
