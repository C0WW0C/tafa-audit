# ============================================================
# TAFA V7 PRO — Inference Engine (Production)
# ============================================================
from __future__ import annotations
from typing import Optional
from logger import logger


class InferenceEngine:
    """
    Wraps any sklearn-compatible model.
    Returns calibrated confidence from predict_proba when available.
    """

    def __init__(self, model=None):
        self.model = model
        self._calls = 0
        logger.info("Inference Engine initialized")

    def predict(self, features: list) -> dict:
        if self.model is None:
            return {"signal": "HOLD", "confidence": 0.0, "source": "no_model"}

        self._calls += 1
        try:
            raw = self.model.predict([features] if not isinstance(features[0], list) else features)
            signal = str(raw[0]).upper()
            if signal not in ("BUY", "SELL", "HOLD"):
                signal = "HOLD"

            # Calibrated confidence via predict_proba
            confidence = 0.5
            if hasattr(self.model, "predict_proba"):
                try:
                    proba = self.model.predict_proba(
                        [features] if not isinstance(features[0], list) else features
                    )[0]
                    confidence = float(max(proba))
                except Exception:
                    pass

            return {
                "signal": signal,
                "confidence": round(confidence, 3),
                "source": "ml",
                "calls": self._calls,
            }

        except Exception as exc:
            logger.error(f"Inference error: {exc}")
            return {"signal": "HOLD", "confidence": 0.0, "source": "error"}

    def is_ready(self) -> bool:
        return self.model is not None
