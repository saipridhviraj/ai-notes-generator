"""Tests for dev vs production prompt profile routing."""


class TestPromptConfig:
    def test_defaults_to_dev_on_groq(self, monkeypatch):
        monkeypatch.delenv("USE_PRODUCTION_PROMPTS", raising=False)
        monkeypatch.delenv("PROMPT_PROFILE", raising=False)
        monkeypatch.delenv("USE_OLLAMA", raising=False)
        from services.prompt_config import use_production_prompts, get_prompt_profile

        assert use_production_prompts() is False
        assert get_prompt_profile() == "dev"

    def test_auto_production_when_ollama(self, monkeypatch):
        monkeypatch.setenv("USE_OLLAMA", "true")
        monkeypatch.delenv("USE_PRODUCTION_PROMPTS", raising=False)
        from services.prompt_config import use_production_prompts

        assert use_production_prompts() is True

    def test_explicit_production_override(self, monkeypatch):
        monkeypatch.setenv("USE_PRODUCTION_PROMPTS", "true")
        monkeypatch.delenv("USE_OLLAMA", raising=False)
        from services.prompt_config import use_production_prompts

        assert use_production_prompts() is True

    def test_explicit_dev_overrides_ollama(self, monkeypatch):
        monkeypatch.setenv("USE_OLLAMA", "true")
        monkeypatch.setenv("USE_PRODUCTION_PROMPTS", "false")
        from services.prompt_config import use_production_prompts

        assert use_production_prompts() is False

    def test_note_max_tokens_by_profile(self, monkeypatch):
        monkeypatch.delenv("USE_OLLAMA", raising=False)
        monkeypatch.setenv("USE_PRODUCTION_PROMPTS", "true")
        from importlib import reload
        import services.prompt_config as pc

        reload(pc)
        assert pc.get_note_max_tokens() == 8192

        monkeypatch.setenv("USE_PRODUCTION_PROMPTS", "false")
        reload(pc)
        assert pc.get_note_max_tokens() == 2048

    def test_ollama_defaults_light_eval_when_unset(self, monkeypatch):
        monkeypatch.setenv("USE_OLLAMA", "true")
        monkeypatch.delenv("FAST_EVAL_HEURISTIC", raising=False)
        monkeypatch.delenv("EVAL_MODE", raising=False)
        monkeypatch.delenv("OLLAMA_2MIN_MODE", raising=False)
        from importlib import reload
        import services.prompt_config as pc

        reload(pc)
        assert pc.get_eval_mode() == "light"
        assert pc.use_fast_eval_heuristic() is False

    def test_ollama_2min_mode_tightens_caps(self, monkeypatch):
        monkeypatch.setenv("USE_OLLAMA", "true")
        monkeypatch.setenv("OLLAMA_2MIN_MODE", "true")
        from importlib import reload
        import services.prompt_config as pc

        reload(pc)
        assert pc.is_two_minute_mode() is True
        assert pc.use_fast_eval_heuristic() is True
        assert pc.get_note_max_tokens() == 2048
        assert pc.get_research_max_tokens() == 512
        assert pc.get_tutor_max_tokens() == 768

    def test_ollama_8k_context_caps_few_shot_example(self, monkeypatch):
        monkeypatch.setenv("USE_OLLAMA", "true")
        monkeypatch.setenv("OLLAMA_FAST_MODE", "false")
        monkeypatch.setenv("OLLAMA_2MIN_MODE", "false")
        monkeypatch.setenv("OLLAMA_NUM_CTX", "8192")
        monkeypatch.delenv("FEW_SHOT_MAX_CHARS", raising=False)
        from importlib import reload
        import services.prompt_config as pc

        reload(pc)
        assert pc.get_few_shot_max_chars() == 4500

    def test_diagram_pipeline_defaults_off(self, monkeypatch):
        monkeypatch.delenv("DIAGRAM_PIPELINE", raising=False)
        from importlib import reload
        import services.prompt_config as pc

        reload(pc)
        assert pc.use_diagram_pipeline() is False

    def test_diagram_pipeline_can_enable(self, monkeypatch):
        monkeypatch.setenv("DIAGRAM_PIPELINE", "true")
        from importlib import reload
        import services.prompt_config as pc

        reload(pc)
        assert pc.use_diagram_pipeline() is True

    def test_diagram_pipeline_can_disable(self, monkeypatch):
        monkeypatch.setenv("DIAGRAM_PIPELINE", "false")
        from importlib import reload
        import services.prompt_config as pc

        reload(pc)
        assert pc.use_diagram_pipeline() is False


