import { useState, useRef, useEffect } from "react";
import axios from "axios";
import { sendSessionChat, clearSessionChat, type ChatMessage as ChatMessageItem } from "../api/client";
import { ChatInput } from "./ChatInput";
import { ChatMessage as ChatBubble } from "./ChatMessage";

interface Props {
  sessionId: string;
  enabled: boolean;
  history: ChatMessageItem[];
  onUpdated: () => void;
}

export function SessionChat({ sessionId, enabled, history, onUpdated }: Props) {
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [history.length, sending]);

  if (!enabled) return null;

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    const text = message.trim();
    if (text.length < 3) return;

    setSending(true);
    setError(null);
    try {
      await sendSessionChat(sessionId, text);
      setMessage("");
      onUpdated();
    } catch (err: unknown) {
      let msg = "Could not apply your edit. Try again.";
      if (axios.isAxiosError(err) && err.response?.data) {
        const detail = (err.response.data as { detail?: string }).detail;
        if (typeof detail === "string") msg = detail;
      }
      setError(msg);
    } finally {
      setSending(false);
    }
  };

  const handleClear = async () => {
    if (history.length === 0) return;
    const ok = window.confirm("Clear all edit messages? Your saved notes are not changed.");
    if (!ok) return;

    setClearing(true);
    setError(null);
    try {
      await clearSessionChat(sessionId);
      onUpdated();
    } catch (err: unknown) {
      let msg = "Could not clear chat history.";
      if (axios.isAxiosError(err) && err.response?.data) {
        const detail = (err.response.data as { detail?: string }).detail;
        if (typeof detail === "string") msg = detail;
      }
      setError(msg);
    } finally {
      setClearing(false);
    }
  };

  return (
    <section
      aria-labelledby="session-chat-heading"
      className="flex flex-col border-t border-white/[0.06] bg-chat-main shrink-0"
    >
      <div className="px-4 py-3 border-b border-white/[0.04] flex items-start justify-between gap-2">
        <div>
          <h3 id="session-chat-heading" className="text-sm font-medium text-white/80">
            Edit notes
          </h3>
          <p className="text-xs text-white/40 mt-0.5">
            Ask for changes — patches run through gap bridger and save to your files.
          </p>
        </div>
        {history.length > 0 && (
          <button
            type="button"
            onClick={handleClear}
            disabled={clearing || sending}
            className="text-xs text-white/40 hover:text-red-400 shrink-0 px-2 py-1 rounded-lg
                       hover:bg-white/[0.06] disabled:opacity-40"
          >
            {clearing ? "Clearing…" : "Clear edits"}
          </button>
        )}
      </div>

      {history.length > 0 && (
        <div ref={scrollRef} className="max-h-48 overflow-y-auto chat-scroll px-4 py-2">
          {history.map((item, i) => (
            <ChatBubble
              key={`${item.ts}-${i}`}
              role={item.role === "user" ? "user" : "assistant"}
              icon={item.role === "user" ? "Y" : "✦"}
            >
              {item.content}
            </ChatBubble>
          ))}
        </div>
      )}

      <div className="p-4 pt-2">
        <ChatInput
          value={message}
          onChange={setMessage}
          onSubmit={handleSend}
          placeholder='e.g. "Add a section on tokenization"'
          disabled={sending}
          loading={sending}
          minLength={3}
          submitLabel="Apply edit"
          rows={1}
        />
        {error && (
          <p className="text-xs text-red-400 mt-2 px-2" role="alert">
            {error}
          </p>
        )}
      </div>
    </section>
  );
}
