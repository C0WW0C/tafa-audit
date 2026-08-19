# ============================================================
# TAFA V7 PRO — AI Brain (Production)
# Fusionne : IntelligentStrategy V4 + ML RandomForest +
#            Sentiment + Regime + Online learning
# ============================================================
from __future__ import annotations

import math
import threading
from typing import Optional

from logger import logger


class TAFABrain:
    """
    Central AI decision engine.
    Aggregates 4 signal sources with adaptive weights:
      1. IntelligentStrategy V4  (EMA/RSI/ATR — lab-calibrated)
      2. RandomForest ML         (pattern recognition)
      3. Sentiment Engine        (news/fear-greed bias)
      4. Regime Router           (meta-filter)
    """

    def __init__(self):
        self.name = "TAFA_NEURAL_BRAIN"
        self.confidence = 0.0
        self.last_signal = "HOLD"
        self.last_regime = "UNKNOWN"
        self.cycle = 0
        self._lock = threading.RLock()

        # Source weights (sum=1, updated via online learning)
        self._weights = {
            "strategy": 0.50,
            "ml":       0.25,
            "sentiment":0.10,
            "momentum": 0.15,
        }

        # Sub-components (lazy-initialized)
        self._strategy = None
        self._ml       = None
        self._sentiment= None

        # Store contribution of each source to final decision for feedback
        self._last_contributions = {k: 0.0 for k in self._weights}

        logger.info("TAFA Brain initialized")

    # ─────────────────────────────────────────────────────────
    # LAZY INIT
    # ─────────────────────────────────────────────────────────

    def _get_strategy(self):
        if self._strategy is None:
            try:
                from trading.intelligent_strategy import IntelligentStrategy
                self._strategy = IntelligentStrategy()
            except Exception as exc:
                logger.error(f"Brain: strategy load failed: {exc}")
        return self._strategy

    def _get_ml(self):
        # ML vote falls back to strategy signal (weight 0.25) until a
        # ModelManager with .predict() is provided.
        return self._ml  # always None here — intentional graceful degradation

    def _get_sentiment(self):
        if self._sentiment is None:
            try:
                from sentiment_engine import SentimentEngine
                self._sentiment = SentimentEngine()
            except Exception:
                pass
        return self._sentiment

    # ─────────────────────────────────────────────────────────
    # FEED DATA
    # ─────────────────────────────────────────────────────────

    def update_bar(self, o, h, l, c, v=0.0, confirmed: bool = True) -> None:
        with self._lock:
            strat = self._get_strategy()
            if strat:
                strat.update_bar(o, h, l, c, v, confirmed=confirmed)

    def update_price(self, price: float) -> None:
        with self._lock:
            strat = self._get_strategy()
            if strat:
                strat.update_price(price)

    def add_sentiment(self, score: float) -> None:
        with self._lock:
            sent = self._get_sentiment()
            if sent:
                sent.add(score)

    # ─────────────────────────────────────────────────────────
    # ANALYZE
    # ─────────────────────────────────────────────────────────

    def analyze(self, symbol: str, price: float) -> str:
        with self._lock:
            return self._analyze_locked(symbol, price)

    def _analyze_locked(self, symbol: str, price: float) -> str:
        self.cycle += 1
        votes: dict[str, str]    = {}
        confs: dict[str, float]  = {}

        # ── 1. IntelligentStrategy V4
        strat = self._get_strategy()
        if strat:
            sig = strat.analyze(symbol, price, already_updated=False)
            votes["strategy"] = sig
            confs["strategy"] = getattr(strat, "last_confidence", 0.5)
            self.last_regime = getattr(strat, "last_regime", "UNKNOWN")
        else:
            votes["strategy"] = "HOLD"
            confs["strategy"] = 0.0

        # ── 2. ML classifier
        ml = self._get_ml()
        if ml and strat and len(getattr(strat, "closes", [])) >= 20:
            try:
                features = self._build_features(strat)
                pred = ml.predict([features])
                ml_sig = str(pred[0]).upper() if pred is not None else "HOLD"
                if ml_sig not in ("BUY", "SELL", "HOLD"):
                    ml_sig = "HOLD"
                votes["ml"] = ml_sig
                confs["ml"] = 0.6
            except Exception:
                votes["ml"] = votes["strategy"]
                confs["ml"] = 0.3
        else:
            votes["ml"] = votes["strategy"]
            confs["ml"] = 0.3

        # ── 3. Sentiment
        sent = self._get_sentiment()
        if sent:
            bias = sent.bias()
            votes["sentiment"] = "BUY" if bias == "POSITIVE" else "SELL" if bias == "NEGATIVE" else "HOLD"
            confs["sentiment"] = 0.5
        else:
            votes["sentiment"] = "HOLD"
            confs["sentiment"] = 0.0

        # ── 4. Momentum (price vs 10-bar SMA)
        if strat and len(getattr(strat, "closes", [])) >= 10:
            closes = strat.closes
            sma10 = sum(closes[-10:]) / 10
            if price > sma10 * 1.003:
                votes["momentum"] = "BUY"
                confs["momentum"] = 0.55
            elif price < sma10 * 0.997:
                votes["momentum"] = "SELL"
                confs["momentum"] = 0.55
            else:
                votes["momentum"] = "HOLD"
                confs["momentum"] = 0.3
        else:
            votes["momentum"] = "HOLD"
            confs["momentum"] = 0.3

        # ── Regime gate
        if self.last_regime == "TREND_DOWN":
            for k in votes:
                if votes[k] == "BUY":
                    votes[k] = "HOLD"

        # ── Weighted vote
        buy = sell = hold = 0.0
        contributions = {src: 0.0 for src in self._weights}
        for src, sig in votes.items():
            w = self._weights.get(src, 0.1)
            c = confs.get(src, 0.5)
            weighted = w * c
            contributions[src] = weighted
            if sig == "BUY":
                buy += weighted
            elif sig == "SELL":
                sell += weighted
            else:
                hold += weighted

        total = buy + sell + hold or 1.0
        buy /= total
        sell /= total
        contrib_total = sum(contributions.values()) or 1.0
        for src in contributions:
            contributions[src] /= contrib_total
        self._last_contributions = contributions

        # Decision threshold
        if buy >= 0.30 and buy > sell * 1.2:
            signal, conf = "BUY", buy
        elif sell >= 0.25 and sell > buy * 1.1:
            signal, conf = "SELL", sell
        else:
            signal, conf = "HOLD", max(buy, sell, 0.2)

        self.last_signal = signal
        self.confidence  = round(conf, 3)
        return signal

    # ─────────────────────────────────────────────────────────
    # FEEDBACK — online weight adaptation
    # ─────────────────────────────────────────────────────────

    def feedback(self, pnl: float, risk_unit: float = 1.0) -> None:
        with self._lock:
            self._feedback_locked(pnl, risk_unit)

    def _feedback_locked(self, pnl: float, risk_unit: float = 1.0) -> None:
        if not self._strategy:
            return
        strat = self._get_strategy()
        if hasattr(strat, "feedback"):
            experts = getattr(strat, "last_experts", {})
            strat.feedback(experts, self.last_signal, pnl, risk_unit)

        reward = max(-1.0, min(1.0, pnl / max(abs(risk_unit), 1e-9)))
        eta = 0.05
        total_contrib = sum(self._last_contributions.values()) or 1.0
        for src, contrib in self._last_contributions.items():
            if contrib > 0.01:
                factor = math.exp(eta * reward * contrib)
                self._weights[src] *= factor

        total = sum(self._weights.values()) or 1.0
        for src in self._weights:
            self._weights[src] = max(0.05, self._weights[src] / total)
        total = sum(self._weights.values()) or 1.0
        for src in self._weights:
            self._weights[src] /= total

    # ─────────────────────────────────────────────────────────
    # FEATURE BUILDER for ML
    # ─────────────────────────────────────────────────────────

    @staticmethod
    def _build_features(strat) -> list[float]:
        closes  = strat.closes[-50:] if len(strat.closes) >= 50 else strat.closes
        highs   = strat.highs[-50:]  if len(strat.highs)  >= 50 else strat.highs
        lows    = strat.lows[-50:]   if len(strat.lows)   >= 50 else strat.lows
        volumes = strat.volumes[-50:]if len(strat.volumes)>= 50 else strat.volumes

        def safe(v): return float(v) if v is not None else 0.0

        from trading.intelligent_strategy import ema, rsi, atr_last
        f = [
            safe(ema(closes, 9)),
            safe(ema(closes, 21)),
            safe(ema(closes, 50)) if len(closes) >= 50 else 0.0,
            safe(rsi(closes, 14)),
            safe(atr_last(highs, lows, closes, 14)),
            closes[-1] if closes else 0.0,
            sum(volumes[-5:]) / 5 if len(volumes) >= 5 else 0.0,
            (closes[-1] - closes[-5]) / closes[-5] if len(closes) >= 5 and closes[-5] else 0.0,
            (closes[-1] - closes[-10]) / closes[-10] if len(closes) >= 10 and closes[-10] else 0.0,
        ]
        return f

    def analyze_data(self, market_data: dict) -> str:
        with self._lock:
            price = market_data.get("price") or market_data.get("close")
            symbol = market_data.get("symbol", "BTC-USDC")
            if price:
                return self._analyze_locked(symbol, float(price))
            return "HOLD"

    def get_confidence(self) -> float:
        with self._lock:
            return self.confidence

    def get_state(self) -> dict:
        with self._lock:
            strat = self._get_strategy()
            return {
                "name": self.name,
                "signal": self.last_signal,
                "confidence": self.confidence,
                "regime": self.last_regime,
                "cycle": self.cycle,
                "weights": {k: round(v, 3) for k, v in self._weights.items()},
                "bars": len(getattr(strat, "closes", [])) if strat else 0,
            }


brain = TAFABrain()