class TestPromptRouting:
    def test_dev_student_prompt_truncates_research(self, monkeypatch):
        monkeypatch.setenv("USE_PRODUCTION_PROMPTS", "false")
        from prompts.student_notes_prompts import get_student_notes_user_prompt

        plan = {"topic": "T", "domain": "python", "keywords": ["a"] * 10, "subtopics": ["s"] * 8}
        prompt = get_student_notes_user_prompt(plan, "x" * 5000)
        assert "x" * 1500 in prompt
        assert "x" * 1501 not in prompt
        assert ", ".join(["a"] * 6) in prompt

    def test_production_student_prompt_full_research(self, monkeypatch):
        monkeypatch.setenv("USE_PRODUCTION_PROMPTS", "true")
        from prompts.student_notes_prompts import get_student_notes_user_prompt

        plan = {"topic": "T", "domain": "python", "keywords": ["a"] * 10, "subtopics": ["s"] * 8}
        research = "x" * 5000
        prompt = get_student_notes_user_prompt(plan, research)
        assert research in prompt
        assert ", ".join(["a"] * 10) in prompt

    def test_production_system_prompt_uses_skeleton_not_full_example(self, monkeypatch):
        monkeypatch.setenv("USE_PRODUCTION_PROMPTS", "true")
        from prompts.student_notes_prompts import get_student_notes_system_prompt

        prompt = get_student_notes_system_prompt("EXAMPLE_BLOCK", min_diagrams=4)
        assert "EXAMPLE_BLOCK" not in prompt
        assert "REFERENCE EXAMPLE" not in prompt
        assert "MERMAID RULES" in prompt
        assert "OUTPUT STRUCTURE" in prompt
        assert "flowchart LR" in prompt
        assert "Minimum 4 Mermaid" in prompt

    def test_production_genai_domain_skips_code_rule(self, monkeypatch):
        monkeypatch.setenv("USE_PRODUCTION_PROMPTS", "true")
        from prompts.student_notes_prompts import get_student_notes_system_prompt

        prompt = get_student_notes_system_prompt(domain="genai")
        assert "no code required for this domain" in prompt
        assert "Write ALL code examples in full" not in prompt

    def test_production_python_domain_includes_code_rule(self, monkeypatch):
        monkeypatch.setenv("USE_PRODUCTION_PROMPTS", "true")
        from prompts.student_notes_prompts import get_student_notes_system_prompt

        prompt = get_student_notes_system_prompt(domain="python")
        assert "Write ALL code examples in full" in prompt

    def test_tutor_supplement_system_prompt_builds_without_format_error(self, monkeypatch):
        monkeypatch.setenv("USE_PRODUCTION_PROMPTS", "true")
        monkeypatch.setenv("TUTOR_SUPPLEMENT_MODE", "true")
        from prompts.tutor_notes_prompts import get_tutor_notes_system_prompt

        prompt = get_tutor_notes_system_prompt()
        assert "section_key" in prompt
        assert "TEACHING NOTE" in prompt

    def test_dev_system_prompt_no_example(self, monkeypatch):
        monkeypatch.setenv("USE_PRODUCTION_PROMPTS", "false")
        from prompts.student_notes_prompts import get_student_notes_system_prompt

        prompt = get_student_notes_system_prompt("EXAMPLE_BLOCK")
        assert "EXAMPLE_BLOCK" not in prompt
        assert "Minimum 2 Mermaid diagrams" in prompt
