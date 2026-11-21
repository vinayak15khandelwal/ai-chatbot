const PROMPTS = [
  { title: "Explain a technical concept", text: "Explain how database indexes work and when they hurt performance." },
  { title: "Help me debug code", text: "My React component re-renders on every keystroke. What are the usual causes?" },
  { title: "Compare two technologies", text: "Compare REST and GraphQL for a small team building a public API." },
  { title: "Summarize a complex topic", text: "Summarize how HTTPS and TLS keep a connection secure." },
];

export default function EmptyState({ onPick, disabled }) {
  return (
    <div className="empty">
      <h1>How can I help you today?</h1>
      <p>Ask a question or pick a starting point. Every reply shows where it came from, how long it took and its token usage.</p>
      <div className="prompt-grid">
        {PROMPTS.map((p) => (
          <button key={p.title} type="button" className="prompt" onClick={() => onPick(p.text)} disabled={disabled}>
            <strong>{p.title}</strong>
            <span>{p.text}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
