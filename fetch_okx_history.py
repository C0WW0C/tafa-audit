#!/usr/bin/env python3
"""Download confirmed public OKX OHLCV candles for reproducible paper backtests."""
from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = "https://www.okx.com/api/v5/market/history-candles"


def fetch_candles(symbol: str, timeframe: str, bars: int) -> list[dict[str, str]]:
    """Fetch most recent closed candles with conservative pagination and de-duplication."""
    records: dict[str, dict[str, str]] = {}
    after: str | None = None
    for _ in range((bars + 99) // 100 + 5):
        params = {"instId": symbol, "bar": timeframe, "limit": "100"}
        if after:
            params["after"] = after
        response = requests.get(ENDPOINT, params=params, timeout=15)
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") not in ("0", 0, None):
            raise RuntimeError(f"OKX error for {timeframe}: {payload.get('code')} {payload.get('msg')}")
        rows = payload.get("data") or []
        if not rows:
            break
        oldest = None
        for row in rows:
            if len(row) < 9 or str(row[8]) != "1":
                continue
            timestamp = str(row[0])
            records[timestamp] = {
                "ts": timestamp,
                "open": str(row[1]),
                "high": str(row[2]),
                "low": str(row[3]),
                "close": str(row[4]),
                "volume": str(row[5]),
                "source": "okx-public-history",
                "symbol": symbol,
                "timeframe": timeframe,
                "confirm": "1",
            }
            oldest = min(int(timestamp), oldest) if oldest is not None else int(timestamp)
        if len(records) >= bars or oldest is None:
            break
        after = str(oldest)
        time.sleep(0.12)
    ordered = [records[key] for key in sorted(records, key=int)]
    if len(ordered) < bars:
        raise RuntimeError(f"{timeframe}: only {len(ordered)} confirmed candles downloaded; {bars} required")
    return ordered[-bars:]


def save_csv(candles: list[dict[str, str]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(candles[0]))
        writer.writeheader()
        writer.writerows(candles)


def main() -> int:
    parser = argparse.ArgumentParser(description="Download public confirmed OKX candles for Elite Final backtests.")
    parser.add_argument("--symbol", default=None, help="Compatibilité : un instrument unique.")
    parser.add_argument("--symbols", default="BTC-USDC,ETH-USDC,SOL-USDC", help="Instruments séparés par des virgules.")
    parser.add_argument("--bars", type=int, default=2000)
    parser.add_argument("--timeframes", default="5m,15m,1H,4H")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "data" / "market")
    args = parser.parse_args()
    if args.bars < 200:
        raise SystemExit("--bars must be at least 200")
    symbols = [args.symbol] if args.symbol else [item.strip() for item in args.symbols.split(",") if item.strip()]
    if not symbols:
        raise SystemExit("at least one symbol is required")
    for symbol in symbols:
        for timeframe in (item.strip() for item in args.timeframes.split(",") if item.strip()):
            candles = fetch_candles(symbol, timeframe, args.bars)
            output = args.out_dir / f"okx_{symbol}_{timeframe}_{args.bars}.csv"
            save_csv(candles, output)
            print(f"{symbol} {timeframe}: {len(candles)} confirmed candles -> {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
