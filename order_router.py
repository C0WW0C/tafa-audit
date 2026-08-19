# ============================================================
# TAFA V7 PRO
# ORDER ROUTER FINAL
# ============================================================


from logger import logger



class OrderRouter:


    def __init__(
        self,
        order_manager=None
    ):


        self.order_manager = order_manager


        logger.info(
            "Order Router initialized"
        )



    # ========================================================
    # ROUTE ORDER
    # ========================================================

    def route(
        self,
        symbol,
        side,
        qty,
        price
    ):


        if side not in [

            "BUY",

            "SELL"

        ]:


            return None



        logger.info(

            f"ROUTE {side} {symbol}"

        )



        if self.order_manager:


            return self.order_manager.create_order(

                symbol,

                side,

                qty,

                price

            )



        return {


            "status":

            "PAPER",


            "symbol":

            symbol,


            "side":

            side,


            "qty":

            qty,


            "price":

            price

        }