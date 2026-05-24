import { useMemo } from "react";
import { DiagramFlow } from "./DiagramFlow";
import { parseDiagramSpec } from "../types/diagram";

interface Props {
  jsonBody: string;
  fallbackAlt?: string;
  fallbackSrc?: string;
}

export function DiagramBlock({ jsonBody, fallbackAlt, fallbackSrc }: Props) {
  const spec = useMemo(() => {
    try {
      return parseDiagramSpec(jsonBody);
    } catch {
      return null;
    }
  }, [jsonBody]);

  if (!spec) {
    if (fallbackSrc) {
      return (
        <img
          src={fallbackSrc}
          alt={fallbackAlt ?? "Diagram"}
          className="w-full rounded-lg border border-slate-700 bg-slate-950"
        />
      );
    }
    return (
      <pre className="text-xs text-red-300 bg-slate-950 p-3 rounded-lg border border-red-900/50">
        Invalid diagram JSON
      </pre>
    );
  }

  return (
    <div className="rounded-lg overflow-hidden border border-slate-700">
      <div className="bg-slate-800 px-3 py-1 text-[10px] uppercase tracking-wide text-slate-400 flex justify-between">
        <span>Diagram</span>
        {spec.title && <span className="text-slate-500 normal-case">{spec.title}</span>}
      </div>
      <DiagramFlow spec={spec} />
      {fallbackSrc && (
        <details className="border-t border-slate-700 px-3 py-2 text-xs text-slate-500">
          <summary className="cursor-pointer hover:text-slate-400">Static SVG export</summary>
          <img src={fallbackSrc} alt={fallbackAlt ?? spec.title ?? "Diagram"} className="mt-2 w-full" />
        </details>
      )}
    </div>
  );
}
