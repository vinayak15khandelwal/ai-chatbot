const BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/+$/, "");

export function newSessionId() {
  if (globalThis.crypto?.randomUUID) return "s-" + crypto.randomUUID();
  return "s-" + Math.random().toString(36).slice(2) + Date.now().toString(36);
}

function describeDetail(detail) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => `${(d.loc || []).filter((p) => p !== "body").join(".") || "request"}: ${d.msg}`)
      .join("; ");
  }
  return "";
}

/** Sends one message. Resolves to the parsed response or throws an Error with a readable message. */
export async function sendChat({ sessionId, message, systemPrompt, simulate }) {
  const headers = { "Content-Type": "application/json" };
  if (simulate) headers["X-Simulate-Failure"] = simulate;
  const body = { session_id: sessionId, message };
  if (systemPrompt && systemPrompt.trim()) body.system_prompt = systemPrompt.trim();

  let res;
  try {
    res = await fetch(`${BASE}/chat`, { method: "POST", headers, body: JSON.stringify(body) });
  } catch {
    throw new Error("Can't reach the server. Check your connection and that the backend is running, then try again.");
  }

  let data = null;
  try {
    data = await res.json();
  } catch {
    /* non-JSON body handled below */
  }

  if (!res.ok) {
    if (res.status === 503) {
      throw new Error("All AI providers are unavailable right now (rate-limited or down). Your message was not saved — try again in a moment.");
    }
    if (res.status === 422) {
      const why = describeDetail(data?.detail);
      throw new Error(`That message can't be sent${why ? ` (${why})` : ""}. Messages must be 1–4000 characters.`);
    }
    throw new Error(describeDetail(data?.detail) || `The server returned an unexpected error (${res.status}).`);
  }

  const m = data?.metadata;
  if (!data || typeof data.reply !== "string" || !m) {
    throw new Error("The server sent a response in an unexpected format.");
  }
  return data;
}
