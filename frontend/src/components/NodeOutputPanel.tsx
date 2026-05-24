import { MarkdownLite } from "./MarkdownLite";
import { SuggestedDiagramsPanel } from "./SuggestedDiagramsPanel";
import type { NodeArtifactResponse } from "../api/client";

function hasSuggestedDiagrams(
  artifact: NodeArtifactResponse | null | undefined
): artifact is NodeArtifactResponse & { suggested_diagrams: string[] } {
  return Boolean(artifact?.suggested_diagrams?.length);
}

interface Props {
  artifact: NodeArtifactResponse | null;
  loading: boolean;
  error: string | null;
  liveFallback?: { label: string; text: string; hint?: string | null };
}

export function NodeOutputPanel({ artifact, loading, error, liveFallback }: Props) {
  if (loading) {
    return (
      <div className="surface-elevated p-4 text-sm text-white/40 min-h-[20rem] flex items-center justify-center">
        Loading step output…
      </div>
    );
  }

  if (error) {
    return (
      <div role="alert" className="surface-elevated p-4 text-sm text-red-300 border-red-500/20">
        {error}
      </div>
    );
  }

  if (liveFallback?.text) {
    return (
      <div className="surface-elevated border-chat-accent/20 p-4 flex flex-col gap-2 min-h-[20rem] flex-1">
        <header className="shrink-0">
          <h3 className="text-sm font-medium text-chat-accent">{liveFallback.label}</h3>
          {liveFallback.hint && (
            <p className="text-[11px] text-white/35 mt-0.5">{liveFallback.hint}</p>
          )}
          <p className="text-[10px] text-chat-accent/80 mt-1">● live stream</p>
        </header>
        <pre className="text-xs text-white/70 font-mono whitespace-pre-wrap flex-1 overflow-y-auto chat-scroll leading-relaxed min-h-[16rem] max-h-[40vh]">
          {liveFallback.text}
        </pre>
      </div>
    );
  }

  if (!artifact) {
    return (
      <div className="surface-elevated p-4 text-sm text-white/35 italic min-h-[12rem] flex items-center justify-center">
        Select a completed step to inspect its output.
      </div>
    );
  }

  return (
    <div className="surface-elevated p-4 flex flex-col gap-2 min-h-[20rem] flex-1 max-h-[70vh]">
      <header className="shrink-0 flex items-center justify-between gap-2">
        <h3 className="text-sm font-medium text-white/90 flex items-center gap-2">
          <span aria-hidden>{artifact.persona_icon}</span>
          {artifact.label}
        </h3>
        <span className="text-[10px] text-white/30">
          {artifact.char_count.toLocaleString()} chars · {artifact.format}
        </span>
      </header>
      {hasSuggestedDiagrams(artifact) && (
        <SuggestedDiagramsPanel diagrams={artifact.suggested_diagrams} />
      )}
      <div className="flex-1 overflow-y-auto chat-scroll min-h-[16rem]">
        {artifact.format === "json" ? (
          <pre className="text-xs text-white/70 font-mono whitespace-pre-wrap leading-relaxed">
            {artifact.content}
          </pre>
        ) : (
          <MarkdownLite content={artifact.content} />
        )}
      </div>
    </div>
  );
}
