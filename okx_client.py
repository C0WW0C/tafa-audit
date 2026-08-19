# ============================================================
# TAFA V7 PRO — OKX Client (Production)
# Public endpoints work without keys.
# Private endpoints require DEMO/LIVE credentials.
# ============================================================

from __future__ import annotations

import base64
import hmac
import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Optional

import requests

from logger import logger


class OKXClient:
    """OKX REST client with public + signed private API support."""

    BASE_URL = "https://www.okx.com"
    TIMEOUT = (3.05, 8)
    PUBLIC_MAX_ATTEMPTS = 3
    PUBLIC_RETRY_DELAY_SECONDS = 0.25

    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        passphrase: Optional[str] = None,
        demo: bool = True,
    ):
        self.api_key = api_key or os.getenv("OKX_API_KEY", "")
        self.secret_key = secret_key or os.getenv("OKX_SECRET_KEY", "")
        self.passphrase = passphrase or os.getenv("OKX_PASSPHRASE", "")
        self.demo = demo
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        logger.info(f"OKX Client ready (demo={self.demo})")

    # ------------------------------------------------------------------
    # Auth helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _timestamp() -> str:
        return (
            datetime.now(timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z")
        )

    def _sign(self, timestamp: str, method: str, path: str, body: str = "") -> str:
        message = f"{timestamp}{method.upper()}{path}{body}"
        mac = hmac.new(
            self.secret_key.encode("utf-8"),
            message.encode("utf-8"),
            digestmod="sha256",
        )
        return base64.b64encode(mac.digest()).decode()

    def _private_headers(self, method: str, path: str, body: str = "") -> dict:
        ts = self._timestamp()
        headers = {
            "OK-ACCESS-KEY": self.api_key,
            "OK-ACCESS-SIGN": self._sign(ts, method, path, body),
            "OK-ACCESS-TIMESTAMP": ts,
            "OK-ACCESS-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json",
        }
        if self.demo:
            headers["x-simulated-trading"] = "1"
        return headers

    def has_credentials(self) -> bool:
        return bool(self.api_key and self.secret_key and self.passphrase)

    # ------------------------------------------------------------------
    # HTTP
    # ------------------------------------------------------------------

    @staticmethod
    def _is_retryable_public_error(exc: requests.RequestException) -> bool:
        """Retry only transient public-network failures; TLS verification stays enabled."""
        if isinstance(
            exc,
            (
                requests.exceptions.SSLError,
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
            ),
        ):
            return True
        if isinstance(exc, requests.exceptions.HTTPError) and exc.response is not None:
            return exc.response.status_code == 429 or exc.response.status_code >= 500
        return False

    def _get_public(self, path: str, params: Optional[dict] = None) -> dict:
        url = self.BASE_URL + path
        last_error: Optional[requests.RequestException] = None

        for attempt in range(self.PUBLIC_MAX_ATTEMPTS):
            try:
                # ``requests`` verifies TLS certificates by default. Do not
                # disable verification to work around an interrupted handshake.
                resp = self.session.get(url, params=params, timeout=self.TIMEOUT)
                resp.raise_for_status()
                data = resp.json()
                if str(data.get("code", "0")) != "0":
                    logger.warning(f"OKX public error {data.get('code')}: {data.get('msg')}")
                self._public_err_logged = False
                return data
            except requests.RequestException as exc:
                last_error = exc
                if not self._is_retryable_public_error(exc) or attempt == self.PUBLIC_MAX_ATTEMPTS - 1:
                    break
                delay = self.PUBLIC_RETRY_DELAY_SECONDS * (2**attempt)
                logger.warning(
                    "OKX public request interrupted; retry %s/%s in %.2fs: %s",
                    attempt + 1,
                    self.PUBLIC_MAX_ATTEMPTS - 1,
                    delay,
                    exc,
                )
                time.sleep(delay)

        message = str(last_error) if last_error else "unknown public request failure"
        if not getattr(self, "_public_err_logged", False):
            logger.error(f"OKX public request failed after retries: {message}")
            self._public_err_logged = True
        return {"code": "-1", "data": [], "msg": message}

    def _request_private(
        self,
        method: str,
        path: str,
        body: Optional[dict] = None,
    ) -> dict:
        if not self.has_credentials():
            logger.error("Private API called without credentials")
            return {"code": "-1", "data": [], "msg": "missing credentials"}

        body_str = json.dumps(body) if body else ""
        headers = self._private_headers(method, path, body_str)
        url = self.BASE_URL + path
        try:
            resp = self.session.request(
                method.upper(),
                url,
                headers=headers,
                data=body_str if body_str else None,
                timeout=self.TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            if str(data.get("code", "0")) != "0":
                logger.warning(f"OKX private error {data.get('code')}: {data.get('msg')}")
            return data
        except requests.RequestException as exc:
            logger.error(f"OKX private request failed: {exc}")
            return {"code": "-1", "data": [], "msg": str(exc)}

    # ------------------------------------------------------------------
    # Public market data
    # ------------------------------------------------------------------

    def get_ticker(self, symbol: str) -> Optional[float]:
        """Return last traded price for instrument, e.g. BTC-USDC."""
        data = self._get_public("/api/v5/market/ticker", {"instId": symbol})
        try:
            items = data.get("data") or []
            if not items:
                return None
            return float(items[0]["last"])
        except (KeyError, TypeError, ValueError) as exc:
            logger.error(f"Ticker parse error for {symbol}: {exc}")
            return None

    def get_order_book(self, symbol: str, depth: int = 5) -> dict:
        """Return a shallow public order book. No credentials or private routes are used."""
        depth = max(1, min(int(depth), 5))
        data = self._get_public("/api/v5/market/books", {"instId": symbol, "sz": str(depth)})

        def levels(rows) -> list[dict]:
            out = []
            for row in rows or []:
                try:
                    price, size = float(row[0]), float(row[1])
                    if price > 0 and size >= 0:
                        out.append({"price": price, "size": size})
                except (IndexError, TypeError, ValueError):
                    continue
            return out[:depth]

        try:
            row = (data.get("data") or [{}])[0]
            bids = sorted(levels(row.get("bids")), key=lambda x: x["price"], reverse=True)
            asks = sorted(levels(row.get("asks")), key=lambda x: x["price"])
            best_bid = bids[0]["price"] if bids else None
            best_ask = asks[0]["price"] if asks else None
            return {
                "bids": bids,
                "asks": asks,
                "best_bid": best_bid,
                "best_ask": best_ask,
                "spread": best_ask - best_bid if best_bid is not None and best_ask is not None else None,
                "ts": row.get("ts"),
                "source": "okx_public_rest",
            }
        except (IndexError, TypeError, ValueError):
            return {"bids": [], "asks": [], "best_bid": None, "best_ask": None, "spread": None, "source": "none"}

    @staticmethod
    def _normalize_bar(bar: str) -> str:
        """OKX bar ids: 1m/5m/15m/1H/4H/1D (hour/day uppercase)."""
        b = str(bar or "15m").strip()
        key = b.lower().replace(" ", "")
        mapping = {
            "1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m", "30m": "30m",
            "1h": "1H", "1H": "1H", "2h": "2H", "2H": "2H",
            "4h": "4H", "4H": "4H", "6h": "6H", "6H": "6H",
            "12h": "12H", "12H": "12H", "1d": "1D", "1D": "1D", "1w": "1W",
        }
        return mapping.get(key, mapping.get(b, b))

    def get_candles(
        self,
        symbol: str,
        bar: str = "15m",
        limit: int = 100,
    ) -> list[dict]:
        bar = self._normalize_bar(bar)
        data = self._get_public(
            "/api/v5/market/candles",
            {"instId": symbol, "bar": bar, "limit": str(limit)},
        )
        candles = []
        for row in data.get("data") or []:
            try:
                # OKX: [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]
                candles.append(
                    {
                        "timestamp": datetime.fromtimestamp(
                            int(row[0]) / 1000, tz=timezone.utc
                        ),
                        "open": float(row[1]),
                        "high": float(row[2]),
                        "low": float(row[3]),
                        "close": float(row[4]),
                        "volume": float(row[5]),
                    }
                )
            except (IndexError, ValueError, TypeError):
                continue
        candles.reverse()  # chronological
        return candles

    # ------------------------------------------------------------------
    # Private account / trading
    # ------------------------------------------------------------------

    def get_balance(self, ccy: str = "USDC") -> float:
        data = self._request_private("GET", "/api/v5/account/balance")
        try:
            for detail in (data.get("data") or [{}])[0].get("details") or []:
                if detail.get("ccy") == ccy:
                    return float(detail.get("availBal") or detail.get("cashBal") or 0)
        except (TypeError, ValueError, IndexError) as exc:
            logger.error(f"Balance parse error: {exc}")
        return 0.0

    def place_order(
        self,
        symbol: str,
        side: str,
        size: str,
        order_type: str = "market",
        td_mode: str = "cash",
    ) -> dict:
        body = {
            "instId": symbol,
            "tdMode": td_mode,
            "side": side.lower(),
            "ordType": order_type,
            "sz": str(size),
        }
        return self._request_private("POST", "/api/v5/trade/order", body)

    def get_positions(self) -> list:
        data = self._request_private("GET", "/api/v5/account/positions")
        return data.get("data") or []
