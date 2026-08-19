#!/usr/bin/env python3
"""Validate and register local OHLCV datasets for reproducible TAFA backtests."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {"ts", "open", "high", "low", "close", "volume", "source", "symbol", "timeframe"}


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(path: Path) -> dict:
    errors: list[str] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not REQUIRED.issubset(reader.fieldnames):
            return {"path": str(path), "status": "invalid", "errors": ["missing required columns"]}
        rows = list(reader)
    timestamps: list[int] = []
    for index, row in enumerate(rows, start=2):
        try:
            timestamp = int(row["ts"])
            opn, high, low, close, volume = (float(row[key]) for key in ("open", "high", "low", "close", "volume"))
            if timestamp <= 0 or min(opn, high, low, close, volume) < 0 or high < max(opn, low, close) or low > min(opn, high, close):
                errors.append(f"row {index}: invalid OHLCV")
            timestamps.append(timestamp)
        except (ValueError, TypeError):
            errors.append(f"row {index}: invalid numeric data")
    monotonic = all(right > left for left, right in zip(timestamps, timestamps[1:]))
    if not monotonic:
        errors.append("timestamps are not strictly increasing")
    first = rows[0] if rows else {}
    return {
        "path": str(path), "status": "valid" if not errors else "invalid", "errors": errors[:20],
        "bars": len(rows), "from_ts": timestamps[0] if timestamps else None, "to_ts": timestamps[-1] if timestamps else None,
        "source": first.get("source"), "symbol": first.get("symbol"), "timeframe": first.get("timeframe"),
        "content_hash": file_hash(path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate OHLCV CSV datasets and create an auditable manifest.")
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data" / "market")
    parser.add_argument("--pattern", default="okx_*_2000.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "market" / "dataset_manifest.json")
    args = parser.parse_args()
    datasets = [validate(path) for path in sorted(args.data_dir.glob(args.pattern))]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"datasets": datasets}, indent=2), encoding="utf-8")
    invalid = [item for item in datasets if item["status"] != "valid"]
    print(f"datasets={len(datasets)} valid={len(datasets) - len(invalid)} invalid={len(invalid)} manifest={args.output}")
    return 1 if invalid else 0


if __name__ == "__main__":
    raise SystemExit(main())
