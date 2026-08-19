"""TAFA foundation-model consensus gate.

This module never downloads weights, never fabricates a forecast and never
places an order.  It exchanges normalized OHLCV payloads with two separately
hosted inference endpoints, then fails closed to HOLD unless Kronos-base and
Chronos-2 agree with TAFA's existing strategy signal.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict, List, Optional


VALID_SIGNALS = {"BUY", "SELL", "HOLD"}


@dataclass
class ModelVote:
    model: str
    signal: str = "HOLD"
    confidence: float = 0.0
    state: str = "unavailable"
    detail: str = ""
    latency_ms: int = 0

    def public(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FoundationDecision:
    signal: str = "HOLD"
    confidence: float = 0.0
    accepted: bool = False
    state: str = "disabled"
    reason: str = "foundation_models_disabled"
    kronos: Optional[ModelVote] = None
    chronos: Optional[ModelVote] = None
    sampled_bars: int = 0

    def public(self) -> Dict[str, Any]:
        return {
            "enabled": self.state not in {"disabled", "paper_only_blocked"},
            "state": self.state,
            "signal": self.signal,
            "confidence": round(float(self.confidence), 3),
            "accepted": bool(self.accepted),
            "reason": self.reason,
            "sampled_bars": self.sampled_bars,
            "kronos": self.kronos.public() if self.kronos else None,
            "chronos": self.chronos.public() if self.chronos else None,
        }


Transport = Callable[[str, Dict[str, Any], float], Dict[str, Any]]


class HttpForecastClient:
    """Minimal, dependency-free client for a dedicated model serving endpoint.

    The endpoint contract is intentionally simple: it receives
    ``{model, symbol, timeframe, candles}`` and returns at least
    ``{signal: BUY|SELL|HOLD, confidence: 0..1}``.  It keeps model hosting
    separate from TAFA, so credentials and accelerator resources never enter
    the dashboard or the trading process.
    """

    def __init__(
        self,
        model: str,
        endpoint_env: str,
        *,
        endpoint: Optional[str] = None,
        transport: Optional[Transport] = None,
    ) -> None:
        self.model = model
        self.endpoint_env = endpoint_env
        self.endpoint = (endpoint if endpoint is not None else os.getenv(endpoint_env, "")).strip()
        self.transport = transport or self._post_json

    @staticmethod
    def _post_json(endpoint: str, payload: Dict[str, Any], timeout_s: float) -> Dict[str, Any]:
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        request = urllib.request.Request(
            endpoint,
            data=data,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            parsed = json.loads(response.read().decode("utf-8"))
        if not isinstance(parsed, dict):
            raise ValueError("réponse de modèle invalide")
        return parsed

    def forecast(self, *, symbol: str, timeframe: str, candles: List[Dict[str, float]], timeout_s: float) -> ModelVote:
        # config.py loads .env lazily. Resolve a previously absent endpoint at
        # call time as well, so a paper profile is honored after TAFA startup.
        endpoint = self.endpoint or os.getenv(self.endpoint_env, "").strip()
        if not endpoint:
            return ModelVote(self.model, state="not_configured", detail="endpoint_absent")
        if not candles:
            return ModelVote(self.model, state="insufficient_data", detail="no_candles")

        started = time.monotonic()
        payload = {
            "model": self.model,
            "symbol": symbol,
            "timeframe": timeframe,
            "candles": candles,
        }
        try:
            raw = self.transport(endpoint, payload, timeout_s)
            signal = str(raw.get("signal", "HOLD")).upper().strip()
            if signal not in VALID_SIGNALS:
                raise ValueError("signal de modèle invalide")
            confidence = max(0.0, min(1.0, float(raw.get("confidence", 0.0))))
            return ModelVote(
                self.model,
                signal=signal,
                confidence=confidence,
                state="ready",
                latency_ms=round((time.monotonic() - started) * 1000),
            )
        except (urllib.error.URLError, TimeoutError, ValueError, TypeError, json.JSONDecodeError) as exc:
            return ModelVote(
                self.model,
                state="error",
                detail=str(exc)[:160],
                latency_ms=round((time.monotonic() - started) * 1000),
            )


class FoundationModelConsensus:
    """Require a conservative model consensus before a paper-trade signal.

    The original TAFA strategy remains the source of market context.  When
    enabled, the candidate must be BUY or SELL, be supported by both external
    models, exceed the configured confidence floor, and match TAFA's original
    strategy.  Any missing endpoint, timeout or disagreement returns HOLD.
    """

    def __init__(
        self,
        *,
        enabled: Optional[bool] = None,
        min_confidence: Optional[float] = None,
        max_context: Optional[int] = None,
        timeout_s: Optional[float] = None,
        paper_only: Optional[bool] = None,
        kronos: Optional[HttpForecastClient] = None,
        chronos: Optional[HttpForecastClient] = None,
    ) -> None:
        self._enabled_override = enabled
        self._min_confidence_override = min_confidence
        self._max_context_override = max_context
        self._timeout_override = timeout_s
        self._paper_only_override = paper_only
        self.kronos = kronos or HttpForecastClient("NeoQuasar/Kronos-base", "TAFA_KRONOS_ENDPOINT")
        self.chronos = chronos or HttpForecastClient("amazon/chronos-2", "TAFA_CHRONOS_ENDPOINT")
        self.last = FoundationDecision()

    @staticmethod
    def _bool(value: Any, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return default

    def _settings(self) -> Dict[str, Any]:
        cfg: Dict[str, Any] = {}
        try:
            from core.runtime_config import get_config
            cfg = get_config()
        except Exception:
            pass
        try:
            from config import PAPER_TRADING
            default_paper = bool(PAPER_TRADING)
        except Exception:
            default_paper = True
        return {
            "enabled": self._enabled_override if self._enabled_override is not None else self._bool(cfg.get("foundation_models_on"), False),
            "min_confidence": max(0.0, min(1.0, float(self._min_confidence_override if self._min_confidence_override is not None else cfg.get("foundation_min_conf", 0.70)))),
            "max_context": max(60, min(512, int(self._max_context_override if self._max_context_override is not None else cfg.get("foundation_context", 240)))),
            "timeout_s": max(0.5, min(15.0, float(self._timeout_override if self._timeout_override is not None else cfg.get("foundation_timeout_s", 4.0)))),
            "paper_only": self._paper_only_override if self._paper_only_override is not None else default_paper,
        }

    @staticmethod
    def _candles(strategy: Any, context: int) -> List[Dict[str, float]]:
        opens = list(getattr(strategy, "opens", []) or [])[-context:]
        highs = list(getattr(strategy, "highs", []) or [])[-context:]
        lows = list(getattr(strategy, "lows", []) or [])[-context:]
        closes = list(getattr(strategy, "closes", []) or [])[-context:]
        volumes = list(getattr(strategy, "volumes", []) or [])[-context:]
        size = min(len(opens), len(highs), len(lows), len(closes), len(volumes))
        if size < 60:
            return []
        return [
            {
                "open": float(opens[i]),
                "high": float(highs[i]),
                "low": float(lows[i]),
                "close": float(closes[i]),
                "volume": float(volumes[i]),
            }
            for i in range(size)
        ]

    def evaluate(self, *, symbol: str, timeframe: str, strategy: Any, candidate_signal: str) -> FoundationDecision:
        settings = self._settings()
        candidate = str(candidate_signal or "HOLD").upper()
        if not settings["enabled"]:
            self.last = FoundationDecision(state="disabled", reason="foundation_models_disabled")
            return self.last
        if not settings["paper_only"]:
            self.last = FoundationDecision(state="paper_only_blocked", reason="foundation_models_are_paper_only")
            return self.last
        if candidate not in {"BUY", "SELL"}:
            self.last = FoundationDecision(state="candidate_hold", reason="base_strategy_has_no_trade")
            return self.last

        candles = self._candles(strategy, settings["max_context"])
        if not candles:
            self.last = FoundationDecision(state="insufficient_data", reason="need_60_complete_ohlcv_bars")
            return self.last

        kronos = self.kronos.forecast(symbol=symbol, timeframe=timeframe, candles=candles, timeout_s=settings["timeout_s"])
        chronos = self.chronos.forecast(symbol=symbol, timeframe=timeframe, candles=candles, timeout_s=settings["timeout_s"])
        agree = kronos.signal == chronos.signal == candidate
        quality = min(kronos.confidence, chronos.confidence)
        accepted = bool(
            kronos.state == "ready"
            and chronos.state == "ready"
            and agree
            and quality >= settings["min_confidence"]
        )
        reason = "consensus_accepted" if accepted else "model_disagreement_or_low_confidence"
        self.last = FoundationDecision(
            signal=candidate if accepted else "HOLD",
            confidence=quality if accepted else 0.0,
            accepted=accepted,
            state="ready" if accepted else "blocked",
            reason=reason,
            kronos=kronos,
            chronos=chronos,
            sampled_bars=len(candles),
        )
        return self.last

    def status(self) -> Dict[str, Any]:
        return self.last.public()
