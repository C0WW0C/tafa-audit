# ============================================================
# TAFA V7 PRO
# OPTIMIZER ENGINE FINAL
# ============================================================


from logger import logger



class OptimizerEngine:


    def __init__(self):

        self.best=None


        logger.info(
            "Optimizer Engine initialized"
        )



    # ========================================================
    # OPTIMIZE
    # ========================================================

    def optimize(
        self,
        configurations,
        evaluator
    ):


        scores=[]



        for config in configurations:


            score=evaluator(
                config
            )


            scores.append(

                {

                "config":config,

                "score":score

                }

            )



        self.best=max(

            scores,

            key=lambda x:x["score"]

        )


        return self.best



    # ========================================================
    # RESULT
    # ========================================================

    def get_best(self):

        return self.best