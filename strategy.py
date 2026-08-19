# ============================================================
# TAFA V7 PRO — Strategy facade (Intelligent V3)
# ============================================================

from trading.intelligent_strategy import IntelligentStrategy


class Strategy(IntelligentStrategy):
    """Backward-compatible name used by the engine."""

    def __init__(self):
        super().__init__()
