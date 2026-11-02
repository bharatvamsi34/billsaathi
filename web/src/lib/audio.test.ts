import { describe, expect, it } from "vitest";
import { encodeWav } from "./audio";

describe("encodeWav", () => {
  it("writes the 16 kHz mono 16-bit header the API requires", async () => {
    const view = new DataView(await encodeWav(new Float32Array([0, 0.5, -1, 2])).arrayBuffer());
    const text = (at: number, n: number) => String.fromCharCode(...Array.from({ length: n }, (_, i) => view.getUint8(at + i)));
    expect(text(0, 4)).toBe("RIFF");
    expect(text(8, 4)).toBe("WAVE");
    expect(view.getUint16(20, true)).toBe(1); // PCM
    expect(view.getUint16(22, true)).toBe(1); // mono
    expect(view.getUint32(24, true)).toBe(16000);
    expect(view.getUint16(34, true)).toBe(16); // bits
    expect(view.getUint32(40, true)).toBe(8); // 4 samples
    expect(view.getInt16(44, true)).toBe(0);
    expect(view.getInt16(46, true)).toBe(16383);
    expect(view.getInt16(48, true)).toBe(-32768);
    expect(view.getInt16(50, true)).toBe(32767); // out-of-range input is clipped
  });
});
