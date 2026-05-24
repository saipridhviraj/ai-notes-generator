import type { PipelineStep } from "./PipelineProgress";

interface Props {
  steps: PipelineStep[];
  percent: number;
  activeLabel?: string | null;
  isActive: boolean;
  statusDetail?: string | null;
}

function connectorClass(left: PipelineStep["state"], right: PipelineStep["state"]) {
  if (left === "done" && (right === "active" || right === "done")) {
    return "text-chat-accent";
  }
  if (left === "active") {
    return "text-chat-accent/70 animate-pulse";
  }
  return "text-white/15";
}

export function PipelineFlowchart({ steps, percent, activeLabel, isActive, statusDetail }: Props) {
  const activeStep = steps.find((s) => s.state === "active");

  return (
    <div className="surface-card p-4 flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-medium text-white/80">Generation flow</h3>
        <span className="text-xs font-mono text-chat-accent">{Math.round(percent)}%</span>
      </div>

      {activeStep && isActive && (
        <div
          className="flex items-center gap-2 rounded-xl bg-chat-accent/10 border border-chat-accent/20 px-3 py-2"
          role="status"
          aria-live="polite"
        >
          <span className="relative flex h-2 w-2 shrink-0">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-chat-accent opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-chat-accent" />
          </span>
          <span className="text-xs text-white/80">
            <span className="font-medium text-chat-accent">In progress · </span>
            {activeStep.persona_icon} {activeLabel ?? activeStep.label}
            {statusDetail && (
              <span className="block text-[10px] text-white/40 mt-0.5 font-normal">
                {statusDetail}
              </span>
            )}
          </span>
        </div>
      )}

      <div className="overflow-x-auto pb-1 chat-scroll">
        <ol className="flex items-stretch gap-0 min-w-max" aria-label="Pipeline steps">
          {steps.map((step, i) => {
            const isCurrent = step.state === "active";
            const isDone = step.state === "done";
            const isSkipped = step.state === "skipped";

            return (
              <li key={step.id} className="flex items-center gap-0">
                <div
                  aria-current={isCurrent ? "step" : undefined}
                  className={`relative flex flex-col items-center min-w-[5rem] max-w-[6rem] px-2 py-2.5 rounded-xl text-center transition-all duration-300 ${
                    isCurrent
                      ? "bg-chat-accent/15 ring-1 ring-chat-accent/50 scale-105 z-10"
                      : isDone
                        ? "bg-chat-accent/5 ring-1 ring-chat-accent/20 text-chat-accent"
                        : isSkipped
                          ? "opacity-30 text-white/30"
                          : "bg-white/[0.03] text-white/35 ring-1 ring-white/[0.06]"
                  }`}
                >
                  {isCurrent && (
                    <span className="absolute -top-2 left-1/2 -translate-x-1/2 text-[9px] font-bold uppercase tracking-wide bg-chat-accent text-white px-1.5 py-0.5 rounded-full whitespace-nowrap">
                      Now
                    </span>
                  )}
                  <span className="text-xl leading-none mt-1" aria-hidden>
                    {isDone ? "✓" : step.persona_icon}
                  </span>
                  <span
                    className={`text-[10px] font-semibold mt-1.5 leading-tight ${
                      isCurrent ? "text-white" : ""
                    }`}
                  >
                    {step.label}
                  </span>
                  <span className="text-[9px] text-white/30 mt-0.5 leading-tight line-clamp-2">
                    {step.persona}
                  </span>
                </div>
                {i < steps.length - 1 && (
                  <span
                    className={`text-sm px-0.5 self-center ${connectorClass(step.state, steps[i + 1].state)}`}
                    aria-hidden
                  >
                    →
                  </span>
                )}
              </li>
            );
          })}
        </ol>
      </div>
    </div>
  );
}
