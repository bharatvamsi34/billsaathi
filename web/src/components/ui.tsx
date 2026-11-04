"use client";

// Shared building blocks, so every screen looks like one product.
import { AnimatePresence, motion, type HTMLMotionProps } from "motion/react";
import type { ReactNode } from "react";

export const EASE = { duration: 0.2, ease: "easeOut" } as const;
export const rise = { initial: { opacity: 0, y: 8 }, animate: { opacity: 1, y: 0 }, transition: EASE } as const;

type Variant = "primary" | "secondary" | "ghost" | "danger" | "safe" | "onDark" | "onDarkGhost";
type Size = "sm" | "md" | "lg";

const VARIANTS: Record<Variant, string> = {
  primary: "bg-brand text-white shadow-soft hover:bg-brand-bright",
  secondary: "border border-line bg-card text-ink shadow-soft hover:border-brand hover:text-brand",
  ghost: "text-brand hover:bg-brand-soft",
  danger: "bg-scam text-white shadow-soft hover:brightness-110",
  safe: "bg-safe text-white shadow-soft hover:brightness-110",
  onDark: "bg-white text-navy shadow-lift hover:bg-brand-soft",
  onDarkGhost: "border border-white/35 text-white hover:border-white hover:bg-white/10",
};
const SIZES: Record<Size, string> = {
  sm: "min-h-11 px-4 text-[15px] lg:min-h-9",
  md: "min-h-11 px-5 text-[15px]",
  lg: "min-h-13 px-6 text-base",
};

export function buttonClass(variant: Variant = "primary", size: Size = "md", extra = ""): string {
  return `inline-flex items-center justify-center gap-2 rounded-full py-1.5 text-center font-semibold leading-snug transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-50 ${VARIANTS[variant]} ${SIZES[size]} ${extra}`;
}

export function Button({
  variant = "primary",
  size = "md",
  className = "",
  children,
  ...rest
}: { variant?: Variant; size?: Size; children: ReactNode } & HTMLMotionProps<"button">) {
  return (
    <motion.button type="button" whileHover={{ y: -1 }} whileTap={{ scale: 0.98 }} transition={{ duration: 0.15 }} className={buttonClass(variant, size, className)} {...rest}>
      {children}
    </motion.button>
  );
}

/** Long links and UPI IDs break after @ / . and never in the middle of a word, if they can. */
export function Soft({ text }: { text: string }) {
  return (
    <>
      {text.split(/(?<=[@/.])/).map((part, i) => (
        <span key={i}>
          {i > 0 && <wbr />}
          {part}
        </span>
      ))}
    </>
  );
}

export function Card({ className = "", children, ...rest }: { className?: string; children: ReactNode } & React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={`rounded-[18px] border border-line bg-card shadow-soft ${className}`} {...rest}>
      {children}
    </div>
  );
}

export type Tone = "good" | "bad" | "warn" | "info" | "neutral";
const TONES: Record<Tone, string> = {
  good: "bg-safe-bg text-safe",
  bad: "bg-scam-bg text-scam",
  warn: "bg-caution-bg text-caution",
  info: "bg-brand-soft text-brand",
  neutral: "bg-paper text-ink-soft",
};

export function Badge({ tone = "neutral", className = "", children }: { tone?: Tone; className?: string; children: ReactNode }) {
  return <span className={`inline-flex max-w-full items-center gap-1 rounded-full px-2.5 py-0.5 text-[13px] font-semibold leading-snug ${TONES[tone]} ${className}`}>{children}</span>;
}

export function Chip({ active, className = "", children, ...rest }: { active?: boolean; children: ReactNode } & HTMLMotionProps<"button">) {
  return (
    <motion.button
      type="button"
      whileTap={{ scale: 0.97 }}
      transition={{ duration: 0.15 }}
      className={`inline-flex min-h-11 items-center justify-center gap-1.5 rounded-full border px-3.5 text-sm font-semibold leading-tight transition-colors duration-150 disabled:opacity-50 ${
        active ? "border-brand bg-brand-soft text-brand" : "border-line bg-card text-ink hover:border-brand hover:text-brand"
      } ${className}`}
      {...rest}
    >
      {children}
    </motion.button>
  );
}

export function Tabs<T extends string>({ tabs, value, onChange, label, id = "tabs" }: { tabs: { value: T; label: string }[]; value: T; onChange: (v: T) => void; label: string; id?: string }) {
  return (
    <div role="tablist" aria-label={label} className="grid grid-cols-2 gap-1 rounded-full bg-[#e9edf2] p-1">
      {tabs.map((tab) => {
        const on = tab.value === value;
        return (
          <button
            key={tab.value}
            type="button"
            role="tab"
            aria-selected={on}
            onClick={() => onChange(tab.value)}
            className={`relative min-h-10 rounded-full px-3 text-[15px] font-semibold transition-colors duration-150 ${on ? "text-ink" : "text-muted hover:text-ink"}`}
          >
            {on && <motion.span layoutId={`${id}-pill`} transition={{ duration: 0.2, ease: "easeOut" }} className="absolute inset-0 rounded-full bg-card shadow-soft" />}
            <span className="relative">{tab.label}</span>
          </button>
        );
      })}
    </div>
  );
}

export function Switch({ checked, onChange, label, disabled, dark }: { checked: boolean; onChange: (v: boolean) => void; label: string; disabled?: boolean; dark?: boolean }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex min-h-8 shrink-0 items-center gap-1.5 before:absolute before:inset-x-0 before:-inset-y-1.5 lg:before:hidden whitespace-nowrap rounded-full text-[12px] font-semibold leading-tight disabled:opacity-50 lg:gap-2 lg:text-[13px] ${dark ? "text-white" : "text-ink"}`}
    >
      <span className={`relative h-5 w-9 shrink-0 rounded-full transition-colors duration-150 ${checked ? "bg-brand" : "bg-[#727F8E]"}`}>
        <motion.span animate={{ x: checked ? 16 : 0 }} transition={{ duration: 0.15, ease: "easeOut" }} className="absolute left-0.5 top-0.5 block h-4 w-4 rounded-full bg-white shadow" />
      </span>
      {label}
    </button>
  );
}

export function Skeleton({ lines = 2, className = "" }: { lines?: number; className?: string }) {
  return (
    <div aria-hidden="true" className={`space-y-2 ${className}`}>
      {Array.from({ length: lines }, (_, i) => (
        <div key={i} className={`skeleton h-3 ${i % 2 ? "w-2/3" : "w-11/12"}`} />
      ))}
    </div>
  );
}

export function Toast({ message }: { message: string | null }) {
  return (
    <AnimatePresence>
      {message && (
        <motion.p
          role="status"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 12 }}
          transition={EASE}
          className="glass fixed inset-x-4 bottom-5 z-30 mx-auto max-w-md rounded-2xl border border-line px-4 py-3 text-center text-[15px] font-semibold shadow-lift"
        >
          {message}
        </motion.p>
      )}
    </AnimatePresence>
  );
}
