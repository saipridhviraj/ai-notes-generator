"""Tests for light eval structural summary."""

from utils.eval_summary import (
    build_eval_summary,
    compute_alignment_issues,
    compute_heading_alignment,
)


def test_build_eval_summary_includes_headings_not_body():
    plan = {
        "keywords": ["class", "object"],
        "subtopics": ["Introduction", "Classes"],
    }
    student = (
        "# Python OOP\n\n"
        "## Introduction\n\nclass and object basics.\n\n"
        "## Classes\n\nMore on class.\n\n"
        "## Revision Questions\n\n1. Q?\n\n"
        "## Homework\n\nDo this.\n\n"
        "```mermaid\nflowchart TD\nA-->B\nstyle A fill:#1a1a2e,color:#e2e8f0\n```\n"
    )
    tutor = (
        "# Python OOP\n\n"
        "## Introduction\n\n> **👨‍🏫 TEACHING NOTE:** Say hi.\n\n"
        "## Classes\n\nBody.\n"
    )
    summary = build_eval_summary(
        plan=plan,
        student_notes=student,
        tutor_notes=tutor,
        mermaid_issues=[],
        supplement_mode=True,
    )
    assert "PLAN SUBTOPICS" in summary
    assert "Introduction" in summary
    assert "class and object basics" not in summary
    assert "MERMAID COUNT:" in summary
    assert "PYTHON MISSING KEYWORDS: none" in summary
    assert "REVISION SECTION: yes" in summary
    assert "HOMEWORK SECTION: yes" in summary
    assert "HEADING ALIGNMENT" in summary
    assert "STUDENT-ONLY H2" in summary
    assert "Revision Questions" in summary


def test_missing_keywords_listed():
    summary = build_eval_summary(
        plan={"keywords": ["decorator", "closure"], "subtopics": ["Intro"]},
        student_notes="## Intro\n\nplain text only.",
        tutor_notes="",
        mermaid_issues=["Only 0 Mermaid diagram(s) found"],
    )
    assert "decorator" in summary
    assert "PYTHON MERMAID ISSUES:" in summary


def test_compute_heading_alignment_detects_gaps():
    student = "## Intro\n\nBody.\n\n## Advanced\n\nMore.\n"
    tutor = "## Intro\n\n> **👨‍🏫 TEACHING NOTE:** Hi.\n\n## Extra\n\nOnly tutor.\n"
    align = compute_heading_alignment(student, tutor)
    assert align["matched"] == ["Intro"]
    assert "Advanced" in align["student_only"]
    assert "Extra" in align["tutor_only"]
    assert align["missing_annotations"] == []


def test_compute_alignment_issues_includes_missing_annotations():
    student = "## Intro\n\nBody.\n\n## Classes\n\nMore.\n"
    tutor = "## Intro\n\n> **👨‍🏫 TEACHING NOTE:** Hi.\n\n## Classes\n\nPlain tutor text.\n"
    issues = compute_alignment_issues(student, tutor)
    assert any("Missing tutor annotation" in i and "Classes" in i for i in issues)
