# ============================================================
# TAFA V7 PRO
# BENCHMARK ENGINE FINAL
# ============================================================



class Benchmark:


    def __init__(self):

        self.results=[]



    # ========================================================
    # ADD
    # ========================================================

    def add(
        self,
        name,
        score
    ):


        self.results.append(

            {

            "strategy":

            name,


            "score":

            score

            }

        )



    # ========================================================
    # RANK
    # ========================================================

    def ranking(self):


        return sorted(

            self.results,

            key=lambda x:x["score"],

            reverse=True

        )