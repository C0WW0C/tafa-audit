# ============================================================
# TAFA V7 PRO — Paper Trading Account (Production)
# ============================================================

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from logger import logger


@dataclass
class Position:
    symbol: str
    side: str  # LONG only for spot paper
    qty: float
    entry: float


class PaperTrading:
    """Spot-style paper account with USDC balance and open positions."""

    def __init__(self, capital: float = 1000.0, quote: str = "USDC"):
        self.initial_capital = float(capital)
        self.balance = float(capital)
        self.quote = quote
        self.positions: dict[str, Position] = {}
        self.realized_pnl = 0.0
        self.trade_count = 0
        logger.info(f"PaperTrading account started with {self.balance:.2f} {quote}")

    def equity(self, marks: Optional[dict[str, float]] = None) -> float:
        total = self.balance
        marks = marks or {}
        for symbol, pos in self.positions.items():
            px = marks.get(symbol, pos.entry)
            total += pos.qty * px
        return total

    def buy(self, symbol: str, qty: float, price: float) -> bool:
        cost = qty * price
        if cost <= 0 or cost > self.balance:
            logger.warning(f"Paper BUY rejected: cost={cost:.4f} balance={self.balance:.4f}")
            return False
        self.balance -= cost
        if symbol in self.positions:
            pos = self.positions[symbol]
            new_qty = pos.qty + qty
            pos.entry = ((pos.entry * pos.qty) + (price * qty)) / new_qty
            pos.qty = new_qty
        else:
            self.positions[symbol] = Position(symbol=symbol, side="LONG", qty=qty, entry=price)
        self.trade_count += 1
        return True

    def sell(self, symbol: str, qty: float, price: float) -> float:
        """Sell qty (or full position if qty >= held). Returns realized PnL."""
        pos = self.positions.get(symbol)
        if not pos or pos.qty <= 0:
            logger.warning(f"Paper SELL rejected: no position on {symbol}")
            return 0.0
        sell_qty = min(qty, pos.qty)
        proceeds = sell_qty * price
        pnl = (price - pos.entry) * sell_qty
        self.balance += proceeds
        self.realized_pnl += pnl
        pos.qty -= sell_qty
        if pos.qty <= 1e-12:
            del self.positions[symbol]
        self.trade_count += 1
        return pnl

    def position_qty(self, symbol: str) -> float:
        pos = self.positions.get(symbol)
        return pos.qty if pos else 0.0

    def status(self, marks: Optional[dict[str, float]] = None) -> dict:
        marks = marks or {}
        eq = self.equity(marks)
        # Primary open position (spot paper = at most one logical focus)
        qty = 0.0
        entry = None
        upnl = 0.0
        side = "FLAT"
        for s, pos in self.positions.items():
            qty = float(pos.qty)
            entry = float(pos.entry)
            px = float(marks.get(s, pos.entry))
            upnl = (px - pos.entry) * pos.qty
            side = "LONG" if pos.qty > 0 else "FLAT"
            break
        return {
            "balance": self.balance,
            "equity": eq,
            "initial_capital": self.initial_capital,
            "capital": self.initial_capital,
            "session_pnl": eq - self.initial_capital,
            "session_return_pct": ((eq / self.initial_capital) - 1.0) * 100.0 if self.initial_capital else 0.0,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": upnl,
            "qty": qty,
            "entry": entry,
            "entry_price": entry,
            "side": side,
            "positions": {
                s: {"qty": p.qty, "entry": p.entry, "side": p.side} for s, p in self.positions.items()
            },
            "trades": self.trade_count,
            "trade_count": self.trade_count,
        }
