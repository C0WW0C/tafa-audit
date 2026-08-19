# ============================================================
# TAFA V7 PRO
# DCA MANAGER FINAL
# ============================================================

import threading
from logger import logger


class DCAManager:
    """Gestion simple de Dollar-Cost Averaging (DCA) sur position existante."""

    def __init__(self, max_dca_orders: int = 3, dca_step_pct: float = 0.02):
        self.max_dca_orders = max_dca_orders
        self.dca_step_pct = dca_step_pct
        self.dca_count = 0
        self.last_entry = 0.0
        self._lock = threading.RLock()
        logger.info("DCA Manager initialized")

    def reset(self):
        """Réinitialise le compteur DCA après fermeture de position."""
        with self._lock:
            self.dca_count = 0
            self.last_entry = 0.0

    def should_dca(self, current_price: float) -> bool:
        """
        Vérifie si un DCA est nécessaire.

        Retourne True si le prix a baissé de plus de dca_step_pct
        depuis la dernière entrée et que le nombre max n'est pas atteint.
        """
        with self._lock:
            if self.dca_count >= self.max_dca_orders:
                return False
            if self.last_entry <= 0:
                return False
            return (self.last_entry - current_price) / self.last_entry >= self.dca_step_pct

    def register_entry(self, price: float):
        """Enregistre une nouvelle entrée (utile pour le prochain DCA)."""
        with self._lock:
            self.last_entry = float(price)
            self.dca_count += 1