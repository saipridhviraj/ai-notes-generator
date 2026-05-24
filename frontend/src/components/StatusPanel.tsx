import { useState, useEffect } from "react";
import axios from "axios";
import { useQueryClient } from "@tanstack/react-query";
import { usePolling } from "../hooks/usePolling";
import { useTokenStream } from "../hooks/useTokenStream";
import { useNodeArtifact } from "../hooks/useNodeArtifact";
import { tutorRespond, cancelGeneration, resumeFromNode, restartGeneration, type ResumeFromNode } from "../api/client";
import { PipelineFlowchart } from "./PipelineFlowchart";
import { ActivePersonaBanner } from "./ActivePersonaBanner";
import { LiveTokenPanel } from "./LiveTokenPanel";
import { NodeOutputRail } from "./NodeOutputRail";
import { NodeOutputPanel } from "./NodeOutputPanel";
import { MarkdownLite } from "./MarkdownLite";
import { SessionNotesPreview } from "./SessionNotesPreview";
import { SessionChat } from "./SessionChat";
import { QualityReviewPanel } from "./QualityReviewPanel";
import { ChatMessage } from "./ChatMessage";
import { clearLastSessionId } from "../utils/sessionStorage";

interface Props {
  sessionId: string;
  onReset: () => void;
}

const STATUS_LABEL: Record<string, string> = {
  running: "⚙️  Running",
  awaiting_tutor: "🤚 Awaiting Your Review",
  completed: "✅ Completed",
  failed: "❌ Failed",
  max_retries_reached: "⚠️  Max Retries — Saved Best",
  rejected: "🚫 Rejected by Tutor",
  cancelled: "⏹️ Cancelled",
};

const NODE_HINTS: Record<string, string> = {
  planner: "Planning curriculum — JSON output, usually fast (~30s).",
  research: "Writer instructions + suggested diagram brief for the student notes agent.",
  student_notes: "Writing complete student-facing lesson notes — longest step on local Ollama.",
  tutor_notes: "Adding tutor annotations (JSON) on top of student notes.",
  gap_bridger: "Patching small gaps from quality review.",
  diagram_generator: "Generating JSON diagrams and SVG visuals from placeholders.",
  mermaid_repair: "Repairing broken diagrams in existing notes.",
  evaluator: "Scoring quality — no live tokens; usually 30–90s on local Ollama.",
  final_response: "Saving files and finishing.",
  consult_tutor: "Waiting for your plan approval.",
};

