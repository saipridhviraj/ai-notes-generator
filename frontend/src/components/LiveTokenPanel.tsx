interface Props {
  personaIcon?: string | null;
  personaName?: string | null;
  connected: boolean;
  text: string;
  nodeHint?: string | null;
  statusDetail?: string | null;
  isStarting?: boolean;
}

export function LiveTokenPanel({
  personaIcon,
  personaName,
  connected,
  text,
  nodeHint,
  statusDetail,
  isStarting,
}: Props) {
  const displayText = text || statusDetail || "";
  const showStarting = isStarting && !text;

  if (!displayText && !showStarting) return null;

  return (
    <div className="surface-elevated p-4 flex flex-col gap-2 min-h-[20rem] flex-1">
      <div className="flex items-center justify-between gap-2 shrink-0">
        <div>
          <h3 className="text-sm font-medium text-white/80 flex items-center gap-2">
            {personaIcon && <span aria-hidden>{personaIcon}</span>}
            {personaName ?? "Live output"}
          </h3>
          {nodeHint && <p className="text-[11px] text-white/35 mt-0.5">{nodeHint}</p>}
        </div>
        <span
          className={`text-xs shrink-0 ${connected ? "text-chat-accent" : "text-white/30"}`}
          aria-live="polite"
        >
          {showStarting ? "● starting…" : connected ? "● live" : "reconnecting…"}
        </span>
      </div>
      {showStarting && !displayText ? (
        <div
          className="flex-1 flex items-center justify-center min-h-[16rem] text-sm text-white/50"
          aria-live="polite"
        >
          <span className="inline-flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-chat-accent animate-pulse" />
            Starting step…
          </span>
        </div>
      ) : (
        <pre
          className="text-xs text-white/70 font-mono whitespace-pre-wrap flex-1 overflow-y-auto chat-scroll
                     leading-relaxed min-h-[16rem] max-h-[32rem]"
          aria-live="polite"
          aria-label="Live LLM output for current pipeline step"
        >
          {displayText}
        </pre>
      )}
    </div>
  );
}
