# Lightweight OHLCV feed for dashboard (no web.server import side-effects)
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]

_OKX_BAR = {
    "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "1H", "1H": "1H", "4h": "4H", "4H": "4H",
    "1d": "1D", "1D": "1D",
}


def _safe_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def candles_payload(symbol: str = "BTC-USDC", bar: str = "15m", limit: int = 200) -> Dict[str, Any]:
    """Closed bars only — OKX public first, local CSV fallback."""
    limit = max(10, min(int(limit or 200), 500))
    symbol = str(symbol or "BTC-USDC").replace("/", "-").upper()
    bar_in = str(bar or "15m")
    okx_bar = _OKX_BAR.get(bar_in, _OKX_BAR.get(bar_in.lower(), "15m"))
    candles: List[dict] = []
    source = "none"

    # Source 1 : OKX
    try:
        from exchange.okx_client import OKXClient
        client = OKXClient()
        raw = client.get_candles(symbol, bar=okx_bar, limit=limit) or []
        for c in reversed(list(raw)):
            ts = c.get("timestamp")
            if hasattr(ts, "timestamp"):
                tsec = int(ts.timestamp())
            else:
                try:
                    tsec = int(float(ts))
                    if tsec > 10_000_000_000:
                        tsec //= 1000
                except Exception:
                    continue
            candles.append(
                {
                    "time": tsec,
                    "open": _safe_float(c.get("open")),
                    "high": _safe_float(c.get("high")),
                    "low": _safe_float(c.get("low")),
                    "close": _safe_float(c.get("close")),
                    "volume": _safe_float(c.get("volume") or 0),
                }
            )
        if candles:
            source = "okx"
    except Exception:
        candles = []

    # Source 2 : CSV local
    if not candles:
        try:
            from data.loader import default_dataset, load_csv_candles
            tf = bar_in.lower() if bar_in.lower() in ("5m", "15m", "1h", "4h", "1d") else "15m"
            path = default_dataset(tf)
            rows = load_csv_candles(path)[-limit:]
            for c in rows:
                ts = c.get("ts") or c.get("timestamp") or c.get("time")
                try:
                    if hasattr(ts, "timestamp"):
                        tsec = int(ts.timestamp())
                    else:
                        tsec = int(float(ts))
                        if tsec > 10_000_000_000:
                            tsec //= 1000
                except Exception:
                    continue
                candles.append(
                    {
                        "time": tsec,
                        "open": _safe_float(c.get("open")),
                        "high": _safe_float(c.get("high")),
                        "low": _safe_float(c.get("low")),
                        "close": _safe_float(c.get("close")),
                        "volume": _safe_float(c.get("volume") or 0),
                    }
                )
            if candles:
                source = "csv"
        except Exception:
            candles = []

    return {
        "ok": bool(candles),
        "symbol": symbol,
        "bar": bar_in,
        "source": source,
        "count": len(candles),
        "candles": candles,
    }