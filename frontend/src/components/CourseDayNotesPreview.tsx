import { useState } from "react";
import axios from "axios";
import { useQueryClient } from "@tanstack/react-query";
import { usePolling } from "../hooks/usePolling";
import {
  resumeFromNode,
  type ResumeFromNode,
} from "../api/client";
import { SessionNotesPreview } from "./SessionNotesPreview";
import { SessionChat } from "./SessionChat";
import { QualityReviewPanel } from "./QualityReviewPanel";

interface DayPlan {
  day: number;
  title: string;
  topic: string;
}

interface Props {
  daysCompleted: number[];
  daySessions: Record<string, string>;
  planDays: DayPlan[];
}

export function CourseDayNotesPreview({ daysCompleted, daySessions, planDays }: Props) {
  const queryClient = useQueryClient();
  const sorted = [...daysCompleted].sort((a, b) => a - b);
  const [selectedDay, setSelectedDay] = useState<number>(() => sorted[sorted.length - 1] ?? 0);
  const [resuming, setResuming] = useState(false);
  const [resumeError, setResumeError] = useState<string | null>(null);
  const [streamGeneration, setStreamGeneration] = useState(0);

  const sessionId = daySessions[String(selectedDay)];
  const dayInfo = planDays.find((d) => d.day === selectedDay);

  const { data: sessionStatus } = usePolling(sessionId ?? null, streamGeneration);

  const chatEnabled =
    Boolean(sessionId) &&
    ["completed", "max_retries_reached"].includes(sessionStatus?.status ?? "");

  const hasStudentNotes = Boolean(
    sessionStatus?.node_artifacts?.some((a) => a.node_id === "student_notes" && a.available)
  );
  const canRegenerate =
    hasStudentNotes &&
    ["completed", "max_retries_reached", "failed", "cancelled"].includes(
      sessionStatus?.status ?? ""
    );

  const handleResume = async (fromNode: ResumeFromNode) => {
    if (!sessionId) return;
    setResuming(true);
    setResumeError(null);
    try {
      await resumeFromNode(sessionId, fromNode);
      setStreamGeneration((g) => g + 1);
      queryClient.invalidateQueries({ queryKey: ["status", sessionId] });
      queryClient.invalidateQueries({ queryKey: ["result", sessionId] });
    } catch (err: unknown) {
      let message = "Failed to regenerate.";
      if (axios.isAxiosError(err) && err.response?.data) {
        const detail = (err.response.data as { detail?: string }).detail;
        if (typeof detail === "string") message = detail;
      }
      setResumeError(message);
    } finally {
      setResuming(false);
    }
  };

  if (!sessionId || sorted.length === 0) return null;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-3">
        <label htmlFor="day-preview-select" className="text-sm text-slate-400">
          Preview day
        </label>
        <select
          id="day-preview-select"
          value={selectedDay}
          onChange={(e) => setSelectedDay(Number(e.target.value))}
          className="bg-slate-800 border border-slate-600 text-slate-100 text-sm rounded-lg px-3 py-1.5"
        >
          {sorted.map((day) => {
            const info = planDays.find((d) => d.day === day);
            return (
              <option key={day} value={day}>
                Day {String(day).padStart(2, "0")}
                {info?.title ? `: ${info.title}` : ""}
              </option>
            );
          })}
        </select>
        {dayInfo && (
          <span className="text-xs text-slate-500 truncate">{dayInfo.topic}</span>
        )}
      </div>

      {chatEnabled && sessionStatus && (
        <QualityReviewPanel
          evaluationPassed={sessionStatus.evaluation_passed}
          diagramIssueCount={sessionStatus.diagram_issue_count}
          retryCount={sessionStatus.retry_count}
          canRegenerate={canRegenerate}
          resuming={resuming}
          onResume={handleResume}
        />
      )}

      {resumeError && (
        <p role="alert" className="text-xs text-red-400">
          {resumeError}
        </p>
      )}

      <SessionNotesPreview sessionId={sessionId} enabled={Boolean(sessionId)} />
      <SessionChat
        sessionId={sessionId}
        enabled={chatEnabled}
        history={sessionStatus?.chat_history ?? []}
        onUpdated={() => {
          queryClient.invalidateQueries({ queryKey: ["status", sessionId] });
          queryClient.invalidateQueries({ queryKey: ["result", sessionId] });
          queryClient.invalidateQueries({ queryKey: ["course"] });
        }}
      />
    </div>
  );
}
