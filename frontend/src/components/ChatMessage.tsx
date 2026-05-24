interface Props {
  role: "user" | "assistant" | "system";
  icon?: string;
  title?: string;
  children: React.ReactNode;
  actions?: React.ReactNode;
}

export function ChatMessage({ role, icon, title, children, actions }: Props) {
  const isUser = role === "user";

  return (
    <div
      className={`flex gap-3 py-4 ${isUser ? "flex-row-reverse" : ""}`}
      data-role={role}
    >
      <div
        className={`shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm
          ${isUser ? "bg-chat-accent/20 text-chat-accent" : "bg-chat-elevated text-white/70"}`}
        aria-hidden
      >
        {icon ?? (isUser ? "You" : "AI").slice(0, 1)}
      </div>
      <div className={`flex flex-col gap-2 min-w-0 max-w-[85%] ${isUser ? "items-end" : "items-start"}`}>
        {title && (
          <span className="text-xs font-medium text-white/50 px-1">{title}</span>
        )}
        <div
          className={`text-[15px] leading-relaxed ${
            isUser
              ? "bg-chat-surface border border-white/[0.08] rounded-2xl rounded-tr-md px-4 py-3 text-white/90"
              : "text-white/85"
          }`}
        >
          {children}
        </div>
        {actions && <div className="flex flex-wrap gap-2 px-1">{actions}</div>}
      </div>
    </div>
  );
}
