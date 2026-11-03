"use client";

import { animate, useReducedMotion } from "motion/react";
import { useEffect, useState } from "react";

/** A headline number counting up once. The right number is in the first render, so nothing depends on this. */
export default function CountUp({ value, decimals = 0 }: { value: number; decimals?: number }) {
  const reduced = useReducedMotion();
  const [shown, setShown] = useState(value);
  useEffect(() => {
    if (reduced || value === 0) return;
    const controls = animate(0, value, { duration: 0.6, ease: "easeOut", onUpdate: setShown });
    return () => controls.stop();
  }, [value, reduced]);
  return <>{shown.toFixed(decimals)}</>;
}
