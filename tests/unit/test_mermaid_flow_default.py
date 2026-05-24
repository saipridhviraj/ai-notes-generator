"""QA: default pipeline must use inline Mermaid (not JSON/SVG diagram pipeline)."""

from __future__ import annotations

from importlib import reload
from unittest.mock import MagicMock, patch

import pytest

from graph.state import KeywordPlan


@pytest.fixture
def keyword_plan():
    return KeywordPlan(
        topic="Python Decorators",
        domain="python",
        intent="comprehensive_notes",
        keywords=["decorators", "closure"],
        subtopics=["syntax", "use cases"],
        needs_web_search=False,
    )


@pytest.fixture
def mermaid_default_env(monkeypatch):
    """Ensure DIAGRAM_PIPELINE is off — matches production default."""
    monkeypatch.delenv("DIAGRAM_PIPELINE", raising=False)
    monkeypatch.setenv("DIAGRAM_PIPELINE", "false")
    monkeypatch.setenv("MERMAID_GENERATION_MODE", "json")
    import services.prompt_config as pc

    reload(pc)
    yield pc


class TestDefaultPipelineRouting:
    def test_pipeline_has_eight_steps_without_diagram_generator(self, mermaid_default_env):
        from utils.pipeline_progress import get_pipeline_steps

        steps = get_pipeline_steps()
        node_ids = [node for node, _ in steps]
        assert len(steps) == 8
        assert "diagram_generator" not in node_ids
        assert node_ids.index("student_notes") + 1 == node_ids.index("tutor_notes")

    def test_next_node_after_student_notes_is_tutor(self, mermaid_default_env):
        from utils.pipeline_progress import next_pipeline_node

        state = {"status": "running", "student_notes": "# Notes", "retry_count": 0}
        assert next_pipeline_node("student_notes", state) == "tutor_notes"

    def test_diagram_generator_step_only_when_pipeline_enabled(self, monkeypatch):
        monkeypatch.setenv("DIAGRAM_PIPELINE", "true")
        import services.prompt_config as pc

        reload(pc)
        from utils.pipeline_progress import get_pipeline_steps, next_pipeline_node

        steps = get_pipeline_steps()
        node_ids = [node for node, _ in steps]
        assert len(steps) == 9
        assert "diagram_generator" in node_ids
        assert next_pipeline_node("student_notes", {"retry_count": 0}) == "diagram_generator"


class TestStudentNotesMermaidPath:
    def test_calls_ensure_mermaid_not_placeholders(self, keyword_plan, base_state, mermaid_default_env):
        from graph.nodes.student_notes_creator import student_notes_creator

        state = {**base_state, "planner_output": keyword_plan}
        with (
            patch("graph.nodes.student_notes_creator.groq_client") as mock_groq,
            patch(
                "graph.nodes.student_notes_creator.ensure_mermaid_diagrams",
                side_effect=lambda notes, *args, **kwargs: notes,
            ) as mock_ensure,
            patch(
                "graph.nodes.student_notes_creator.convert_mermaid_blocks_to_placeholders",
                side_effect=AssertionError("placeholders must not run when DIAGRAM_PIPELINE=false"),
            ),
        ):
            mock_groq.complete.return_value = "# Student\n\n```mermaid\ngraph TD\nA-->B\n```"
            student_notes_creator(state)

        mock_ensure.assert_called_once()

    def test_production_prompts_require_mermaid_blocks(self, mermaid_default_env, monkeypatch):
        monkeypatch.setenv("USE_PRODUCTION_PROMPTS", "true")
        from prompts.profiles.production.student_notes_prompts import get_student_notes_system_prompt

        prompt = get_student_notes_system_prompt("EXAMPLE", min_diagrams=4)
        assert "Minimum 4 Mermaid" in prompt
        assert "<!-- diagram:" not in prompt
        assert "NEVER ```mermaid```" not in prompt


class TestMermaidRepairPath:
    def test_repair_uses_ensure_mermaid_by_default(self, keyword_plan, base_state, mermaid_default_env):
        from graph.nodes.mermaid_repair_node import mermaid_repair_node

        state = {
            **base_state,
            "planner_output": keyword_plan,
            "student_notes": "# Notes\n",
        }
        with (
            patch(
                "graph.nodes.mermaid_repair_node.ensure_mermaid_diagrams",
                return_value="# Notes\n```mermaid\ngraph TD\nA-->B\n```",
            ) as mock_ensure,
            patch(
                "graph.nodes.mermaid_repair_node.render_diagrams_in_notes",
                side_effect=AssertionError("JSON/SVG pipeline must not run"),
            ),
        ):
            result = mermaid_repair_node(state)

        mock_ensure.assert_called_once()
        assert "```mermaid" in result["student_notes"]


