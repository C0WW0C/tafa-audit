# ============================================================
# TAFA V7 PRO
# STRATEGY OPTIMIZER AI FINAL
# ============================================================


from logger import logger



class StrategyOptimizerAI:


    def __init__(self):

        self.best=None


        logger.info(
            "Strategy Optimizer AI initialized"
        )



    # ========================================================
    # OPTIMIZE
    # ========================================================

    def optimize(
        self,
        results
    ):


        if not results:

            return None



        self.best=max(

            results,

            key=lambda x:

            x.get(
                "score",
                0
            )

        )



        return self.best



    # ========================================================
    # GET BEST
    # ========================================================

    def get_best(self):

        return self.best