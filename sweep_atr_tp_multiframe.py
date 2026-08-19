#!/usr/bin/env python3
"""Sweep ATR stop and percentage take-profit settings on real local OHLCV data.

The script reports independent results per timeframe. It intentionally does not
sum P&L across timeframes because the simulated positions can overlap in time.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from itertools import product
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backtesting.historical import BacktestConfig, HistoricalBacktester
from backtesting.multiframe import parse_timeframes


def parse_float_grid(value: str | Iterable[float]) -> tuple[float, ...]:
    """Parse a positive comma-separated parameter grid without silent coercion."""
    if not isinstance(value, str):
        parsed = tuple(float(item) for item in value)
    else:
        try:
            parsed = tuple(float(item.strip()) for item in value.split(",") if item.strip())
        except ValueError as exc:
            raise ValueError("grid values must be numeric") from exc
    if not parsed or any(item <= 0 for item in parsed):
        raise ValueError("grid values must be non-empty positive numbers")
    return parsed


def dataset_path(data_dir: Path, symbol: str, timeframe: str, bars: int) -> Path:
    return data_dir / f"okx_{symbol}_{timeframe}_{bars}.csv"


def run_sweep(
    *,
    timeframes: tuple[str, ...],
    atr_stops: tuple[float, ...],
    take_profits: tuple[float, ...],
    data_dir: Path,
    symbol: str,
    capital: float,
    bars: int,
    fee_bps: float,
    pos_frac: float,
    min_trades: int,
) -> list[dict]:
    """Run the requested grid on each timeframe and return flat audit-ready rows."""
    candle_sets: dict[str, list[dict]] = {}
    for timeframe in timeframes:
        path = dataset_path(data_dir, symbol, timeframe, bars)
        candles = HistoricalBacktester.load_candles(path, timeframe=timeframe)
        if len(candles) < bars:
            raise ValueError(f"{timeframe}: {len(candles)} candles found; {bars} required")
        candle_sets[timeframe] = candles[-bars:]

    rows: list[dict] = []
    for timeframe, atr_sl, target_tp_pct in product(timeframes, atr_stops, take_profits):
        result = HistoricalBacktester(
            BacktestConfig(
                capital=capital,
                pos_frac=pos_frac,
                fee_bps=fee_bps,
                atr_sl=atr_sl,
                symbol=symbol,
                target_tp_pct=target_tp_pct,
                # A parameter sweep should observe the whole dataset; no session stop.
                net_target_usd=None,
            )
        ).run(candle_sets[timeframe]).to_dict(include_curve=False)
        profit_factor = result.get("profit_factor")
        row = {
            "timeframe": timeframe,
            "atr_stop": atr_sl,
            "take_profit_pct": target_tp_pct,
            "bars": result["bars"],
            "trades": result["trades"],
            "net_pnl_usdc": result["total_pnl"],
            "return_pct": result["return_pct"],
            "final_equity": result["final_equity"],
            "max_drawdown_pct": result["max_drawdown_pct"],
            "winrate_pct": result["winrate_pct"],
            "profit_factor": profit_factor,
            "eligible": bool(result["trades"] >= min_trades and profit_factor is not None),
            "exit_sl": result["exit_reasons"].get("SL", 0),
            "exit_tp": result["exit_reasons"].get("TP", 0),
            "exit_signal": result["exit_reasons"].get("SIGNAL", 0),
        }
        rows.append(row)
    return rows


def sort_rows(rows: list[dict]) -> list[dict]:
    """Rank by eligibility, net P&L, profit factor, then lower drawdown."""
    return sorted(
        rows,
        key=lambda row: (
            row["eligible"],
            row["net_pnl_usdc"],
            row["profit_factor"] if row["profit_factor"] is not None else -1.0,
            -row["max_drawdown_pct"],
        ),
        reverse=True,
    )


def save_results(rows: list[dict], output: Path, metadata: dict) -> tuple[Path, Path]:
    output.parent.mkdir(parents=True, exist_ok=True)
    json_path = output.with_suffix(".json")
    csv_path = output.with_suffix(".csv")
    json_path.write_text(json.dumps({"metadata": metadata, "rows": rows}, indent=2), encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else [])
        writer.writeheader()
        writer.writerows(rows)
    return json_path, csv_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Sweep ATR stops and percentage take-profits across Elite Final timeframes.")
    parser.add_argument("--symbol", default="BTC-USDC")
    parser.add_argument("--timeframes", default="5m,15m,1H,4H")
    parser.add_argument("--atr-stops", default="1.0,1.2,1.5,2.0")
    parser.add_argument("--take-profits", default="1.4,1.8,2.2")
    parser.add_argument("--capital", type=float, default=500.0)
    parser.add_argument("--bars", type=int, default=2000)
    parser.add_argument("--fee-bps", type=float, default=8.0)
    parser.add_argument("--pos-frac", type=float, default=0.15)
    parser.add_argument("--min-trades", type=int, default=10)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data" / "market")
    parser.add_argument("--output", type=Path, default=ROOT / "reports" / "atr_tp_sweep_2000")
    args = parser.parse_args()

    if args.bars < 200 or args.capital <= 0 or args.pos_frac <= 0 or args.fee_bps < 0 or args.min_trades < 1:
        raise SystemExit("invalid capital, bars, fee, position fraction, or minimum trades")
    timeframes = parse_timeframes(args.timeframes)
    atr_stops = parse_float_grid(args.atr_stops)
    take_profits = parse_float_grid(args.take_profits)
    rows = sort_rows(
        run_sweep(
            timeframes=timeframes,
            atr_stops=atr_stops,
            take_profits=take_profits,
            data_dir=args.data_dir,
            symbol=args.symbol,
            capital=args.capital,
            bars=args.bars,
            fee_bps=args.fee_bps,
            pos_frac=args.pos_frac,
            min_trades=args.min_trades,
        )
    )
    metadata = {
        "symbol": args.symbol,
        "timeframes": timeframes,
        "bars_per_timeframe": args.bars,
        "capital_per_timeframe": args.capital,
        "fee_bps_per_side": args.fee_bps,
        "position_fraction": args.pos_frac,
        "atr_stop_grid": atr_stops,
        "take_profit_pct_grid": take_profits,
        "minimum_trades_for_eligibility": args.min_trades,
        "warning": "Rankings are in-sample research results, not a profitability claim. Validate selections on separate chronological data.",
    }
    json_path, csv_path = save_results(rows, args.output, metadata)
    print(f"Combinations: {len(rows)}; results: {json_path} and {csv_path}")
    for row in rows[: min(12, len(rows))]:
        print(
            f"{row['timeframe']:>3} ATR={row['atr_stop']:<3} TP={row['take_profit_pct']:<3}% "
            f"trades={row['trades']:<3} pnl={row['net_pnl_usdc']:<7} "
            f"PF={row['profit_factor']} DD={row['max_drawdown_pct']} eligible={row['eligible']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
