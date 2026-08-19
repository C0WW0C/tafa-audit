#!/usr/bin/env python3
"""Prove strategy → parent → gate → paper execute can fire a BUY."""
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from trading.intelligent_strategy import IntelligentStrategy
from trading.paper_trading import PaperTrading
from trading.trade_manager import TradeManager
from core.quality_gate_live import gate
from ai.neural_parent_brain import NeuralParentBrain

def main() -> int:
    s = IntelligentStrategy()
    px = 50_000.0
    for _ in range(130):
        px *= 1.003
        s.update_bar(px, px * 1.001, px * 0.999, px, 50.0, confirmed=True)
    sig = s.analyze("BTC-USDC", px, already_updated=True)
    brain = NeuralParentBrain()
    dec = brain.decide(s, sig, px, risk_ok=True)
    ok, why = gate.accept(dec.signal, dec.confidence, dec.regime, len(s.closes))
    print(f"signal={sig} parent={dec.signal} conf={dec.confidence:.3f} gate={ok}/{why}")
    if not (sig == "BUY" and dec.signal == "BUY" and ok):
        print("FAIL pipeline blocked")
        return 1
    paper = PaperTrading(capital=1000.0)
    tm = TradeManager(paper=paper)
    executed = tm.execute("BTC-USDC", "BUY", px)
    qty = paper.position_qty("BTC-USDC")
    print(f"execute={executed} qty={qty:.8f} equity={paper.equity({'BTC-USDC': px}):.2f}")
    if not executed or qty <= 0:
        print("FAIL paper did not open")
        return 1
    print("PASS — paper trade opened")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
