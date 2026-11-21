import { useEffect, useRef } from "react";
import { SendIcon } from "./Icons.jsx";

const MAX = 4000;

export default function Composer({ value, onChange, onSubmit, sending, inputRef }) {
  const fallback = useRef(null);
  const ref = inputRef ?? fallback;

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [value, ref]);

  function onKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      onSubmit();
    }
  }
  const empty = !value.trim();
  return (
    <div className="composer-wrap">
      <div className="composer">
        <textarea
          ref={ref}
          data-testid="chat-input"
          className="composer-input"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={onKeyDown}
          rows={1}
          maxLength={MAX}
          placeholder="Message Resilient Chat"
          aria-label="Message"
        />
        <button type="button" data-testid="send-button" className="send-btn" onClick={() => onSubmit()}
          disabled={sending || empty} aria-label={sending ? "Sending" : "Send message"}>
          {sending ? <span className="spinner" aria-hidden="true" /> : <SendIcon />}
        </button>
      </div>
      <p className="composer-hint">
        <span>Enter to send · Shift + Enter for a new line</span>
        {value.length > MAX * 0.85 && <span className="count">{value.length} / {MAX}</span>}
      </p>
    </div>
  );
}
