"""Windows shadow cleanup — SAFE (never deletes core/ risk/ trading/).

Only removes a directory named database/Database when database.py exists
as a file (true shadow of the module).

Run:  python scripts/fix_windows_shadows.py
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# NEVER delete these packages (required by the bot)
PROTECTED = {
    "core",
    "risk",
    "trading",
    "ai",
    "exchange",
    "backtesting",
    "data",
    "portfolio",
    "web",
    "tests",
    "scripts",
    "tools",
    "analysis",
    "config_pkg",
    "ui_pages",
    "logs",
}


def main() -> int:
    print("ROOT", ROOT)
    removed = []

    # Only safe target: folder that shadows database.py module file
    for name in ("database", "Database"):
        p = ROOT / name
        if p.is_dir() and (ROOT / "database.py").is_file():
            # refuse if it looks like our real package tree (shouldn't)
            if p.name.lower() in PROTECTED:
                print("SKIP protected", p)
                continue
            try:
                shutil.rmtree(p)
                removed.append(name)
                print("REMOVED shadow folder:", name + "/")
            except Exception as e:
                print("FAIL remove", name, e)
                return 1

    # Report required packages
    for pkg in ("core", "risk", "trading", "exchange", "backtesting"):
        d = ROOT / pkg
        init = d / "__init__.py"
        status = "OK" if d.is_dir() and init.is_file() else "MISSING"
        print(f"{status} package {pkg}/")
        if status == "MISSING":
            print("  -> Re-extract the zip. Do NOT delete core/ risk/ trading/")
            return 1

    sys.path.insert(0, str(ROOT))
    try:
        import core  # noqa: F401
        from core.engine import TAFAEngine  # noqa: F401
        from core.database import save_signal  # noqa: F401
        print("OK import core + database + TAFAEngine")
    except Exception as e:
        print("FAIL import:", type(e).__name__, e)
        return 1

    print("Done. removed=", removed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
