import type { NodeArtifactItem } from "../api/client";

interface Props {
  artifacts: NodeArtifactItem[];
  selectedNodeId: string | null;
  currentNodeId: string | null;
  onSelect: (nodeId: string) => void;
}

const STATE_STYLE: Record<string, string> = {
  done: "border-chat-accent/30 bg-chat-accent/5 hover:bg-chat-accent/10",
  active: "border-chat-accent/50 bg-chat-accent/10 ring-1 ring-chat-accent/20",
  pending: "border-white/[0.06] bg-white/[0.02] opacity-50",
  skipped: "border-white/[0.04] opacity-30",
};

export function NodeOutputRail({ artifacts, selectedNodeId, currentNodeId, onSelect }: Props) {
  return (
    <nav aria-label="Pipeline node outputs" className="flex flex-col gap-1">
      <h3 className="text-[10px] font-medium uppercase tracking-wider text-white/30 px-1 mb-1">
        Steps
      </h3>
      {artifacts.map((item) => {
        const isSelected = selectedNodeId === item.node_id;
        const isLive = currentNodeId === item.node_id && item.state === "active";
        const clickable = item.available || item.state === "done" || item.state === "active";

        return (
          <button
            key={item.node_id}
            type="button"
            disabled={!clickable && item.state === "pending"}
            onClick={() => clickable && onSelect(item.node_id)}
            className={`
              w-full text-left rounded-xl border px-2.5 py-2 transition-colors
              ${STATE_STYLE[item.state] ?? STATE_STYLE.pending}
              ${isSelected ? "ring-1 ring-white/30" : ""}
              ${clickable ? "cursor-pointer" : "cursor-default"}
            `}
          >
            <div className="flex items-center gap-2 min-w-0">
              <span className="text-sm shrink-0" aria-hidden>
                {item.persona_icon}
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-medium text-white/80 truncate">{item.label}</p>
                <p className="text-[10px] text-white/30 truncate">
                  {item.available
                    ? item.node_id === "research" && item.suggested_diagram_count
                      ? `${item.suggested_diagram_count} diagrams`
                      : `${item.char_count.toLocaleString()} chars`
                    : isLive
                      ? "Streaming…"
                      : item.state === "skipped"
                        ? "Skipped"
                        : "Pending"}
                </p>
              </div>
              {isLive && (
                <span className="text-[10px] text-chat-accent shrink-0 animate-pulse">●</span>
              )}
              {item.available && !isLive && (
                <span className="text-[10px] text-chat-accent shrink-0">✓</span>
              )}
            </div>
          </button>
        );
      })}
    </nav>
  );
}
