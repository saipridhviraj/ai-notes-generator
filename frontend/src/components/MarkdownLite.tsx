/** Lightweight markdown renderer for tutor plan review (no extra deps). */

function renderInline(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={i} className="text-slate-100 font-semibold">
          {part.slice(2, -2)}
        </strong>
      );
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return (
        <code key={i} className="text-violet-300 bg-slate-900 px-1 rounded text-xs">
          {part.slice(1, -1)}
        </code>
      );
    }
    return part;
  });
}

interface Props {
  content: string;
  className?: string;
}

export function MarkdownLite({ content, className = "" }: Props) {
  const lines = content.split("\n");

  return (
    <div className={`text-sm text-slate-200 space-y-2 ${className}`}>
      {lines.map((line, idx) => {
        const trimmed = line.trim();
        if (!trimmed) return <div key={idx} className="h-1" />;
        if (trimmed.startsWith("## ")) {
          return (
            <h4 key={idx} className="text-base font-semibold text-yellow-300 mt-3 first:mt-0">
              {trimmed.slice(3)}
            </h4>
          );
        }
        if (trimmed.startsWith("### ")) {
          return (
            <h5 key={idx} className="text-sm font-semibold text-violet-300 mt-2">
              {trimmed.slice(4)}
            </h5>
          );
        }
        if (trimmed.startsWith("- ")) {
          return (
            <li key={idx} className="ml-4 list-disc marker:text-violet-400">
              {renderInline(trimmed.slice(2))}
            </li>
          );
        }
        return <p key={idx}>{renderInline(trimmed)}</p>;
      })}
    </div>
  );
}
