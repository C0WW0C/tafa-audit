# ============================================================
# TAFA V7 PRO
# MODEL TRAINING PIPELINE FINAL
# ============================================================

from logger import logger


class ModelTrainingPipeline:

    def __init__(self, feature_store=None, model=None, quality_gate=None):
        self.feature_store = feature_store
        self.model = model
        self.quality_gate = quality_gate
        self.last_score = 0
        logger.info("Model Training Pipeline initialized")

    def train(self):
        if not self.feature_store:
            return False
        dataset = self.feature_store.dataset()
        if len(dataset) < 100:
            logger.warning("Not enough training data")
            return False
        X = [x["features"] for x in dataset]
        y = [x["target"] for x in dataset]
        if self.model is None:
            return False
        self.model.train(X, y)
        return True

    def validate(self, accuracy, baseline):
        if self.quality_gate:
            return self.quality_gate.validate(accuracy, baseline)
        return False
