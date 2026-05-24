interface Props {
  icon: string;
  name: string;
  blurb: string | null;
  taskLabel?: string | null;
  isLive?: boolean;
}

export function ActivePersonaBanner({
  icon,
  name,
  blurb,
  taskLabel,
  isLive = false,
}: Props) {
  return (
    <div
      className="surface-card border-chat-accent/20 p-4 flex gap-3 items-start"
      role="status"
      aria-live="polite"
      aria-label={`Active specialist: ${name}`}
    >
      <span className="text-2xl shrink-0" aria-hidden>
        {icon}
      </span>
      <div className="flex flex-col gap-0.5 min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-medium text-white/90">{name}</span>
          {isLive && (
            <span className="text-xs text-chat-accent font-medium">● working</span>
          )}
        </div>
        {taskLabel && <span className="text-xs text-white/60">{taskLabel}</span>}
        {blurb && <p className="text-xs text-white/40 leading-relaxed">{blurb}</p>}
      </div>
    </div>
  );
}
