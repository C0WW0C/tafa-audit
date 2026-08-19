# ============================================================
# TAFA V7 PRO — AI Quality Gate
# ============================================================
"""Gate that blocks model deployment when accuracy or edge is too low."""

from __future__ import annotations

from logger import logger


class AIQualityGate:
    """Validate ML model quality before live use."""

    def __init__(self, min_accuracy: float = 0.60, min_edge: float = 0.05) -> None:
        self.min_accuracy = min_accuracy
        self.min_edge = min_edge
        self.status = False

    def validate(self, accuracy: float, baseline: float) -> bool:
        """Return True when accuracy and edge (accuracy - baseline) meet thresholds."""
        edge = accuracy - baseline
        if accuracy >= self.min_accuracy and edge >= self.min_edge:
            self.status = True
            logger.info("AI QUALITY GATE PASSED")
            return True
        self.status = False
        logger.warning("AI QUALITY GATE BLOCKED")
        return False

    def is_ready(self) -> bool:
        return self.status
