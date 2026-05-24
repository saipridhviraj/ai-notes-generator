import { useEffect, useRef, useState } from "react";
import { personaForNode } from "../constants/nodePersonas";

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const API_KEY = import.meta.env.VITE_API_KEY ?? "";

export interface TokenStreamState {
  node: string | null;
  personaName: string | null;
  personaIcon: string | null;
  text: string;
  connected: boolean;
}

export function useTokenStream(sessionId: string | null, enabled: boolean) {
  const [stream, setStream] = useState<TokenStreamState>({
    node: null,
    personaName: null,
    personaIcon: null,
    text: "",
    connected: false,
  });
  const retryRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const goneRef = useRef(false);

  useEffect(() => {
    goneRef.current = false;
    if (!sessionId || !enabled) {
      setStream({ node: null, personaName: null, personaIcon: null, text: "", connected: false });
      return;
    }

    let cancelled = false;
    const controller = new AbortController();

    const connect = async () => {
      try {
        const res = await fetch(`${API_BASE}/stream/${sessionId}`, {
          headers: {
            ...(API_KEY ? { "X-API-Key": API_KEY } : {}),
            Accept: "text/event-stream",
          },
          signal: controller.signal,
        });

        if (!res.ok || !res.body) {
          if (res.status === 404) {
            goneRef.current = true;
            return;
          }
          throw new Error(`Stream failed (${res.status})`);
        }

        if (cancelled) return;
        setStream((prev) => ({ ...prev, connected: true }));

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (!cancelled) {
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
              node?: string;
              token?: string;
              text?: string;
            };

            if (event.type === "start" && event.node) {
              const p = personaForNode(event.node);
              setStream({
                node: event.node,
                personaName: p?.name ?? null,
                personaIcon: p?.icon ?? null,
                text: "",
                connected: true,
              });
            } else if (event.type === "snapshot" && event.node) {
              const p = personaForNode(event.node);
              setStream({
                node: event.node,
                personaName: p?.name ?? null,
                personaIcon: p?.icon ?? null,
                text: event.text ?? "",
                connected: true,
              });
            } else if (event.type === "activity" && event.text) {
              setStream((prev) => ({
                ...prev,
                text: prev.text + event.text,
                connected: true,
              }));
            } else if (event.type === "token" && event.token) {
              setStream((prev) => {
                const node = event.node ?? prev.node;
                const p = personaForNode(node);
                return {
                  ...prev,
                  node,
                  personaName: p?.name ?? prev.personaName,
                  personaIcon: p?.icon ?? prev.personaIcon,
                  text: prev.text + event.token,
                  connected: true,
                };
              });
            }
          }
        }
      } catch (err) {
        if (cancelled || controller.signal.aborted || goneRef.current) return;
        setStream((prev) => ({ ...prev, connected: false }));
        retryRef.current = setTimeout(connect, 1500);
      }
    };

    connect();

    return () => {
      cancelled = true;
      controller.abort();
      if (retryRef.current) clearTimeout(retryRef.current);
    };
  }, [sessionId, enabled]);

  return stream;
}
