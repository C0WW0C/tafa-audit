# ============================================================
# TAFA V7 PRO
# WALK FORWARD VALIDATION FINAL
# ============================================================

from logger import logger


class WalkForward:

    def __init__(self, train_size=0.70):
        self.train_size = train_size
        self.results = []
        logger.info("Walk Forward initialized")

    def split(self, data):
        index = int(len(data) * self.train_size)
        return data[:index], data[index:]

    def evaluate(self, model, data):
        train, test = self.split(data)
        model.train(train)
        score = model.evaluate(test)
        self.results.append(score)
        return score
