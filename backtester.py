# ============================================================
# TAFA V7 PRO — Backtester
# ============================================================
"""Lightweight paper backtester for unit tests and quick sims."""

from __future__ import annotations

from typing import Any

from logger import logger


class Backtester:
    """Simple balance/position backtester used by tests and demos."""

    def __init__(self, capital: float = 1000.0) -> None:
        self.initial_capital = float(capital)
        self.balance = float(capital)
        self.position = 0.0
        self.trades: list[dict[str, Any]] = []
        logger.info("Backtester initialized")

    def reset(self) -> None:
        self.balance = self.initial_capital
        self.position = 0.0
        self.trades = []

    def buy(self, price: float, amount: float) -> bool:
        """Spend `amount` quote currency at `price`. Returns False if insufficient balance."""
        if price <= 0 or amount <= 0:
            return False
        if self.balance < amount:
            return False
        qty = amount / price
        self.balance -= amount
        self.position += qty
        self.trades.append({"side": "BUY", "price": price, "qty": qty, "amount": amount})
        return True

    def sell(self, price: float) -> bool:
        """Close entire position at `price`. Returns False if flat."""
        if price <= 0 or self.position <= 0:
            return False
        value = self.position * price
        qty = self.position
        self.balance += value
        self.trades.append({"side": "SELL", "price": price, "qty": qty, "amount": value})
        self.position = 0.0
        return True

    def equity(self, mark_price: float | None = None) -> float:
        """Cash + mark-to-market position."""
        px = mark_price if mark_price is not None else 0.0
        return self.balance + self.position * px

    def summary(self) -> dict[str, Any]:
        return {
            "initial_capital": self.initial_capital,
            "balance": self.balance,
            "position": self.position,
            "trades": len(self.trades),
        }
