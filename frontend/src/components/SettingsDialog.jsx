import { useEffect, useRef } from "react";
import { CloseIcon } from "./Icons.jsx";

export const SIMULATIONS = [
  { value: "", title: "Off", desc: "Normal operation. Requests use the live key pool." },
  { value: "key_1=429", title: "Key 1 rate-limited (429)", desc: "key_1 fails; the request should fail over to key_2." },
  { value: "key_1=500", title: "Key 1 server error (500)", desc: "key_1 fails with a provider error; key_2 should answer." },
  { value: "*=429", title: "All keys fail (429)", desc: "Every key fails; expect a 503 and nothing saved to history." },
];

export default function SettingsDialog({ open, onClose, theme, onTheme, systemPrompt, onSystemPrompt, simulate, onSimulate }) {
  const ref = useRef(null);

  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);

  return (
    <dialog ref={ref} className="dialog" onClose={onClose} onClick={(e) => { if (e.target === ref.current) onClose(); }} aria-labelledby="settings-title">
      <div className="dialog-head">
        <h2 id="settings-title">Settings</h2>
        <button type="button" className="btn btn-ghost btn-icon" onClick={onClose} aria-label="Close settings"><CloseIcon /></button>
      </div>
      <div className="dialog-body">
        <section className="settings-section">
          <h3>General</h3>
          <div className="field">
            <label htmlFor="system-prompt">System prompt</label>
            <textarea
              id="system-prompt"
              className="input"
              data-testid="system-prompt-input"
              value={systemPrompt}
              onChange={(e) => onSystemPrompt(e.target.value)}
              maxLength={8000}
              placeholder="e.g. You are a concise technical assistant."
            />
            <p className="help">Sent with each message and kept for this conversation. Leave empty to use the default assistant behavior.</p>
          </div>
        </section>

        <section className="settings-section">
          <h3>Appearance</h3>
          <div className="field">
            <span className="field-label" id="theme-label">Theme</span>
            <div className="segmented" role="group" aria-labelledby="theme-label">
              {["light", "dark", "system"].map((t) => (
                <button key={t} type="button" aria-pressed={theme === t} onClick={() => onTheme(t)}>
                  {t[0].toUpperCase() + t.slice(1)}
                </button>
              ))}
            </div>
          </div>
        </section>

        <details className="settings-section dev" open={Boolean(simulate)}>
          <summary><h3>Developer tools</h3></summary>
          <div className="field">
            <span className="field-label">Failure simulation</span>
            <p className="help">Makes chosen keys fail for each message you send, to demonstrate automatic failover. Requires the backend setting ENABLE_FAILURE_SIMULATION.</p>
            <div className="radio-list" role="radiogroup" aria-label="Failure simulation">
              {SIMULATIONS.map((s) => (
                <label key={s.value || "off"} className="radio-row">
                  <input type="radio" name="simulate" checked={simulate === s.value} onChange={() => onSimulate(s.value)} />
                  <div><strong>{s.title}</strong><span>{s.desc}</span></div>
                </label>
              ))}
            </div>
          </div>
        </details>
      </div>
      <div className="dialog-foot">
        <button type="button" className="btn btn-primary" onClick={onClose}>Done</button>
      </div>
    </dialog>
  );
}
