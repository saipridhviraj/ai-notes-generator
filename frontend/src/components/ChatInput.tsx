interface Props {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  placeholder?: string;
  disabled?: boolean;
  loading?: boolean;
  minLength?: number;
  submitLabel?: string;
  rows?: number;
  className?: string;
}

export function ChatInput({
  value,
  onChange,
  onSubmit,
  placeholder = "Message…",
  disabled = false,
  loading = false,
  minLength = 3,
  submitLabel = "Send",
  rows = 1,
  className = "",
}: Props) {
  const canSend = value.trim().length >= minLength && !loading && !disabled;

  return (
    <form onSubmit={onSubmit} className={`relative ${className}`}>
      <div className="flex items-end gap-2 surface-card p-2 pl-4">
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          rows={rows}
          disabled={disabled || loading}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              if (canSend) onSubmit(e);
            }
          }}
          className="flex-1 bg-transparent border-0 text-[15px] text-white placeholder:text-white/40
                     focus:outline-none focus:ring-0 resize-none py-2 max-h-32 chat-scroll"
        />
        <button
          type="submit"
          disabled={!canSend}
          aria-label={submitLabel}
          className="shrink-0 w-9 h-9 flex items-center justify-center rounded-xl
                     bg-white text-black disabled:opacity-30 disabled:cursor-not-allowed
                     hover:bg-white/90 transition-colors mb-0.5"
        >
          {loading ? (
            <span className="w-4 h-4 border-2 border-black/20 border-t-black rounded-full animate-spin" />
          ) : (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
              <path
                d="M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8-8-8z"
                fill="currentColor"
                transform="rotate(-90 12 12)"
              />
            </svg>
          )}
        </button>
      </div>
    </form>
  );
}
