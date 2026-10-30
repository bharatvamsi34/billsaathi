"use client";

import { useSyncExternalStore } from "react";
import { LANGS, type Lang } from "./i18n";

// The chosen language, remembered in this browser when storage is available (it may be
// blocked; then it lasts for this visit only). The server render is always English.
const KEY = "billsaathi.lang";
const EVENT = "billsaathi-lang";
let memory: Lang = "en";

function read(): Lang {
  try {
    const saved = localStorage.getItem(KEY);
    if (saved && LANGS.some((l) => l.code === saved)) return saved as Lang;
  } catch {}
  return memory;
}

function subscribe(onChange: () => void): () => void {
  window.addEventListener(EVENT, onChange);
  window.addEventListener("storage", onChange);
  return () => {
    window.removeEventListener(EVENT, onChange);
    window.removeEventListener("storage", onChange);
  };
}

export function useLang(): [Lang, (lang: Lang) => void] {
  const lang = useSyncExternalStore(subscribe, read, () => "en" as Lang);
  const set = (next: Lang) => {
    memory = next;
    try {
      localStorage.setItem(KEY, next);
    } catch {}
    window.dispatchEvent(new Event(EVENT));
  };
  return [lang, set];
}
