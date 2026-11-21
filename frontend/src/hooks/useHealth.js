import { useEffect, useState } from "react";
import { getHealth } from "../api.js";

/** Polls GET /health so the sidebar can show real backend connectivity. */
export function useHealth(intervalMs = 60000) {
  const [health, setHealth] = useState({ state: "checking", keys: null });
  useEffect(() => {
    let alive = true;
    const run = async () => {
      const h = await getHealth();
      if (alive) setHealth(h);
    };
    run();
    const id = setInterval(run, intervalMs);
    return () => { alive = false; clearInterval(id); };
  }, [intervalMs]);
  return health;
}
