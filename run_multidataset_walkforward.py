#!/usr/bin/env python3
"""Run TAFA walk-forward validation across multiple validated OHLCV datasets."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backtesting.historical import HistoricalBacktester
from scripts.sweep_atr_tp_multiframe import dataset_path, parse_float_grid
from scripts.walk_forward_atr_tp import validate_timeframe


def split_values(value: str) -> tuple[str, ...]:
    values = tuple(item.strip() for item in value.split(",") if item.strip())
    if not values:
        raise ValueError("at least one value is required")
    return values


def run_matrix(
    *, symbols: tuple[str, ...], timeframes: tuple[str, ...], data_dir: Path, bars: int,
    atr_stops: tuple[float, ...], take_profits: tuple[float, ...], capital: float,
    pos_frac: float, fee_bps: float, train_ratio: float, min_train_trades: int,
    min_train_profit_factor: float, min_test_trades: int, min_test_profit_factor: float,
    max_test_drawdown_pct: float,
) -> list[dict]:
    results: list[dict] = []
    for symbol in symbols:
        for timeframe in timeframes:
            path = dataset_path(data_dir, symbol, timeframe, bars)
            if not path.is_file():
                results.append({"symbol": symbol, "timeframe": timeframe, "status": "missing_dataset", "path": str(path)})
                continue
            candles = HistoricalBacktester.load_candles(path, timeframe=timeframe)[-bars:]
            if len(candles) != bars:
                results.append({"symbol": symbol, "timeframe": timeframe, "status": "insufficient_bars", "path": str(path), "bars": len(candles)})
                continue
            item = validate_timeframe(
                timeframe=timeframe, candles=candles, atr_stops=atr_stops, take_profits=take_profits,
                train_ratio=train_ratio, capital=capital, pos_frac=pos_frac, fee_bps=fee_bps,
                symbol=symbol, min_train_trades=min_train_trades,
                min_train_profit_factor=min_train_profit_factor, min_test_trades=min_test_trades,
                min_test_profit_factor=min_test_profit_factor, max_test_drawdown_pct=max_test_drawdown_pct,
            )
            item["symbol"] = symbol
            item["path"] = str(path)
            results.append(item)
    return results


def write_reports(results: list[dict], output: Path, metadata: dict) -> tuple[Path, Path]:
    output.parent.mkdir(parents=True, exist_ok=True)
    json_path, csv_path = output.with_suffix(".json"), output.with_suffix(".csv")
    json_path.write_text(json.dumps({"metadata": metadata, "results": results}, indent=2), encoding="utf-8")
    columns = ["symbol", "timeframe", "status", "train_bars", "test_bars", "atr_stop", "take_profit_pct", "train_pnl_usdc", "test_pnl_usdc", "test_profit_factor", "test_max_drawdown_pct"]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for item in results:
            selection = item.get("selection") or {}
            train, test = selection.get("train", {}), selection.get("test", {})
            writer.writerow({
                "symbol": item.get("symbol"), "timeframe": item.get("timeframe"), "status": item.get("status"),
                "train_bars": item.get("train_bars"), "test_bars": item.get("test_bars"),
                "atr_stop": selection.get("atr_stop"), "take_profit_pct": selection.get("take_profit_pct"),
                "train_pnl_usdc": train.get("net_pnl_usdc"), "test_pnl_usdc": test.get("net_pnl_usdc"),
                "test_profit_factor": test.get("profit_factor"), "test_max_drawdown_pct": test.get("max_drawdown_pct"),
            })
    return json_path, csv_path


def main() -> int:
    parser = argparse.ArgumentParser(description="TAFA multi-dataset chronological walk-forward validation.")
    parser.add_argument("--symbols", default="BTC-USDC,ETH-USDC,SOL-USDC")
    parser.add_argument("--timeframes", default="1H,4H")
    parser.add_argument("--bars", type=int, default=2000)
    parser.add_argument("--atr-stops", default="1.0,1.2,1.5,2.0")
    parser.add_argument("--take-profits", default="1.4,1.8,2.2")
    parser.add_argument("--capital", type=float, default=500.0)
    parser.add_argument("--pos-frac", type=float, default=0.15)
    parser.add_argument("--fee-bps", type=float, default=8.0)
    parser.add_argument("--train-ratio", type=float, default=0.6)
    parser.add_argument("--min-train-trades", type=int, default=8)
    parser.add_argument("--min-train-profit-factor", type=float, default=1.0)
    parser.add_argument("--min-test-trades", type=int, default=5)
    parser.add_argument("--min-test-profit-factor", type=float, default=1.1)
    parser.add_argument("--max-test-drawdown-pct", type=float, default=2.0)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data" / "market")
    parser.add_argument("--output", type=Path, default=ROOT / "reports" / "multidataset_walkforward_2000")
    args = parser.parse_args()
    symbols, timeframes = split_values(args.symbols), split_values(args.timeframes)
    atr_stops, take_profits = parse_float_grid(args.atr_stops), parse_float_grid(args.take_profits)
    results = run_matrix(
        symbols=symbols, timeframes=timeframes, data_dir=args.data_dir, bars=args.bars,
        atr_stops=atr_stops, take_profits=take_profits, capital=args.capital,
        pos_frac=args.pos_frac, fee_bps=args.fee_bps, train_ratio=args.train_ratio,
        min_train_trades=args.min_train_trades, min_train_profit_factor=args.min_train_profit_factor,
        min_test_trades=args.min_test_trades, min_test_profit_factor=args.min_test_profit_factor,
        max_test_drawdown_pct=args.max_test_drawdown_pct,
    )
    metadata = {
        "symbols": symbols, "timeframes": timeframes, "bars_per_dataset": args.bars,
        "capital_per_dataset": args.capital, "fee_bps_per_side": args.fee_bps,
        "train_ratio": args.train_ratio, "atr_stop_grid": atr_stops,
        "take_profit_pct_grid": take_profits,
        "warning": "Datasets and outcomes are research evidence only; no real-order action is implied.",
    }
    json_path, csv_path = write_reports(results, args.output, metadata)
    accepted = sum(1 for item in results if item.get("status") == "accepted_for_paper_research")
    print(f"datasets={len(results)} accepted={accepted} results={json_path} {csv_path}")
    for item in results:
        print(f"{item.get('symbol')} {item.get('timeframe')}: {item.get('status')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
