# ============================================================
# TAFA V7 PRO
# STRATEGY REGISTRY FINAL (version corrigée)
# ============================================================

import threading
from logger import logger


class StrategyRegistry:
    def __init__(self):
        self.strategies = {}
        self._lock = threading.RLock()
        logger.info("Strategy Registry initialized")

    def register(self, name: str, strategy) -> None:
        """Enregistre une stratégie sous un nom normalisé."""
        key = str(name).strip().upper()
        with self._lock:
            self.strategies[key] = strategy
        logger.info(f"Strategy registered: {key}")

    def get(self, name: str):
        """Retourne une stratégie par nom, ou None si absente."""
        key = str(name).strip().upper()
        with self._lock:
            return self.strategies.get(key)

    def list(self):
        """Retourne la liste des noms de stratégies enregistrées."""
        with self._lock:
            return list(self.strategies.keys())