class TestEvaluatorMermaidValidation:
    def test_evaluator_validates_mermaid_not_diagram_json(self, base_state, mermaid_default_env):
        from graph.nodes.evaluator_node import evaluator_node

        passing = MagicMock()
        passing.passed = True
        passing.model_copy.return_value = passing
        passing.diagram_issues = []
        passing.alignment_issues = []
        passing.student_notes_score = 90
        passing.tutor_notes_score = 90
        passing.missing_topics = []

        state = {
            **base_state,
            "student_notes": "# Notes\n```mermaid\ngraph TD\nA-->B\n```",
            "tutor_notes": "# Tutor",
            "retry_count": 0,
        }
        with (
            patch("graph.nodes.evaluator_node.groq_client") as mock_groq,
            patch(
                "graph.nodes.evaluator_node.validate_all_mermaid_in_notes",
                return_value=[],
            ) as mock_mermaid_val,
            patch(
                "graph.nodes.evaluator_node.validate_diagrams_in_notes",
                side_effect=AssertionError("diagram-json validator must not run"),
            ),
            patch("graph.nodes.evaluator_node.heuristic_evaluate", return_value=passing),
        ):
            mock_groq.complete_json.return_value = passing.model_dump()
            evaluator_node(state)

        mock_mermaid_val.assert_called_once()


class TestJsonFallbackOnRepairOnly:
    def test_json_mode_used_for_repair_not_when_valid(self, monkeypatch):
        monkeypatch.setenv("MERMAID_GENERATION_MODE", "json")
        monkeypatch.setenv("MIN_MERMAID_DIAGRAMS", "1")

        notes = (
            "# Topic\n\n## Intro\n\n"
            "```mermaid\ngraph TD\nBad[Label: x]\n```\n"
        )

        with (
            patch(
                "utils.mermaid_enforce.generate_repair_patch_json",
                return_value=(
                    "<!-- replace: 1 -->\n"
                    "```mermaid\nflowchart TD\n"
                    'A["Label: x"] --> B\n'
                    "style A fill:#1a1a2e,stroke:#7c3aed,color:#e2e8f0\n"
                    "style B fill:#16213e,stroke:#2563eb,color:#e2e8f0\n```"
                ),
            ) as mock_json_repair,
            patch(
                "utils.mermaid_enforce.generate_supplement_patch_json",
                side_effect=AssertionError("supplement JSON must not run when diagram exists"),
            ),
        ):
            from utils.mermaid_enforce import ensure_mermaid_diagrams

            class FakeLLM:
                def complete(self, **kwargs):
                    raise AssertionError("direct mermaid LLM must not run when json repair succeeds")

            result = ensure_mermaid_diagrams(notes, {"topic": "T"}, FakeLLM(), errors=[])

        mock_json_repair.assert_called()
        assert "```mermaid" in result

    def test_valid_notes_skip_all_llm_repair(self, monkeypatch):
        monkeypatch.setenv("MIN_MERMAID_DIAGRAMS", "1")

        valid_block = (
            "```mermaid\nflowchart TD\n"
            'A["Step"] --> B["Next"]\n'
            "style A fill:#1a1a2e,stroke:#7c3aed,color:#e2e8f0\n"
            "style B fill:#16213e,stroke:#2563eb,color:#e2e8f0\n```"
        )
        notes = f"# Topic\n\n## Intro\n\n{valid_block}\n"

        with (
            patch("utils.mermaid_enforce.generate_repair_patch_json") as mock_repair,
            patch("utils.mermaid_enforce.generate_supplement_patch_json") as mock_supplement,
        ):
            from utils.mermaid_enforce import ensure_mermaid_diagrams

            class FakeLLM:
                def complete(self, **kwargs):
                    raise AssertionError("LLM must not run when diagrams are valid")

            result = ensure_mermaid_diagrams(notes, {"topic": "T"}, FakeLLM(), errors=[])

        mock_repair.assert_not_called()
        mock_supplement.assert_not_called()
        assert "flowchart TD" in result
