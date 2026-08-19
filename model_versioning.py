# ============================================================
# TAFA V7 PRO
# MODEL VERSIONING FINAL
# ============================================================


from datetime import datetime



class ModelVersioning:


    def __init__(self):

        self.models=[]



    # ========================================================
    # REGISTER
    # ========================================================

    def register(
        self,
        version,
        score
    ):


        self.models.append(

            {

            "version":

            version,


            "score":

            score,


            "date":

            datetime.utcnow().isoformat()

            }

        )



    # ========================================================
    # BEST MODEL
    # ========================================================

    def best(self):


        if not self.models:

            return None



        return max(

            self.models,

            key=lambda x:x["score"]

        )