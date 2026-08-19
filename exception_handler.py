# ============================================================
# TAFA V7 PRO
# EXCEPTION HANDLER FINAL
# ============================================================


from logger import logger



class ExceptionHandler:



    def __init__(self):

        pass



    # ========================================================
    # HANDLE
    # ========================================================

    def handle(
        self,
        error
    ):


        logger.error(

            f"TAFA ERROR : {error}"

        )


        return {


            "status":

            "ERROR",


            "message":

            str(error)

        }



    # ========================================================
    # SAFE EXECUTION
    # ========================================================

    def safe_execute(
        self,
        function,
        *args
    ):


        try:

            return function(
                *args
            )


        except Exception as e:


            return self.handle(e)