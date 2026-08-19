"""Probe TAFA's live local endpoint wiring with stored BTC-USDC OHLCV data.

It submits no order and only prints the consensus result.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data" / "market" / "okx_BTC-USDC_4H_2000.csv"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai.foundation_models import FoundationModelConsensus


class History:
    def __init__(self, rows: list[dict[str, str]]) -> None:
        self.opens = [float(row["open"]) for row in rows]
        self.highs = [float(row["high"]) for row in rows]
        self.lows = [float(row["low"]) for row in rows]
        self.closes = [float(row["close"]) for row in rows]
        self.volumes = [float(row["volume"]) for row in rows]


def main() -> None:
    with DATASET.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))[-240:]
    decision = FoundationModelConsensus().evaluate(
        symbol="BTC-USDC",
        timeframe="4h",
        strategy=History(rows),
        candidate_signal="BUY",
    )
    print(json.dumps(decision.public(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