export function StatusPanel({ sessionId, onReset }: Props) {
  const queryClient = useQueryClient();
  const [streamGeneration, setStreamGeneration] = useState(0);
  const { data: status, error, isLoading, refetch } = usePolling(sessionId, streamGeneration);
  const tokenStream = useTokenStream(sessionId, status?.status === "running");
  const [feedback, setFeedback] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [responded, setResponded] = useState(false);
  const [tutorError, setTutorError] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [splitView, setSplitView] = useState(false);
  const [resuming, setResuming] = useState(false);
  const [restarting, setRestarting] = useState(false);

  const artifacts = status?.node_artifacts ?? [];
  const selectedMeta = artifacts.find((a) => a.node_id === selectedNodeId);
  const { artifact, loading: artifactLoading, error: artifactError, reload: reloadArtifact } = useNodeArtifact(
    sessionId,
    selectedNodeId,
    Boolean(selectedMeta?.available)
  );

  useEffect(() => {
    if (
      selectedNodeId &&
      status?.status &&
      ["completed", "max_retries_reached"].includes(status.status)
    ) {
      reloadArtifact();
    }
  }, [status?.status, streamGeneration, selectedNodeId, reloadArtifact]);

  // Auto-select latest completed node when new output arrives
  useEffect(() => {
    if (!status?.node_artifacts?.length) return;
    const done = [...status.node_artifacts].reverse().find((a) => a.available);
    if (done && !selectedNodeId) {
      setSelectedNodeId(done.node_id);
      setSplitView(true);
    }
  }, [status?.node_artifacts, selectedNodeId]);

  useEffect(() => {
    if (axios.isAxiosError(error) && error.response?.status === 404) {
      clearLastSessionId();
    }
  }, [error]);

  const handleSelectNode = (nodeId: string) => {
    setSelectedNodeId(nodeId);
    setSplitView(true);
  };

  const hasStudentNotes = artifacts.some(
    (a) => a.node_id === "student_notes" && a.available
  );
  const canRegenerate =
    hasStudentNotes &&
    ["completed", "max_retries_reached", "failed", "cancelled"].includes(
      status?.status ?? ""
    );

  const handleResume = async (fromNode: ResumeFromNode) => {
    setResuming(true);
    setTutorError(null);
    try {
      await resumeFromNode(sessionId, fromNode);
      setStreamGeneration((g) => g + 1);
      setResponded(false);
      void queryClient.invalidateQueries({ queryKey: ["result", sessionId] });
      void queryClient.invalidateQueries({ queryKey: ["nodeArtifact", sessionId] });
    } catch (err: unknown) {
      let message = "Failed to resume generation.";
      if (axios.isAxiosError(err) && err.response?.data) {
        const data = err.response.data as { detail?: string };
        if (typeof data.detail === "string") message = data.detail;
      }
      setTutorError(message);
    } finally {
      setResuming(false);
    }
  };

  const handleRestart = async () => {
    setRestarting(true);
    setTutorError(null);
    try {
      await restartGeneration(sessionId);
      setStreamGeneration((g) => g + 1);
      setResponded(false);
      void queryClient.invalidateQueries({ queryKey: ["result", sessionId] });
    } catch (err: unknown) {
      let message = "Failed to restart generation.";
      if (axios.isAxiosError(err) && err.response?.data) {
        const data = err.response.data as { detail?: string };
        if (typeof data.detail === "string") message = data.detail;
      }
      setTutorError(message);
    } finally {
      setRestarting(false);
    }
  };

  const handleCancel = async () => {
    setCancelling(true);
    try {
      await cancelGeneration(sessionId);
    } catch {
      setTutorError("Failed to cancel generation.");
    } finally {
      setCancelling(false);
    }
  };

  const formatElapsed = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return m > 0 ? `${m}m ${s}s` : `${s}s`;
  };

  const handleTutorRespond = async (approved: boolean) => {
    setSubmitting(true);
    setTutorError(null);
    try {
      await tutorRespond(sessionId, {
        approved,
        feedback,
        response_to: "plan_verification",
      });
      setFeedback("");
      setResponded(true);
    } catch (err: unknown) {
      let message = "Failed to send response. Please try again.";
      if (axios.isAxiosError(err) && err.response?.data) {
        const data = err.response.data as { detail?: string | Array<{ msg: string }> };
        if (typeof data.detail === "string") message = data.detail;
        else if (Array.isArray(data.detail) && data.detail[0]?.msg) message = data.detail[0].msg;
      }
      setTutorError(message);
    } finally {
      setSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div role="status" aria-live="polite" className="text-slate-400 text-sm">
        Loading status…
      </div>
    );
  }

  if (error) {
    const is404 = axios.isAxiosError(error) && error.response?.status === 404;
    return (
      <div className="flex-1 flex flex-col items-center justify-center px-4 py-12 text-center gap-4">
        <p role="alert" className="text-sm text-white/60 max-w-md">
          {is404
            ? "This conversation is no longer available — it may have been deleted or the server was restarted."
            : `Error fetching status: ${error.message}`}
        </p>
        <button type="button" onClick={onReset} className="btn-primary">
          Start new chat
        </button>
      </div>
    );
  }

  if (!status) return null;

  const label = STATUS_LABEL[status.status] ?? status.status;
  const isTerminal = ["completed", "failed", "rejected", "cancelled", "max_retries_reached"].includes(
    status.status
  );
  const isRunning = status.status === "running";
  const isInterrupted = Boolean(status.interrupted);
  const showNotesPreview = ["completed", "max_retries_reached"].includes(status.status);
  const showPipeline =
    isRunning || status.status === "awaiting_tutor" || status.status === "completed";
  const currentNode = status.current_node ?? undefined;
  const nodeHint = currentNode ? NODE_HINTS[currentNode] : null;
  const isStartingStep = isRunning && status.node_phase === "starting";
  const liveText =
    tokenStream.text ||
    (isRunning && status.status_detail && tokenStream.node === currentNode ? status.status_detail : "");
  const showLiveForSelected =
    isRunning && selectedNodeId === currentNode && !selectedMeta?.available;
  const liveFallback =
    showLiveForSelected && liveText
      ? {
          label: status.node_label ?? "Live output",
          text: liveText,
          hint: nodeHint,
        }
      : undefined;
  const showLivePanel =
    isRunning && (Boolean(liveText) || isStartingStep || Boolean(status.status_detail));

  return (
    <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
      {/* Scrollable workspace */}
      <div className="flex-1 overflow-y-auto chat-scroll px-4 py-4">
        <div className="max-w-6xl mx-auto flex flex-col gap-4">
          {/* Status bar */}
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <span
                className={`text-xs font-medium px-2.5 py-1 rounded-full ${
                  isTerminal
                    ? status.status === "completed" || status.status === "max_retries_reached"
                      ? "bg-chat-accent/20 text-chat-accent"
                      : "bg-red-500/20 text-red-300"
                    : "bg-amber-500/20 text-amber-200"
                }`}
                aria-live="polite"
              >
                {label.replace(/^[^\s]+\s*/, "")}
                {status.elapsed_seconds > 0 && ` · ${formatElapsed(status.elapsed_seconds)}`}
              </span>
            </div>
            {isTerminal && (
              <button type="button" onClick={onReset} className="btn-ghost text-chat-accent">
                New chat
              </button>
            )}
          </div>

      {isInterrupted && (
        <div
          role="alert"
          className="surface-card border-amber-500/30 p-4 flex flex-col gap-3"
        >
          <p className="text-sm text-amber-200/90">
            Generation was interrupted (likely by a server restart). Restart from the last checkpoint
            or cancel.
          </p>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={restarting}
              onClick={handleRestart}
              className="btn-primary text-sm py-2"
            >
              {restarting ? "Restarting…" : "Restart generation"}
            </button>
            <button
              type="button"
              disabled={cancelling}
              onClick={handleCancel}
              className="btn-ghost border border-white/10"
            >
              {cancelling ? "Cancelling…" : "Cancel"}
            </button>
          </div>
        </div>
      )}

      {showPipeline && status.pipeline_steps.length > 0 && (
        <PipelineFlowchart
          steps={status.pipeline_steps}
          percent={status.progress_percent}
          activeLabel={status.node_label}
          isActive={isRunning}
          statusDetail={status.status_detail}
        />
      )}

      {(status.active_persona && (isRunning || status.status === "awaiting_tutor")) && (
        <ActivePersonaBanner
          icon={status.active_persona_icon ?? "🤖"}
          name={status.active_persona}
          blurb={status.active_persona_blurb}
          taskLabel={status.status_detail ?? status.node_label}
          isLive={isRunning && status.node_phase === "streaming"}
        />
      )}

      <div className="flex flex-col gap-4">
        {(isRunning || artifacts.some((a) => a.available)) && artifacts.length > 0 && (
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setSplitView((v) => !v)}
              className={`text-xs px-3 py-1.5 rounded-lg transition-colors ${
                splitView
                  ? "bg-white/10 text-white"
                  : "text-white/50 hover:bg-white/[0.06] hover:text-white/80"
              }`}
            >
              {splitView ? "◧ Split view on" : "◨ Show step outputs"}
            </button>
          </div>
        )}

        <div
          className={
            splitView && artifacts.length > 0
              ? "grid grid-cols-1 xl:grid-cols-[12rem_minmax(0,1fr)_minmax(0,1fr)] gap-4 items-start"
              : "grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)] gap-4 items-start"
          }
        >
          {splitView && artifacts.length > 0 && (
            <NodeOutputRail
              artifacts={artifacts}
              selectedNodeId={selectedNodeId}
              currentNodeId={currentNode ?? null}
              onSelect={handleSelectNode}
            />
          )}

          {splitView ? (
            <>
              <NodeOutputPanel
                artifact={artifact}
                loading={artifactLoading && !liveFallback}
                error={artifactError}
                liveFallback={liveFallback}
              />
              <div className="flex flex-col gap-3 min-h-[20rem]">
                <dl className="surface-elevated p-4 grid grid-cols-2 gap-y-2 text-sm">
                  <dt className="text-white/40">Current step</dt>
                  <dd className="text-white/90">{status.node_label ?? "—"}</dd>
                  <dt className="text-white/40">Progress</dt>
                  <dd className="text-white/90">
                    {status.progress_step}/{status.progress_total} (
                    {Math.round(status.progress_percent)}%)
                  </dd>
                </dl>
                {showLivePanel && (
                  <LiveTokenPanel
                    personaIcon={tokenStream.personaIcon ?? status.active_persona_icon}
                    personaName={tokenStream.personaName ?? status.active_persona ?? undefined}
                    connected={tokenStream.connected}
                    text={liveText}
                    nodeHint={nodeHint}
                    statusDetail={status.status_detail}
                    isStarting={isStartingStep}
                  />
                )}
              </div>
            </>
          ) : (
            <>
              <aside className="flex flex-col gap-3">
                <dl className="surface-elevated p-4 grid grid-cols-2 gap-y-2 text-sm">
                  <dt className="text-white/40">Step</dt>
                  <dd className="text-white/90">{status.node_label ?? "—"}</dd>
                  <dt className="text-white/40">Progress</dt>
                  <dd className="text-white/90">
                    {status.progress_step}/{status.progress_total} (
                    {Math.round(status.progress_percent)}%)
                  </dd>
                  {status.retry_count > 0 && (
                    <>
                      <dt className="text-white/40">Retries</dt>
                      <dd>{status.retry_count}</dd>
                    </>
                  )}
                </dl>

                {isRunning && !isInterrupted && (
                  <button
                    onClick={handleCancel}
                    disabled={cancelling}
                    className="self-start btn-ghost border border-white/10"
                  >
                    {cancelling ? "Cancelling…" : "Cancel generation"}
                  </button>
                )}

                {status.output_files.length > 0 && (
                  <div className="surface-elevated p-4">
                    <h3 className="text-sm font-medium text-white/50 mb-1">Generated files</h3>
                    <ul className="text-xs text-white/60 space-y-1 font-mono break-all">
                      {status.output_files.map((f) => (
                        <li key={f}>{f}</li>
                      ))}
                    </ul>
                  </div>
                )}

          {status.errors.length > 0 && (
            <div role="alert" className="surface-elevated p-4 border-red-500/20">
              <h3 className="text-sm font-medium text-red-400 mb-1">Warnings / errors</h3>
              <ul className="list-disc list-inside text-xs text-red-300/90">
                {status.errors.map((e, i) => (
                  <li key={i}>{e}</li>
                ))}
              </ul>
              {canRegenerate && (
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    disabled={resuming}
                    onClick={() => handleResume("student_notes")}
                    className="text-xs btn-primary py-1.5 px-3"
                  >
                    {resuming ? "Regenerating…" : "↻ Regenerate student notes"}
                  </button>
                  <button
                    type="button"
                    disabled={resuming}
                    onClick={() => handleResume("evaluator")}
                    className="text-xs btn-ghost border border-white/10 py-1.5"
                  >
                    Retry quality check
                  </button>
                  <button
                    type="button"
                    disabled={resuming}
                    onClick={() => handleResume("tutor_notes")}
                    className="text-xs btn-ghost border border-white/10 py-1.5"
                  >
                    Retry tutor step
                  </button>
                </div>
              )}
            </div>
          )}
              </aside>

              <div className="flex flex-col gap-3 min-h-[20rem]">
                {showLivePanel && (
                  <LiveTokenPanel
                    personaIcon={tokenStream.personaIcon ?? status.active_persona_icon}
                    personaName={tokenStream.personaName ?? status.active_persona ?? undefined}
                    connected={tokenStream.connected}
                    text={liveText}
                    nodeHint={nodeHint}
                    statusDetail={status.status_detail}
                    isStarting={isStartingStep}
                  />
                )}
              </div>
            </>
          )}
        </div>

        {splitView && (
          <div className="flex flex-wrap gap-3">
            {isRunning && !isInterrupted && (
              <button
                onClick={handleCancel}
                disabled={cancelling}
                className="btn-ghost border border-white/10"
              >
                {cancelling ? "Cancelling…" : "Cancel generation"}
              </button>
            )}
            {status.errors.length > 0 && (
              <div role="alert" className="flex-1 min-w-[16rem] surface-elevated p-4 border-red-500/20">
                <h3 className="text-sm font-medium text-red-400 mb-1">Warnings / errors</h3>
                <ul className="list-disc list-inside text-xs text-red-300/90">
                  {status.errors.map((e, i) => (
                    <li key={i}>{e}</li>
                  ))}
                </ul>
                {canRegenerate && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    <button
                      type="button"
                      disabled={resuming}
                      onClick={() => handleResume("student_notes")}
                      className="text-xs btn-primary py-1.5 px-3"
                    >
                      {resuming ? "Regenerating…" : "↻ Regenerate diagrams"}
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {showNotesPreview && (
        <>
          <QualityReviewPanel
            evaluationPassed={status.evaluation_passed}
            diagramIssueCount={status.diagram_issue_count}
            retryCount={status.retry_count}
            canRegenerate={canRegenerate}
            resuming={resuming}
            onResume={handleResume}
          />
          <SessionNotesPreview sessionId={sessionId} enabled={showNotesPreview} />
        </>
      )}

      {status.status === "awaiting_tutor" && responded && (
        <ChatMessage role="assistant" icon="✓" title="Curriculum Planner">
          Plan approved — research brief → student notes → tutor guide…
        </ChatMessage>
      )}

      {status.status === "awaiting_tutor" && status.tutor_question && !responded && (
        <ChatMessage
          role="assistant"
          icon="📋"
          title="Curriculum plan review"
          actions={
            <>
              <textarea
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                placeholder="Optional feedback (e.g. add keyword: functools)…"
                rows={2}
                className="w-full surface-elevated px-3 py-2 text-sm text-white/90 resize-none
                           placeholder:text-white/30 focus:outline-none focus:ring-1 focus:ring-white/20"
              />
              {tutorError && (
                <p role="alert" className="text-red-400 text-sm w-full">
                  {tutorError}
                </p>
              )}
              <button
                onClick={() => handleTutorRespond(true)}
                disabled={submitting}
                className="btn-primary text-sm flex-1 min-w-[8rem]"
              >
                Approve plan
              </button>
              <button
                onClick={() => handleTutorRespond(false)}
                disabled={submitting}
                className="btn-ghost border border-red-500/30 text-red-300 flex-1 min-w-[8rem]"
              >
                Reject
              </button>
            </>
          }
        >
          <MarkdownLite content={status.tutor_question} />
        </ChatMessage>
      )}
        </div>
      </div>

      {showNotesPreview && (
        <SessionChat
          sessionId={sessionId}
          enabled={showNotesPreview}
          history={status.chat_history ?? []}
          onUpdated={() => {
            refetch();
            queryClient.invalidateQueries({ queryKey: ["result", sessionId] });
            queryClient.invalidateQueries({ queryKey: ["sessions"] });
          }}
        />
      )}
    </div>
  );
}
