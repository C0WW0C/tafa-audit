#!/usr/bin/env python3
"""Safe M7 launcher: force the TAFA runtime into OKX public paper/demo mode."""
from __future__ import annotations

import os


PAPER_DEMO_ENV = {
    "TAFA_MODE": "DEMO",
    "ENABLE_LIVE": "false",
    "LIVE_CONFIRM": "",
    "TAFA_ENGINE": "native",
    "TAFA_PAPER_ONLY": "true",
}


def configure_paper_demo() -> dict[str, str]:
    """Override potentially unsafe inherited variables before config.py is imported."""
    os.environ.update(PAPER_DEMO_ENV)
    return dict(PAPER_DEMO_ENV)


def main() -> int:
    configure_paper_demo()
    print("TAFA M7 PAPER/DEMO — OKX public data only; live trading is forcibly disabled.")
    from run_v10 import main as run_v10_main

    return run_v10_main()


if __name__ == "__main__":
    raise SystemExit(main())
