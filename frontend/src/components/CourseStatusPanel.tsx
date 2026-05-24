import { useState, useEffect } from "react";
import axios from "axios";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getCourseStatus,
  respondCoursePlan,
  respondCourseCheckpoint,
  cancelCourse,
  resumeCourseBatch,
  retryCourseDay,
  type CourseStatusResponse,
} from "../api/client";
import { invalidateCourseHistory, isCourseTerminal } from "../utils/historyInvalidation";
import { DayPlanChecklist } from "./DayPlanChecklist";
import { DayGenerationProgress } from "./DayGenerationProgress";
import { PipelineProgress } from "./PipelineProgress";
import { CourseDayNotesPreview } from "./CourseDayNotesPreview";

interface Props {
  courseId: string;
  onReset: () => void;
}

const STATUS_LABEL: Record<string, string> = {
  awaiting_plan_approval: "📋 Awaiting plan approval",
  generating: "⚙️ Generating daily notes",
  awaiting_checkpoint: "🤚 Checkpoint review",
  completed: "✅ Course completed",
  failed: "❌ Failed",
  rejected: "🚫 Plan rejected",
  paused: "⏸️ Paused",
};

function courseRefetchInterval(status?: string) {
  if (status === "generating") return 2000;
  return false;
}

function CourseProgressBar({ status }: { status: CourseStatusResponse }) {
  const inFlight =
    status.status === "generating" && status.current_generating_day != null;
  const percent = inFlight
    ? Math.min(
        99,
        ((status.days_completed.length + 0.5) / status.total_days) * 100
      )
    : status.progress_percent;

  return (
    <PipelineProgress
      percent={percent}
      step={status.days_completed.length}
      total={status.total_days}
      steps={[]}
      activeLabel={
        inFlight && status.current_day_title
          ? `Day ${status.current_generating_day}: ${status.current_day_title}`
          : undefined
      }
      isActive={status.status === "generating"}
    />
  );
}

