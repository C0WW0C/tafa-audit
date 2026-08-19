#!/usr/bin/env python3
"""TAFA V10 production readiness — strict."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

def main() -> int:
    fails = 0
    def ok(name, fn):
        nonlocal fails
        try:
            fn()
            print(f"  OK  {name}")
        except Exception as e:
            fails += 1
            print(f"  FAIL {name}: {e}")

    print("=== TAFA X ULTIMATE FINAL Health ===\n")

    ok("imports_v10", lambda: [
        importlib.import_module(m)
        for m in (
            "core.engine_v10",
            "core.circuit_breaker",
            "core.trade_journal",
            "core.quality_gate_live",
            "core.engine",
            "trading.strategy",
            "risk.risk_manager",
            "ai.neural_parent_brain",
        )
    ])

    def paper():
        import config
        assert config.PAPER_TRADING is True
    ok("paper_default", paper)

    def breaker():
        from core.circuit_breaker import CircuitBreaker
        b = CircuitBreaker(max_drawdown=0.1)
        b.peak_equity = 1000
        allowed, _ = b.allow(850)  # 15% DD
        assert allowed is False
    ok("circuit_breaker", breaker)

    def gate():
        from core.quality_gate_live import SignalQuality
        g = SignalQuality(min_confidence=0.62, min_bars=50)
        a, _ = g.accept("BUY", 0.4, "TREND_UP", 100)
        assert a is False
        a, _ = g.accept("BUY", 0.7, "TREND_DOWN", 100)
        assert a is False
        a, _ = g.accept("BUY", 0.7, "TREND_UP", 100)
        assert a is True
    ok("quality_gate", gate)

    def engine():
        from core.engine_v10 import TAFAEngineV10
        e = TAFAEngineV10()
        e.start()
        e.run_cycle()
        assert e.status().get("version") == "TAFA_X_ULTIMATE_FINAL"
        assert e.inner.last_price is not None
        e.stop()
    ok("engine_v10_cycle", engine)

    def journal():
        from core.trade_journal import log_event, read_events
        log_event("health_ping", ok=True)
        assert any(x.get("kind") == "health_ping" for x in read_events(20))
    ok("journal", journal)

    print(f"\n=== {'PASS' if fails == 0 else 'FAIL'} ({fails} failed) ===")
    return 1 if fails else 0

if __name__ == "__main__":
    raise SystemExit(main())
