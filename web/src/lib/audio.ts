// Voice input in the browser: record with MediaRecorder, then convert to the WAV the API expects
// (16 kHz, mono, 16-bit) with Web Audio. No conversion happens on the server.
export const SAMPLE_RATE = 16000;
export const MAX_SECONDS = 60;

/** 16-bit PCM WAV from samples in the range -1..1 (pure, so it is unit-tested). */
export function encodeWav(samples: Float32Array, sampleRate = SAMPLE_RATE): Blob {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  const text = (at: number, value: string) => {
    for (let i = 0; i < value.length; i++) view.setUint8(at + i, value.charCodeAt(i));
  };
  text(0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  text(8, "WAVE");
  text(12, "fmt ");
  view.setUint32(16, 16, true); // size of this header part
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, 1, true); // mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true); // bytes per second
  view.setUint16(32, 2, true); // bytes per frame
  view.setUint16(34, 16, true); // bits per sample
  text(36, "data");
  view.setUint32(40, samples.length * 2, true);
  samples.forEach((s, i) => {
    const clipped = Math.max(-1, Math.min(1, s));
    view.setInt16(44 + i * 2, clipped < 0 ? clipped * 0x8000 : clipped * 0x7fff, true);
  });
  return new Blob([buffer], { type: "audio/wav" });
}

/** Any recording the browser can decode, as 16 kHz mono WAV (OfflineAudioContext resamples and mixes down). */
export async function toWav(recording: Blob): Promise<Blob> {
  const context = new AudioContext();
  try {
    const decoded = await context.decodeAudioData(await recording.arrayBuffer());
    const seconds = Math.min(decoded.duration, MAX_SECONDS);
    const offline = new OfflineAudioContext(1, Math.ceil(seconds * SAMPLE_RATE), SAMPLE_RATE);
    const source = offline.createBufferSource();
    source.buffer = decoded;
    source.connect(offline.destination);
    source.start();
    const rendered = await offline.startRendering();
    return encodeWav(rendered.getChannelData(0));
  } finally {
    void context.close();
  }
}

export type Recorder = { stop: () => Promise<Blob>; cancel: () => void };

/** Start the microphone. Throws if the browser cannot record or permission is refused. */
export async function startRecording(): Promise<Recorder> {
  if (typeof MediaRecorder === "undefined" || !navigator.mediaDevices) throw new Error("recording not supported");
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const recorder = new MediaRecorder(stream);
  const chunks: Blob[] = [];
  recorder.ondataavailable = (e) => chunks.push(e.data);
  recorder.start();
  const release = () => stream.getTracks().forEach((track) => track.stop());
  return {
    stop: () =>
      new Promise((resolve) => {
        recorder.onstop = () => {
          release();
          resolve(new Blob(chunks, { type: recorder.mimeType }));
        };
        recorder.stop();
      }),
    cancel: () => {
      recorder.onstop = release;
      recorder.stop();
    },
  };
}