export function CourseStatusPanel({ courseId, onReset }: Props) {
  const queryClient = useQueryClient();
  const { data: status, refetch } = useQuery({
    queryKey: ["course", courseId],
    queryFn: () => getCourseStatus(courseId),
    refetchInterval: (q) => courseRefetchInterval(q.state.data?.status),
  });
  const [submitting, setSubmitting] = useState(false);
  const [planFeedback, setPlanFeedback] = useState("");
  const [checkpointFeedback, setCheckpointFeedback] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    if (status && isCourseTerminal(status.status)) {
      invalidateCourseHistory(queryClient);
    }
  }, [status?.status, queryClient, status]);

  const handlePlanRespond = async (approved: boolean) => {
    setSubmitting(true);
    setActionError(null);
    try {
      await respondCoursePlan(courseId, approved, planFeedback);
      setPlanFeedback("");
      await refetch();
      invalidateCourseHistory(queryClient);
    } catch (err: unknown) {
      setActionError(readError(err));
    } finally {
      setSubmitting(false);
    }
  };

  const handleCheckpointRespond = async (approved: boolean) => {
    setSubmitting(true);
    setActionError(null);
    try {
      await respondCourseCheckpoint(courseId, approved, checkpointFeedback);
      setCheckpointFeedback("");
      await refetch();
      invalidateCourseHistory(queryClient);
    } catch (err: unknown) {
      setActionError(readError(err));
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancel = async () => {
    setSubmitting(true);
    setActionError(null);
    try {
      await cancelCourse(courseId);
      await refetch();
      invalidateCourseHistory(queryClient);
    } catch (err: unknown) {
      setActionError(readError(err));
    } finally {
      setSubmitting(false);
    }
  };

  const handleResumeBatch = async () => {
    setSubmitting(true);
    setActionError(null);
    try {
      await resumeCourseBatch(courseId);
      await refetch();
      invalidateCourseHistory(queryClient);
    } catch (err: unknown) {
      setActionError(readError(err));
    } finally {
      setSubmitting(false);
    }
  };

  const handleRetryDay = async () => {
    setSubmitting(true);
    setActionError(null);
    try {
      await retryCourseDay(courseId);
      await refetch();
      invalidateCourseHistory(queryClient);
    } catch (err: unknown) {
      setActionError(readError(err));
    } finally {
      setSubmitting(false);
    }
  };

  if (!status) {
    return <p className="text-slate-400 text-sm">Loading course…</p>;
  }

  const label = STATUS_LABEL[status.status] ?? status.status;
  const isTerminal = ["completed", "failed", "rejected", "paused"].includes(status.status);
  const showPlanList = status.plan_days.length > 0;
  const isInterrupted = Boolean(status.interrupted);
  const canResume = ["generating", "paused", "failed"].includes(status.status) && !status.batch_active;
  const canCancel = status.status === "generating" && !isInterrupted;
  const canRetryDay = status.status === "failed";

  return (
    <section className="max-w-7xl mx-auto flex flex-col gap-4">
      <div className="flex justify-between items-start gap-4">
        <div>
          <h2 className="text-xl font-semibold text-slate-100">{status.course_name}</h2>
          <p className="text-sm text-slate-400 mt-0.5">{label}</p>
        </div>
        {isTerminal && (
          <button onClick={onReset} className="text-sm text-violet-400 underline shrink-0">
            Start new course
          </button>
        )}
      </div>

      {isInterrupted && (
        <div
          role="alert"
          className="bg-amber-900/30 border border-amber-500/40 rounded-xl p-4 flex flex-col gap-3"
        >
          <p className="text-sm text-amber-200">
            Course generation was interrupted (likely by a server restart). Continue from the next
            day or retry the failed day.
          </p>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={submitting}
              onClick={handleResumeBatch}
              className="text-sm bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white rounded-lg px-4 py-2"
            >
              Continue generation
            </button>
            {canRetryDay && (
              <button
                type="button"
                disabled={submitting}
                onClick={handleRetryDay}
                className="text-sm bg-slate-700 hover:bg-slate-600 disabled:opacity-50 text-slate-200 rounded-lg px-4 py-2"
              >
                Retry failed day
              </button>
            )}
          </div>
        </div>
      )}

      {status.status === "paused" && (
        <div className="bg-slate-800 border border-slate-600 rounded-xl p-4 flex flex-col gap-3">
          <p className="text-sm text-slate-300">Generation paused. Resume when ready.</p>
          <button
            type="button"
            disabled={submitting}
            onClick={handleResumeBatch}
            className="self-start text-sm bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white rounded-lg px-4 py-2"
          >
            Resume generation
          </button>
        </div>
      )}

      {actionError && (
        <p role="alert" className="text-sm text-red-400">
          {actionError}
        </p>
      )}

      <CourseProgressBar status={status} />

      <dl className="bg-slate-800 rounded-xl p-4 grid grid-cols-2 gap-y-2 text-sm">
        <dt className="text-slate-400">Days completed</dt>
        <dd>
          {status.days_completed.length} / {status.total_days}
        </dd>
        <dt className="text-slate-400">Hours per day</dt>
        <dd>{status.hours_per_day}h</dd>
        <dt className="text-slate-400">Output folder</dt>
        <dd className="font-mono text-xs break-all col-span-1">{status.output_root}</dd>
      </dl>

      {showPlanList && (
        <DayPlanChecklist
          days={status.plan_days}
          daysCompleted={status.days_completed}
          currentDay={status.current_generating_day}
          checkpointEvery={status.checkpoint_every}
        />
      )}

      {status.status === "generating" && status.current_session_id && status.current_generating_day && (
        <DayGenerationProgress
          sessionId={status.current_session_id}
          dayLabel={`Day ${String(status.current_generating_day).padStart(2, "0")}${
            status.current_day_title ? `: ${status.current_day_title}` : ""
          }`}
        />
      )}

      {(canCancel || canResume) && !isInterrupted && status.status !== "paused" && (
        <div className="flex flex-wrap gap-2">
          {canCancel && (
            <button
              type="button"
              disabled={submitting}
              onClick={handleCancel}
              className="text-sm bg-slate-700 hover:bg-slate-600 disabled:opacity-50 text-slate-200 rounded-lg px-4 py-2"
            >
              Pause generation
            </button>
          )}
          {canResume && status.status === "failed" && (
            <button
              type="button"
              disabled={submitting}
              onClick={handleRetryDay}
              className="text-sm bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white rounded-lg px-4 py-2"
            >
              Retry failed day
            </button>
          )}
        </div>
      )}

      {status.days_completed.length > 0 && Object.keys(status.day_sessions).length > 0 && (
        <CourseDayNotesPreview
          daysCompleted={status.days_completed}
          daySessions={status.day_sessions}
          planDays={status.plan_days}
        />
      )}

      {status.status === "awaiting_plan_approval" && (
        <div className="bg-slate-700 rounded-xl p-4 flex flex-col gap-3">
          <p className="text-yellow-300 text-sm font-medium">
            Review the full {status.total_days}-day plan above, then approve to start batch
            generation.
          </p>
          {status.plan_summary && (
            <p className="text-sm text-slate-300 whitespace-pre-wrap">{status.plan_summary}</p>
          )}
          <textarea
            value={planFeedback}
            onChange={(e) => setPlanFeedback(e.target.value)}
            placeholder="Optional feedback if rejecting…"
            rows={2}
            className="bg-slate-800 border border-slate-600 text-slate-100 rounded-lg px-3 py-2 text-sm resize-none"
          />
          <div className="flex gap-2">
            <button
              onClick={() => handlePlanRespond(true)}
              disabled={submitting}
              className="flex-1 bg-emerald-600 rounded-lg py-2 text-sm"
            >
              Approve plan — start generation
            </button>
            <button
              onClick={() => handlePlanRespond(false)}
              disabled={submitting}
              className="flex-1 bg-red-700 rounded-lg py-2 text-sm"
            >
              Reject
            </button>
          </div>
        </div>
      )}

      {status.status === "awaiting_checkpoint" && status.checkpoint_message && (
        <div className="bg-slate-700 rounded-xl p-4 flex flex-col gap-3">
          <p className="text-yellow-300 text-sm whitespace-pre-wrap">{status.checkpoint_message}</p>
          <textarea
            value={checkpointFeedback}
            onChange={(e) => setCheckpointFeedback(e.target.value)}
            placeholder="Optional feedback if stopping…"
            rows={2}
            className="bg-slate-800 border border-slate-600 text-slate-100 rounded-lg px-3 py-2 text-sm resize-none"
          />
          <div className="flex gap-2">
            <button
              onClick={() => handleCheckpointRespond(true)}
              disabled={submitting}
              className="flex-1 bg-emerald-600 rounded-lg py-2 text-sm"
            >
              Approve batch — continue
            </button>
            <button
              onClick={() => handleCheckpointRespond(false)}
              disabled={submitting}
              className="flex-1 bg-red-700 rounded-lg py-2 text-sm"
            >
              Stop course
            </button>
          </div>
        </div>
      )}

      {status.errors.length > 0 && (
        <div role="alert" className="text-red-300 text-sm">
          <h3 className="font-medium text-red-400 mb-1">Errors</h3>
          <ul className="list-disc list-inside">
            {status.errors.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

function readError(err: unknown): string {
  if (axios.isAxiosError(err) && err.response?.data) {
    const detail = (err.response.data as { detail?: string }).detail;
    if (typeof detail === "string") return detail;
  }
  return "Action failed. Try again.";
}
