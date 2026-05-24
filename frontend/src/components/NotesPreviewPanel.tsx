import { useState } from "react";
import type { ResultResponse } from "../api/client";
import { downloadTextFile } from "../utils/download";
import { MarkdownDocument } from "./MarkdownDocument";

interface Props {
  result: ResultResponse;
}

function NoteColumn({
  title,
  icon,
  filename,
  markdown,
  accent,
}: {
  title: string;
  icon: string;
  filename: string | null;
  markdown: string;
  accent: string;
}) {
  return (
    <div className={`flex flex-col min-h-[20rem] max-h-[70vh] rounded-2xl border ${accent} overflow-hidden`}>
      <header className="shrink-0 px-4 py-3 border-b border-white/[0.06] bg-chat-sidebar/50">
        <h3 className="text-sm font-medium text-white/90 flex items-center gap-2">
          <span aria-hidden>{icon}</span>
          {title}
          {filename && (
            <span className="text-[10px] font-mono text-white/30 ml-auto truncate max-w-[40%]">
              {filename}
            </span>
          )}
        </h3>
      </header>
      <div className="flex-1 overflow-y-auto chat-scroll px-4 py-4 bg-chat-surface/50">
        {markdown ? (
          <MarkdownDocument content={markdown} />
        ) : (
          <p className="text-white/40 italic text-sm">No content available.</p>
        )}
      </div>
    </div>
  );
}

export function NotesPreviewPanel({ result }: Props) {
  const [mobileTab, setMobileTab] = useState<"student" | "tutor">("student");

  const student = result.student_markdown ?? "";
  const tutor = result.tutor_markdown ?? "";

  if (!student && !tutor) return null;

  return (
    <section
      aria-labelledby="notes-preview-heading"
      className="surface-card p-4 flex flex-col gap-4"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id="notes-preview-heading" className="text-base font-medium text-white/90">
            Generated notes
          </h2>
          {result.topic && <p className="text-sm text-white/45 mt-0.5">{result.topic}</p>}
          {result.summary && <p className="text-xs text-white/30 mt-1">{result.summary}</p>}
        </div>
        {result.evaluation_score && (
          <span className="text-xs surface-elevated px-2.5 py-1 text-white/50">
            Quality: student {result.evaluation_score.student} · tutor{" "}
            {result.evaluation_score.tutor}
          </span>
        )}
        {(student || tutor) && (
          <div className="flex flex-wrap gap-2">
            {student && (
              <button
                type="button"
                onClick={() =>
                  downloadTextFile(result.student_file ?? "student_notes.md", student)
                }
                className="text-xs btn-ghost border border-white/10 py-1.5"
              >
                ↓ Student
              </button>
            )}
            {tutor && (
              <button
                type="button"
                onClick={() =>
                  downloadTextFile(result.tutor_file ?? "tutor_notes.md", tutor)
                }
                className="text-xs btn-ghost border border-white/10 py-1.5"
              >
                ↓ Tutor
              </button>
            )}
          </div>
        )}
      </div>

      {/* Mobile: one column with tabs */}
      <div className="lg:hidden flex flex-col gap-3">
        <div className="flex gap-1">
          {(["student", "tutor"] as const).map((id) => (
            <button
              key={id}
              type="button"
              onClick={() => setMobileTab(id)}
              className={`flex-1 px-3 py-2 text-xs font-medium rounded-lg ${
                mobileTab === id
                  ? "bg-white/10 text-white"
                  : "bg-white/[0.03] text-white/45"
              }`}
            >
              {id === "student" ? "📘 Student" : "📗 Tutor"}
            </button>
          ))}
        </div>
        {mobileTab === "student" ? (
          <NoteColumn
            title="Student notes"
            icon="📘"
            filename={result.student_file}
            markdown={student}
            accent="border-blue-500/20"
          />
        ) : (
          <NoteColumn
            title="Tutor guide"
            icon="📗"
            filename={result.tutor_file}
            markdown={tutor}
            accent="border-emerald-500/20"
          />
        )}
      </div>

      {/* Desktop: side by side */}
      <div className="hidden lg:grid lg:grid-cols-2 gap-4">
        <NoteColumn
          title="Student notes"
          icon="📘"
          filename={result.student_file}
          markdown={student}
          accent="border-blue-900/50"
        />
        <NoteColumn
          title="Tutor guide"
          icon="📗"
          filename={result.tutor_file}
          markdown={tutor}
          accent="border-emerald-900/50"
        />
      </div>
    </section>
  );
}
