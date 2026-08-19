# ============================================================
# TAFA V7 PRO
# PERFORMANCE REPORT FINAL
# ============================================================

from datetime import datetime
import json


class PerformanceReport:

    def __init__(self):
        self.data = {}

    def create(self, metrics):
        self.data = {
            "date": datetime.utcnow().isoformat(),
            "metrics": metrics,
        }
        return self.data

    def export(self, file="performance.json"):
        with open(file, "w") as f:
            json.dump(self.data, f, indent=4)
