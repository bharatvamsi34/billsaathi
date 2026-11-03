"use client";

import { useSyncExternalStore } from "react";

// Synthetic consumer numbers from the mock biller registry (docs/TESTING.md), for the agent's one
// question in a demo. Short names match the biller name the reading returns.
export const DEMO_CONSUMERS: [RegExp, string][] = [
  [/demo\s*power/i, "DP-4410-882761"],
  [/sample\s*vidyut/i, "SVS905403060"],
  [/example\s*bijli/i, "2774392066"],
  [/example\s*jal/i, "EJB49787225"],
  [/demogas/i, "BP24994833"],
  [/demo\s*mobile/i, "DM816336795"],
  [/skydemo/i, "SD592425240"],
  [/fiberdemo/i, "FD33274624"],
];
export const WRONG_CONSUMER = "XX-0000-000000";

export function demoConsumer(biller: string | null | undefined): string {
  const hit = DEMO_CONSUMERS.find(([pattern]) => pattern.test(biller ?? ""));
  return hit ? hit[1] : DEMO_CONSUMERS[0][1];
}

const noSubscribe = () => () => {};

/** ?demo=1, for recording the video: bigger type and no first-visit hint. No behaviour change. */
export function useDemoMode(): boolean {
  return useSyncExternalStore(
    noSubscribe,
    () => new URLSearchParams(window.location.search).get("demo") === "1",
    () => false,
  );
}
