/** Fix common LLM Mermaid mistakes so diagrams render in Mermaid v11 (mirrors backend normalize). */

const SUBGRAPH_ID = /^\s*subgraph\s+(\w+)/gm;
const UNQUOTED_NODE = /(\b[A-Za-z][A-Za-z0-9_]*)\[([^\]"\n]+)\]/g;
const QUOTED_NODE = /(\b[A-Za-z][A-Za-z0-9_]*)\["([^"\n]+)"\]/g;
const STYLE_LINE = /^(\s*style\s+)(\w+)(\s+.+)$/;
const DIAGRAM_HEADERS =
  /^\s*(flowchart\s+\w+|graph\s+\w+|sequenceDiagram|classDiagram|stateDiagram|erDiagram)\s*$/;
const EMOJI =
  /[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\u{1F600}-\u{1F64F}]/gu;
const DEFAULT_STYLE =
  "fill:#1a1a2e,stroke:#7c3aed,stroke-width:2px,color:#e2e8f0";

function subgraphIds(block: string): Set<string> {
  const ids = new Set<string>();
  SUBGRAPH_ID.lastIndex = 0;
  let m: RegExpExecArray | null;
  while ((m = SUBGRAPH_ID.exec(block)) !== null) {
    ids.add(m[1]);
  }
  return ids;
}

function dedupeHeaders(block: string): string {
  const lines = block.split("\n");
  const headerIdx: number[] = [];
  lines.forEach((line, i) => {
    if (DIAGRAM_HEADERS.test(line.trim())) headerIdx.push(i);
  });
  if (headerIdx.length <= 1) return block;

  const flowIdx = headerIdx.find((i) => /^flowchart|^graph/.test(lines[i].trim()));
  const keep = flowIdx ?? headerIdx[headerIdx.length - 1];
  return lines.filter((_, i) => !headerIdx.includes(i) || i === keep).join("\n");
}

function quoteAllLabels(block: string): string {
  return block.replace(UNQUOTED_NODE, (_full, nodeId: string, label: string) => {
    const escaped = label.replace(/"/g, "#quot;");
    return `${nodeId}["${escaped}"]`;
  });
}

function stripEmojis(block: string): string {
  return block.replace(QUOTED_NODE, (_full, nodeId: string, label: string) => {
    const cleaned = label.replace(EMOJI, "").replace(/\s{2,}/g, " ").trim();
    return `${nodeId}["${cleaned}"]`;
  });
}

function ensureFlowchartHeader(block: string): string {
  const trimmed = block.trim();
  if (!trimmed) return "flowchart TD\n";
  const first = trimmed.split("\n")[0].trim();
  if (/^(flowchart|graph)\s/.test(first)) {
    return trimmed.replace(/^graph\s/, "flowchart ");
  }
  return `flowchart TD\n${trimmed}`;
}

function styledNodes(block: string): Set<string> {
  const styled = new Set<string>();
  for (const line of block.split("\n")) {
    const m = line.match(/^\s*style\s+(\w+)/);
    if (m) styled.add(m[1]);
  }
  return styled;
}

function nodeIds(block: string): Set<string> {
  const ids = new Set<string>();
  QUOTED_NODE.lastIndex = 0;
  let m: RegExpExecArray | null;
  while ((m = QUOTED_NODE.exec(block)) !== null) {
    ids.add(m[1]);
  }
  const edgeRe = /\b([A-Za-z][A-Za-z0-9_]*)\s*-->/g;
  while ((m = edgeRe.exec(block)) !== null) {
    ids.add(m[1]);
  }
  return ids;
}

function ensureNodeStyles(block: string): string {
  const styled = styledNodes(block);
  const subgraphs = subgraphIds(block);
  const missing = [...nodeIds(block)].filter((id) => !styled.has(id) && !subgraphs.has(id));
  if (!missing.length) return block;
  const additions = missing.map((id) => `style ${id} ${DEFAULT_STYLE}`).join("\n");
  return `${block.trimEnd()}\n\n${additions}\n`;
}

export function sanitizeMermaidBlock(block: string): string {
  if (!block?.trim()) return block;

  if (/sequenceDiagram|participant\s|->>/.test(block)) {
    return block;
  }

  const subgraphs = subgraphIds(block);
  let lines = block
    .split("\n")
    .filter((line) => {
      const style = line.match(STYLE_LINE);
      return !(style && subgraphs.has(style[2]));
    });

  let out = lines.join("\n");
  out = dedupeHeaders(out);
  out = quoteAllLabels(out);
  out = stripEmojis(out);
  out = ensureFlowchartHeader(out);
  out = ensureNodeStyles(out);
  return out;
}

export function isMermaidErrorSvg(svg: string): boolean {
  return /Syntax error in text/i.test(svg) || /aria-roledescription="error"/i.test(svg);
}
