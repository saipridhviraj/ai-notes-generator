import type { ResumeFromNode } from "../api/client";

interface Props {
  evaluationPassed?: boolean | null;
  diagramIssueCount?: number;
  retryCount?: number;
  canRegenerate: boolean;
  resuming: boolean;
  onResume: (fromNode: ResumeFromNode) => void;
}

export function QualityReviewPanel({
  evaluationPassed,
  diagramIssueCount = 0,
  retryCount = 0,
  canRegenerate,
  resuming,
  onResume,
}: Props) {
  return (
    <div role="status" className="surface-elevated p-4 text-sm">
      <p className="font-medium text-white/80 mb-1">Quality review</p>
      <p className="text-xs text-white/45">
        {evaluationPassed === true
          ? "Evaluation passed"
          : evaluationPassed === false
            ? "Evaluation did not fully pass — notes saved anyway"
            : "Evaluation not available"}
        {diagramIssueCount > 0 && ` · ${diagramIssueCount} diagram issue(s)`}
        {retryCount > 0 && ` · ${retryCount} repair cycle(s)`}
      </p>
      {canRegenerate && (
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            type="button"
            disabled={resuming}
            onClick={() => onResume("student_notes")}
            className="text-xs btn-primary py-1.5 px-3"
          >
            {resuming ? "Regenerating…" : "↻ Regenerate student notes"}
          </button>
          <button
            type="button"
            disabled={resuming}
            onClick={() => onResume("mermaid_repair")}
            className="text-xs btn-ghost border border-violet-500/30 text-violet-200 py-1.5"
          >
            Repair diagrams only
          </button>
          <button
            type="button"
            disabled={resuming}
            onClick={() => onResume("evaluator")}
            className="text-xs btn-ghost border border-white/10 py-1.5"
          >
            Retry quality check
          </button>
          <button
            type="button"
            disabled={resuming}
            onClick={() => onResume("tutor_notes")}
            className="text-xs btn-ghost border border-white/10 py-1.5"
          >
            Retry tutor step
          </button>
        </div>
      )}
    </div>
  );
}
