# ============================================================
# TAFA V7 PRO — Auto-config from last real backtest / lab
# ============================================================

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "data" / "datasets" / "last_backtest_report.json"

# Lab champion on Binance BTCUSDC 1h (market was -16%, strategy +0.7% best run)
CHAMPION = {
    "timeframe": "4h",
    "ema_fast": 12,
    "ema_slow": 55,
    "rsi_max": 65,
    "atr_sl": 1.5,
    "atr_tp": 4.5,
    "pos_frac": 0.15,
    "fee_bps": 8.0,
    "source": "opt_sweep_binance_BTCUSDC_4h",
}


def load_report() -> Dict[str, Any]:
    if REPORT.exists():
        try:
            return json.loads(REPORT.read_text())
        except Exception:
            return {}
    return {}


def recommended_config() -> Dict[str, Any]:
    rep = load_report()
    cfg = dict(CHAMPION)
    if rep.get("profit_factor") and rep["profit_factor"] >= 1.2:
        cfg["validated"] = True
        cfg["last_pf"] = rep["profit_factor"]
        cfg["last_wr"] = rep.get("winrate_pct")
        cfg["last_return_pct"] = rep.get("return_pct")
    else:
        cfg["validated"] = False
    return cfg
