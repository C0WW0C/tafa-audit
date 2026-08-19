# ============================================================
# TAFA V7 PRO — Walk-forward backtest (compat wrapper)
# ============================================================
from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backtesting.historical import BacktestConfig, HistoricalBacktester, run_historical
from data.loader import default_dataset


def load_candles(path: str | None = None):
    return HistoricalBacktester.load_candles(path)


def run_backtest(candles, capital: float = 1000.0, **kwargs):
    allowed = ("pos_frac", "fee_bps", "train_ratio", "atr_sl", "atr_tp", "symbol")
    cfg = BacktestConfig(
        capital=capital,
        **{k: v for k, v in kwargs.items() if k in allowed},
    )
    return HistoricalBacktester(cfg).run(candles).to_dict()


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=None)
    ap.add_argument("--tf", default="15m")
    args = ap.parse_args()
    path = args.csv or str(default_dataset(args.tf))
    report = run_historical(csv=path, timeframe=args.tf)
    print(json.dumps(report, indent=2))
