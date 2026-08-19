# ============================================================
# TAFA V10 — Circuit Breaker (fail-safe production) - version corrigée
# ============================================================
from __future__ import annotations

import time
import threading
from dataclasses import dataclass, field
from typing import List


@dataclass
class CircuitBreaker:
    """Hard stops before the account melts."""

    max_drawdown: float = 0.12          # 12% from peak
    max_daily_loss: float = 0.05        # 5% of day start
    max_consec_losses: int = 5
    max_errors_per_hour: int = 20
    cooldown_s: float = 300.0           # 5 min after trip

    peak_equity: float = 0.0
    day_start_equity: float = 0.0
    day_key: str = ""
    consec_losses: int = 0
    error_ts: List[float] = field(default_factory=list)
    tripped: bool = False
    trip_reason: str = ""
    trip_until: float = 0.0

    # Thread safety
    _lock: threading.RLock = field(default_factory=threading.RLock, repr=False)

    def reset_day_if_needed(self, equity: float) -> None:
        key = time.strftime("%Y-%m-%d")
        if key != self.day_key:
            self.day_key = key
            self.day_start_equity = equity
            self.consec_losses = 0
            # ✅ FIX: purge les erreurs de la veille pour repartir proprement chaque jour
            self.error_ts = []

    def update_equity(self, equity: float) -> None:
        with self._lock:
            self.reset_day_if_needed(equity)
            if equity > self.peak_equity:
                self.peak_equity = equity
            if self.day_start_equity <= 0:
                self.day_start_equity = equity

    def record_trade(self, pnl: float) -> None:
        with self._lock:
            if pnl < 0:
                self.consec_losses += 1
            else:
                self.consec_losses = 0

    def record_error(self) -> None:
        now = time.monotonic()
        with self._lock:
            self.error_ts = [t for t in self.error_ts if now - t < 3600]
            self.error_ts.append(now)

    def allow(self, equity: float) -> tuple[bool, str]:
        with self._lock:
            now = time.monotonic()

            # Cooldown check
            if self.tripped:
                if now < self.trip_until:
                    return False, self.trip_reason or "circuit_tripped"
                else:
                    # Cooldown expired: reset trip state
                    self.tripped = False
                    self.trip_reason = ""

            self.update_equity(equity)

            # Drawdown
            peak = max(self.peak_equity, equity, 1e-9)
            dd = (peak - equity) / peak
            if dd >= self.max_drawdown:
                return self._trip(f"MAX_DRAWDOWN {dd:.1%} >= {self.max_drawdown:.0%}")

            # Daily loss
            day0 = max(self.day_start_equity, 1e-9)
            daily_loss = (day0 - equity) / day0
            if daily_loss >= self.max_daily_loss:
                return self._trip(f"MAX_DAILY_LOSS {daily_loss:.1%}")

            # Consecutive losses
            if self.consec_losses >= self.max_consec_losses:
                return self._trip(f"CONSEC_LOSSES {self.consec_losses}")

            # Error rate
            errs = sum(1 for t in self.error_ts if now - t < 3600)
            if errs >= self.max_errors_per_hour:
                return self._trip(f"ERROR_RATE {errs}/h")

            return True, "ok"

    def _trip(self, reason: str) -> tuple[bool, str]:
        self.tripped = True
        self.trip_reason = reason
        self.trip_until = time.monotonic() + self.cooldown_s
        return False, reason

    def reset(self) -> None:
        """Réinitialise complètement le circuit breaker (tests, redémarrage propre)."""
        with self._lock:
            self.peak_equity = 0.0
            self.day_start_equity = 0.0
            self.day_key = ""
            self.consec_losses = 0
            self.error_ts = []
            self.tripped = False
            self.trip_reason = ""
            self.trip_until = 0.0

    def status(self) -> dict:
        with self._lock:
            now = time.monotonic()
            return {
                "tripped": self.tripped,
                "reason": self.trip_reason,
                "peak_equity": round(self.peak_equity, 2),
                "day_start_equity": round(self.day_start_equity, 2),
                "consec_losses": self.consec_losses,
                "cooldown_left_s": max(0, int(self.trip_until - now)) if self.tripped else 0,
                "errors_last_hour": sum(1 for t in self.error_ts if now - t < 3600),
            }


# Singleton
breaker = CircuitBreaker()