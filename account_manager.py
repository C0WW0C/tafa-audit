# ============================================================
# TAFA V7 PRO
# ACCOUNT MANAGER FINAL
# ============================================================


from logger import logger


from config import (
    QUOTE_CURRENCY
)



class AccountManager:


    def __init__(
        self,
        client=None
    ):

        self.client = client

        self.balance = 0

        self.positions = {}



        logger.info(
            "Account Manager initialized"
        )



    # ========================================================
    # BALANCE
    # ========================================================

    def get_balance(self):


        if self.client:


            try:

                data = (
                    self.client.get_balance()
                )

                self.balance = data


            except Exception as e:


                logger.error(
                    f"Balance error {e}"
                )


        return self.balance



    # ========================================================
    # UPDATE BALANCE
    # ========================================================

    def update_balance(
            self,
            amount
    ):

        self.balance = amount



    # ========================================================
    # POSITION MEMORY
    # ========================================================

    def add_position(
            self,
            symbol,
            qty,
            price
    ):


        self.positions[symbol] = {


            "qty": qty,


            "entry": price


        }



    # ========================================================
    # REMOVE POSITION
    # ========================================================

    def remove_position(
            self,
            symbol
    ):


        if symbol in self.positions:

            del self.positions[symbol]



    # ========================================================
    # GET POSITIONS
    # ========================================================

    def get_positions(self):

        return self.positions