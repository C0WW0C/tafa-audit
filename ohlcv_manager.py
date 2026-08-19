# ============================================================
# TAFA V7 PRO
# OHLCV MANAGER FINAL
# ============================================================

from logger import logger


class OHLCVManager:

    def __init__(self):
        self.data = []
        logger.info("OHLCV Manager initialized")

    def add(self, candle):
        self.data.append(candle)
        if len(self.data) > 5000:
            self.data.pop(0)

    def get(self, limit=100):
        return self.data[-limit:]

    def last(self):
        if self.data:
            return self.data[-1]
        return None
