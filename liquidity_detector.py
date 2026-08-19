# ============================================================
# TAFA V7 PRO
# LIQUIDITY DETECTOR FINAL
# ============================================================


from logger import logger



class LiquidityDetector:


    def __init__(self):

        self.order_flow = []

        logger.info(
            "Liquidity Detector initialized"
        )



    # ========================================================
    # UPDATE FLOW
    # ========================================================

    def update(
        self,
        volume,
        price_change
    ):


        self.order_flow.append(

            {

            "volume":volume,

            "change":price_change

            }

        )



        if len(self.order_flow)>200:

            self.order_flow.pop(0)



    # ========================================================
    # VOLUME PRESSURE
    # ========================================================

    def volume_pressure(self):


        if not self.order_flow:

            return 0



        buy = 0

        sell = 0



        for item in self.order_flow:


            if item["change"] > 0:

                buy += item["volume"]


            else:

                sell += item["volume"]



        total = buy + sell



        if total == 0:

            return 0



        return (
            buy - sell
        ) / total



    # ========================================================
    # SIGNAL
    # ========================================================

    def signal(self):


        pressure = self.volume_pressure()



        if pressure > 0.4:

            return "BUY"



        if pressure < -0.4:

            return "SELL"



        return "HOLD"