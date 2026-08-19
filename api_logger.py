# ============================================================
# TAFA V7 PRO
# API LOGGER FINAL (version corrigée)
# ============================================================

from datetime import datetime, timezone
import threading


class APILogger:
    """Thread-safe API call logger with bounded memory."""

    def __init__(self, max_entries: int = 5000):
        self.logs = []
        self.max_entries = max_entries
        self._lock = threading.RLock()   # ✅ thread safety

    # ========================================================
    # ADD LOG
    # ========================================================

    def add(self, action: str, status: str, message: str = "") -> None:
        """Ajoute une entrée de log avec horodatage UTC."""
        status = str(status).upper()
        with self._lock:
            self.logs.append(
                {
                    "time": datetime.now(timezone.utc).isoformat(),
                    "action": action,
                    "status": status,
                    "message": message,
                }
            )
            # Garde une taille raisonnable
            if len(self.logs) > self.max_entries:
                self.logs = self.logs[-self.max_entries:]

    # ========================================================
    # GET
    # ========================================================

    def get_logs(self, limit: int = 100) -> list:
        """Retourne les derniers logs (copie)."""
        with self._lock:
            return list(self.logs[-limit:])

    # ========================================================
    # CLEAR
    # ========================================================

    def clear(self) -> None:
        """Vide tous les logs."""
        with self._lock:
            self.logs.clear()