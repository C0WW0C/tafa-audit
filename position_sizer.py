# ============================================================
# TAFA V7 PRO
# POSITION SIZER FINAL
# ============================================================



class PositionSizer:


    def __init__(
        self,
        risk_percent=0.01
    ):


        self.risk_percent=risk_percent



    # ========================================================
    # CALCUL QTY
    # ========================================================

    def calculate(
        self,
        capital,
        price,
        stop_distance
    ):


        risk_amount=(

            capital *

            self.risk_percent

        )



        if stop_distance<=0:

            return 0



        qty=(

            risk_amount

            /

            stop_distance

        )



        return qty/price