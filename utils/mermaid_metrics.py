"""In-process Mermaid pipeline metrics (repair rate tracking)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class MermaidMetrics:
    """Cumulative counters for Mermaid enforce passes."""

    generated: int = 0
    passed_after_normalize: int = 0
    llm_repair_calls: int = 0
    failed: int = 0

    def reset(self) -> None:
        self.generated = 0
        self.passed_after_normalize = 0
        self.llm_repair_calls = 0
        self.failed = 0

    @property
    def repaired(self) -> int:
        return self.llm_repair_calls

    @property
    def repair_rate(self) -> float:
        if self.generated <= 0:
            return 0.0
        return self.llm_repair_calls / self.generated

    def snapshot(self) -> dict[str, float | int]:
        return {
            "generated": self.generated,
            "passed_after_normalize": self.passed_after_normalize,
            "repaired": self.repaired,
            "failed": self.failed,
            "repair_rate": round(self.repair_rate, 4),
        }

    def log_summary(self, *, context: str = "") -> None:
        data = self.snapshot()
        prefix = f"[mermaid_metrics] {context} " if context else "[mermaid_metrics] "
        rate_pct = data["repair_rate"] * 100 if isinstance(data["repair_rate"], float) else 0
        logger.info(
            "%sgenerated=%s normalized_ok=%s repaired=%s failed=%s repair_rate=%.1f%%",
            prefix,
            data["generated"],
            data["passed_after_normalize"],
            data["repaired"],
            data["failed"],
            rate_pct,
        )


_metrics = MermaidMetrics()


def get_mermaid_metrics() -> MermaidMetrics:
    return _metrics


def reset_mermaid_metrics() -> None:
    _metrics.reset()
