# ============================================================
# TAFA V7 PRO
# GRID ENGINE V2 FINAL
# ============================================================

from config import (
    GRID_LEVELS,
    GRID_STEP_PERCENT
)

from logger import logger



class GridEngine:


    def __init__(self):

        self.levels = []

        logger.info(
            "Grid Engine initialized"
        )



    # ========================================================
    # CREATE GRID
    # ========================================================

    def create_grid(
        self,
        price
    ):


        self.levels=[]


        step = (
            GRID_STEP_PERCENT
            /
            100
        )


        for i in range(
            1,
            GRID_LEVELS+1
        ):


            buy = price * (
                1 -
                step*i
            )


            sell = price * (
                1 +
                step*i
            )


            self.levels.append(

                {

                "level":i,

                "buy":round(
                    buy,
                    4
                ),

                "sell":round(
                    sell,
                    4
                )

                }

            )


        return self.levels



    # ========================================================
    # CHECK GRID SIGNAL
    # ========================================================

    def check(
        self,
        price
    ):


        for level in self.levels:


            if price <= level["buy"]:

                return "BUY"



            if price >= level["sell"]:

                return "SELL"



        return "HOLD"