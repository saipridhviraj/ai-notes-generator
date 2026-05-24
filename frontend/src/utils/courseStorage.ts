const LAST_COURSE_KEY = "ai-notes-last-course-id";
const LAST_FLOW_MODE_KEY = "ai-notes-last-flow-mode";

export type StoredFlowMode = "single" | "course";

export function saveLastCourseId(courseId: string): void {
  try {
    localStorage.setItem(LAST_COURSE_KEY, courseId);
  } catch {
    /* ignore quota / private mode */
  }
}

export function loadLastCourseId(): string | null {
  try {
    return localStorage.getItem(LAST_COURSE_KEY);
  } catch {
    return null;
  }
}

export function clearLastCourseId(): void {
  try {
    localStorage.removeItem(LAST_COURSE_KEY);
  } catch {
    /* ignore */
  }
}

export function saveLastFlowMode(mode: StoredFlowMode): void {
  try {
    localStorage.setItem(LAST_FLOW_MODE_KEY, mode);
  } catch {
    /* ignore */
  }
}

export function loadLastFlowMode(): StoredFlowMode | null {
  try {
    const value = localStorage.getItem(LAST_FLOW_MODE_KEY);
    return value === "single" || value === "course" ? value : null;
  } catch {
    return null;
  }
}
