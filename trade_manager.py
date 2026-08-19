# ============================================================
# TAFA V7 PRO — Trade Manager (Production)
# ============================================================

from __future__ import annotations

from typing import Optional

from config import (
    INITIAL_CAPITAL,
    ORDER_SIZE_USD,
    PAPER_TRADING,
    ENABLE_LIVE,
    MIN_ORDER_USD,
    PAPER_SESSION_NET_TARGET_USD,
)
try:
    from config import LIVE_CONFIRM
except Exception:
    LIVE_CONFIRM = ""

from core.database import save_trade, save_order, save_performance
from core.paper_execution_guard import PaperExecutionGuard
from core.trade_journal import log_event
from logger import logger, log_trade
from risk.risk_manager import risk_manager
from trading.paper_trading import PaperTrading

try:
    from exchange.okx_client import OKXClient
except Exception:
    OKXClient = None  # type: ignore


class TradeManager:
    """Routes orders to paper account or live OKX with hard safety gates."""

    def __init__(
        self,
        paper: Optional[PaperTrading] = None,
        client: Optional[object] = None,
        guard: Optional[PaperExecutionGuard] = None,
    ):
        self.paper = paper or PaperTrading(capital=INITIAL_CAPITAL)
        self.client = client
        self.guard = guard or PaperExecutionGuard()
        self.strategy_ref = None  # optional IntelligentStrategy for online learning
        if self.client is None and OKXClient is not None and not PAPER_TRADING:
            self.client = OKXClient()
        logger.info(f"Trade Manager initialized (paper={PAPER_TRADING})")

    def execute(self, symbol: str, side: str, price: float) -> bool:
        side = side.upper()
        if side not in ("BUY", "SELL"):
            return False
        if price is None or price <= 0:
            logger.warning("Invalid price for execution")
            return False
        if not risk_manager.can_trade():
            logger.warning("Trade blocked by risk manager")
            return False

        if side == "BUY":
            if self._paper_session_target_reached():
                logger.info("New paper BUY blocked: net session target already reached")
                return False
            notional = min(ORDER_SIZE_USD, risk_manager.current_balance * 0.95)
            if notional < MIN_ORDER_USD:
                logger.warning(f"Order size {notional:.2f} below minimum")
                return False
            qty = risk_manager.calculate_position_size(price)
            if qty <= 0:
                qty = notional / price
            if qty <= 0:
                return False
            return self._execute_paper_guarded(symbol, side, qty, price)

        # SELL — close existing position
        qty = self._open_qty(symbol)
        if qty <= 0:
            logger.info(f"No position to sell on {symbol}")
            return False
        return self._execute_paper_guarded(symbol, side, qty, price)

    def execute_manual_paper(self, symbol: str, side: str, price: float, notional: float) -> dict:
        """Execute a dashboard request against the local paper account only."""
        side = str(side).upper()
        try:
            notional = float(notional)
        except (TypeError, ValueError):
            return {"ok": False, "reason": "invalid_notional"}
        if not PAPER_TRADING or ENABLE_LIVE:
            return {"ok": False, "reason": "paper_only"}
        if side not in {"BUY", "SELL"} or price <= 0 or notional <= 0:
            return {"ok": False, "reason": "invalid_request"}
        if side == "BUY":
            if not risk_manager.can_trade():
                return {"ok": False, "reason": "risk_block"}
            if self._paper_session_target_reached():
                return {"ok": False, "reason": "session_target_reached"}
            qty = min(notional, self.paper.balance * 0.95) / price
        else:
            held = self._open_qty(symbol)
            if held <= 0:
                return {"ok": False, "reason": "no_open_position"}
            qty = min(held, notional / price)
        if qty <= 0:
            return {"ok": False, "reason": "quantity_zero"}
        ok = self._execute_paper_guarded(symbol, side, qty, price)
        reason = "filled" if ok else self.guard.status().get("last_decision", {}).get("reason", "rejected")
        log_event(
            "manual_paper_order",
            symbol=symbol,
            side=side,
            price=price,
            qty=qty,
            notional=round(qty * price, 8),
            ok=bool(ok),
            reason=reason,
        )
        return {"ok": bool(ok), "reason": reason, "qty": qty, "notional": round(qty * price, 8), "price": price}

    def _execute_paper_guarded(self, symbol: str, side: str, qty: float, price: float) -> bool:
        """Apply local-only safeguards before the paper account is changed."""
        if PAPER_TRADING or not ENABLE_LIVE:
            decision = self.guard.check_entry(symbol, side)
            if not decision.allowed:
                log_event(
                    "paper_guard_block",
                    symbol=symbol,
                    side=side,
                    reason=decision.reason,
                    price=price,
                    qty=qty,
                )
                logger.warning(f"Paper {side} blocked by guard: {decision.reason} ({symbol})")
                return False
            ok = self._buy(symbol, qty, price) if side == "BUY" else self._sell(symbol, qty, price)
            if ok:
                self.guard.record_trade(symbol, side)
                log_event("paper_guard_pass", symbol=symbol, side=side, reason=decision.reason, price=price, qty=qty)
            return ok
        return self._buy(symbol, qty, price) if side == "BUY" else self._sell(symbol, qty, price)

    def guard_status(self) -> dict:
        return self.guard.status()

    def _paper_session_target_reached(self) -> bool:
        """Stop only new paper entries once a configured net session gain is realized."""
        if not PAPER_TRADING or PAPER_SESSION_NET_TARGET_USD <= 0:
            return False
        realized_net = self.paper.balance - self.paper.initial_capital
        return realized_net >= PAPER_SESSION_NET_TARGET_USD

    def _open_qty(self, symbol: str) -> float:
        if PAPER_TRADING:
            return self.paper.position_qty(symbol)
        return 0.0

    def _buy(self, symbol: str, qty: float, price: float) -> bool:
        if PAPER_TRADING or not ENABLE_LIVE:
            ok = self.paper.buy(symbol, qty, price)
            if not ok:
                return False
            log_trade("BUY", symbol, qty, price)
            save_trade(symbol, "BUY", qty, price, 0.0, "TAFA_FUSION", "DEMO")
            risk_manager.register_position(symbol, "BUY", qty, price)
            self._snapshot(price_map={symbol: price})
            return True

        # LIVE path — only if explicitly enabled + confirm phrase
        if not ENABLE_LIVE or LIVE_CONFIRM != "I_UNDERSTAND_THE_RISK":
            logger.error("LIVE blocked: ENABLE_LIVE/LIVE_CONFIRM gate")
            return False
        if PAPER_TRADING:
            logger.error("LIVE blocked: PAPER_TRADING still True")
            return False
        if self.client is None or not self.client.has_credentials():
            logger.error("LIVE blocked: missing OKX credentials")
            return False
        resp = self.client.place_order(symbol, "buy", f"{qty:.8f}")
        if str(resp.get("code")) != "0":
            logger.error(f"LIVE BUY failed: {resp}")
            return False
        order_id = (resp.get("data") or [{}])[0].get("ordId", "")
        save_order(order_id, symbol, "BUY", "market", qty, price, "submitted")
        save_trade(symbol, "BUY", qty, price, 0.0, "TAFA_FUSION", "LIVE")
        risk_manager.register_position(symbol, "BUY", qty, price)
        log_trade("BUY", symbol, qty, price)
        return True

    def _sell(self, symbol: str, qty: float, price: float) -> bool:
        if PAPER_TRADING or not ENABLE_LIVE:
            pnl = self.paper.sell(symbol, qty, price)
            log_trade("SELL", symbol, qty, price, pnl)
            save_trade(symbol, "SELL", qty, price, pnl, "TAFA_INTEL", "DEMO")
            risk_manager.close_position()
            risk_manager.update_balance(self.paper.equity({symbol: price}))
            if self.strategy_ref is not None and hasattr(self.strategy_ref, "feedback"):
                experts = getattr(self.strategy_ref, "last_experts", {})
                self.strategy_ref.feedback(experts, "SELL", pnl, risk_unit=max(self.paper.initial_capital * 0.02, 1.0))
            self._snapshot(price_map={symbol: price})
            return True

        if not ENABLE_LIVE or LIVE_CONFIRM != "I_UNDERSTAND_THE_RISK":
            logger.error("LIVE blocked: ENABLE_LIVE/LIVE_CONFIRM gate")
            return False
        if PAPER_TRADING:
            logger.error("LIVE blocked: PAPER_TRADING still True")
            return False
        if self.client is None or not self.client.has_credentials():
            logger.error("LIVE blocked: missing OKX credentials")
            return False
        resp = self.client.place_order(symbol, "sell", f"{qty:.8f}")
        if str(resp.get("code")) != "0":
            logger.error(f"LIVE SELL failed: {resp}")
            return False
        order_id = (resp.get("data") or [{}])[0].get("ordId", "")
        save_order(order_id, symbol, "SELL", "market", qty, price, "submitted")
        save_trade(symbol, "SELL", qty, price, 0.0, "TAFA_FUSION", "LIVE")
        risk_manager.close_position()
        log_trade("SELL", symbol, qty, price)
        return True

    def _snapshot(self, price_map: Optional[dict] = None) -> None:
        eq = self.paper.equity(price_map)
        risk_manager.update_balance(eq)
        dd = risk_manager.get_drawdown()
        pnl = eq - self.paper.initial_capital
        try:
            save_performance(self.paper.balance, eq, pnl, dd)
        except Exception as exc:
            logger.error(f"Performance save error: {exc}")
