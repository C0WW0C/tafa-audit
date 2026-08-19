#!/usr/bin/env python3
"""Run the Elite Final independent multi-timeframe paper backtest."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backtesting.multiframe import MultiTimeframeBacktester, MultiTimeframeConfig, parse_timeframes


def main() -> int:
    parser = argparse.ArgumentParser(description="TAFA Elite Final multi-timeframe backtest.")
    parser.add_argument("--symbol", default="BTC-USDC")
    parser.add_argument("--capital", type=float, default=500.0)
    parser.add_argument("--bars", type=int, default=2000)
    parser.add_argument("--timeframes", default="5m,15m,1H,4H")
    parser.add_argument("--tp-pct", type=float, default=1.8, help="Take-profit percentage for this paper research profile.")
    parser.add_argument("--net-target-usd", type=float, default=5.0, help="Stop new simulated entries after this net session profit.")
    parser.add_argument("--pos-frac", type=float, default=0.15, help="Maximum paper capital fraction per simulated entry.")
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data" / "market")
    parser.add_argument("--output", type=Path, default=ROOT / "reports" / "elite_final_mtf_2000.json")
    args = parser.parse_args()
    timeframes = parse_timeframes(args.timeframes)
    config = MultiTimeframeConfig(
        capital=args.capital,
        bars=args.bars,
        timeframes=timeframes,
        symbol=args.symbol,
        target_tp_pct=args.tp_pct,
        net_target_usd=args.net_target_usd,
        pos_frac=args.pos_frac,
    )
    files = {
        timeframe: args.data_dir / f"okx_{args.symbol}_{timeframe}_{args.bars}.csv"
        for timeframe in timeframes
    }
    result = MultiTimeframeBacktester(config).run_files(files)
    saved = MultiTimeframeBacktester.save_report(result, args.output)
    print(f"Elite Final report: {saved}")
    for timeframe, report in result.results.items():
        print(
            f"{timeframe}: bars={report['bars']} trades={report['trades']} "
            f"equity={report['final_equity']} return={report['return_pct']}% "
            f"net_target_reached={report['net_target_reached']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
