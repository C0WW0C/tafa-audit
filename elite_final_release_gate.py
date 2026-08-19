#!/usr/bin/env python3
"""Release gate for Elite Final: real public datasets, 2,000 bars and 500 USDC paper mode."""
from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TIMEFRAMES = ("5m", "15m", "1H", "4H")
REQUIRED = (
    "run_elite_final_paper.py",
    ".env.elite-final-paper.example",
    "backtesting/multiframe.py",
    "scripts/fetch_okx_history.py",
    "scripts/run_elite_final_backtest.py",
    "ELITE_FINAL_RUNBOOK.md",
)


def candle_count(path: Path) -> int:
    with path.open(newline="", encoding="utf-8") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate TAFA Elite Final paper/demo release.")
    parser.add_argument("--with-smoke", action="store_true", help="Also run the public OKX paper/demo smoke test.")
    args = parser.parse_args()
    errors: list[str] = []
    for rel in REQUIRED:
        if not (ROOT / rel).is_file():
            errors.append(f"missing Elite Final file: {rel}")
    for timeframe in TIMEFRAMES:
        dataset = ROOT / "data" / "market" / f"okx_BTC-USDC_{timeframe}_2000.csv"
        if not dataset.is_file():
            errors.append(f"missing dataset: {dataset.name}")
        elif candle_count(dataset) != 2000:
            errors.append(f"{dataset.name}: expected 2000 candles")

    env = os.environ.copy()
    env.update(
        {
            "TAFA_MODE": "DEMO",
            "ENABLE_LIVE": "false",
            "LIVE_CONFIRM": "",
            "TAFA_PAPER_ONLY": "true",
            "TAFA_PAPER_CAPITAL": "500",
            "TAFA_ENGINE": "native",
            "PYTHONPATH": str(ROOT),
        }
    )
    print("Elite Final gate: DEMO/PAPER, capital 500 USDC, 2,000 candles per timeframe")
    if not errors:
        command = [sys.executable, "scripts/m7_release_gate.py"]
        if args.with_smoke:
            command.append("--with-smoke")
        if subprocess.run(command, cwd=ROOT, env=env).returncode:
            errors.append("M7 release gate failed")
    if not errors and subprocess.run(
        [sys.executable, "scripts/run_elite_final_backtest.py"], cwd=ROOT, env=env
    ).returncode:
        errors.append("Elite Final backtest failed")

    if errors:
        print("ELITE FINAL RELEASE GATE: FAILED")
        for error in errors:
            print(" -", error)
        return 1
    print("ELITE FINAL RELEASE GATE: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
