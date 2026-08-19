# ============================================================
# TAFA V7 PRO
# LIVE SWITCH FINAL
# ============================================================


from logger import logger



class LiveSwitch:


    def __init__(self):

        self.live=False



    def enable_live(self):


        self.live=True


        logger.warning(
            "LIVE MODE ENABLED"
        )



    def disable_live(self):


        self.live=False



    def status(self):


        return self.live