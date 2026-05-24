"""P0 tests for file_service — BUG-1 regression: output must be in generated_notes/."""
from services.file_service import save_markdown, NOTES_DIR, slugify


class TestNotesDir:
    def test_notes_dir_is_generated_notes(self):
        """BUG-1 regression — NOTES_DIR must resolve to <project_root>/generated_notes."""
        assert NOTES_DIR.name == "generated_notes"

    def test_notes_dir_is_absolute(self):
        assert NOTES_DIR.is_absolute()

    def test_notes_dir_parent_is_project_root(self):
        # Parent of generated_notes should contain main.py
        assert (NOTES_DIR.parent / "main.py").exists()


class TestSaveMarkdown:
    def test_saves_to_specified_dir(self, tmp_path):
        path = save_markdown("# Hello", "test.md", tmp_path)
        assert path.parent == tmp_path
        assert path.name == "test.md"
        assert path.read_text() == "# Hello"

    def test_creates_output_dir_if_not_exists(self, tmp_path):
        output_dir = tmp_path / "nested" / "dir"
        assert not output_dir.exists()
        path = save_markdown("# Test", "test.md", output_dir)
        assert output_dir.exists()
        assert path.exists()

    def test_default_dir_is_notes_dir(self, tmp_path, monkeypatch):
        """Without output_dir arg, falls back to NOTES_DIR, not cwd."""
        import services.file_service as fs
        monkeypatch.setattr(fs, "NOTES_DIR", tmp_path)
        path = save_markdown("# Default", "default.md")
        assert path.parent == tmp_path


class TestSlugify:
    def test_spaces_become_underscores(self):
        assert slugify("Python Basics") == "python_basics"

    def test_special_chars_stripped(self):
        result = slugify("C++ Programming!")
        assert "+" not in result
        assert "!" not in result

    def test_no_leading_trailing_underscores(self):
        result = slugify("  Hello World  ")
        assert not result.startswith("_")
        assert not result.endswith("_")

    def test_consecutive_underscores_collapsed(self):
        result = slugify("Hello   World")
        assert "__" not in result
