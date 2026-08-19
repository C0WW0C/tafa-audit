# ============================================================
# TAFA V7 PRO — Market Data (Production) - version corrigée
# Multi-source: OKX → CoinGecko → Binance → offline fallback
# ============================================================
from __future__ import annotations

import json
import time
import threading
import urllib.request
from typing import Optional

from logger import logger
from exchange.okx_client import OKXClient


COINGECKO_IDS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "XRP": "ripple",
    "DOGE": "dogecoin",
}
COINGECKO_CACHE_SECONDS = 55.0
COINGECKO_MAX_AGE_SECONDS = 120.0


class MarketData:
    """Fetches public quotes with an explicit, safe source hierarchy.

    OKX remains the preferred venue quote. CoinGecko provides a broad USD
    reference fallback only; it is never used as an order-book or execution
    source. Binance and the local model remain subsequent fallbacks.
    """

    def __init__(self, client: Optional[OKXClient] = None):
        self.client = client or OKXClient()
        self.prices: list[float] = []
        self.candles: list[dict] = []
        self._last_error: Optional[str] = None
        self._last_source: str = "none"
        self._coingecko_cache: dict[str, tuple[float, float, float]] = {}
        self._quote_meta: dict = {"source": "none", "symbol": None, "updated_at": None}
        self._lock = threading.RLock()          # ✅ thread safety
        logger.info("Market Data initialized")

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    def get_price(self, symbol: str) -> Optional[float]:
        """Return current price from OKX → CoinGecko → Binance → last known."""
        with self._lock:
            price = None
            source = "none"
            try:
                price = self.client.get_ticker(symbol)
                if price and price > 0:
                    source = "okx"
            except Exception as exc:
                self._last_error = str(exc)

            if price is None or price <= 0:
                price = self._coingecko_price(symbol)
                if price:
                    source = "coingecko_usd_proxy"

            if price is None or price <= 0:
                price = self._binance_price(symbol)
                if price:
                    source = "binance"

            if price is None or price <= 0:
                price = self._offline_fallback(symbol)
                if price:
                    source = "offline_last_known"

            if price is None or price <= 0:
                self._last_error = f"no price for {symbol}"
                return None

            price = float(price)
            self.prices.append(price)
            if len(self.prices) > 5000:
                self.prices.pop(0)

            self._last_source = source
            self._last_error = None
            self._quote_meta = {
                "source": source,
                "symbol": symbol.upper(),
                "updated_at": time.time(),
                "quote_currency": "USD" if source == "coingecko_usd_proxy" else None,
            }
            return price

    def load_candles(self, symbol: str, bar: str = "15m", limit: int = 100) -> list[dict]:
        """Load candles from OKX, fallback to local CSV."""
        with self._lock:
            try:
                candles = self.client.get_candles(symbol, bar=bar, limit=limit)
                if candles:
                    self.candles = candles
                    return candles
            except Exception as exc:
                logger.warning(f"OKX candles failed: {exc}")

            try:
                from data.loader import default_dataset, load_csv_candles
                path = default_dataset(bar if bar in ("5m", "15m", "1h", "4h", "1d") else "1h")
                candles = load_csv_candles(path)[-limit:]
                self.candles = candles
                return candles
            except Exception as exc:
                logger.warning(f"Local CSV candles failed: {exc}")
                return []

    def source(self) -> str:
        with self._lock:
            return self._last_source

    def quote_status(self) -> dict:
        """Return provenance for observability without exposing any secret."""
        with self._lock:
            return dict(self._quote_meta)

    # ------------------------------------------------------------------
    # HTTP HELPERS
    # ------------------------------------------------------------------

    def _http_json(self, url: str, timeout: float = 6.0) -> Optional[dict]:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "TAFA/7"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            return None

    # ------------------------------------------------------------------
    # SOURCE FALLBACKS
    # ------------------------------------------------------------------

    def _binance_price(self, symbol: str) -> Optional[float]:
        if "-" not in symbol:
            return None
        base = symbol.split("-")[0].upper()
        data = self._http_json(
            f"https://api.binance.com/api/v3/ticker/price?symbol={base}USDT"
        )
        try:
            if data and data.get("price"):
                return float(data["price"])
        except (TypeError, ValueError):
            pass
        return None

    def _coingecko_price(self, symbol: str) -> Optional[float]:
        if "-" not in symbol:
            return None
        base = symbol.split("-")[0].upper()
        gid = COINGECKO_IDS.get(base)
        if not gid:
            return None

        now = time.time()
        cached = self._coingecko_cache.get(gid)
        if cached:
            value, upstream_updated_at, cached_at = cached
            if now - cached_at <= COINGECKO_CACHE_SECONDS:
                if now - upstream_updated_at <= COINGECKO_MAX_AGE_SECONDS:
                    return value

        data = self._http_json(
            "https://api.coingecko.com/api/v3/simple/price"
            f"?ids={gid}&vs_currencies=usd&include_last_updated_at=true"
        )
        try:
            row = (data or {}).get(gid, {})
            val = float(row["usd"])
            upstream_updated_at = float(row["last_updated_at"])
            if val <= 0 or now - upstream_updated_at > COINGECKO_MAX_AGE_SECONDS:
                return None
            self._coingecko_cache[gid] = (val, upstream_updated_at, now)
            return val
        except (KeyError, TypeError, ValueError):
            return None

    def _offline_fallback(self, symbol: str) -> Optional[float]:
        """
        Last-resort fallback: use the most recent known price.
        No random variation is added — we must not fabricate synthetic prices.
        """
        if self.prices:
            return float(self.prices[-1])
        # If no price history at all, return None.
        # Static seed prices are no longer used to avoid misleading the bot.
        return None