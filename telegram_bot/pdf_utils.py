"""Convert Markdown notes to styled PDF bytes using weasyprint."""
import re
import markdown
from weasyprint import HTML, CSS

# Mermaid blocks are rendered as styled code blocks in the PDF
_MERMAID_RE = re.compile(r"```mermaid\n(.*?)```", re.DOTALL)

_CSS = CSS(string="""
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Fira+Code:wght@400;500&display=swap');

@page {
    margin: 2.5cm 2cm;
    @bottom-center {
        content: counter(page) " / " counter(pages);
        font-size: 9pt;
        color: #888;
    }
}

body {
    font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.7;
    color: #1a1a2e;
    max-width: 100%;
}

h1 {
    font-size: 22pt;
    font-weight: 700;
    color: #1a56db;
    border-bottom: 3px solid #1a56db;
    padding-bottom: 0.3em;
    margin-top: 0;
}

h2 {
    font-size: 16pt;
    font-weight: 600;
    color: #1e429f;
    border-bottom: 1px solid #dbeafe;
    padding-bottom: 0.2em;
    margin-top: 1.5em;
}

h3 {
    font-size: 13pt;
    font-weight: 600;
    color: #1e3a8a;
    margin-top: 1.2em;
}

h4, h5, h6 {
    font-weight: 600;
    color: #374151;
}

p { margin: 0.6em 0; }

code {
    font-family: 'Fira Code', 'Courier New', monospace;
    font-size: 0.88em;
    background: #f0f4ff;
    color: #1e3a8a;
    padding: 2px 6px;
    border-radius: 4px;
}

pre {
    background: #1e1e2e;
    color: #cdd6f4;
    padding: 1em 1.2em;
    border-radius: 8px;
    overflow-x: auto;
    margin: 1em 0;
    border-left: 4px solid #1a56db;
}

pre code {
    background: none;
    color: inherit;
    padding: 0;
    font-size: 0.85em;
}

blockquote {
    border-left: 4px solid #1a56db;
    background: #eff6ff;
    margin: 1em 0;
    padding: 0.8em 1.2em;
    border-radius: 0 6px 6px 0;
    color: #1e3a8a;
}

blockquote p { margin: 0; }

table {
    border-collapse: collapse;
    width: 100%;
    margin: 1em 0;
    font-size: 0.95em;
}

th {
    background: #1a56db;
    color: white;
    padding: 8px 12px;
    text-align: left;
    font-weight: 600;
}

td {
    padding: 7px 12px;
    border-bottom: 1px solid #e5e7eb;
}

tr:nth-child(even) td { background: #f8faff; }

ul, ol { padding-left: 1.5em; margin: 0.5em 0; }
li { margin: 0.3em 0; }

.mermaid-block {
    background: #f8f9fa;
    border: 1px solid #e2e8f0;
    border-left: 4px solid #64748b;
    border-radius: 0 6px 6px 0;
    padding: 0.8em 1em;
    margin: 1em 0;
    font-family: 'Fira Code', monospace;
    font-size: 0.82em;
    color: #475569;
    white-space: pre;
}

.mermaid-label {
    font-size: 0.75em;
    font-weight: 600;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.3em;
}

strong { font-weight: 700; color: #111827; }
em { font-style: italic; }
a { color: #1a56db; text-decoration: none; }
hr { border: none; border-top: 2px solid #e5e7eb; margin: 1.5em 0; }
""")


def _preprocess_mermaid(md_text: str) -> str:
    """Replace ```mermaid blocks with a styled div before markdown conversion."""
    def replace(m: re.Match) -> str:
        code = m.group(1).strip()
        return (
            f'<div class="mermaid-block">'
            f'<div class="mermaid-label">📊 Diagram (Mermaid)</div>'
            f'{code}'
            f"</div>"
        )
    return _MERMAID_RE.sub(replace, md_text)


def markdown_to_pdf(md_text: str, title: str = "") -> bytes:
    """Convert a Markdown string to PDF bytes."""
    preprocessed = _preprocess_mermaid(md_text)

    html_body = markdown.markdown(
        preprocessed,
        extensions=["fenced_code", "tables", "toc", "nl2br"],
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{title}</title>
</head>
<body>
{html_body}
</body>
</html>"""

    return HTML(string=html).write_pdf(stylesheets=[_CSS])
