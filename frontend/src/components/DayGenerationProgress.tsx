import { usePolling } from "../hooks/usePolling";
import { useTokenStream } from "../hooks/useTokenStream";
import { PipelineFlowchart } from "./PipelineFlowchart";
import { ActivePersonaBanner } from "./ActivePersonaBanner";
import { LiveTokenPanel } from "./LiveTokenPanel";

interface Props {
  sessionId: string;
  dayLabel: string;
}

function formatElapsed(seconds: number) {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

const NODE_HINTS: Record<string, string> = {
  research: "Writer instructions for the student notes agent — not the final lesson yet.",
  student_notes: "Writing complete student-facing lesson notes.",
  tutor_notes: "Adding tutor annotations on top of student notes (not rewriting).",
  gap_bridger: "Patching small gaps from quality review.",
};

export function DayGenerationProgress({ sessionId, dayLabel }: Props) {
  const { data: status, isLoading, error } = usePolling(sessionId);
  const tokenStream = useTokenStream(sessionId, status?.status === "running");

  if (isLoading) {
    return <p className="text-slate-400 text-sm">Loading day {dayLabel}…</p>;
  }
  if (error) {
    return <p className="text-red-400 text-sm">Day status error: {error.message}</p>;
  }
  if (!status) return null;

  const isRunning = status.status === "running";
  const showPipeline =
    isRunning || status.status === "awaiting_tutor" || status.status === "completed";
  const currentNode = status.current_node ?? undefined;
  const nodeHint = currentNode ? NODE_HINTS[currentNode] : null;

  return (
    <div className="flex flex-col gap-3 border border-slate-700 rounded-xl p-4 bg-slate-900/50">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-violet-300">Active day: {dayLabel}</h3>
        {status.elapsed_seconds > 0 && (
          <span className="text-xs text-slate-500">{formatElapsed(status.elapsed_seconds)}</span>
        )}
      </div>

      {showPipeline && status.pipeline_steps.length > 0 && (
        <PipelineFlowchart
          steps={status.pipeline_steps}
          percent={status.progress_percent}
          activeLabel={status.node_label}
          isActive={isRunning}
        />
      )}

      {(status.active_persona && (isRunning || status.status === "awaiting_tutor")) && (
        <ActivePersonaBanner
          icon={status.active_persona_icon ?? "🤖"}
          name={status.active_persona}
          blurb={status.active_persona_blurb}
          taskLabel={status.node_label}
          isLive={isRunning}
        />
      )}

      {isRunning && (
        <LiveTokenPanel
          personaIcon={tokenStream.personaIcon ?? status.active_persona_icon}
          personaName={tokenStream.personaName ?? status.active_persona ?? undefined}
          connected={tokenStream.connected}
          text={tokenStream.text}
          nodeHint={nodeHint}
        />
      )}
      {isRunning && !tokenStream.text && (
        <p className="text-sm text-slate-500 italic px-1">
          Waiting for live output from {status.node_label ?? "current step"}…
        </p>
      )}
    </div>
  );
}
