#!/usr/bin/env python3
"""Elite Final paper-only launcher with a 500 USDC local paper portfolio."""
from __future__ import annotations

import os


ELITE_FINAL_ENV = {
    "TAFA_MODE": "DEMO",
    "ENABLE_LIVE": "false",
    "LIVE_CONFIRM": "",
    "TAFA_ENGINE": "native",
    "TAFA_PAPER_ONLY": "true",
    "TAFA_PAPER_CAPITAL": "500",
    "TAFA_ELITE_TIMEFRAMES": "5m,15m,1H,4H",
    "TAFA_TARGET_TP_PERCENT": "1.8",
    "TAFA_PAPER_SESSION_NET_TARGET_USD": "5",
    "TAFA_STORAGE_PROFILE": "local",
}


def configure_elite_final_paper() -> dict[str, str]:
    os.environ.update(ELITE_FINAL_ENV)
    from core.storage_profile import resolve_storage_profile

    # Verifies the paper-only persistence contract without opening a service.
    resolve_storage_profile()
    return dict(ELITE_FINAL_ENV)


def main() -> int:
    configure_elite_final_paper()
    print("TAFA ELITE FINAL — PAPER/DEMO ONLY — 500 USDC local portfolio.")
    from run_v10 import main as run_v10_main

    return run_v10_main()


if __name__ == "__main__":
    raise SystemExit(main())
