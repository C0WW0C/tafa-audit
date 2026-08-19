#!/usr/bin/env python3
"""
Smoke audit — closed-bars only (anti look-ahead).
Run from project root:
  python3 scripts/audit_closed_bars_smoke.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    from trading.intelligent_strategy import IntelligentStrategy

    s = IntelligentStrategy()
    errors: list[str] = []

    # 1) Strategy identity
    if "CLOSED" not in (s.name or "") and "V7" not in (s.name or ""):
        errors.append(f"expected V7_CLOSED name, got {s.name!r}")

    # 2) Forming bar must NOT grow series
    s.update_bar(100, 101, 99, 100.5, 10, confirmed=False)
    if len(s.closes) != 0:
        errors.append(f"forming bar polluted closes: len={len(s.closes)}")
    if getattr(s, "_forming", None) is None:
        errors.append("_forming not set after unconfirmed bar")

    # 3) Tick must NOT create OHLC bar
    before = len(s.closes)
    s.update_price(100.7)
    if len(s.closes) != before:
        errors.append(f"tick polluted closes: {before} → {len(s.closes)}")
    if getattr(s, "last_price", None) != 100.7:
        errors.append(f"last_price not updated by tick: {getattr(s, 'last_price', None)}")

    # 4) Closed bars must append
    for i in range(5):
        s.update_bar(100 + i, 101 + i, 99 + i, 100.5 + i, 10, confirmed=True)
    if len(s.closes) != 5:
        errors.append(f"expected 5 closed bars, got {len(s.closes)}")
    if getattr(s, "_forming", None) is not None:
        errors.append("_forming should be cleared after confirmed bar")

    # 5) analyze with tick only (already_updated=False) must not grow closes
    before = len(s.closes)
    s.analyze("BTC-USDC", 105.0, already_updated=False)
    if len(s.closes) != before:
        errors.append(f"analyze(tick) polluted closes: {before} → {len(s.closes)}")

    print("=== audit_closed_bars_smoke ===")
    print(f"strategy: {s.name}")
    print(f"closes:   {len(s.closes)}")
    print(f"last_px:  {s.last_price}")
    if errors:
        print("FAIL")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("PASS — closed-bars only, no tick pollution")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
