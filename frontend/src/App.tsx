import { useState, useEffect } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StatusPanel } from "./components/StatusPanel";
import { CourseStatusPanel } from "./components/CourseStatusPanel";
import { FlowTabs, type FlowMode } from "./components/FlowTabs";
import { SessionHistory } from "./components/SessionHistory";
import { CourseHistory } from "./components/CourseHistory";
import { WelcomeScreen } from "./components/WelcomeScreen";
import { getStatus, getCourseStatus } from "./api/client";
import {
  clearLastSessionId,
  loadLastSessionId,
  saveLastSessionId,
} from "./utils/sessionStorage";
import {
  clearLastCourseId,
  loadLastCourseId,
  loadLastFlowMode,
  saveLastCourseId,
  saveLastFlowMode,
} from "./utils/courseStorage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5_000,
      gcTime: 60_000,
    },
  },
});

function Dashboard() {
  const [mode, setMode] = useState<FlowMode>(() => loadLastFlowMode() ?? "single");
  const [lessonSessionId, setLessonSessionId] = useState<string | null>(null);
  const [courseId, setCourseId] = useState<string | null>(null);
  const [restoring, setRestoring] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function restore() {
      const savedMode = loadLastFlowMode() ?? "single";
      const savedSession = loadLastSessionId();
      const savedCourse = loadLastCourseId();

      if (savedMode === "course" && savedCourse) {
        try {
          await getCourseStatus(savedCourse);
          if (!cancelled) {
            setMode("course");
            setCourseId(savedCourse);
          }
        } catch {
          clearLastCourseId();
        }
      } else if (savedSession) {
        try {
          await getStatus(savedSession);
          if (!cancelled) {
            setMode("single");
            setLessonSessionId(savedSession);
          }
        } catch {
          clearLastSessionId();
        }
      }

      if (!cancelled) setRestoring(false);
    }

    restore();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleModeChange = (next: FlowMode) => {
    setMode(next);
    saveLastFlowMode(next);
  };

  const handleSessionStarted = (sessionId: string) => {
    saveLastSessionId(sessionId);
    saveLastFlowMode("single");
    setLessonSessionId(sessionId);
  };

  const resetLesson = () => {
    clearLastSessionId();
    setLessonSessionId(null);
  };

  const handleCourseStarted = (id: string) => {
    saveLastCourseId(id);
    saveLastFlowMode("course");
    setCourseId(id);
  };

  const resetCourse = () => {
    clearLastCourseId();
    setCourseId(null);
  };

  const activeTitle =
    mode === "single"
      ? lessonSessionId
        ? "Lesson generation"
        : "New lesson"
      : courseId
        ? "Course generation"
        : "New course";

  return (
    <div className="h-screen flex bg-chat-main text-white overflow-hidden">
      {/* Sidebar overlay (mobile) */}
      {sidebarOpen && (
        <button
          type="button"
          aria-label="Close sidebar"
          className="lg:hidden fixed inset-0 bg-black/50 z-30"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed lg:static inset-y-0 left-0 z-40 w-[260px] shrink-0
          bg-chat-sidebar border-r border-white/[0.08] flex flex-col
          transition-transform duration-200
          ${sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}
        `}
      >
        <div className="p-3 flex flex-col gap-1 border-b border-white/[0.06]">
          <div className="flex items-center gap-2 px-1 py-1">
            <span className="text-lg" aria-hidden>
              📝
            </span>
            <span className="font-semibold text-sm truncate">AI Notes</span>
          </div>
          <FlowTabs
            mode={mode}
            onChange={handleModeChange}
            lessonActive={!!lessonSessionId}
            courseActive={!!courseId}
          />
        </div>

        <div className="flex-1 min-h-0 overflow-hidden flex flex-col p-2">
          {mode === "single" ? (
            <SessionHistory
              activeSessionId={lessonSessionId}
              onSelect={handleSessionStarted}
              onNewSession={resetLesson}
            />
          ) : (
            <CourseHistory
              activeCourseId={courseId}
              onSelect={handleCourseStarted}
              onNewCourse={resetCourse}
            />
          )}
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0 min-h-0">
        <header className="shrink-0 flex items-center gap-3 px-4 py-3 border-b border-white/[0.06]">
          <button
            type="button"
            onClick={() => setSidebarOpen((v) => !v)}
            className="lg:hidden btn-ghost p-2"
            aria-label="Toggle sidebar"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
              <path d="M3 6h18v2H3V6zm0 5h18v2H3v-2zm0 5h18v2H3v-2z" />
            </svg>
          </button>
          <h1 className="text-sm font-medium text-white/90 truncate">{activeTitle}</h1>
        </header>

        <main id="main-content" className="flex-1 flex flex-col min-h-0 overflow-hidden">
          {restoring ? (
            <div className="flex-1 flex items-center justify-center">
              <p className="text-sm text-white/40" role="status">
                Restoring last session…
              </p>
            </div>
          ) : mode === "single" ? (
            lessonSessionId ? (
              <StatusPanel sessionId={lessonSessionId} onReset={resetLesson} />
            ) : (
              <WelcomeScreen onStarted={handleSessionStarted} />
            )
          ) : courseId ? (
            <div className="flex-1 min-h-0 overflow-y-auto chat-scroll px-4 py-4">
              <CourseStatusPanel courseId={courseId} onReset={resetCourse} />
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center px-4 pb-8">
              <div className="w-full max-w-lg text-center">
                <h1 className="text-2xl font-semibold text-white">Full course mode</h1>
                <p className="text-white/50 text-sm mt-2">
                  Click <strong className="text-white/70 font-medium">+ New course</strong> in the
                  sidebar to plan a syllabus, or reopen a previous course.
                </p>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Dashboard />
    </QueryClientProvider>
  );
}
