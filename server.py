"""Local inference endpoints for TAFA's paper-only foundation-model gate.

The service binds to loopback by default and exposes two explicit routes:
``POST /kronos/predict`` and ``POST /chronos/predict``. It loads official
model weights lazily on first request; loading failure is reported as an HTTP
503, never replaced by a synthetic forecast.
"""
from __future__ import annotations

import json
import os
import sys
import threading
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
MAX_BODY_BYTES = 2_000_000
MAX_CANDLES = 512
MIN_CANDLES = 60


class ModelUnavailable(RuntimeError):
    """Raised when a real local model cannot be loaded or queried."""


def _bounded_float(value: Any, field: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} doit être numérique") from exc
    if result != result or result in (float("inf"), float("-inf")):
        raise ValueError(f"{field} doit être fini")
    return result


def validate_request(payload: Dict[str, Any]) -> Tuple[str, str, List[Dict[str, float]]]:
    if not isinstance(payload, dict):
        raise ValueError("corps JSON objet attendu")
    symbol = str(payload.get("symbol", "")).upper().strip()
    timeframe = str(payload.get("timeframe", "")).strip().lower()
    candles = payload.get("candles")
    if not symbol or len(symbol) > 24:
        raise ValueError("symbol invalide")
    if not timeframe or len(timeframe) > 12:
        raise ValueError("timeframe invalide")
    if not isinstance(candles, list) or not MIN_CANDLES <= len(candles) <= MAX_CANDLES:
        raise ValueError(f"candles doit contenir entre {MIN_CANDLES} et {MAX_CANDLES} barres")

    cleaned: List[Dict[str, float]] = []
    for index, candle in enumerate(candles):
        if not isinstance(candle, dict):
            raise ValueError(f"candle[{index}] doit être un objet")
        row = {key: _bounded_float(candle.get(key), f"candle[{index}].{key}") for key in ("open", "high", "low", "close", "volume")}
        if row["low"] > min(row["open"], row["close"]) or row["high"] < max(row["open"], row["close"]) or row["high"] < row["low"]:
            raise ValueError(f"candle[{index}] OHLC incohérent")
        if row["volume"] < 0:
            raise ValueError(f"candle[{index}].volume doit être positif")
        cleaned.append(row)
    return symbol, timeframe, cleaned


def _step_for_timeframe(timeframe: str):
    import pandas as pd

    mapping = {"1m": "1min", "3m": "3min", "5m": "5min", "15m": "15min", "30m": "30min", "1h": "1h", "2h": "2h", "4h": "4h", "6h": "6h", "12h": "12h", "1d": "1D"}
    return pd.tseries.frequencies.to_offset(mapping.get(timeframe, "4h"))


@dataclass
class ForecastResult:
    model: str
    signal: str
    confidence: float
    forecast_close: float
    last_close: float

    def public(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "signal": self.signal,
            "confidence": round(self.confidence, 4),
            "forecast_close": round(self.forecast_close, 8),
            "last_close": round(self.last_close, 8),
        }


