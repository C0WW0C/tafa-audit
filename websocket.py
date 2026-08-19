# ============================================================
# TAFA V7 PRO — OKX WebSocket (DEMO / LIVE public)
# Ticker stream is primary (works on DEMO).
# Candle channel may fail on paper (error 60018) → we build
# live candles from ticks as fallback.
# ============================================================

from __future__ import annotations

import json
import os
import threading
import time
from typing import Callable, Dict, List, Optional

from logger import logger

try:
    import websocket
except ImportError:  # pragma: no cover
    websocket = None
    logger.warning("websocket-client not installed — pip install websocket-client")


class OKXWebSocket:
    """Public OKX WebSocket for price + candle streaming."""

    DEMO_URL = "wss://wspap.okx.com:8443/ws/v5/public"
    LIVE_URL = "wss://ws.okx.com:8443/ws/v5/public"

    # OKX channel suffixes (official)
    TF_MAP = {
        "1m": "1m",
        "3m": "3m",
        "5m": "5m",
        "15m": "15m",
        "30m": "30m",
        "1h": "1H",
        "1H": "1H",
        "2h": "2H",
        "2H": "2H",
        "4h": "4H",
        "4H": "4H",
        "6h": "6H",
        "6H": "6H",
        "12h": "12H",
        "12H": "12H",
        "1d": "1D",
        "1D": "1D",
        "1w": "1W",
        "1W": "1W",
    }

    TF_SECONDS = {
        "1m": 60,
        "3m": 180,
        "5m": 300,
        "15m": 900,
        "30m": 1800,
        "1H": 3600,
        "2H": 7200,
        "4H": 14400,
        "6H": 21600,
        "12H": 43200,
        "1D": 86400,
        "1W": 604800,
    }

    def __init__(
        self,
        symbol: str = "BTC-USDC",
        timeframe: str = "1H",
        demo: bool = True,
        on_price: Optional[Callable[[float], None]] = None,
        on_candle: Optional[Callable[[dict], None]] = None,
    ):
        self.symbol = symbol
        self.timeframe = self.TF_MAP.get(timeframe, self.TF_MAP.get(str(timeframe).lower(), "1H"))
        self.demo = demo
        self.on_price = on_price
        self.on_candle = on_candle

        self.ws = None
        self._thread: Optional[threading.Thread] = None
        self.running = False
        self.connected = False
        self.last_price: Optional[float] = None
        self.last_candle: Optional[dict] = None
        self.last_message_ts: float = 0.0
        self._lock = threading.Lock()
        self._reconnect_delay = 3.0
        self._max_reconnect_delay = 60.0
        self._should_run = False
        self.candle_channel_ok = False
        self.candle_channel_error: Optional[str] = None
        self.book_channel_ok = False
        self.book_channel_error: Optional[str] = None
        self.order_book: dict = {"bids": [], "asks": [], "best_bid": None, "best_ask": None, "spread": None, "ts": None}

        # Synthetic candle from ticks (fallback when candle channel rejected)
        self._tick_candle: Optional[dict] = None
        self._tick_candle_start: float = 0.0
        self._tf_sec = self.TF_SECONDS.get(self.timeframe, 3600)
        # On OKX paper public, candle subscriptions can return 60018 while
        # ticker and book streams work. Prefer the tested tick→candle path by
        # default; allow an operator to opt in when the exchange supports it.
        self._try_candle_channel = (not demo) or os.getenv("TAFA_DEMO_CANDLE_SUBSCRIBE", "false").strip().lower() in {"1", "true", "yes", "on"}

        # Alternate instIds to try for candles on DEMO
        self._candle_inst_candidates = self._build_inst_candidates(symbol)

        logger.info(
            f"OKX WebSocket ready symbol={symbol} tf={self.timeframe} "
            f"mode={'DEMO' if demo else 'LIVE'}"
        )

    @staticmethod
    def _build_inst_candidates(symbol: str) -> List[str]:
        s = symbol.upper().replace("_", "-")
        out = [s]
        # DEMO often has BTC-USDT more reliably than BTC-USDC for candles
        if "USDC" in s:
            out.append(s.replace("USDC", "USDT"))
        if "USDT" in s and "USDC" not in out:
            out.append(s.replace("USDT", "USDC"))
        # dedupe preserve order
        seen = set()
        uniq = []
        for x in out:
            if x not in seen:
                seen.add(x)
                uniq.append(x)
        return uniq

    @property
    def url(self) -> str:
        return self.DEMO_URL if self.demo else self.LIVE_URL

    def connect(self) -> bool:
        if websocket is None:
            logger.warning("websocket-client missing — pip install websocket-client")
            return False
        if self.running:
            return True
        self._should_run = True
        self.running = True
        self._thread = threading.Thread(target=self._run_loop, name="okx-ws", daemon=True)
        self._thread.start()
        logger.info(f"OKX WS connecting → {self.url}")
        return True

    def _run_loop(self) -> None:
        delay = self._reconnect_delay
        while self._should_run:
            try:
                self.ws = websocket.WebSocketApp(
                    self.url,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                )
                self.ws.run_forever(ping_interval=20, ping_timeout=10)
            except Exception as exc:
                logger.error(f"OKX WS loop error: {exc}")
            self.connected = False
            if not self._should_run:
                break
            logger.warning(f"OKX WS reconnect in {delay:.0f}s…")
            time.sleep(delay)
            delay = min(delay * 1.5, self._max_reconnect_delay)
        self.running = False

    def _on_open(self, ws) -> None:
        if not self._should_run:
            try:
                ws.close()
            except Exception:
                pass
            return
        self.connected = True
        self._reconnect_delay = 3.0
        logger.info("OKX WS connected")

        # 1) Always subscribe ticker on primary symbol (works on DEMO)
        ticker_args = [{"channel": "tickers", "instId": self.symbol}]
        try:
            ws.send(json.dumps({"op": "subscribe", "args": ticker_args}))
        except Exception as exc:
            if self._should_run:
                logger.error(f"OKX WS ticker subscribe error: {exc}")
            return
        logger.info(f"OKX WS subscribed tickers {self.symbol}")

        try:
            ws.send(json.dumps({"op": "subscribe", "args": [{"channel": "books5", "instId": self.symbol}]}))
        except Exception as exc:
            if self._should_run:
                logger.error(f"OKX WS book subscribe error: {exc}")
        else:
            logger.info(f"OKX WS subscribed books5 {self.symbol}")

        # 2) In paper mode the synthetic tick→candle path is the safe default.
        if not self._try_candle_channel:
            logger.info("OKX WS DEMO: tick→candle fallback selected; candle subscription skipped")
            return

        # Optional candle channels (operator opt-in on DEMO, default on LIVE)
        candle_args = []
        for inst in self._candle_inst_candidates:
            candle_args.append(
                {"channel": f"candle{self.timeframe}", "instId": inst}
            )
        if not self._should_run:
            return
        try:
            ws.send(json.dumps({"op": "subscribe", "args": candle_args}))
        except Exception as exc:
            if self._should_run:
                logger.error(f"OKX WS candle subscribe error: {exc}")
            return
        logger.info(
            f"OKX WS candle subscribe tried: candle{self.timeframe} "
            f"inst={self._candle_inst_candidates}"
        )

    def _on_message(self, ws, message: str) -> None:
        self.last_message_ts = time.time()
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            return

        event = data.get("event")
        if event == "subscribe":
            arg = data.get("arg") or {}
            ch = arg.get("channel", "")
            if ch.startswith("candle"):
                self.candle_channel_ok = True
                self.candle_channel_error = None
                logger.info(f"OKX WS candle OK: {arg}")
            elif ch == "books5":
                self.book_channel_ok = True
                self.book_channel_error = None
            return

        if event == "error":
            msg = data.get("msg", "")
            code = data.get("code", "")
            # 60018 = wrong channel/inst — expected on DEMO for some pairs
            if "candle" in msg.lower() or code == "60018":
                self.candle_channel_error = msg
                logger.warning(
                    f"OKX WS candle unavailable ({code}): using tick→candle fallback"
                )
            else:
                if "book" in msg.lower():
                    self.book_channel_error = msg
                logger.error(f"OKX WS event error: {data}")
            return

        if event in ("channel-conn-count", "login"):
            return

        arg = data.get("arg") or {}
        channel = arg.get("channel", "")
        rows: List = data.get("data") or []
        if not rows:
            return

        if channel == "tickers":
            self._handle_ticker(rows[0])
        elif channel == "books5":
            self._handle_book(rows[0])
        elif channel.startswith("candle"):
            self._handle_candle(rows[0])

    def _handle_book(self, row: dict) -> None:
        def levels(raw) -> list[dict]:
            out = []
            for level in raw or []:
                try:
                    price, size = float(level[0]), float(level[1])
                    if price > 0 and size >= 0:
                        out.append({"price": price, "size": size})
                except (IndexError, TypeError, ValueError):
                    continue
            return out[:5]

        bids = sorted(levels(row.get("bids")), key=lambda x: x["price"], reverse=True)
        asks = sorted(levels(row.get("asks")), key=lambda x: x["price"])
        best_bid = bids[0]["price"] if bids else None
        best_ask = asks[0]["price"] if asks else None
        with self._lock:
            self.order_book = {
                "bids": bids,
                "asks": asks,
                "best_bid": best_bid,
                "best_ask": best_ask,
                "spread": (best_ask - best_bid) if best_bid is not None and best_ask is not None else None,
                "ts": row.get("ts"),
            }

    def _handle_ticker(self, row: dict) -> None:
        try:
            price = float(row.get("last") or row.get("lastPx") or 0)
        except (TypeError, ValueError):
            return
        if price <= 0:
            return
        with self._lock:
            self.last_price = price
        self._update_tick_candle(price)
        if self.on_price:
            try:
                self.on_price(price)
            except Exception as exc:
                logger.error(f"on_price callback: {exc}")

    def _update_tick_candle(self, price: float) -> None:
        """Build OHLCV bars from ticks when native candle channel is missing."""
        now = time.time()
        bucket = int(now // self._tf_sec) * self._tf_sec
        with self._lock:
            if self._tick_candle is None or self._tick_candle_start != bucket:
                # close previous synthetic candle
                if self._tick_candle is not None and self._tick_candle_start != bucket:
                    closed = dict(self._tick_candle)
                    closed["confirm"] = "1"
                    self.last_candle = closed
                    cb = closed
                    fire = True
                else:
                    fire = False
                    cb = None
                self._tick_candle_start = bucket
                self._tick_candle = {
                    "ts": str(int(bucket * 1000)),
                    "open": price,
                    "high": price,
                    "low": price,
                    "close": price,
                    "volume": 0.0,
                    "confirm": "0",
                    "source": "tick_synth",
                }
            else:
                c = self._tick_candle
                c["high"] = max(c["high"], price)
                c["low"] = min(c["low"], price)
                c["close"] = price
                c["volume"] = c.get("volume", 0) + 1  # tick count proxy
                self.last_candle = dict(c)
                fire = False
                cb = None

        if fire and cb and self.on_candle:
            try:
                self.on_candle(cb)
            except Exception as exc:
                logger.error(f"on_candle callback: {exc}")

    def _handle_candle(self, row) -> None:
        try:
            if isinstance(row, dict):
                candle = {
                    "ts": row.get("ts"),
                    "open": float(row["o"]),
                    "high": float(row["h"]),
                    "low": float(row["l"]),
                    "close": float(row["c"]),
                    "volume": float(row.get("vol", 0)),
                    "confirm": str(row.get("confirm", "0")),
                    "source": "okx",
                }
            else:
                candle = {
                    "ts": row[0],
                    "open": float(row[1]),
                    "high": float(row[2]),
                    "low": float(row[3]),
                    "close": float(row[4]),
                    "volume": float(row[5]) if len(row) > 5 else 0.0,
                    "confirm": str(row[8]) if len(row) > 8 else "0",
                    "source": "okx",
                }
        except (IndexError, KeyError, TypeError, ValueError) as exc:
            logger.error(f"candle parse: {exc}")
            return

        self.candle_channel_ok = True
        with self._lock:
            self.last_candle = candle
            self.last_price = candle["close"]

        if self.on_candle:
            try:
                self.on_candle(candle)
            except Exception as exc:
                logger.error(f"on_candle callback: {exc}")

    def _on_error(self, ws, error) -> None:
        if self._should_run:
            logger.error(f"OKX WS error: {error}")

    def _on_close(self, ws, code, msg) -> None:
        self.connected = False
        if self._should_run:
            logger.warning(f"OKX WS closed code={code} msg={msg}")

    def get_price(self) -> Optional[float]:
        with self._lock:
            return self.last_price

    def get_candle(self) -> Optional[dict]:
        with self._lock:
            return dict(self.last_candle) if self.last_candle else None

    def get_book(self) -> dict:
        with self._lock:
            return dict(self.order_book)

    def status(self) -> dict:
        return {
            "running": self.running,
            "connected": self.connected,
            "demo": self.demo,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "last_price": self.last_price,
            "candle_channel_ok": self.candle_channel_ok,
            "candle_fallback": not self.candle_channel_ok,
            "candle_error": self.candle_channel_error,
            "book": self.get_book(),
            "book_channel_ok": self.book_channel_ok,
            "book_error": self.book_channel_error,
            "last_candle": self.last_candle,
            "last_message_age_s": round(time.time() - self.last_message_ts, 1)
            if self.last_message_ts
            else None,
            "url": self.url,
        }

    def stop(self) -> None:
        self._should_run = False
        self.running = False
        ws = self.ws
        try:
            if ws and getattr(ws, "sock", None):
                ws.close()
        except Exception:
            pass
        thread = self._thread
        if thread and thread is not threading.current_thread():
            thread.join(timeout=1.0)
        logger.info("OKX WS stopped")
