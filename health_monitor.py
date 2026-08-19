# ============================================================
# TAFA V7 PRO
# HEALTH MONITOR FINAL (version corrigée)
# ============================================================

from datetime import datetime, timezone
import threading


class HealthMonitor:
    """Simple thread-safe health status registry."""

    VALID_STATES = {"OK", "WARN", "ERROR", "UNKNOWN"}

    def __init__(self):
        self.status = {}
        self._lock = threading.RLock()   # ✅ thread safety

    # ========================================================
    # UPDATE
    # ========================================================

    def update(self, module: str, state: str) -> None:
        """Met à jour l'état d'un module avec horodatage UTC."""
        state = str(state).upper()
        if state not in self.VALID_STATES:
            state = "UNKNOWN"
        with self._lock:
            self.status[module] = {
                "state": state,
                "time": datetime.now(timezone.utc).isoformat(),
            }

    # ========================================================
    # CHECK
    # ========================================================

    def check(self) -> dict:
        """Retourne une copie de l'état complet."""
        with self._lock:
            return dict(self.status)

    # ========================================================
    # ONLINE
    # ========================================================

    def is_online(self, module: str, max_age_seconds: float = 60.0) -> bool:
        """Vérifie qu'un module est 'OK' et que sa dernière mise à jour est récente."""
        with self._lock:
            if module not in self.status:
                return False
            entry = self.status[module]
            if entry.get("state") != "OK":
                return False

            try:
                ts = datetime.fromisoformat(entry["time"])
                age = (datetime.now(timezone.utc) - ts).total_seconds()
            except Exception:
                return False

            return age <= max_age_seconds