class LocalInferenceRuntime:
    """Lazy CPU runtime for the official Kronos and Chronos implementations."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._kronos_predictor = None
        self._chronos_pipeline = None
        self._errors: Dict[str, str] = {}
        self.edge = max(0.0, min(0.05, float(os.getenv("TAFA_MODEL_SIGNAL_EDGE", "0.002"))))
        self.device = os.getenv("TAFA_MODEL_DEVICE", "cpu").strip() or "cpu"

    def _signal(self, model: str, forecast_close: float, last_close: float) -> ForecastResult:
        if last_close <= 0:
            raise ModelUnavailable("last_close invalide")
        change = (forecast_close / last_close) - 1.0
        magnitude = abs(change)
        signal = "BUY" if change >= self.edge else "SELL" if change <= -self.edge else "HOLD"
        # Confidence expresses distance from the configured no-trade band,
        # not historical accuracy. It is capped to retain a conservative gate.
        confidence = min(0.95, max(0.0, magnitude / max(self.edge * 4, 1e-9)))
        return ForecastResult(model, signal, confidence, forecast_close, last_close)

    def _load_kronos(self):
        if self._kronos_predictor is not None:
            return self._kronos_predictor
        source = ROOT / "third_party" / "Kronos"
        if not source.exists():
            raise ModelUnavailable("source Kronos absent : exécutez scripts/setup_local_model_server.sh")
        with self._lock:
            if self._kronos_predictor is not None:
                return self._kronos_predictor
            try:
                if str(source) not in sys.path:
                    sys.path.insert(0, str(source))
                from model import Kronos, KronosPredictor, KronosTokenizer

                tokenizer = KronosTokenizer.from_pretrained("NeoQuasar/Kronos-Tokenizer-base")
                model = Kronos.from_pretrained("NeoQuasar/Kronos-base")
                self._kronos_predictor = KronosPredictor(model, tokenizer, device=self.device, max_context=MAX_CANDLES)
                return self._kronos_predictor
            except Exception as exc:
                self._errors["kronos"] = str(exc)
                raise ModelUnavailable(f"chargement Kronos impossible : {exc}") from exc

    def _load_chronos(self):
        if self._chronos_pipeline is not None:
            return self._chronos_pipeline
        with self._lock:
            if self._chronos_pipeline is not None:
                return self._chronos_pipeline
            try:
                from chronos import Chronos2Pipeline

                self._chronos_pipeline = Chronos2Pipeline.from_pretrained("amazon/chronos-2", device_map=self.device)
                return self._chronos_pipeline
            except Exception as exc:
                self._errors["chronos"] = str(exc)
                raise ModelUnavailable(f"chargement Chronos impossible : {exc}") from exc

    def predict_kronos(self, symbol: str, timeframe: str, candles: List[Dict[str, float]]) -> ForecastResult:
        try:
            import pandas as pd
        except Exception as exc:
            raise ModelUnavailable(f"pandas indisponible : {exc}") from exc
        predictor = self._load_kronos()
        frame = pd.DataFrame(candles)
        frame["amount"] = frame["close"] * frame["volume"]
        timestamps = pd.Series(pd.date_range("2024-01-01", periods=len(frame), freq=_step_for_timeframe(timeframe)))
        future = pd.Series(pd.date_range(timestamps.iloc[-1] + _step_for_timeframe(timeframe), periods=1, freq=_step_for_timeframe(timeframe)))
        try:
            forecast = predictor.predict(
                df=frame[["open", "high", "low", "close", "volume", "amount"]],
                x_timestamp=timestamps,
                y_timestamp=future,
                pred_len=1,
                T=1.0,
                top_p=0.9,
                sample_count=1,
            )
            return self._signal("NeoQuasar/Kronos-base", float(forecast["close"].iloc[-1]), float(frame["close"].iloc[-1]))
        except Exception as exc:
            raise ModelUnavailable(f"prédiction Kronos impossible : {exc}") from exc

    def predict_chronos(self, symbol: str, timeframe: str, candles: List[Dict[str, float]]) -> ForecastResult:
        try:
            import pandas as pd
        except Exception as exc:
            raise ModelUnavailable(f"pandas indisponible : {exc}") from exc
        pipeline = self._load_chronos()
        frame = pd.DataFrame(candles)
        frame["id"] = symbol
        frame["timestamp"] = pd.date_range("2024-01-01", periods=len(frame), freq=_step_for_timeframe(timeframe))
        context = frame[["id", "timestamp", "close"]].rename(columns={"close": "target"})
        try:
            forecast = pipeline.predict_df(
                context,
                prediction_length=1,
                quantile_levels=[0.1, 0.5, 0.9],
                id_column="id",
                timestamp_column="timestamp",
                target="target",
            )
            return self._signal("amazon/chronos-2", float(forecast["predictions"].iloc[-1]), float(context["target"].iloc[-1]))
        except Exception as exc:
            raise ModelUnavailable(f"prédiction Chronos impossible : {exc}") from exc

    def health(self) -> Dict[str, Any]:
        return {
            "ok": True,
            "bind": "loopback",
            "device": self.device,
            "models": {
                "kronos": "ready" if self._kronos_predictor is not None else "lazy",
                "chronos": "ready" if self._chronos_pipeline is not None else "lazy",
            },
            "errors": dict(self._errors),
        }


class InferenceHandler(BaseHTTPRequestHandler):
    runtime: LocalInferenceRuntime

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("[tafa-model-server] %s\n" % (fmt % args))

    def _json(self, status: int, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path.rstrip("/") == "/health":
            self._json(HTTPStatus.OK, self.runtime.health())
            return
        self._json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "route introuvable"})

    def do_POST(self) -> None:
        route = self.path.rstrip("/")
        if route not in {"/kronos/predict", "/chronos/predict"}:
            self._json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "route introuvable"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size <= 0 or size > MAX_BODY_BYTES:
                raise ValueError("taille de requête invalide")
            payload = json.loads(self.rfile.read(size).decode("utf-8"))
            symbol, timeframe, candles = validate_request(payload)
            result = self.runtime.predict_kronos(symbol, timeframe, candles) if route.startswith("/kronos") else self.runtime.predict_chronos(symbol, timeframe, candles)
            self._json(HTTPStatus.OK, result.public())
        except ValueError as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
        except ModelUnavailable as exc:
            self._json(HTTPStatus.SERVICE_UNAVAILABLE, {"ok": False, "error": str(exc)})
        except Exception as exc:
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": str(exc)})


def create_server(host: str | None = None, port: int | None = None, runtime: LocalInferenceRuntime | None = None) -> ThreadingHTTPServer:
    bind_host = host or os.getenv("TAFA_MODEL_SERVER_HOST", "127.0.0.1")
    if bind_host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("le serveur de modèles doit rester lié à loopback")
    bind_port = int(port if port is not None else os.getenv("TAFA_MODEL_SERVER_PORT", "8787"))
    handler = type("ConfiguredInferenceHandler", (InferenceHandler,), {"runtime": runtime or LocalInferenceRuntime()})
    return ThreadingHTTPServer((bind_host, bind_port), handler)


def main() -> None:
    server = create_server()
    print(f"TAFA model server → http://127.0.0.1:{server.server_address[1]}")
    print("Routes : GET /health · POST /kronos/predict · POST /chronos/predict")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
