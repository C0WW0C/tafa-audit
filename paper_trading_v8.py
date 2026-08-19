# ============================================================
# TAFA V8 — PAPER TRADING ACCOUNT
# ============================================================

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("PaperTradingV8")


class PaperTradingV8:
    """Simulated trading account."""
    
    def __init__(self, initial_capital: float = 10000.0):
        self.initial_capital = initial_capital
        self.balance = initial_capital
        self.positions = {}  # symbol -> qty
        self.entry_prices = {}  # symbol -> price
    
    def execute_order(
        self,
        symbol: str,
        side: str,
        price: float,
        size: str,
    ) -> Dict[str, Any]:
        """Execute paper trade."""
        try:
            qty = float(size)
            notional = qty * price
            
            if side.upper() == "BUY":
                if notional > self.balance:
                    return {"code": "-1", "msg": "Insufficient balance"}
                
                self.balance -= notional
                self.positions[symbol] = self.positions.get(symbol, 0) + qty
                self.entry_prices[symbol] = price
                
                logger.info(f"Paper BUY {qty} {symbol} @ {price}")
                return {"code": "0", "data": [{"ordId": "paper-buy-1"}]}
            
            elif side.upper() == "SELL":
                current_qty = self.positions.get(symbol, 0)
                if current_qty < qty:
                    return {"code": "-1", "msg": "Insufficient position"}
                
                self.balance += notional
                self.positions[symbol] = current_qty - qty
                
                logger.info(f"Paper SELL {qty} {symbol} @ {price}")
                return {"code": "0", "data": [{"ordId": "paper-sell-1"}]}
            
            return {"code": "-1", "msg": "Invalid side"}
        
        except Exception as e:
            logger.error(f"Paper order error: {e}")
            return {"code": "-1", "msg": str(e)}
    
    def get_positions(self) -> list:
        """Get current positions."""
        return [
            {"symbol": sym, "qty": qty, "entry_price": self.entry_prices.get(sym)}
            for sym, qty in self.positions.items()
            if qty > 0
        ]
    
    def equity(self, mark_prices: Dict[str, float]) -> float:
        """Calculate total equity."""
        equity = self.balance
        for symbol, qty in self.positions.items():
            if qty > 0 and symbol in mark_prices:
                equity += qty * mark_prices[symbol]
        return equity
    
    def status(self, mark_prices: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """Return account status."""
        eq = self.equity(mark_prices or {}) if mark_prices else self.balance
        return {
            "balance": self.balance,
            "equity": eq,
            "positions": self.get_positions(),
            "pnl": eq - self.initial_capital,
        }
