from pathlib import Path
from typing import Optional

from utils.helpers import slugify  # noqa: F401 — re-exported for backwards compat

PROJECT_ROOT = Path(__file__).resolve().parent.parent
NOTES_DIR = PROJECT_ROOT / "generated_notes"


def save_markdown(
    content: str,
    filename: str,
    output_dir: Optional[Path] = None,
) -> Path:
    if output_dir is None:
        output_dir = NOTES_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / filename
    try:
        target.write_text(content, encoding="utf-8")
    except Exception as e:
        raise IOError(f"FileService: could not write '{target}': {e}") from e
    return target.resolve()


_example_cache: dict[tuple[str, int | None], str] = {}


def load_example(filename: str, max_chars: int | None = None) -> str:
    cache_key = (filename, max_chars)
    cached = _example_cache.get(cache_key)
    if cached is not None:
        return cached

    path = Path(__file__).parent.parent / "examples" / filename
    if not path.exists():
        raise FileNotFoundError(
            f"Missing required example file: examples/{filename}\n"
            f"Copy your Day 1 notes into the examples/ folder before running.\n"
            f"See README.md for setup instructions."
        )
    text = path.read_text(encoding="utf-8")
    if max_chars is not None and len(text) > max_chars:
        text = (
            text[:max_chars].rstrip()
            + "\n\n...(style reference truncated for faster local generation)...\n"
        )
    _example_cache[cache_key] = text
    return text


