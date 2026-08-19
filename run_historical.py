# ============================================================
# TAFA V7 PRO — CLI historical backtest
# ============================================================
"""Usage:
    python -m backtesting.run_historical --tf 15m
    python -m backtesting.run_historical --csv data/market/okx_BTC-USDC_15m.csv --capital 1000
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backtesting.historical import BacktestConfig, HistoricalBacktester


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="TAFA V7 PRO historical backtest")
    ap.add_argument("--csv", default=None, help="OHLCV CSV path")
    ap.add_argument("--tf", default="15m", help="Timeframe when --csv omitted (5m/15m/1h/4h/1d)")
    ap.add_argument("--capital", type=float, default=None, help="Starting capital (default: config)")
    ap.add_argument("--pos-frac", type=float, default=0.15, help="Fraction of equity per trade")
    ap.add_argument("--fee-bps", type=float, default=8.0, help="Fee in basis points per side")
    ap.add_argument("--train-ratio", type=float, default=0.2, help="Warm-up ratio before trading")
    ap.add_argument("--atr-sl", type=float, default=2.0, help="ATR multiple for stop-loss")
    ap.add_argument("--atr-tp", type=float, default=3.5, help="ATR multiple for take-profit")
    ap.add_argument("--out", default=None, help="Report JSON output path")
    ap.add_argument("--curve", action="store_true", help="Include equity curve in report")
    args = ap.parse_args(argv)

    cfg = BacktestConfig(
        capital=args.capital if args.capital is not None else BacktestConfig().capital,
        pos_frac=args.pos_frac,
        fee_bps=args.fee_bps,
        train_ratio=args.train_ratio,
        atr_sl=args.atr_sl,
        atr_tp=args.atr_tp,
    )
    bt = HistoricalBacktester(cfg)
    result = bt.run_file(args.csv, timeframe=args.tf)
    path = bt.save_report(result, out=args.out, include_curve=args.curve)
    print(json.dumps(result.to_dict(include_curve=False), indent=2))
    print(f"\n[report saved] {path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
