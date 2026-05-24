import { useEffect, useId, useRef, useState } from "react";
import mermaid from "mermaid";
import { isMermaidErrorSvg, sanitizeMermaidBlock } from "../utils/mermaidSanitize";

let mermaidInitialized = false;

function initMermaid() {
  if (mermaidInitialized) return;
  mermaid.initialize({
    startOnLoad: false,
    theme: "dark",
    securityLevel: "loose",
    fontFamily: "ui-monospace, monospace",
  });
  mermaidInitialized = true;
}

interface Props {
  chart: string;
}

export function MermaidDiagram({ chart }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const reactId = useId().replace(/:/g, "");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    initMermaid();
    const el = containerRef.current;
    if (!el) return;

    let cancelled = false;
    const source = chart.trim();
    const safeChart = sanitizeMermaidBlock(source);
    const renderId = `mermaid-${reactId}-${Math.random().toString(36).slice(2, 9)}`;

    mermaid
      .render(renderId, safeChart)
      .then(({ svg }) => {
        if (!cancelled && containerRef.current) {
          if (isMermaidErrorSvg(svg)) {
            setError("Mermaid syntax error");
            containerRef.current.innerHTML = "";
            return;
          }
          containerRef.current.innerHTML = svg;
          setError(null);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to render diagram");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [chart, reactId]);

  if (error) {
    return (
      <div className="rounded-lg border border-amber-500/40 bg-slate-950 p-3">
        <p className="text-xs text-amber-300 mb-2">Diagram preview failed — showing source:</p>
        <pre className="text-xs text-slate-400 whitespace-pre-wrap font-mono">{sanitizeMermaidBlock(chart.trim())}</pre>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="mermaid-diagram overflow-x-auto p-3 bg-slate-950 flex justify-center [&_svg]:max-w-full"
      aria-label="Mermaid diagram"
    />
  );
}
