# ============================================================
# TAFA V7 PRO
# MONTE CARLO SIMULATOR FINAL
# ============================================================

import random


class MonteCarlo:

    def __init__(self, simulations=1000):
        self.simulations = simulations

    def run(self, returns):
        results = []
        for _ in range(self.simulations):
            sample = [random.choice(returns) for _ in returns]
            results.append(sum(sample))
        return {
            "average": sum(results) / len(results) if results else 0,
            "worst": min(results) if results else 0,
            "best": max(results) if results else 0,
        }
