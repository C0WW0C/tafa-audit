# ============================================================
# TAFA V7 PRO
# ORDER ENGINE FINAL (version corrigée)
# ============================================================

import threading
from logger import logger
from core.database import save_order


class OrderManager:
    def __init__(self, client=None):
        self.client = client
        self._lock = threading.RLock()

    def create_order(self, symbol, side, qty, price=None):
        """Crée un ordre market ou limit via le client, ou simule en paper."""
        with self._lock:
            order_type = "market" if price is None else "limit"

            logger.info(f"ORDER {side} {symbol} qty={qty} type={order_type}")

            if self.client:
                try:
                    if order_type == "limit":
                        # Pour un ordre limit, il faut ajouter le prix
                        result = self.client.place_order(
                            symbol=symbol,
                            side=side,
                            size=str(qty),
                            order_type=order_type,
                            price=str(price),
                        )
                    else:
                        result = self.client.place_order(
                            symbol=symbol,
                            side=side,
                            size=str(qty),
                            order_type=order_type,
                        )
                except Exception as exc:
                    logger.error(f"Order creation failed: {exc}")
                    return {"error": str(exc)}

                order_id = str(result.get("id") or result.get("ordId") or "unknown")
                save_order(order_id, symbol, side, order_type, qty, price, "submitted")
                return result

            # Mode paper local
            save_order("paper", symbol, side, order_type, qty, price, "filled")
            return {"id": "paper", "status": "filled"}