# ============================================================
# TAFA V7 PRO
# TRAILING STOP FINAL
# ============================================================



class TrailingStop:


    def __init__(
        self,
        distance=0.0045
    ):


        self.distance=distance

        self.highest=0



    # ========================================================
    # UPDATE
    # ========================================================

    def update(
        self,
        price
    ):


        if price > self.highest:

            self.highest=price



        stop = (

            self.highest *

            (1-self.distance)

        )


        return stop



    # ========================================================
    # CHECK
    # ========================================================

    def check(
        self,
        price
    ):


        stop=self.update(
            price
        )


        if price <= stop:

            return "EXIT"



        return "HOLD"