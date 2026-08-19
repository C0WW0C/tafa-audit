"""TAFA Neural Parent Brain.

Meta-controller for V10: it does not place orders.  It combines the existing
strategy signal, regime, expert agreement, volatility and risk state, then
returns a conservative BUY/SELL/HOLD decision.  The controller is deliberately
model-agnostic: no synthetic training data and no fake accuracy metrics.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class ParentDecision:
    signal: str = "HOLD"
    confidence: float = 0.0
    regime: str = "UNKNOWN"
    strategy: str = "TAFA_INTEL_V6"
    reason: str = ""
    scores: Dict[str, float] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "signal": self.signal,
            "confidence": round(self.confidence, 3),
            "regime": self.regime,
            "strategy": self.strategy,
            "reason": self.reason,
            "scores": {k: round(float(v), 3) for k, v in self.scores.items()},
        }


class NeuralParentBrain:
    """Meta-layer sitting above V10's existing strategy.

    The parent can veto a signal, but never bypasses the downstream risk
    manager or live quality gate.  Feedback changes only meta weights and is
    bounded to prevent runaway adaptation.
    """

    def __init__(self, min_confidence: float = 0.40):
        self.name = "TAFA_NEURAL_PARENT_BRAIN_V1"
        self.min_confidence = float(min_confidence)
        self.last = ParentDecision()
        self.cycles = 0
        self._weights = {
            "base_signal": 0.42,
            "regime": 0.23,
            "expert_agreement": 0.20,
            "momentum": 0.10,
            "volatility": 0.05,
        }
        self._eta = 0.02
        self._config_signature = None

    @staticmethod
    def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
        return max(lo, min(hi, float(x)))

    def decide(self, strategy: Any, base_signal: str, price: float,
               risk_ok: bool = True) -> ParentDecision:
        self.cycles += 1
        signal = str(base_signal or "HOLD").upper()
        regime = str(getattr(strategy, "last_regime", "UNKNOWN") or "UNKNOWN")
        base_conf = self._clamp(getattr(strategy, "last_confidence", 0.0) or 0.0)
        experts = getattr(strategy, "last_experts", {}) or {}
        closes = list(getattr(strategy, "closes", []) or [])
        atr = getattr(strategy, "last_atr", None)

        buys = sum(1 for v in experts.values() if str(v).upper() == "BUY")
        sells = sum(1 for v in experts.values() if str(v).upper() == "SELL")
        total = max(1, len(experts))
        agreement = max(buys, sells) / total

        momentum = 0.5
        if len(closes) >= 10 and closes[-10]:
            change = (closes[-1] - closes[-10]) / abs(closes[-10])
            momentum = self._clamp(0.5 + change * 8.0)

        volatility = 0.0
        if atr and price:
            volatility = self._clamp(float(atr) / float(price) * 12.0)

        regime_score = {
            "TREND_UP": 1.0,
            "RANGE": 0.55,
            "TREND_DOWN": 0.0,
            "VOLATILE": 0.15,
            "UNKNOWN": 0.35,
        }.get(regime, 0.35)

        scores = {
            "base": base_conf,
            "regime": regime_score,
            "agreement": agreement,
            "momentum": momentum,
            "volatility": volatility,
        }
        confidence = (
            self._weights["base_signal"] * base_conf
            + self._weights["regime"] * regime_score
            + self._weights["expert_agreement"] * agreement
            + self._weights["momentum"] * (momentum if signal == "BUY" else 1.0 - momentum)
            + self._weights["volatility"] * (1.0 - volatility)
        )
        confidence = self._clamp(confidence)

        reason = "accepted"
        final = signal
        if not risk_ok:
            final, reason = "HOLD", "risk_manager_block"
        elif signal == "BUY" and regime == "TREND_DOWN":
            final, reason = "HOLD", f"regime_veto:{regime}"
        elif signal == "BUY" and confidence < self.min_confidence:
            final, reason = "HOLD", "parent_confidence_below_threshold"
        elif signal == "SELL" and regime == "TREND_UP" and confidence < 0.30:
            final, reason = "HOLD", "weak_exit_signal"
        elif signal not in ("BUY", "SELL", "HOLD"):
            final, reason = "HOLD", "invalid_signal"

        self.last = ParentDecision(
            signal=final,
            confidence=confidence,
            regime=regime,
            strategy=getattr(strategy, "name", "TAFA_INTEL_V6"),
            reason=reason,
            scores=scores,
        )
        return self.last

    def apply_config(self, cfg: Dict[str, Any]) -> None:
        """Apply bounded paper-runtime meta parameters without resetting on every cycle."""
        keys = ["parent_brain_eta"] + [f"parent_weight_{name}" for name in self._weights]
        signature = tuple((key, cfg.get(key)) for key in keys if key in cfg)
        if signature == self._config_signature:
            return
        if "parent_brain_eta" in cfg:
            self._eta = self._clamp(cfg["parent_brain_eta"], 0.001, 0.1)
        for name in self._weights:
            key = f"parent_weight_{name}"
            if key in cfg:
                self._weights[name] = self._clamp(cfg[key])
        total = sum(self._weights.values())
        if total <= 0:
            self._weights = {name: 0.0 for name in self._weights}
            self._weights["base_signal"] = 1.0
        else:
            self._weights = {name: value / total for name, value in self._weights.items()}
        self._config_signature = signature

    def feedback(self, pnl: float) -> None:
        """Small bounded online adaptation; no synthetic labels are used."""
        reward = self._clamp((float(pnl) + 1.0) / 2.0) * 2.0 - 1.0
        eta = self._eta
        if reward > 0:
            self._weights["base_signal"] += eta
            self._weights["expert_agreement"] += eta * 0.5
        else:
            self._weights["regime"] += eta
            self._weights["volatility"] += eta * 0.5
        total = sum(self._weights.values()) or 1.0
        for k in self._weights:
            self._weights[k] = self._clamp(self._weights[k] / total, 0.03, 0.70)
        total = sum(self._weights.values()) or 1.0
        for k in self._weights:
            self._weights[k] /= total

    def status(self) -> dict:
        return {
            "name": self.name,
            "cycles": self.cycles,
            "weights": {k: round(v, 3) for k, v in self._weights.items()},
            "eta": self._eta,
            "last": self.last.as_dict(),
            "synthetic_training": False,
        }
