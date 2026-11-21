import { useEffect, useState } from "react";

const KEY = "theme";
const read = () => {
  try { return localStorage.getItem(KEY) || "system"; } catch { return "system"; }
};

/** Theme preference: "light" | "dark" | "system". Resolved value is written to <html data-theme>. */
export function useTheme() {
  const [pref, setPref] = useState(read);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const apply = () => {
      const dark = pref === "dark" || (pref === "system" && mq.matches);
      document.documentElement.dataset.theme = dark ? "dark" : "light";
    };
    apply();
    try { localStorage.setItem(KEY, pref); } catch { /* storage unavailable: keep in memory */ }
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, [pref]);

  return [pref, setPref];
}
