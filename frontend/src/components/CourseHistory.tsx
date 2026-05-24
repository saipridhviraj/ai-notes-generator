import { useState, useEffect } from "react";
import axios from "axios";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { deleteAllCourses, deleteCourse, getCourseStatus, listCourses, startCoursePlan, type CourseSummary } from "../api/client";
import {
  downloadAllCourseDays,
  downloadCourseDayNotes,
  downloadLatestCourseDay,
} from "../utils/courseDownloads";

interface Props {
  activeCourseId: string | null;
  onSelect: (courseId: string) => void;
  onNewCourse: () => void;
}

function formatWhen(ts: number): string {
  const d = new Date(ts * 1000);
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const STATUS_DOT: Record<string, string> = {
  completed: "bg-chat-accent",
  generating: "bg-amber-400",
  awaiting_plan_approval: "bg-yellow-400",
  awaiting_checkpoint: "bg-yellow-400",
  planning: "bg-white/30",
  failed: "bg-red-400",
  rejected: "bg-orange-400",
  paused: "bg-white/30",
};

export function CourseHistory({ activeCourseId, onSelect, onNewCourse }: Props) {
  const queryClient = useQueryClient();
  const [courseName, setCourseName] = useState("Full Gen AI Syllabus");
  const [syllabus, setSyllabus] = useState("");
  const [totalDays, setTotalDays] = useState(30);
  const [hoursPerDay, setHoursPerDay] = useState(1.5);
  const [checkpointEvery, setCheckpointEvery] = useState(4);
  const [languages, setLanguages] = useState("python");
  const [showForm, setShowForm] = useState(false);
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [clearingAll, setClearingAll] = useState(false);
  const [expandedDownloadId, setExpandedDownloadId] = useState<string | null>(null);
  const [selectedDay, setSelectedDay] = useState<number>(1);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["courses"],
    queryFn: () => listCourses(40),
    staleTime: 10_000,
  });

  const { data: expandedCourse } = useQuery({
    queryKey: ["course", expandedDownloadId],
    queryFn: () => getCourseStatus(expandedDownloadId!),
    enabled: Boolean(expandedDownloadId),
  });

  const courses: CourseSummary[] = data?.courses ?? [];
  const expandedDays = expandedCourse
    ? [...expandedCourse.days_completed].sort((a, b) => a - b)
    : [];

  useEffect(() => {
    if (expandedDays.length > 0) {
      setSelectedDay(expandedDays[expandedDays.length - 1]);
    }
  }, [expandedDownloadId, expandedDays.length]);

  const handleStartCourse = async (e: React.FormEvent) => {
    e.preventDefault();
    if (syllabus.trim().length < 50) {
      setStartError("Syllabus must be at least 50 characters.");
      return;
    }
    setStartError(null);
    setStarting(true);
    try {
      const res = await startCoursePlan({
        course_name: courseName.trim(),
        syllabus: syllabus.trim(),
        total_days: totalDays,
        hours_per_day: hoursPerDay,
        checkpoint_every: checkpointEvery,
        programming_languages: languages
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      });
      setShowForm(false);
      queryClient.invalidateQueries({ queryKey: ["courses"] });
      onSelect(res.course_id);
    } catch (err: unknown) {
      let message = "Could not start course planning.";
      if (axios.isAxiosError(err) && err.response?.data) {
        const detail = (err.response.data as { detail?: string }).detail;
        if (typeof detail === "string") message = detail;
      }
      setStartError(message);
    } finally {
      setStarting(false);
    }
  };

  const runDownload = async (
    courseId: string,
    fn: () => Promise<void>
  ) => {
    setDownloadingId(courseId);
    try {
      await fn();
    } catch {
      /* user can retry from day preview */
    } finally {
      setDownloadingId(null);
    }
  };

  const toggleDownloads = (courseId: string, daysCount: number) => {
    if (expandedDownloadId === courseId) {
      setExpandedDownloadId(null);
      return;
    }
    setExpandedDownloadId(courseId);
    setSelectedDay(Math.max(1, daysCount));
  };

  const handleDelete = async (courseId: string, name: string) => {
    const ok = window.confirm(`Delete course "${name}"? This cannot be undone.`);
    if (!ok) return;

    setDeletingId(courseId);
    try {
      await deleteCourse(courseId);
      if (courseId === activeCourseId) {
        onNewCourse();
      }
      if (expandedDownloadId === courseId) {
        setExpandedDownloadId(null);
      }
      queryClient.invalidateQueries({ queryKey: ["courses"] });
    } catch (err: unknown) {
      let message = "Could not delete course.";
      if (axios.isAxiosError(err) && err.response?.data) {
        const detail = (err.response.data as { detail?: string }).detail;
        if (typeof detail === "string") message = detail;
      }
      window.alert(message);
    } finally {
      setDeletingId(null);
    }
  };

  const handleDeleteAll = async () => {
    if (courses.length === 0) return;
    const ok = window.confirm(
      `Delete all ${courses.length} course(s)? This cannot be undone. Generated note files on disk are kept.`
    );
    if (!ok) return;

    setClearingAll(true);
    try {
      await deleteAllCourses();
      onNewCourse();
      setExpandedDownloadId(null);
      queryClient.invalidateQueries({ queryKey: ["courses"] });
    } catch (err: unknown) {
      let message = "Could not clear course history.";
      if (axios.isAxiosError(err) && err.response?.data) {
        const detail = (err.response.data as { detail?: string }).detail;
        if (typeof detail === "string") message = detail;
      }
      window.alert(message);
    } finally {
      setClearingAll(false);
    }
  };

  return (
    <div className="flex flex-col h-full min-h-0 gap-2">
      <button
        type="button"
        onClick={() => {
          onNewCourse();
          setShowForm(true);
        }}
        className="sidebar-item border border-white/10 hover:border-white/20 mx-1"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" className="shrink-0 opacity-70" aria-hidden>
          <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z" />
        </svg>
        New course
      </button>

      {showForm && (
        <section className="mx-1 surface-elevated p-3 flex flex-col gap-2 max-h-[50vh] overflow-y-auto chat-scroll">
          <form onSubmit={handleStartCourse} className="flex flex-col gap-2">
            <input
              type="text"
              value={courseName}
              onChange={(e) => setCourseName(e.target.value)}
              placeholder="Course name"
              maxLength={200}
              disabled={starting}
              className="bg-chat-sidebar border border-white/10 text-white rounded-lg px-3 py-2 text-sm
                         focus:outline-none focus:ring-1 focus:ring-white/20 placeholder:text-white/30"
              required
            />
            <textarea
              value={syllabus}
              onChange={(e) => setSyllabus(e.target.value)}
              placeholder="Full syllabus (min 50 chars)…"
              rows={4}
              minLength={50}
              disabled={starting}
              className="bg-chat-sidebar border border-white/10 text-white rounded-lg px-3 py-2 text-sm
                         focus:outline-none focus:ring-1 focus:ring-white/20 placeholder:text-white/30 resize-y"
              required
            />
            <div className="grid grid-cols-2 gap-2">
              <label className="flex flex-col gap-0.5 text-[10px] text-white/40">
                Days
                <input
                  type="number"
                  min={1}
                  max={60}
                  value={totalDays}
                  onChange={(e) => setTotalDays(Number(e.target.value))}
                  disabled={starting}
                  className="bg-chat-sidebar border border-white/10 text-white rounded-lg px-2 py-1.5 text-xs"
                />
              </label>
              <label className="flex flex-col gap-0.5 text-[10px] text-white/40">
                Hours/day
                <input
                  type="number"
                  min={0.5}
                  max={8}
                  step={0.5}
                  value={hoursPerDay}
                  onChange={(e) => setHoursPerDay(Number(e.target.value))}
                  disabled={starting}
                  className="bg-chat-sidebar border border-white/10 text-white rounded-lg px-2 py-1.5 text-xs"
                />
              </label>
              <label className="flex flex-col gap-0.5 text-[10px] text-white/40">
                Checkpoint
                <input
                  type="number"
                  min={1}
                  max={10}
                  value={checkpointEvery}
                  onChange={(e) => setCheckpointEvery(Number(e.target.value))}
                  disabled={starting}
                  className="bg-chat-sidebar border border-white/10 text-white rounded-lg px-2 py-1.5 text-xs"
                />
              </label>
              <label className="flex flex-col gap-0.5 text-[10px] text-white/40">
                Languages
                <input
                  type="text"
                  value={languages}
                  onChange={(e) => setLanguages(e.target.value)}
                  disabled={starting}
                  placeholder="python"
                  className="bg-chat-sidebar border border-white/10 text-white rounded-lg px-2 py-1.5 text-xs"
                />
              </label>
            </div>
            {startError && (
              <p className="text-xs text-red-400" role="alert">
                {startError}
              </p>
            )}
            <div className="flex gap-2">
              <button type="submit" disabled={starting} className="flex-1 text-xs btn-primary py-2">
                {starting ? "Planning…" : "Create plan"}
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="text-xs btn-ghost border border-white/10"
              >
                Cancel
              </button>
            </div>
          </form>
        </section>
      )}

      <div className="flex items-center justify-between px-3 pt-2">
        <span className="text-[11px] font-medium uppercase tracking-wider text-white/30">Recent</span>
        <div className="flex items-center gap-2">
          {courses.length > 0 && (
            <button
              type="button"
              onClick={handleDeleteAll}
              disabled={clearingAll}
              className="text-[11px] text-red-400/70 hover:text-red-400 disabled:opacity-40"
            >
              {clearingAll ? "Clearing…" : "Clear all"}
            </button>
          )}
          <button type="button" onClick={() => refetch()} className="text-[11px] text-white/40 hover:text-white/70">
            Refresh
          </button>
        </div>
      </div>

      {isLoading && <p className="text-xs text-white/30 px-3">Loading…</p>}
      {error && (
        <p className="text-xs text-red-400 px-3" role="alert">
          Could not load courses.
        </p>
      )}

      <ul className="flex-1 overflow-y-auto chat-scroll px-1 space-y-0.5">
        {courses.length === 0 && !isLoading && (
          <li className="text-xs text-white/30 px-3 py-2">No courses yet.</li>
        )}
        {courses.map((c) => {
          const active = c.course_id === activeCourseId;
          const canDownload = c.has_notes;
          const busy = downloadingId === c.course_id;
          const downloadsOpen = expandedDownloadId === c.course_id;
          const deleting = deletingId === c.course_id;

          return (
            <li key={c.course_id} className="group">
              <div className="flex items-center min-w-0">
                <button
                  type="button"
                  onClick={() => onSelect(c.course_id)}
                  className={`sidebar-item group flex-1 min-w-0 ${active ? "sidebar-item-active" : ""}`}
                >
                  <span
                    className={`w-2 h-2 rounded-full shrink-0 ${STATUS_DOT[c.status] ?? "bg-white/20"}`}
                    aria-hidden
                  />
                  <span className="truncate flex-1 text-left">{c.course_name}</span>
                </button>
                <button
                  type="button"
                  aria-label={`Delete ${c.course_name}`}
                  disabled={deleting}
                  onClick={() => handleDelete(c.course_id, c.course_name)}
                  className="shrink-0 p-2 mr-1 rounded-lg text-white/0 group-hover:text-white/40
                             hover:!text-red-400 hover:bg-white/[0.06] transition-colors
                             disabled:opacity-40"
                >
                  {deleting ? "…" : "×"}
                </button>
              </div>
              <div className="ml-8 px-1 pb-1 flex flex-wrap gap-1 items-center text-[10px] text-white/30">
                <span>{formatWhen(c.start_time)}</span>
                <span>
                  {c.days_completed_count}/{c.total_days} days
                </span>
                {c.chat_count > 0 && <span>{c.chat_count} edits</span>}
              </div>
              {canDownload && (
                <div className="px-2 pb-2 ml-6 flex flex-col gap-1">
                  <button
                    type="button"
                    onClick={() => toggleDownloads(c.course_id, c.days_completed_count)}
                    className="text-[10px] text-left text-white/40 hover:text-white/70"
                  >
                    {downloadsOpen ? "▾ Hide downloads" : "▸ Downloads"}
                  </button>
                  {!downloadsOpen && (
                    <div className="flex flex-wrap gap-1">
                      {(["student", "tutor", "both"] as const).map((which) => (
                        <button
                          key={which}
                          type="button"
                          disabled={busy}
                          onClick={() =>
                            runDownload(c.course_id, () => downloadLatestCourseDay(c.course_id, which))
                          }
                          className="text-[10px] px-2 py-0.5 rounded-md bg-white/[0.06] hover:bg-white/10
                                     text-white/60 disabled:opacity-40 capitalize"
                        >
                          ↓ {which}
                        </button>
                      ))}
                    </div>
                  )}
                  {downloadsOpen && (
                    <div className="flex flex-col gap-1">
                      {expandedDays.length > 0 && (
                        <select
                          value={selectedDay}
                          onChange={(e) => setSelectedDay(Number(e.target.value))}
                          className="text-[10px] bg-chat-sidebar border border-white/10 text-white rounded px-2 py-1"
                        >
                          {expandedDays.map((day) => (
                            <option key={day} value={day}>
                              Day {String(day).padStart(2, "0")}
                            </option>
                          ))}
                        </select>
                      )}
                      <div className="flex flex-wrap gap-1">
                        {(["student", "tutor", "both"] as const).map((which) => (
                          <button
                            key={`day-${which}`}
                            type="button"
                            disabled={busy || expandedDays.length === 0}
                            onClick={() =>
                              runDownload(c.course_id, () =>
                                downloadCourseDayNotes(c.course_id, selectedDay, which)
                              )
                            }
                            className="text-[10px] px-2 py-0.5 rounded-md bg-white/[0.06] hover:bg-white/10
                                       text-white/60 disabled:opacity-40"
                          >
                            Day ↓ {which}
                          </button>
                        ))}
                      </div>
                      <div className="flex flex-wrap gap-1">
                        {(["student", "tutor", "both"] as const).map((which) => (
                          <button
                            key={`all-${which}`}
                            type="button"
                            disabled={busy}
                            onClick={() =>
                              runDownload(c.course_id, () => downloadAllCourseDays(c.course_id, which))
                            }
                            className="text-[10px] px-2 py-0.5 rounded-md bg-white/[0.06] hover:bg-white/10
                                       text-white/60 disabled:opacity-40 capitalize"
                          >
                            All ↓ {which}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
