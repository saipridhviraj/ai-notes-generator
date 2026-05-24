import type { QueryClient } from "@tanstack/react-query";

const SESSION_TERMINAL = new Set([
  "completed",
  "failed",
  "max_retries_reached",
  "rejected",
  "cancelled",
]);

const COURSE_TERMINAL = new Set(["completed", "failed", "rejected", "paused"]);

export function invalidateSessionHistory(queryClient: QueryClient): void {
  queryClient.invalidateQueries({ queryKey: ["sessions"] });
}

export function invalidateCourseHistory(queryClient: QueryClient): void {
  queryClient.invalidateQueries({ queryKey: ["courses"] });
}

export function isSessionTerminal(status?: string): boolean {
  return Boolean(status && SESSION_TERMINAL.has(status));
}

export function isCourseTerminal(status?: string): boolean {
  return Boolean(status && COURSE_TERMINAL.has(status));
}
