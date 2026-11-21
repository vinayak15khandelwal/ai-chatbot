import { LogoMark, PlusIcon, SettingsIcon, SidebarIcon } from "./Icons.jsx";

const STATUS = {
  checking: { label: "Checking connection…", cls: "dot-idle" },
  ok: { label: "Connected", cls: "dot-ok" },
  degraded: { label: "Degraded", cls: "dot-warn" },
  down: { label: "Backend unreachable", cls: "dot-bad" },
};

export default function Sidebar({ collapsed, onToggle, onNewChat, onOpenSettings, sessionId, hasMessages, health, disabled }) {
  const st = STATUS[health.state] ?? STATUS.checking;
  const statusText = health.state === "ok" && health.keys ? `Connected · ${health.keys} keys` : st.label;
  return (
    <aside className="sidebar" aria-label="Sidebar">
      <div className="sidebar-top">
        <div className="brand">
          <LogoMark className="brand-mark" />
          <span className="brand-name">Resilient Chat</span>
        </div>
        <button type="button" className="btn btn-ghost btn-icon collapse-btn" onClick={onToggle}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"} data-tip={collapsed ? "Expand" : "Collapse"}>
          <SidebarIcon />
        </button>
      </div>

      <nav className="sidebar-nav" aria-label="Chat">
        <button type="button" className="nav-item nav-primary" onClick={onNewChat} disabled={disabled} data-tip="New chat">
          <PlusIcon /><span className="nav-label">New chat</span>
        </button>
        <div className="nav-section nav-label">Current</div>
        <div className="nav-item nav-active" aria-current="page" title={sessionId}>
          <span className="nav-dot" aria-hidden="true" />
          <span className="nav-label">{hasMessages ? "Active conversation" : "New conversation"}</span>
        </div>
      </nav>

      <div className="sidebar-bottom">
        <button type="button" className="nav-item" onClick={onOpenSettings} data-tip="Settings">
          <SettingsIcon /><span className="nav-label">Settings</span>
        </button>
        <div className="status" role="status" title={statusText}>
          <span className={`dot ${st.cls}`} aria-hidden="true" />
          <span className="nav-label">{statusText}</span>
        </div>
      </div>
    </aside>
  );
}
