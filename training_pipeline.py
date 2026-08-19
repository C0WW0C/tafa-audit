# ============================================================
# TAFA V7 PRO — Training Pipeline (Production)
# Builds features from live candle history and trains/retrains
# the ML model automatically when enough samples exist.
# ============================================================
from __future__ import annotations

from typing import Optional
from logger import logger


class TrainingPipeline:

    MIN_SAMPLES = 150  # minimum candles before first train

    def __init__(self, model=None, quality_gate=None):
        self.model        = model
        self.quality_gate = quality_gate
        self.history: list[dict] = []
        self.train_count  = 0
        self.last_accuracy: Optional[float] = None
        logger.info("Training Pipeline initialized")

    # ──────────────────────────────────────────────────────
    # ADD SAMPLE
    # ──────────────────────────────────────────────────────

    def add_sample(self, features: list, label: str) -> None:
        """Add one labelled sample (label: 'BUY', 'SELL', 'HOLD')."""
        self.history.append({"features": features, "label": label})
        if len(self.history) > 10_000:
            self.history.pop(0)

    def add_candle(self, candle: dict, label: str) -> None:
        """Auto-extract features from OHLCV dict and add."""
        try:
            feats = [
                float(candle.get("open", 0)),
                float(candle.get("high", 0)),
                float(candle.get("low", 0)),
                float(candle.get("close", 0)),
                float(candle.get("volume", 0)),
            ]
            self.add_sample(feats, label)
        except Exception as exc:
            logger.error(f"add_candle error: {exc}")

    # ──────────────────────────────────────────────────────
    # TRAIN
    # ──────────────────────────────────────────────────────

    def train(self, X=None, y=None) -> bool:
        """Train using provided X/y or internal history."""
        if X is None or y is None:
            if len(self.history) < self.MIN_SAMPLES:
                logger.warning(
                    f"Training skipped: only {len(self.history)}/{self.MIN_SAMPLES} samples"
                )
                return False
            X = [s["features"] for s in self.history]
            y = [s["label"]    for s in self.history]

        if self.model is None:
            try:
                from model_manager import ModelManager
                self.model = ModelManager()
            except Exception as exc:
                logger.error(f"Model init failed: {exc}")
                return False

        try:
            self.model.train(X, y)
            self.train_count += 1
            logger.info(
                f"Training complete — samples={len(X)} run=#{self.train_count}"
            )

            # Validation split accuracy
            split = max(10, len(X) // 5)
            X_val, y_val = X[-split:], y[-split:]
            try:
                preds = self.model.predict(X_val)
                correct = sum(1 for p, t in zip(preds, y_val) if str(p) == str(t))
                self.last_accuracy = correct / len(y_val)
                logger.info(f"Validation accuracy: {self.last_accuracy:.2%}")
            except Exception:
                self.last_accuracy = None

            # Quality gate check
            if self.quality_gate and self.last_accuracy is not None:
                baseline = 1 / 3  # 3-class random baseline
                passed = self.quality_gate.validate(self.last_accuracy, baseline)
                if not passed:
                    logger.warning("Quality gate blocked this model version")
                    return False

            return True

        except Exception as exc:
            logger.error(f"Training error: {exc}")
            return False

    def should_retrain(self, every: int = 500) -> bool:
        return len(self.history) > 0 and len(self.history) % every == 0

    def get_history(self) -> list:
        return self.history

    def stats(self) -> dict:
        return {
            "samples": len(self.history),
            "train_count": self.train_count,
            "last_accuracy": self.last_accuracy,
        }
