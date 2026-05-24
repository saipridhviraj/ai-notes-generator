export interface PipelineStep {
  id: string;
  label: string;
  persona: string;
  persona_icon: string;
  state: "done" | "active" | "pending" | "skipped";
}

interface Props {
  percent: number;
  step: number;
  total: number;
  steps: PipelineStep[];
  elapsedLabel?: string;
  activeLabel?: string | null;
  isActive: boolean;
}

function stepIcon(state: PipelineStep["state"]) {
  switch (state) {
    case "done":
      return "✓";
    case "active":
      return "●";
    case "skipped":
      return "—";
    default:
      return "○";
  }
}

export function PipelineProgress({
  percent,
  step,
  total,
  steps,
  elapsedLabel,
  activeLabel,
  isActive,
}: Props) {
  const clamped = Math.min(100, Math.max(0, percent));

  return (
    <div
      className="bg-slate-800 rounded-xl p-4 flex flex-col gap-3"
      aria-labelledby="pipeline-heading"
    >
      <div className="flex items-center justify-between gap-2">
        <h3 id="pipeline-heading" className="text-sm font-semibold text-slate-100">
          Generation progress
        </h3>
        <span className="text-sm font-mono text-violet-300" aria-live="polite">
          {Math.round(clamped)}%
        </span>
      </div>

      <div
        role="progressbar"
        aria-valuenow={Math.round(clamped)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`Step ${step} of ${total}`}
        className="h-2.5 w-full bg-slate-700 rounded-full overflow-hidden"
      >
        <div
          className={`h-full rounded-full transition-all duration-700 ease-out ${
            isActive
              ? "bg-gradient-to-r from-violet-600 to-violet-400 animate-pulse"
              : "bg-violet-500"
          }`}
          style={{ width: `${clamped}%` }}
        />
      </div>

      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-400">
        <span>
          Step {step} of {total}
        </span>
        {elapsedLabel && <span>· {elapsedLabel} elapsed</span>}
        {activeLabel && isActive && (
          <span className="text-violet-300">· {activeLabel}</span>
        )}
      </div>

      <ol className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 text-xs">
        {steps.map((s) => (
          <li
            key={s.id}
            className={`flex items-center gap-2 rounded-lg px-2 py-1.5 ${
              s.state === "active"
                ? "bg-violet-900/40 text-violet-200 ring-1 ring-violet-500/50"
                : s.state === "done"
                  ? "text-emerald-400/90"
                  : s.state === "skipped"
                    ? "text-slate-500 line-through"
                    : "text-slate-500"
            }`}
          >
            <span aria-hidden className="w-4 text-center shrink-0">
              {s.state === "active" ? s.persona_icon : stepIcon(s.state)}
            </span>
            <span className="flex flex-col min-w-0">
              <span className="truncate font-medium">{s.persona}</span>
              <span className="truncate text-[10px] opacity-75">{s.label}</span>
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}
