"""Paper-only execution safeguards for TAFA Elite.

This module has no exchange client and cannot create, cancel or amend an
exchange order. It only protects the local PaperTrading path from duplicate
entries and provides a bounded cancellation budget for future simulated limit
order components.
"""
from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Callable


@dataclass(frozen=True)
class GuardDecision:
    allowed: bool
    reason: str


class PaperExecutionGuard:
    """Bound duplicate paper entries; never block a risk-driven paper sell."""

    def __init__(
        self,
        duplicate_buy_window_seconds: float = 15.0,
        cancel_window_seconds: float = 300.0,
        max_cancels_per_symbol: int = 3,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.duplicate_buy_window_seconds = max(0.0, float(duplicate_buy_window_seconds))
        self.cancel_window_seconds = max(1.0, float(cancel_window_seconds))
        self.max_cancels_per_symbol = max(1, int(max_cancels_per_symbol))
        self._clock = clock or time.monotonic
        self._recent_buys: dict[str, float] = {}
        self._recent_cancels: dict[str, list[float]] = {}
        self._last_decision = GuardDecision(True, "not_checked")
        self._blocked_entries = 0
        self._blocked_cancels = 0

    @staticmethod
    def _symbol(symbol: str) -> str:
        return str(symbol).strip().upper()

    def check_entry(self, symbol: str, side: str) -> GuardDecision:
        """Reject only repeated BUY requests during the bounded cooldown.

        Sells are intentionally always allowed through this guard because an
        exit may be triggered by a stop-loss, take-profit or circuit breaker.
        """

        side = str(side).strip().upper()
        normalized = self._symbol(symbol)
        if not normalized or side not in {"BUY", "SELL"}:
            self._blocked_entries += 1
            self._last_decision = GuardDecision(False, "invalid_symbol_or_side")
            return self._last_decision
        if side == "SELL":
            self._last_decision = GuardDecision(True, "sell_exit_priority")
            return self._last_decision
        now = self._clock()
        last_buy = self._recent_buys.get(normalized)
        if last_buy is not None and now - last_buy < self.duplicate_buy_window_seconds:
            self._blocked_entries += 1
            self._last_decision = GuardDecision(False, "duplicate_buy_cooldown")
            return self._last_decision
        self._last_decision = GuardDecision(True, "entry_allowed")
        return self._last_decision

    def record_trade(self, symbol: str, side: str) -> None:
        if str(side).strip().upper() == "BUY":
            self._recent_buys[self._symbol(symbol)] = self._clock()

    def request_cancel(self, symbol: str) -> GuardDecision:
        """Reserve a cancellation slot for a future *paper* limit-order path."""

        normalized = self._symbol(symbol)
        now = self._clock()
        history = [ts for ts in self._recent_cancels.get(normalized, []) if now - ts < self.cancel_window_seconds]
        if len(history) >= self.max_cancels_per_symbol:
            self._blocked_cancels += 1
            self._recent_cancels[normalized] = history
            self._last_decision = GuardDecision(False, "cancel_budget_exhausted")
            return self._last_decision
        history.append(now)
        self._recent_cancels[normalized] = history
        self._last_decision = GuardDecision(True, "cancel_allowed")
        return self._last_decision

    def status(self) -> dict[str, object]:
        now = self._clock()
        active_cancels = {
            symbol: len([ts for ts in values if now - ts < self.cancel_window_seconds])
            for symbol, values in self._recent_cancels.items()
        }
        return {
            "mode": "paper_only",
            "duplicate_buy_window_seconds": self.duplicate_buy_window_seconds,
            "cancel_window_seconds": self.cancel_window_seconds,
            "max_cancels_per_symbol": self.max_cancels_per_symbol,
            "blocked_entries": self._blocked_entries,
            "blocked_cancels": self._blocked_cancels,
            "active_cancels": active_cancels,
            "last_decision": {"allowed": self._last_decision.allowed, "reason": self._last_decision.reason},
        }
