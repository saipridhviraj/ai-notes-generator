"""Tests for section-key student/tutor handoff."""
from utils.notes_sections import (
    annotations_from_tutor_json,
    build_section_handoff,
    merge_annotations_by_section,
    parse_markdown_sections,
)
from utils.tutor_merge import merge_tutor_json_handoff


SAMPLE = """# Python Decorators

## Decorators

A decorator wraps a function.

### Syntax

Use `@` above the def.

## Use cases

Common patterns here.
"""


class TestParseMarkdownSections:
    def test_splits_by_headings(self):
        sections = parse_markdown_sections(SAMPLE)
        keys = [s.key for s in sections]
        assert "## Decorators" in keys
        assert "### Syntax" in keys
        assert "## Use cases" in keys

    def test_handoff_has_previews(self):
        sections = parse_markdown_sections(SAMPLE)
        handoff = build_section_handoff(sections, preview_chars=20)
        assert handoff[0]["section_key"].startswith("#")
        assert "char_count" in handoff[0]

    def test_tutor_handoff_h2_only(self):
        from utils.notes_sections import build_tutor_handoff

        sections = parse_markdown_sections(SAMPLE)
        handoff = build_tutor_handoff(sections, max_sections=10)
        keys = [h["section_key"] for h in handoff]
        assert "## Decorators" in keys
        assert "## Use cases" in keys
        assert "### Syntax" not in keys


class TestMergeAnnotationsBySection:
    def test_inserts_by_section_key(self):
        annotations = {
            "## Decorators": "> **👨‍🏫 TEACHING NOTE:** Start with wrappers.",
        }
        merged = merge_annotations_by_section(SAMPLE, annotations)
        assert "TEACHING NOTE" in merged
        assert "A decorator wraps" in merged
        assert merged.index("TEACHING NOTE") > merged.index("A decorator wraps")

    def test_json_handoff_merge(self):
        tutor_json = {
            "section_annotations": [
                {
                    "section_key": "## Use cases",
                    "annotations": "> **👨‍🏫 SAY THIS:** Give an example.",
                }
            ]
        }
        merged = merge_tutor_json_handoff(SAMPLE, tutor_json)
        assert "SAY THIS" in merged
        assert "Common patterns" in merged

    def test_annotations_from_list_or_dict(self):
        by_list, _, _ = annotations_from_tutor_json(
            {"section_annotations": [{"section_key": "## A", "annotations": "x"}]}
        )
        by_dict, _, _ = annotations_from_tutor_json({"sections": {"## A": "x"}})
        assert by_list["## A"] == "x"
        assert by_dict["## A"] == "x"

    def test_post_checklist_appended(self):
        tutor_json = {
            "post": "<details>Post checklist</details>",
            "section_annotations": [],
        }
        merged = merge_tutor_json_handoff(SAMPLE, tutor_json)
        assert "Post checklist" in merged
        assert merged.strip().endswith("</details>")
