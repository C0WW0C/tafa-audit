#!/usr/bin/env python3
"""Test OKX DEMO public WebSocket — run on YOUR PC with internet.

  PYTHONPATH=. python scripts/test_okx_ws.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from exchange.websocket import OKXWebSocket


def main():
    prices = []
    candles = []

    def on_price(p: float):
        prices.append(p)
        if len(prices) <= 5 or len(prices) % 10 == 0:
            print(f"  ticker last={p}")

    def on_candle(c: dict):
        candles.append(c)
        flag = "CLOSED" if str(c.get("confirm")) == "1" else "live"
        src = c.get("source", "?")
        print(f"  candle [{src}] {flag} o={c['open']} h={c['high']} l={c['low']} c={c['close']}")

    ws = OKXWebSocket(
        symbol="BTC-USDC",
        timeframe="1H",
        demo=True,
        on_price=on_price,
        on_candle=on_candle,
    )
    print("Connecting OKX DEMO public WS…", ws.url)
    ws.connect()
    try:
        for i in range(25):
            time.sleep(1)
            st = ws.status()
            if i % 5 == 0:
                print(
                    f"[{i}s] connected={st['connected']} last={st['last_price']} "
                    f"candle_ok={st['candle_channel_ok']} fallback={st['candle_fallback']}"
                )
            if st["connected"] and st["last_price"] and len(prices) >= 3:
                break
        print("STATUS", {k: v for k, v in ws.status().items() if k != "last_candle"})
        if not ws.connected:
            print("FAILED: no connection")
            return 1
        if not ws.last_price:
            print("CONNECTED but no price")
            return 2
        print("OK — ticker stream works")
        if not ws.candle_channel_ok:
            print("NOTE — native candle channel rejected on DEMO; tick→candle fallback active")
        return 0
    finally:
        ws.stop()


if __name__ == "__main__":
    raise SystemExit(main())
