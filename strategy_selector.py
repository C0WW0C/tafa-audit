# ============================================================
# TAFA V7 PRO
# STRATEGY SELECTOR FINAL (version corrigée)
# ============================================================

import threading
from logger import logger


class StrategySelector:
    def __init__(self, registry=None):
        self.registry = registry or {}
        self._lock = threading.RLock()
        logger.info("Strategy Selector initialized")

    def select(self, regime: str):
        """Retourne la stratégie correspondant au régime de marché."""
        if not self.registry:
            logger.warning("StrategySelector: registre vide")
            return None

        regime = str(regime).strip().upper()

        mapping = {
            "TREND_UP": "GRID",
            "TREND_DOWN": "DCA",
            "RANGE": "ADAPTIVE_GRID",
        }

        key = mapping.get(regime)
        if key is None:
            logger.warning(f"StrategySelector: régime inconnu '{regime}'")
            return None

        strategy = self.registry.get(key)
        if strategy is None:
            logger.warning(f"StrategySelector: stratégie '{key}' absente du registre")

        return strategy