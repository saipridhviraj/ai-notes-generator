const LAST_SESSION_KEY = "ai-notes-last-session-id";

export function saveLastSessionId(sessionId: string): void {
  try {
    localStorage.setItem(LAST_SESSION_KEY, sessionId);
  } catch {
    /* ignore quota / private mode */
  }
}

export function loadLastSessionId(): string | null {
  try {
    return localStorage.getItem(LAST_SESSION_KEY);
  } catch {
    return null;
  }
}

export function clearLastSessionId(): void {
  try {
    localStorage.removeItem(LAST_SESSION_KEY);
  } catch {
    /* ignore */
  }
}
