const base = { viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.75, strokeLinecap: "round", strokeLinejoin: "round", "aria-hidden": true, className: "icon" };
const make = (d) => (props) => <svg {...base} {...props}>{d}</svg>;

export const PlusIcon = make(<path d="M12 5v14M5 12h14" />);
export const SettingsIcon = make(<><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3h0a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5h0a1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8v0a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z" /></>);
export const SidebarIcon = make(<><rect x="3" y="4" width="18" height="16" rx="2" /><path d="M9 4v16" /></>);
export const MenuIcon = make(<path d="M4 7h16M4 12h16M4 17h16" />);
export const SendIcon = make(<path d="M12 19V5M5 12l7-7 7 7" />);
export const CopyIcon = make(<><rect x="9" y="9" width="11" height="11" rx="2" /><path d="M5 15V6a2 2 0 0 1 2-2h9" /></>);
export const CheckIcon = make(<path d="M5 12l5 5 9-10" />);
export const CloseIcon = make(<path d="M6 6l12 12M18 6L6 18" />);
export const RefreshIcon = make(<><path d="M20 11a8 8 0 1 0-2.3 5.7" /><path d="M20 5v6h-6" /></>);
export const ChevronIcon = make(<path d="M9 6l6 6-6 6" />);
export const LogoMark = (props) => (
  <svg viewBox="0 0 32 32" aria-hidden="true" {...props}>
    <rect width="32" height="32" rx="8" fill="currentColor" />
    <path d="M9 20l4-8 4 6 2-3 4 5z" fill="var(--bg)" />
  </svg>
);
