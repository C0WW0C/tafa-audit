#!/usr/bin/env python3
"""Chronological ATR/TP selection and out-of-sample validation for TAFA Elite.

Parameters are selected only on the earlier train segment and evaluated unchanged
on the later test segment. Results are always separated by timeframe.
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
from scripts.sweep_atr_tp_multiframe import dataset_path, parse_float_grid


def chronological_split(candles: list[dict], train_ratio: float) -> tuple[list[dict], list[dict]]:
    """Split ordered candles without overlap, preserving chronological order."""
    if not 0.5 <= train_ratio <= 0.8:
        raise ValueError("train_ratio must be between 0.5 and 0.8")
    pivot = int(len(candles) * train_ratio)
    train, test = candles[:pivot], candles[pivot:]
    if len(train) < 200 or len(test) < 200:
        raise ValueError("both train and test windows must contain at least 200 candles")
    return train, test


def evaluate(
    candles: list[dict],
    *,
    capital: float,
    pos_frac: float,
    fee_bps: float,
    atr_stop: float,
    take_profit_pct: float,
    symbol: str,
) -> dict:
    result = HistoricalBacktester(
        BacktestConfig(
            capital=capital,
            pos_frac=pos_frac,
            fee_bps=fee_bps,
            atr_sl=atr_stop,
            symbol=symbol,
            target_tp_pct=take_profit_pct,
            net_target_usd=None,
        )
    ).run(candles).to_dict(include_curve=False)
    return {
        "trades": result["trades"],
        "net_pnl_usdc": result["total_pnl"],
        "return_pct": result["return_pct"],
        "final_equity": result["final_equity"],
        "max_drawdown_pct": result["max_drawdown_pct"],
        "winrate_pct": result["winrate_pct"],
        "profit_factor": result["profit_factor"],
        "exit_reasons": result["exit_reasons"],
    }


def rank_train(rows: list[dict], min_trades: int, min_profit_factor: float) -> list[dict]:
    """Rank only configurations with enough trades and a defined profit factor."""
    for row in rows:
        profit_factor = row["train"]["profit_factor"]
        row["train_eligible"] = bool(
            row["train"]["trades"] >= min_trades
            and row["train"]["net_pnl_usdc"] > 0
            and profit_factor is not None
            and profit_factor >= min_profit_factor
        )
    return sorted(
        rows,
        key=lambda row: (
            row["train_eligible"],
            row["train"]["net_pnl_usdc"],
            row["train"]["profit_factor"] if row["train"]["profit_factor"] is not None else -1.0,
            -row["train"]["max_drawdown_pct"],
        ),
        reverse=True,
    )


def validate_timeframe(
    *,
    timeframe: str,
    candles: list[dict],
    atr_stops: tuple[float, ...],
    take_profits: tuple[float, ...],
    train_ratio: float,
    capital: float,
    pos_frac: float,
    fee_bps: float,
    symbol: str,
    min_train_trades: int,
    min_train_profit_factor: float,
    min_test_trades: int,
    min_test_profit_factor: float,
    max_test_drawdown_pct: float,
) -> dict:
    train_candles, test_candles = chronological_split(candles, train_ratio)
    candidates: list[dict] = []
    for atr_stop, take_profit_pct in product(atr_stops, take_profits):
        candidates.append(
            {
                "atr_stop": atr_stop,
                "take_profit_pct": take_profit_pct,
                "train": evaluate(
                    train_candles, capital=capital, pos_frac=pos_frac, fee_bps=fee_bps,
                    atr_stop=atr_stop, take_profit_pct=take_profit_pct, symbol=symbol,
                ),
            }
        )
    ranked = rank_train(candidates, min_train_trades, min_train_profit_factor)
    selected = next((row for row in ranked if row["train_eligible"]), None)
    result: dict = {
        "timeframe": timeframe,
        "train_bars": len(train_candles),
        "test_bars": len(test_candles),
        "train_period": {"from": train_candles[0].get("ts"), "to": train_candles[-1].get("ts")},
        "test_period": {"from": test_candles[0].get("ts"), "to": test_candles[-1].get("ts")},
        "candidate_count": len(candidates),
        "selection": None,
        "status": "rejected_insufficient_train_evidence",
        "top_train_candidates": ranked[:3],
    }
    if selected is None:
        return result
    test = evaluate(
        test_candles, capital=capital, pos_frac=pos_frac, fee_bps=fee_bps,
        atr_stop=selected["atr_stop"], take_profit_pct=selected["take_profit_pct"], symbol=symbol,
    )
    accepted = bool(
        test["trades"] >= min_test_trades
        and test["net_pnl_usdc"] > 0
        and test["profit_factor"] is not None
        and test["profit_factor"] >= min_test_profit_factor
        and test["max_drawdown_pct"] <= max_test_drawdown_pct
    )
    result["selection"] = {
        "atr_stop": selected["atr_stop"],
        "take_profit_pct": selected["take_profit_pct"],
        "train": selected["train"],
        "test": test,
    }
    result["status"] = "accepted_for_paper_research" if accepted else "rejected_out_of_sample"
    return result


def write_reports(results: list[dict], output: Path, metadata: dict) -> tuple[Path, Path]:
    output.parent.mkdir(parents=True, exist_ok=True)
    json_path, csv_path = output.with_suffix(".json"), output.with_suffix(".csv")
    json_path.write_text(json.dumps({"metadata": metadata, "results": results}, indent=2), encoding="utf-8")
    columns = [
        "timeframe", "status", "train_bars", "test_bars", "atr_stop", "take_profit_pct",
        "train_trades", "train_pnl_usdc", "train_profit_factor", "test_trades", "test_pnl_usdc",
        "test_profit_factor", "test_max_drawdown_pct",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for item in results:
            selection = item.get("selection") or {}
            train, test = selection.get("train", {}), selection.get("test", {})
            writer.writerow(
                {
                    "timeframe": item["timeframe"], "status": item["status"],
                    "train_bars": item["train_bars"], "test_bars": item["test_bars"],
                    "atr_stop": selection.get("atr_stop"), "take_profit_pct": selection.get("take_profit_pct"),
                    "train_trades": train.get("trades"), "train_pnl_usdc": train.get("net_pnl_usdc"),
                    "train_profit_factor": train.get("profit_factor"), "test_trades": test.get("trades"),
                    "test_pnl_usdc": test.get("net_pnl_usdc"), "test_profit_factor": test.get("profit_factor"),
                    "test_max_drawdown_pct": test.get("max_drawdown_pct"),
                }
            )
    return json_path, csv_path


def main() -> int:
    parser = argparse.ArgumentParser(description="TAFA Elite chronological ATR/TP walk-forward validation.")
    parser.add_argument("--symbol", default="BTC-USDC")
    parser.add_argument("--timeframes", default="5m,15m,1H,4H")
    parser.add_argument("--atr-stops", default="1.0,1.2,1.5,2.0")
    parser.add_argument("--take-profits", default="1.4,1.8,2.2")
    parser.add_argument("--capital", type=float, default=500.0)
    parser.add_argument("--bars", type=int, default=2000)
    parser.add_argument("--train-ratio", type=float, default=0.6)
    parser.add_argument("--fee-bps", type=float, default=8.0)
    parser.add_argument("--pos-frac", type=float, default=0.15)
    parser.add_argument("--min-train-trades", type=int, default=8)
    parser.add_argument("--min-train-profit-factor", type=float, default=1.0)
    parser.add_argument("--min-test-trades", type=int, default=5)
    parser.add_argument("--min-test-profit-factor", type=float, default=1.1)
    parser.add_argument("--max-test-drawdown-pct", type=float, default=2.0)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data" / "market")
    parser.add_argument("--output", type=Path, default=ROOT / "reports" / "walk_forward_atr_tp_2000")
    args = parser.parse_args()
    if args.bars < 400 or args.capital <= 0 or args.fee_bps < 0 or args.pos_frac <= 0:
        raise SystemExit("invalid backtest settings")
    timeframes = parse_timeframes(args.timeframes)
    atr_stops, take_profits = parse_float_grid(args.atr_stops), parse_float_grid(args.take_profits)
    results: list[dict] = []
    for timeframe in timeframes:
        path = dataset_path(args.data_dir, args.symbol, timeframe, args.bars)
        candles = HistoricalBacktester.load_candles(path, timeframe=timeframe)[-args.bars:]
        if len(candles) != args.bars:
            raise SystemExit(f"{timeframe}: expected {args.bars} candles in {path}")
        results.append(
            validate_timeframe(
                timeframe=timeframe, candles=candles, atr_stops=atr_stops, take_profits=take_profits,
                train_ratio=args.train_ratio, capital=args.capital, pos_frac=args.pos_frac,
                fee_bps=args.fee_bps, symbol=args.symbol, min_train_trades=args.min_train_trades,
                min_train_profit_factor=args.min_train_profit_factor,
                min_test_trades=args.min_test_trades, min_test_profit_factor=args.min_test_profit_factor,
                max_test_drawdown_pct=args.max_test_drawdown_pct,
            )
        )
    metadata = {
        "symbol": args.symbol, "timeframes": timeframes, "bars_per_timeframe": args.bars,
        "train_ratio": args.train_ratio, "fee_bps_per_side": args.fee_bps,
        "capital_per_timeframe": args.capital, "position_fraction": args.pos_frac,
        "train_selection_grid": {"atr_stop": atr_stops, "take_profit_pct": take_profits},
        "acceptance_gate": {
            "min_train_profit_factor": args.min_train_profit_factor,
            "min_test_trades": args.min_test_trades, "min_test_profit_factor": args.min_test_profit_factor,
            "max_test_drawdown_pct": args.max_test_drawdown_pct, "positive_net_pnl_required": True,
        },
        "warning": "Out-of-sample acceptance is evidence for paper research only, not a live-trading approval.",
    }
    json_path, csv_path = write_reports(results, args.output, metadata)
    print(f"Walk-forward results: {json_path} and {csv_path}")
    for item in results:
        selection = item.get("selection") or {}
        print(f"{item['timeframe']}: {item['status']} selection={selection.get('atr_stop')}/{selection.get('take_profit_pct')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
