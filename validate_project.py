#!/usr/bin/env python3
"""Validate TAFA — never deletes core/risk/trading (Windows case FS)."""
from __future__ import annotations

import os
import py_compile
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path = [str(ROOT)] + [
    p for p in sys.path if str(Path(p).resolve()) != str(ROOT.resolve())
]

REQUIRED_PKGS = ("core", "risk", "trading", "exchange", "backtesting", "ai", "data")


def main() -> int:
    print("ROOT", ROOT)
    print("python", sys.executable, sys.version.split()[0])
    errors: list[str] = []

    # Required packages must exist
    for pkg in REQUIRED_PKGS:
        d = ROOT / pkg
        if not d.is_dir():
            msg = f"MISSING package folder {pkg}/  — re-extract zip, do not delete it"
            print("FAIL", msg)
            errors.append(msg)
        elif not (d / "__init__.py").is_file():
            # create empty init if missing
            (d / "__init__.py").write_text("# package\n", encoding="utf-8")
            print("FIXED created", pkg + "/__init__.py")

    # Only remove database/ folder if it shadows database.py (NOT core etc.)
    if (ROOT / "database.py").is_file():
        for name in ("database", "Database"):
            p = ROOT / name
            if p.is_dir():
                try:
                    shutil.rmtree(p)
                    print("FIXED removed shadow", name + "/")
                except Exception as e:
                    errors.append(f"cannot remove shadow {name}/: {e}")
                    print("FAIL", errors[-1])

    critical = [
        "run_v10.py",
        "config.py",
        "core/engine.py",
        "core/database.py",
        "core/__init__.py",
        "trading/trade_manager.py",
        "trading/__init__.py",
        "risk/risk_manager.py",
    ]
    for rel in critical:
        path = ROOT / rel
        if not path.is_file():
            msg = f"missing {rel}"
            print("FAIL", msg)
            errors.append(msg)
            continue
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as e:
            msg = f"syntax {rel}: {e}"
            print("FAIL", msg)
            errors.append(msg)
    print("OK critical syntax")

    for mod in ("core", "core.engine", "core.engine_v10", "core.database", "risk.risk_manager", "trading.trade_manager", "ai.neural_parent_brain", "config"):
        try:
            __import__(mod)
            print("OK import", mod)
        except Exception as e:
            msg = f"import {mod}: {type(e).__name__}: {e}"
            print("FAIL", msg)
            errors.append(msg)

    try:
        from core.engine import TAFAEngine
        from core.database import save_signal
        from core.engine_v10 import TAFAEngineV10
        from ai.neural_parent_brain import NeuralParentBrain

        print("OK TAFAEngine + save_signal + TAFAEngineV10 + NeuralParentBrain")
    except Exception as e:
        msg = f"direct: {type(e).__name__}: {e}"
        print("FAIL", msg)
        errors.append(msg)

    try:
        import pytest  # noqa: F401

        r = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=line"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": str(ROOT)},
        )
        print((r.stdout or "")[-400:])
        if r.returncode != 0:
            errors.append("pytest failed")
            print("FAIL pytest")
        else:
            print("OK pytest")
    except ImportError:
        print("WARN pytest not installed (optional)")

    print("-" * 40)
    if errors:
        print("ERROR LIST:")
        for i, e in enumerate(errors, 1):
            print(f"  {i}. {e}")
    print("ERRORS", len(errors))
    print("RESULT:", "ALL GREEN" if not errors else "PROBLEMS — see list")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
