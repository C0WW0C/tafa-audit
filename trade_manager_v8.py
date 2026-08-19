# ============================================================
# TAFA V8 — TRADE MANAGER
# ============================================================

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("TradeManagerV8")


class TradeManagerV8:
    """Execute & manage trades."""
    
    def __init__(self, client=None, paper_account=None, risk_manager=None):
        self.client = client
        self.paper_account = paper_account
        self.risk_manager = risk_manager
        self.trades = []
    
    def execute(
        self,
        symbol: str,
        side: str,
        price: float,
        size: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute trade (paper or live)."""
        try:
            if self.paper_account:
                # Paper trading
                result = self.paper_account.execute_order(symbol, side, price, size or "0.01")
            else:
                # Live trading via OKX
                result = self.client.place_order(symbol, side, size or "0.01")
            
            if result.get("code") == "0":
                self.trades.append({
                    "symbol": symbol,
                    "side": side,
                    "price": price,
                    "size": size,
                    "status": "executed",
                })
                logger.info(f"Trade executed: {side} {symbol} @ {price}")
                return {"ok": True, "trade_id": result.get("data", [{}])[0].get("ordId")}
            else:
                logger.error(f"Trade failed: {result.get('msg')}")
                return {"ok": False, "error": result.get("msg")}
        
        except Exception as e:
            logger.error(f"Trade execution error: {e}")
            return {"ok": False, "error": str(e)}
    
    def get_open_positions(self) -> list:
        """Get open positions."""
        if self.paper_account:
            return self.paper_account.get_positions()
        return self.client.get_positions()
    
    def get_trades(self, limit: int = 50) -> list:
        """Get trade history."""
        return self.trades[-limit:]
    
    def cancel_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """Cancel order."""
        try:
            result = self.client.cancel_order(order_id, symbol)
            return {"ok": result.get("code") == "0"}
        except Exception as e:
            logger.error(f"Cancel order error: {e}")
            return {"ok": False, "error": str(e)}
