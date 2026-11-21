import { useEffect, useRef, useState } from "react";
import { newSessionId, sendChat } from "./api.js";

const SIM_OPTIONS = [
  { value: "", label: "Off" },
  { value: "key_1=429", label: "key_1 rate-limited (429)" },
  { value: "key_1=500", label: "key_1 server error (500)" },
  { value: "*=429", label: "Every key fails (429)" },
];

const SUGGESTIONS = [
  "What is the capital of France?",
  "Explain what a cache hit is in one sentence.",
];

function Meta({ m }) {
  const hit = m.resolution_source === "LLM_CACHE";
  return (
    <dl className="meta">
      <div className="meta-item">
        <dt>Source</dt>
        <dd>
          <span className={`badge ${hit ? "badge-cache" : "badge-live"}`} data-testid="meta-source">
            {m.resolution_source}
          </span>
        </dd>
      </div>
      <div className="meta-item">
        <dt>Model</dt>
        <dd data-testid="meta-model">{m.model}</dd>
      </div>
      <div className="meta-item">
        <dt>Latency</dt>
        <dd data-testid="meta-latency">{m.latency_ms} ms</dd>
      </div>
      <div className="meta-item">
        <dt>Input tokens</dt>
        <dd data-testid="meta-input-tokens">{m.input_tokens}</dd>
      </div>
      <div className="meta-item">
        <dt>Output tokens</dt>
        <dd data-testid="meta-output-tokens">{m.output_tokens}</dd>
      </div>
      <div className="meta-item meta-extra">
        <dt>Answered by</dt>
        <dd>
          {m.key_id ?? "cache"}
          {m.fallback_attempts > 0 ? ` after ${m.fallback_attempts} failed ${m.fallback_attempts === 1 ? "key" : "keys"}` : ""}
        </dd>
      </div>
    </dl>
  );
}

function Message({ msg }) {
  if (msg.role === "user") {
    return (
      <div className="row row-user">
        <div className="bubble bubble-user">{msg.content}</div>
      </div>
    );
  }
  if (msg.role === "error") {
    return (
      <div className="row">
        <div className="error" role="alert">{msg.content}</div>
      </div>
    );
  }
  return (
    <div className="row">
      <article className="bubble bubble-assistant" data-testid="assistant-message">
        <div className="reply">{msg.content}</div>
        <Meta m={msg.meta} />
      </article>
    </div>
  );
}

export default function App() {
  const [sessionId, setSessionId] = useState(newSessionId); // new session on every page load
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [simulate, setSimulate] = useState("");
  const [sending, setSending] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const busy = useRef(false);
  const endRef = useRef(null);
  const inputRef = useRef(null);
  const counter = useRef(0);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, sending]);

  const nextId = () => ++counter.current;

  async function submit(text) {
    const message = (text ?? input).trim();
    if (!message || busy.current) return;
    busy.current = true;
    setSending(true);
    setMessages((m) => [...m, { id: nextId(), role: "user", content: message }]);
    setInput("");
    try {
      const data = await sendChat({ sessionId, message, systemPrompt, simulate });
      setMessages((m) => [...m, { id: nextId(), role: "assistant", content: data.reply, meta: data.metadata }]);
    } catch (err) {
      setMessages((m) => [...m, { id: nextId(), role: "error", content: err.message }]);
    } finally {
      busy.current = false;
      setSending(false);
      inputRef.current?.focus();
    }
  }

  function onKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      submit();
    }
  }

  function newChat() {
    if (busy.current) return;
    setSessionId(newSessionId());
    setMessages([]);
    setInput("");
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="logo" aria-hidden="true"><i /><i /></span>
          <div>
            <h1>Resilient chat</h1>
            <p className="session" title={sessionId}>Session {sessionId.slice(0, 10)}…</p>
          </div>
        </div>
        <div className="actions">
          <button type="button" className="ghost" onClick={() => setShowSettings((s) => !s)} aria-expanded={showSettings}>
            Settings
          </button>
          <button type="button" className="ghost" onClick={newChat} disabled={sending}>New chat</button>
        </div>
      </header>

      {showSettings && (
        <section className="settings" aria-label="Session settings">
          <label>
            <span>System prompt for this session</span>
            <textarea
              data-testid="system-prompt-input"
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              rows={2}
              maxLength={8000}
              placeholder="e.g. You are a pirate. Keep answers short."
            />
          </label>
          <label>
            <span>Simulate key failure (demo)</span>
            <select value={simulate} onChange={(e) => setSimulate(e.target.value)}>
              {SIM_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </label>
        </section>
      )}

      <main className="thread" aria-live="polite">
        {messages.length === 0 && (
          <div className="empty">
            <h2>Ask anything</h2>
            <p>Each reply shows where it came from, how long it took and how many tokens it used. Ask the same question in a new chat to see a cache hit.</p>
            <div className="chips">
              {SUGGESTIONS.map((s) => (
                <button key={s} type="button" className="chip" onClick={() => submit(s)} disabled={sending}>{s}</button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m) => <Message key={m.id} msg={m} />)}
        {sending && (
          <div className="row">
            <div className="bubble bubble-assistant typing" role="status" aria-label="Waiting for the reply">
              <span /><span /><span />
            </div>
          </div>
        )}
        <div ref={endRef} />
      </main>

      <footer className="composer">
        <textarea
          ref={inputRef}
          data-testid="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          rows={1}
          maxLength={4000}
          placeholder="Write a message — Enter to send, Shift+Enter for a new line"
          aria-label="Message"
        />
        <button type="button" data-testid="send-button" className="send" onClick={() => submit()} disabled={sending || !input.trim()}>
          {sending ? "Sending…" : "Send"}
        </button>
      </footer>
    </div>
  );
}
