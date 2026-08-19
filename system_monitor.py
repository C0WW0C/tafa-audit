# ============================================================
# TAFA V7 PRO
# SYSTEM MONITOR (version corrigée)
# ============================================================

import os
import time
import platform
import threading
from datetime import datetime, timezone
from pathlib import Path

try:
    import psutil
except ImportError:
    psutil = None

from logger import logger


class SystemMonitor:
    def __init__(self):
        self.running = False
        self.stats = {
            "cpu": 0.0,
            "memory": 0.0,
            "disk": 0.0,
            "threads": 0,
            "uptime": 0,
            "platform": platform.platform(),
            "python": platform.python_version(),
            "last_update": None,
        }
        self.start_time = time.time()
        self._lock = threading.RLock()          # ✅ thread safety
        self._stop_event = threading.Event()    # ✅ arrêt réactif
        self._thread = None
        logger.info("System Monitor initialized")

    # =====================================================
    # UPDATE
    # =====================================================

    def update(self):
        with self._lock:
            if psutil:
                self.stats["cpu"] = psutil.cpu_percent(interval=None)
                self.stats["memory"] = psutil.virtual_memory().percent
                try:
                    # Point de montage adapté à l'OS
                    if os.name == "nt":
                        self.stats["disk"] = psutil.disk_usage(str(Path(__file__).anchor)).percent
                    else:
                        self.stats["disk"] = psutil.disk_usage("/").percent
                except Exception:
                    self.stats["disk"] = 0.0

            self.stats["threads"] = threading.active_count()
            self.stats["uptime"] = round(time.time() - self.start_time, 2)
            self.stats["last_update"] = datetime.now(timezone.utc).isoformat()

    # =====================================================
    # GET
    # =====================================================

    def get_stats(self):
        self.update()
        with self._lock:
            return dict(self.stats)

    # =====================================================
    # HEALTH
    # =====================================================

    def health(self):
        self.update()
        with self._lock:
            if self.stats["cpu"] > 95:
                return "CRITICAL"
            if self.stats["memory"] > 90:
                return "WARNING"
            return "OK"

    # =====================================================
    # LOOP
    # =====================================================

    def _loop(self, interval: float):
        while not self._stop_event.is_set():
            self.update()
            self._stop_event.wait(interval)

    def start(self, interval: float = 5):
        """Démarre la surveillance dans un thread en arrière-plan."""
        if self.running:
            return
        self.running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, args=(interval,), daemon=True, name="SystemMonitor")
        self._thread.start()
        logger.info(f"System Monitor loop started (interval={interval}s)")

    def stop(self):
        """Arrête la boucle de surveillance."""
        self.running = False
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        logger.info("System Monitor stopped")