#!/usr/bin/env python3
"""Multi-dataset TSMOM backtests + simple walk-forward OOS.

Usage:
  python3 scripts/run_tsmom_backtests.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backtesting.historical import BacktestConfig, HistoricalBacktester

DATASETS = [
    ("BTC", "4H", "data/market/okx_BTC-USDC_4H_2000.csv"),
    ("BTC", "1H", "data/market/okx_BTC-USDC_1H_2000.csv"),
    ("BTC", "15m", "data/market/okx_BTC-USDC_15m_2000.csv"),
    ("ETH", "4H", "data/market/okx_ETH-USDC_4H_2000.csv"),
    ("ETH", "1H", "data/market/okx_ETH-USDC_1H_2000.csv"),
    ("ETH", "15m", "data/market/okx_ETH-USDC_15m_2000.csv"),
    ("SOL", "4H", "data/market/okx_SOL-USDC_4H_2000.csv"),
    ("SOL", "1H", "data/market/okx_SOL-USDC_1H_2000.csv"),
    ("SOL", "15m", "data/market/okx_SOL-USDC_15m_2000.csv"),
]


def run_one(path: Path, symbol: str, tf: str, capital: float = 1000.0) -> dict:
    cfg = BacktestConfig(
        capital=capital,
        pos_frac=0.20,
        fee_bps=8.0,
        train_ratio=0.25,
        atr_sl=1.5,
        atr_tp=3.0,
        symbol=f"{symbol}-USDC",
    )
    bt = HistoricalBacktester(cfg)
    candles = bt.load_candles(path, timeframe=tf.lower())
    full = bt.run(candles)
    full.source = str(path.name)
    full.symbol = cfg.symbol
    full.timeframe = tf
    full.bars = len(candles)
    if candles:
        full.from_ts = str(candles[0].get("ts") or "")
        full.to_ts = str(candles[-1].get("ts") or "")

    # Walk-forward: first 70% warm+IS metrics ignored; last 30% pure OOS replay
    n = len(candles)
    split = int(n * 0.70)
    oos_candles = candles[: max(split, 80)] + candles[split:]  # keep history for indicators
    # Actually: warm on first 70%, trade only on last 30%
    cfg_oos = BacktestConfig(
        capital=capital,
        pos_frac=0.20,
        fee_bps=8.0,
        train_ratio=max(0.70, (split / n) if n else 0.7),
        atr_sl=1.5,
        atr_tp=3.0,
        symbol=cfg.symbol,
    )
    oos = HistoricalBacktester(cfg_oos).run(candles)
    oos.source = path.name
    oos.symbol = cfg.symbol
    oos.timeframe = tf

    return {
        "symbol": cfg.symbol,
        "tf": tf,
        "file": path.name,
        "bars": len(candles),
        "full": full.to_dict(include_curve=False),
        "oos": oos.to_dict(include_curve=False),
    }


def main() -> int:
    results = []
    print("=" * 72)
    print("TAFA TSMOM multi-dataset backtests (fees 8 bps/side, pos 20%)")
    print("=" * 72)
    hdr = f"{'SYM':8} {'TF':5} {'bars':>5} | {'n':>3} {'WR%':>6} {'PnL':>9} {'Ret%':>7} {'DD%':>6} {'PF':>6} | OOS n/WR/Ret"
    print(hdr)
    print("-" * 72)

    for sym, tf, rel in DATASETS:
        path = ROOT / rel
        if not path.exists():
            print(f"{sym:8} {tf:5} MISSING {rel}")
            continue
        try:
            r = run_one(path, sym, tf)
            results.append(r)
            f, o = r["full"], r["oos"]
            pf = f.get("profit_factor")
            pf_s = f"{pf:.2f}" if isinstance(pf, (int, float)) else "—"
            print(
                f"{sym:8} {tf:5} {r['bars']:5d} | "
                f"{f['trades']:3d} {f['winrate_pct']:6.1f} {f['total_pnl']:9.2f} "
                f"{f['return_pct']:7.2f} {f['max_drawdown_pct']:6.2f} {pf_s:>6} | "
                f"{o['trades']}/{o['winrate_pct']:.0f}%/{o['return_pct']:.1f}%"
            )
        except Exception as exc:
            print(f"{sym:8} {tf:5} ERROR {exc}")

    out = ROOT / "reports" / "tsmom_multidataset_backtest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"results": results}, indent=2, default=str), encoding="utf-8")
    print("-" * 72)
    print(f"Report → {out}")

    # Summary aggregates
    if results:
        rets = [r["full"]["return_pct"] for r in results]
        oos_rets = [r["oos"]["return_pct"] for r in results]
        pos = sum(1 for x in rets if x > 0)
        oos_pos = sum(1 for x in oos_rets if x > 0)
        print(f"Full  : {pos}/{len(rets)} positive return | mean ret {sum(rets)/len(rets):.2f}%")
        print(f"OOS70 : {oos_pos}/{len(oos_rets)} positive return | mean ret {sum(oos_rets)/len(oos_rets):.2f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
