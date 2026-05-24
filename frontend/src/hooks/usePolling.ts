import { useEffect, useRef } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { getStatus, type StatusResponse, API_BASE, getApiKey } from "../api/client";
import { invalidateSessionHistory } from "../utils/historyInvalidation";

const SSE_TERMINAL = new Set([
  "completed",
  "failed",
  "max_retries_reached",
  "rejected",
  "cancelled",
]);

function isSessionNotFound(status: number): boolean {
  return status === 404;
}

/**
 * Session status via SSE (/status-stream) with one initial GET /status fetch.
 * Replaces polling — server pushes only when pipeline state changes.
 *
 * Pass `streamGeneration` (increment after resume/restart) to reconnect SSE after
 * a terminal status — otherwise the stream stays closed on completed sessions.
 */
export function usePolling(sessionId: string | null, streamGeneration = 0) {
  const queryClient = useQueryClient();
  const terminalRef = useRef(false);
  const goneRef = useRef(false);

  const query = useQuery<StatusResponse, Error>({
    queryKey: ["status", sessionId],
    queryFn: () => getStatus(sessionId!),
    enabled: !!sessionId,
    staleTime: Infinity,
    refetchOnWindowFocus: false,
    refetchInterval: false,
  });

  useEffect(() => {
    terminalRef.current = false;
    goneRef.current = false;
    if (!sessionId) return;

    void queryClient.invalidateQueries({ queryKey: ["status", sessionId] });

    let cancelled = false;
    const controller = new AbortController();
    let retryTimer: ReturnType<typeof setTimeout> | null = null;

    const applyStatus = (data: StatusResponse) => {
      queryClient.setQueryData(["status", sessionId], data);
      if (SSE_TERMINAL.has(data.status)) {
        terminalRef.current = true;
        invalidateSessionHistory(queryClient);
      }
    };

    const connect = async () => {
      if (cancelled || terminalRef.current) return;

      try {
        const apiKey = getApiKey();
        const res = await fetch(`${API_BASE}/status-stream/${sessionId}`, {
          headers: {
            Accept: "text/event-stream",
            ...(apiKey ? { "X-API-Key": apiKey } : {}),
          },
          signal: controller.signal,
        });

        if (!res.ok || !res.body) {
          if (isSessionNotFound(res.status)) {
            goneRef.current = true;
            terminalRef.current = true;
            return;
          }
          throw new Error(`Status stream failed (${res.status})`);
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (!cancelled && !terminalRef.current) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const parts = buffer.split("\n\n");
          buffer = parts.pop() ?? "";

          for (const part of parts) {
            const line = part.split("\n").find((l) => l.startsWith("data: "));
            if (!line) continue;

            const event = JSON.parse(line.slice(6)) as {
              type: string;
              data?: StatusResponse;
            };

            if (event.type === "status" && event.data) {
              applyStatus(event.data);
            }
          }
        }
      } catch (err) {
        if (cancelled || controller.signal.aborted || terminalRef.current || goneRef.current) return;
        retryTimer = setTimeout(connect, 3000);
      }
    };

    connect();

    return () => {
      cancelled = true;
      controller.abort();
      if (retryTimer) clearTimeout(retryTimer);
    };
  }, [sessionId, queryClient, streamGeneration]);

  return query;
}

export type { StatusResponse };
