export type FlowMode = "single" | "course";

interface Props {
  mode: FlowMode;
  onChange: (mode: FlowMode) => void;
  lessonActive?: boolean;
  courseActive?: boolean;
}

export function FlowTabs({ mode, onChange, lessonActive, courseActive }: Props) {
  const tabClass = (active: boolean) =>
    `flex-1 text-xs px-2 py-2 rounded-lg transition-colors flex items-center justify-center gap-1.5 ${
      active
        ? "bg-white/10 text-white font-medium"
        : "text-white/50 hover:bg-white/[0.05] hover:text-white/80"
    }`;

  return (
    <nav aria-label="Generation mode" className="flex gap-1 mt-1">
      <button type="button" onClick={() => onChange("single")} className={tabClass(mode === "single")}>
        Lesson
        {lessonActive && (
          <span className="w-1.5 h-1.5 rounded-full bg-chat-accent animate-pulse" aria-label="Active" />
        )}
      </button>
      <button type="button" onClick={() => onChange("course")} className={tabClass(mode === "course")}>
        Course
        {courseActive && (
          <span className="w-1.5 h-1.5 rounded-full bg-chat-accent animate-pulse" aria-label="Active" />
        )}
      </button>
    </nav>
  );
}
