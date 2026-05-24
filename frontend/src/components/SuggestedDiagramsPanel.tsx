interface Props {
  diagrams: string[];
}

export function SuggestedDiagramsPanel({ diagrams }: Props) {
  if (!diagrams.length) return null;

  return (
    <aside
      aria-label="Suggested diagrams from research"
      className="shrink-0 rounded-lg border border-cyan-500/30 bg-cyan-950/20 px-3 py-2.5"
    >
      <h4 className="text-xs font-semibold uppercase tracking-wide text-cyan-300 mb-2">
        Suggested diagrams ({diagrams.length})
      </h4>
      <p className="text-[11px] text-slate-400 mb-2">
        Research brief — student notes step will draw these as Mermaid charts.
      </p>
      <ol className="list-decimal list-inside space-y-1.5 text-xs text-slate-200 leading-relaxed">
        {diagrams.map((item, index) => (
          <li key={index} className="pl-0.5">
            {item}
          </li>
        ))}
      </ol>
    </aside>
  );
}
