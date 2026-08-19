# ============================================================
# TAFA V8 — STRATEGY TEMPLATE
# ============================================================

import logging
from typing import Optional

logger = logging.getLogger("StrategyV8")


class BaseStrategy:
    """Base strategy class."""
    
    def __init__(self, name: str = "BaseStrategy"):
        self.name = name
        self.closes = []
        self.last_price = None
        self.last_confidence = 0.5
    
    def update_bar(self, o: float, h: float, l: float, c: float, v: float, confirmed: bool = False):
        """Update candle."""
        self.last_price = c
        if confirmed:
            self.closes.append(c)
            if len(self.closes) > 200:
                self.closes = self.closes[-200:]
    
    def update_price(self, price: float):
        """Update tick price."""
        self.last_price = price
    
    def analyze(self, symbol: str, price: float) -> Optional[str]:
        """Return BUY, SELL, or HOLD."""
        return "HOLD"
    
    def get_state(self):
        """Return strategy state."""
        return {
            "name": self.name,
            "last_price": self.last_price,
            "closes_count": len(self.closes),
        }


class SimpleMomentumStrategy(BaseStrategy):
    """Simple momentum strategy."""
    
    def __init__(self, period: int = 20, threshold: float = 0.01):
        super().__init__("SimpleMomentum")
        self.period = period
        self.threshold = threshold
    
    def analyze(self, symbol: str, price: float) -> Optional[str]:
        if len(self.closes) < self.period:
            return "HOLD"
        
        past_price = self.closes[-self.period]
        momentum = (price - past_price) / past_price
        
        self.last_confidence = min(1.0, abs(momentum) * 10)
        
        if momentum > self.threshold:
            return "BUY"
        elif momentum < -self.threshold:
            return "SELL"
        return "HOLD"


class RSIStrategy(BaseStrategy):
    """RSI-based strategy."""
    
    def __init__(self, period: int = 14, oversold: float = 30, overbought: float = 70):
        super().__init__("RSI")
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
    
    def _calculate_rsi(self) -> Optional[float]:
        if len(self.closes) < self.period + 1:
            return None
        
        deltas = [self.closes[i] - self.closes[i-1] for i in range(1, len(self.closes))]
        seed = deltas[:self.period]
        
        up = sum(d for d in seed if d > 0) / self.period
        down = -sum(d for d in seed if d < 0) / self.period
        
        rs = up / down if down != 0 else 0
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def analyze(self, symbol: str, price: float) -> Optional[str]:
        rsi = self._calculate_rsi()
        if rsi is None:
            return "HOLD"
        
        self.last_confidence = abs(rsi - 50) / 50
        
        if rsi < self.oversold:
            return "BUY"
        elif rsi > self.overbought:
            return "SELL"
        return "HOLD"
