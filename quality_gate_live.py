# ============================================================
# TAFA V10 — Live quality gate (paper-first, still closed-bars)
# ============================================================
from __future__ import annotations

import threading
from dataclasses import dataclass, field


@dataclass
class SignalQuality:
    # Tuned so paper sessions actually fire trades; LIVE can raise via runtime_config
    min_confidence: float = 0.40
    min_bars: int = 40
    block_regimes: tuple = ("TREND_DOWN",)  # UNKNOWN / RANGE / TREND_UP allowed
    require_volume_ok: bool = False

    # Thread safety (dashboard may update settings while engine reads)
    _lock: threading.RLock = field(default_factory=threading.RLock, repr=False)

    def configure(self, cfg: dict) -> None:
        """Apply runtime settings."""
        with self._lock:
            if "min_conf" in cfg:
                self.min_confidence = max(0.0, min(1.0, float(cfg["min_conf"])))
            if "min_bars" in cfg:
                self.min_bars = max(1, int(cfg["min_bars"]))
            if "block_regimes" in cfg:
                if isinstance(cfg["block_regimes"], (list, tuple)):
                    self.block_regimes = tuple(str(r).upper() for r in cfg["block_regimes"])

    def accept(
        self,
        signal: str,
        confidence: float,
        regime: str,
        bars: int,
        volume_ok: bool = True,
    ) -> tuple[bool, str]:
        with self._lock:
            sig = (str(signal or "HOLD")).upper()
            if sig not in ("BUY", "SELL"):
                return False, "not_actionable"

            try:
                conf = float(confidence)
            except (TypeError, ValueError):
                return False, "invalid_confidence"
            try:
                bar_count = int(bars)
            except (TypeError, ValueError):
                return False, "invalid_bars"

            if bar_count < self.min_bars:
                return False, f"warmup bars={bar_count}<{self.min_bars}"
            if conf < self.min_confidence:
                return False, f"low_conf {conf:.2f}<{self.min_confidence}"
            if sig == "BUY" and str(regime).upper() in self.block_regimes:
                return False, f"regime_block {regime}"
            if self.require_volume_ok and not volume_ok:
                return False, "volume_filter"
            return True, "pass"


gate = SignalQuality()