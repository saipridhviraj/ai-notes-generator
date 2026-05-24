import { useState } from "react";
import axios from "axios";
import { useQueryClient } from "@tanstack/react-query";
import { useQuery } from "@tanstack/react-query";
import { deleteAllSessions, deleteSession, getResult, listSessions, type SessionSummary } from "../api/client";
import { downloadTextFile } from "../utils/download";

interface Props {
  activeSessionId: string | null;
  onSelect: (sessionId: string) => void;
  onNewSession: () => void;
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
  running: "bg-amber-400",
  awaiting_tutor: "bg-yellow-400",
  max_retries_reached: "bg-orange-400",
  failed: "bg-red-400",
  cancelled: "bg-white/30",
};

async function downloadSessionNotes(sessionId: string, which: "student" | "tutor" | "both") {
  const result = await getResult(sessionId);
  if (which === "student" || which === "both") {
    const name = result.student_file ?? "student_notes.md";
    const body = result.student_markdown ?? "";
    if (body) downloadTextFile(name, body);
  }
  if (which === "tutor" || which === "both") {
    const name = result.tutor_file ?? "tutor_notes.md";
    const body = result.tutor_markdown ?? "";
    if (body) downloadTextFile(name, body);
  }
}

export function SessionHistory({ activeSessionId, onSelect, onNewSession }: Props) {
  const queryClient = useQueryClient();
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [clearingAll, setClearingAll] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["sessions"],
    queryFn: () => listSessions(40),
    staleTime: 10_000,
  });

  const sessions: SessionSummary[] = data?.sessions ?? [];

  const handleDownload = async (sessionId: string, which: "student" | "tutor" | "both") => {
    setDownloadingId(sessionId);
    try {
      await downloadSessionNotes(sessionId, which);
    } finally {
      setDownloadingId(null);
    }
  };

  const handleDelete = async (sessionId: string, topic: string) => {
    const ok = window.confirm(`Delete "${topic}"? This cannot be undone.`);
    if (!ok) return;

    setDeletingId(sessionId);
    try {
      await deleteSession(sessionId);
      if (sessionId === activeSessionId) {
        onNewSession();
      }
      if (expandedId === sessionId) {
        setExpandedId(null);
      }
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
    } catch (err: unknown) {
      let message = "Could not delete conversation.";
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
    if (sessions.length === 0) return;
    const ok = window.confirm(
      `Delete all ${sessions.length} conversation(s)? This cannot be undone. Generated note files on disk are kept.`
    );
    if (!ok) return;

    setClearingAll(true);
    try {
      await deleteAllSessions();
      onNewSession();
      setExpandedId(null);
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
    } catch (err: unknown) {
      let message = "Could not clear history.";
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
          queryClient.invalidateQueries({ queryKey: ["sessions"] });
          onNewSession();
        }}
        className="sidebar-item border border-white/10 hover:border-white/20 mx-1"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" className="shrink-0 opacity-70" aria-hidden>
          <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z" />
        </svg>
        New chat
      </button>

      <div className="flex items-center justify-between px-3 pt-2">
        <span className="text-[11px] font-medium uppercase tracking-wider text-white/30">Recent</span>
        <div className="flex items-center gap-2">
          {sessions.length > 0 && (
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
          Could not load sessions.
        </p>
      )}

      <ul className="flex-1 overflow-y-auto chat-scroll px-1 space-y-0.5">
        {sessions.length === 0 && !isLoading && (
          <li className="text-xs text-white/30 px-3 py-2">No conversations yet.</li>
        )}
        {sessions.map((s) => {
          const active = s.session_id === activeSessionId;
          const canDownload =
            s.has_notes && ["completed", "max_retries_reached"].includes(s.status);
          const busy = downloadingId === s.session_id;
          const deleting = deletingId === s.session_id;
          const expanded = expandedId === s.session_id;

          return (
            <li key={s.session_id} className="group relative">
              <div className="flex items-center min-w-0">
                <button
                  type="button"
                  onClick={() => onSelect(s.session_id)}
                  className={`sidebar-item group flex-1 min-w-0 ${active ? "sidebar-item-active" : ""}`}
                >
                  <span
                    className={`w-2 h-2 rounded-full shrink-0 ${STATUS_DOT[s.status] ?? "bg-white/20"}`}
                    aria-hidden
                  />
                  <span className="truncate flex-1 text-left">{s.topic}</span>
                </button>
                <button
                  type="button"
                  aria-label={`Delete ${s.topic}`}
                  disabled={deleting}
                  onClick={() => handleDelete(s.session_id, s.topic)}
                  className="shrink-0 p-2 mr-1 rounded-lg text-white/0 group-hover:text-white/40
                             hover:!text-red-400 hover:bg-white/[0.06] transition-colors
                             disabled:opacity-40"
                >
                  {deleting ? "…" : "×"}
                </button>
              </div>
              {(canDownload || s.chat_count > 0) && (
                <div className="ml-8 px-1 pb-1 flex flex-wrap gap-1 items-center">
                  <span className="text-[10px] text-white/25">{formatWhen(s.start_time)}</span>
                  {s.chat_count > 0 && (
                    <span className="text-[10px] text-white/40">{s.chat_count} edits</span>
                  )}
                  {canDownload && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setExpandedId(expanded ? null : s.session_id);
                      }}
                      className="text-[10px] text-white/40 hover:text-white/70 ml-auto"
                    >
                      {expanded ? "Hide" : "Download"}
                    </button>
                  )}
                </div>
              )}
              {expanded && canDownload && (
                <div className="ml-8 px-1 pb-2 flex flex-wrap gap-1">
                  {(["student", "tutor", "both"] as const).map((which) => (
                    <button
                      key={which}
                      type="button"
                      disabled={busy}
                      onClick={() => handleDownload(s.session_id, which)}
                      className="text-[10px] px-2 py-0.5 rounded-md bg-white/[0.06] hover:bg-white/10
                                 text-white/60 disabled:opacity-40 capitalize"
                    >
                      ↓ {which}
                    </button>
                  ))}
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
