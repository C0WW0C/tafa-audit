# ============================================================
# TAFA V7 PRO
# TRADE GUARD FINAL
# ============================================================


import time


from logger import logger



class TradeGuard:


    def __init__(self):

        self.last_trade_time=0

        self.cooldown=30



        logger.info(
            "Trade Guard initialized"
        )



    # ========================================================
    # CHECK
    # ========================================================

    def allow(self):


        now=time.time()



        if (

            now -

            self.last_trade_time

            <

            self.cooldown

        ):


            logger.warning(
                "Trade cooldown active"
            )


            return False



        return True



    # ========================================================
    # REGISTER
    # ========================================================

    def register(self):


        self.last_trade_time=time.time()