import { useCallback, useEffect, useRef, useState } from "react";
import { newSessionId, sendChat } from "./api.js";
import { useTheme } from "./hooks/useTheme.js";
import { useHealth } from "./hooks/useHealth.js";
import Sidebar from "./components/Sidebar.jsx";
import EmptyState from "./components/EmptyState.jsx";
import Message from "./components/Message.jsx";
import Composer from "./components/Composer.jsx";
import SettingsDialog, { SIMULATIONS } from "./components/SettingsDialog.jsx";
import { MenuIcon } from "./components/Icons.jsx";

export default function App() {
  const [sessionId, setSessionId] = useState(newSessionId); // a new session on every page load
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [simulate, setSimulate] = useState("");
  const [sending, setSending] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [mobileNav, setMobileNav] = useState(false);
  const [theme, setTheme] = useTheme();
  const health = useHealth();

  const busy = useRef(false);
  const idCounter = useRef(0);
  const endRef = useRef(null);
  const inputRef = useRef(null);
  const nextId = () => ++idCounter.current;

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, sending]);

  const submit = useCallback(async (text, { retry = false } = {}) => {
    const message = (text ?? input).trim();
    if (!message || busy.current) return;
    busy.current = true;
    setSending(true);
    setMobileNav(false);
    if (!retry) {
      setMessages((m) => [...m, { id: nextId(), role: "user", content: message }]);
      setInput("");
    }
    try {
      const data = await sendChat({ sessionId, message, systemPrompt, simulate });
      setMessages((m) => [...m, { id: nextId(), role: "assistant", content: data.reply, meta: data.metadata }]);
    } catch (err) {
      // The backend does not store failed requests, so retrying the same text is safe.
      setMessages((m) => [...m, { id: nextId(), role: "error", content: err.message, retryText: message }]);
    } finally {
      busy.current = false;
      setSending(false);
      inputRef.current?.focus();
    }
  }, [input, sessionId, systemPrompt, simulate]);

  function retry(errMsg) {
    setMessages((m) => m.filter((x) => x.id !== errMsg.id));
    submit(errMsg.retryText, { retry: true });
  }

  function newChat() {
    if (busy.current) return;
    setSessionId(newSessionId());
    setMessages([]);
    setInput("");
    setMobileNav(false);
    inputRef.current?.focus();
  }

  const activeSim = SIMULATIONS.find((s) => s.value && s.value === simulate);

  return (
    <div className={`shell ${collapsed ? "is-collapsed" : ""} ${mobileNav ? "nav-open" : ""}`}>
      <Sidebar
        collapsed={collapsed}
        onToggle={() => setCollapsed((c) => !c)}
        onNewChat={newChat}
        onOpenSettings={() => { setSettingsOpen(true); setMobileNav(false); }}
        sessionId={sessionId}
        hasMessages={messages.length > 0}
        health={health}
        disabled={sending}
      />
      <div className="scrim" onClick={() => setMobileNav(false)} aria-hidden="true" />

      <div className="workspace">
        <header className="topbar">
          <button type="button" className="btn btn-ghost btn-icon menu-btn" onClick={() => setMobileNav(true)} aria-label="Open sidebar">
            <MenuIcon />
          </button>
          <div className="topbar-title">
            <span className="title">{messages.length ? "Conversation" : "New conversation"}</span>
            <span className="session-id" title={sessionId}>{sessionId.slice(0, 10)}</span>
          </div>
          {activeSim && (
            <button type="button" className="sim-pill" onClick={() => setSettingsOpen(true)} data-tip="Open developer tools">
              Simulating: {activeSim.title}
            </button>
          )}
        </header>

        <main className="thread" aria-live="polite">
          <div className="thread-inner">
            {messages.length === 0 && !sending ? (
              <EmptyState onPick={(t) => submit(t)} disabled={sending} />
            ) : (
              messages.map((m) => <Message key={m.id} msg={m} onRetry={retry} busy={sending} />)
            )}
            {sending && (
              <div className="turn" role="status" aria-label="Waiting for the reply">
                <div className="thinking"><span /><span /><span /></div>
              </div>
            )}
            <div ref={endRef} />
          </div>
        </main>

        <Composer value={input} onChange={setInput} onSubmit={() => submit()} sending={sending} inputRef={inputRef} />
      </div>

      <SettingsDialog
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        theme={theme}
        onTheme={setTheme}
        systemPrompt={systemPrompt}
        onSystemPrompt={setSystemPrompt}
        simulate={simulate}
        onSimulate={setSimulate}
      />
    </div>
  );
}
