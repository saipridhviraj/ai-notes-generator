import { useMemo } from "react";
import { MermaidDiagram } from "./MermaidDiagram";
import { DiagramBlock } from "./DiagramBlock";

function renderInline(text: string, keyPrefix: string) {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))/g);
  return parts.map((part, i) => {
    const key = `${keyPrefix}-${i}`;
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={key} className="text-slate-100 font-semibold">
          {part.slice(2, -2)}
        </strong>
      );
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return (
        <code key={key} className="text-violet-300 bg-slate-950 px-1 rounded text-[0.85em]">
          {part.slice(1, -1)}
        </code>
      );
    }
    const linkMatch = part.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
    if (linkMatch) {
      return (
        <a
          key={key}
          href={linkMatch[2]}
          target="_blank"
          rel="noopener noreferrer"
          className="text-violet-400 hover:text-violet-300 underline"
        >
          {linkMatch[1]}
        </a>
      );
    }
    return part;
  });
}

type Block =
  | { type: "heading"; level: number; text: string }
  | { type: "paragraph"; text: string }
  | { type: "list"; items: string[] }
  | { type: "blockquote"; text: string }
  | { type: "code"; lang: string; body: string }
  | { type: "image"; alt: string; src: string }
  | { type: "hr" };

function parseMarkdown(content: string): Block[] {
  const lines = content.split("\n");
  const blocks: Block[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

    if (!trimmed) {
      i += 1;
      continue;
    }

    if (trimmed.startsWith("```")) {
      const lang = trimmed.slice(3).trim();
      const body: string[] = [];
      i += 1;
      while (i < lines.length && !lines[i].trim().startsWith("```")) {
        body.push(lines[i]);
        i += 1;
      }
      blocks.push({ type: "code", lang, body: body.join("\n") });
      i += 1;
      continue;
    }

    if (/^(-{3,}|\*{3,}|_{3,})$/.test(trimmed)) {
      blocks.push({ type: "hr" });
      i += 1;
      continue;
    }

    const headingMatch = trimmed.match(/^(#{1,6})\s+(.+)$/);
    if (headingMatch) {
      blocks.push({ type: "heading", level: headingMatch[1].length, text: headingMatch[2] });
      i += 1;
      continue;
    }

    const imageMatch = trimmed.match(/^!\[([^\]]*)\]\(([^)]+)\)$/);
    if (imageMatch) {
      blocks.push({ type: "image", alt: imageMatch[1], src: imageMatch[2] });
      i += 1;
      continue;
    }

    if (trimmed.startsWith(">")) {
      const quoteLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith(">")) {
        quoteLines.push(lines[i].trim().replace(/^>\s?/, ""));
        i += 1;
      }
      blocks.push({ type: "blockquote", text: quoteLines.join("\n") });
      continue;
    }

    if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
      const items: string[] = [];
      while (i < lines.length) {
        const t = lines[i].trim();
        if (t.startsWith("- ") || t.startsWith("* ")) {
          items.push(t.slice(2));
          i += 1;
        } else break;
      }
      blocks.push({ type: "list", items });
      continue;
    }

    const paraLines: string[] = [trimmed];
    i += 1;
    while (i < lines.length) {
      const t = lines[i].trim();
      if (
        !t ||
        t.startsWith("#") ||
        t.startsWith("```") ||
        t.startsWith(">") ||
        t.startsWith("- ") ||
        t.startsWith("* ") ||
        /^(-{3,}|\*{3,}|_{3,})$/.test(t)
      ) {
        break;
      }
      paraLines.push(t);
      i += 1;
    }
    blocks.push({ type: "paragraph", text: paraLines.join(" ") });
  }

  return blocks;
}

const HEADING_CLASS: Record<number, string> = {
  1: "text-2xl font-bold text-slate-50 mt-6 first:mt-0",
  2: "text-xl font-semibold text-yellow-300 mt-5 first:mt-0",
  3: "text-lg font-semibold text-violet-300 mt-4",
  4: "text-base font-semibold text-slate-100 mt-3",
  5: "text-sm font-semibold text-slate-200 mt-2",
  6: "text-sm font-medium text-slate-300 mt-2",
};

interface Props {
  content: string;
  className?: string;
}

export function MarkdownDocument({ content, className = "" }: Props) {
  const blocks = useMemo(() => parseMarkdown(content), [content]);

  return (
    <article className={`text-sm text-slate-200 leading-relaxed space-y-3 ${className}`}>
      {blocks.map((block, idx) => {
        switch (block.type) {
          case "heading": {
            const Tag = `h${Math.min(block.level, 6)}` as keyof JSX.IntrinsicElements;
            return (
              <Tag key={idx} className={HEADING_CLASS[block.level] ?? HEADING_CLASS[4]}>
                {renderInline(block.text, `h-${idx}`)}
              </Tag>
            );
          }
          case "paragraph":
            return <p key={idx}>{renderInline(block.text, `p-${idx}`)}</p>;
          case "list":
            return (
              <ul key={idx} className="list-disc ml-5 space-y-1 marker:text-violet-400">
                {block.items.map((item, j) => (
                  <li key={j}>{renderInline(item, `li-${idx}-${j}`)}</li>
                ))}
              </ul>
            );
          case "blockquote":
            return (
              <blockquote
                key={idx}
                className="border-l-4 border-emerald-500/70 bg-emerald-950/30 rounded-r-lg px-3 py-2 text-emerald-100"
              >
                {block.text.split("\n").map((line, j) => (
                  <p key={j} className={j > 0 ? "mt-1" : ""}>
                    {renderInline(line, `q-${idx}-${j}`)}
                  </p>
                ))}
              </blockquote>
            );
          case "code":
            if (block.lang === "diagram-json" || block.lang === "diagram") {
              const next = blocks[idx + 1];
              const fallback =
                next?.type === "image" ? { alt: next.alt, src: next.src } : undefined;
              return (
                <DiagramBlock
                  key={idx}
                  jsonBody={block.body}
                  fallbackAlt={fallback?.alt}
                  fallbackSrc={fallback?.src}
                />
              );
            }
            if (block.lang === "mermaid") {
              return (
                <div key={idx} className="rounded-lg overflow-hidden border border-slate-700">
                  <div className="bg-slate-800 px-3 py-1 text-[10px] uppercase tracking-wide text-slate-400">
                    Diagram
                  </div>
                  <MermaidDiagram chart={block.body} />
                </div>
              );
            }
            return (
              <div key={idx} className="rounded-lg overflow-hidden border border-slate-700">
                {block.lang && (
                  <div className="bg-slate-800 px-3 py-1 text-[10px] uppercase tracking-wide text-slate-400">
                    {block.lang}
                  </div>
                )}
                <pre className="bg-slate-950 p-3 overflow-x-auto text-xs font-mono text-slate-300 whitespace-pre-wrap">
                  {block.body}
                </pre>
              </div>
            );
          case "image": {
            const prev = blocks[idx - 1];
            if (
              prev?.type === "code" &&
              (prev.lang === "diagram-json" || prev.lang === "diagram")
            ) {
              return null;
            }
            return (
              <img
                key={idx}
                src={block.src}
                alt={block.alt}
                className="w-full rounded-lg border border-slate-700 bg-slate-950"
              />
            );
          }
          case "hr":
            return <hr key={idx} className="border-slate-700 my-4" />;
          default:
            return null;
        }
      })}
    </article>
  );
}
