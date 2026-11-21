import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { CheckIcon, CopyIcon } from "./Icons.jsx";

async function copyText(text) {
  try { await navigator.clipboard.writeText(text); return true; } catch { return false; }
}

export function CopyButton({ text, label = "Copy", className = "" }) {
  const [done, setDone] = useState(false);
  async function onClick() {
    if (await copyText(text)) {
      setDone(true);
      setTimeout(() => setDone(false), 1500);
    }
  }
  return (
    <button type="button" className={`btn btn-ghost copy-btn ${className}`} onClick={onClick} aria-label={done ? "Copied" : label}>
      {done ? <CheckIcon /> : <CopyIcon />}<span>{done ? "Copied" : label}</span>
    </button>
  );
}

function textOf(node) {
  if (node == null || typeof node === "boolean") return "";
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(textOf).join("");
  return textOf(node.props?.children);
}

function Pre({ children }) {
  const code = Array.isArray(children) ? children[0] : children;
  const lang = /language-([\w-]+)/.exec(code?.props?.className || "")?.[1] ?? "text";
  const raw = textOf(code).replace(/\n$/, "");
  return (
    <div className="codeblock">
      <div className="codeblock-bar">
        <span>{lang}</span>
        <CopyButton text={raw} />
      </div>
      <pre><code>{raw}</code></pre>
    </div>
  );
}

const components = {
  pre: Pre,
  table: ({ children }) => <div className="table-wrap"><table>{children}</table></div>,
  a: ({ href, children }) => <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>,
};

export default function Markdown({ children }) {
  return (
    <div className="md">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>{children}</ReactMarkdown>
    </div>
  );
}
