# ============================================================
# TAFA V8 — RISK MANAGER
# ============================================================

import logging
from typing import Dict, Any

logger = logging.getLogger("RiskManagerV8")


class RiskManagerV8:
    """Position & account risk control."""
    
    def __init__(
        self,
        initial_capital: float = 10000.0,
        max_drawdown_pct: float = 20.0,
        max_position_pct: float = 5.0,
        daily_loss_limit: float = None,
    ):
        self.initial_capital = initial_capital
        self.max_drawdown_pct = max_drawdown_pct
        self.max_position_pct = max_position_pct
        self.daily_loss_limit = daily_loss_limit or initial_capital * 0.1
        
        self.current_balance = initial_capital
        self.peak_balance = initial_capital
        self.daily_pnl = 0.0
        self.open_position = None
    
    def update_balance(self, new_balance: float):
        """Update balance & track peak."""
        self.current_balance = new_balance
        if new_balance > self.peak_balance:
            self.peak_balance = new_balance
    
    def update_daily_pnl(self, pnl: float):
        """Accumulate daily PnL."""
        self.daily_pnl += pnl
    
    def reset_daily(self):
        """Reset daily metrics."""
        self.daily_pnl = 0.0
    
    def can_trade(self) -> bool:
        """Check if trading is allowed."""
        # Check drawdown
        drawdown = (self.peak_balance - self.current_balance) / self.peak_balance * 100
        if drawdown > self.max_drawdown_pct:
            logger.warning(f"Drawdown limit hit: {drawdown:.2f}%")
            return False
        
        # Check daily loss
        if self.daily_pnl < -self.daily_loss_limit:
            logger.warning(f"Daily loss limit hit: {self.daily_pnl:.2f}")
            return False
        
        return True
    
    def check_position_size(self, symbol: str, price: float, notional: float) -> bool:
        """Validate position size."""
        position_pct = (notional / self.current_balance) * 100
        if position_pct > self.max_position_pct:
            logger.warning(
                f"Position {symbol} {position_pct:.2f}% exceeds {self.max_position_pct}%"
            )
            return False
        return True
    
    def check_exit(self, price: float, entry_price: float) -> Dict[str, Any]:
        """Check exit conditions (SL, TP, etc)."""
        if self.open_position is None:
            return {"exit": False}
        
        pnl_pct = ((price - entry_price) / entry_price) * 100
        
        # Stop loss at -2%
        if pnl_pct < -2.0:
            return {"exit": True, "reason": "STOP_LOSS"}
        
        # Take profit at +3%
        if pnl_pct > 3.0:
            return {"exit": True, "reason": "TAKE_PROFIT"}
        
        return {"exit": False}
    
    def get_drawdown(self) -> float:
        """Return current drawdown %."""
        if self.peak_balance <= 0:
            return 0.0
        return max(0.0, (self.peak_balance - self.current_balance) / self.peak_balance * 100)
    
    def status(self) -> Dict[str, Any]:
        """Return risk status."""
        return {
            "can_trade": self.can_trade(),
            "drawdown_pct": self.get_drawdown(),
            "balance": self.current_balance,
            "peak": self.peak_balance,
            "daily_pnl": self.daily_pnl,
            "daily_loss_limit": self.daily_loss_limit,
        }
