# ============================================================
# TAFA V7 PRO
# SL TP MANAGER FINAL
# ============================================================



from logger import logger



class SLTPManager:


    def __init__(
        self,
        stop_loss=0.01,
        take_profit=0.03
    ):


        self.stop_loss=stop_loss

        self.take_profit=take_profit



        logger.info(
            "SL TP Manager initialized"
        )



    # ========================================================
    # LEVELS
    # ========================================================

    def calculate(
        self,
        entry
    ):


        return {


            "stop_loss":

            entry *

            (1-self.stop_loss),



            "take_profit":

            entry *

            (1+self.take_profit)

        }



    # ========================================================
    # CHECK
    # ========================================================

    def check(
        self,
        entry,
        current
    ):


        change=(

            current-entry

        )/entry



        if change <= -self.stop_loss:

            return "STOP_LOSS"



        if change >= self.take_profit:

            return "TAKE_PROFIT"



        return "HOLD"