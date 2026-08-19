# ============================================================
# TAFA V7 PRO
# POSITION MANAGER FINAL
# ============================================================


from logger import logger



class PositionManager:


    def __init__(self):

        self.positions={}


        logger.info(
            "Position Manager initialized"
        )



    # ========================================================
    # OPEN
    # ========================================================

    def open_position(
        self,
        symbol,
        qty,
        price
    ):


        self.positions[symbol]={


            "qty":qty,


            "entry":price


        }



    # ========================================================
    # UPDATE
    # ========================================================

    def update_price(
        self,
        symbol,
        price
    ):


        if symbol not in self.positions:

            return None



        entry=self.positions[symbol]["entry"]

        qty=self.positions[symbol]["qty"]



        pnl=(

            price-entry

        )*qty



        return pnl



    # ========================================================
    # CLOSE
    # ========================================================

    def close(
        self,
        symbol
    ):


        if symbol in self.positions:


            del self.positions[symbol]



    # ========================================================
    # ALL
    # ========================================================

    def get_all(self):


        return self.positions