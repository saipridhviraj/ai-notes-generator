"""Tests for Mermaid repair-rate metrics."""

from utils.mermaid_metrics import get_mermaid_metrics, reset_mermaid_metrics


def test_metrics_repair_rate():
    reset_mermaid_metrics()
    m = get_mermaid_metrics()
    m.generated = 10
    m.llm_repair_calls = 2
    assert m.repair_rate == 0.2
    snap = m.snapshot()
    assert snap["generated"] == 10
    assert snap["repaired"] == 2
    assert snap["repair_rate"] == 0.2
