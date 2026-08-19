#!/usr/bin/env python3
"""M7 release gate for TAFA paper/demo packages; never starts live trading."""
from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "run_paper_demo.py",
    ".env.paper-demo.example",
    "scripts/validate_project.py",
    "scripts/self_test.py",
    "web/server.py",
    "M7_PAPER_DEMO_RUNBOOK.md",
)


def run_step(label: str, command: list[str], env: dict[str, str]) -> bool:
    print(f"\n== {label} ==")
    result = subprocess.run(command, cwd=ROOT, env=env, text=True)
    return result.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate TAFA M7 paper/demo release readiness.")
    parser.add_argument("--with-smoke", action="store_true", help="Run the public-market smoke test after static validation.")
    args = parser.parse_args()

    errors: list[str] = []
    for rel in REQUIRED:
        if not (ROOT / rel).is_file():
            errors.append(f"missing required release file: {rel}")
    for module in ("requests", "websocket"):
        if importlib.util.find_spec(module) is None:
            errors.append(f"missing paper/demo runtime dependency: {module}")

    env = os.environ.copy()
    env.update(
        {
            "TAFA_MODE": "DEMO",
            "ENABLE_LIVE": "false",
            "LIVE_CONFIRM": "",
            "TAFA_ENGINE": "native",
            "TAFA_PAPER_ONLY": "true",
            "PYTHONPATH": str(ROOT),
        }
    )
    print("TAFA M7 release gate: PAPER/DEMO only")
    print("mode=", env["TAFA_MODE"], "enable_live=", env["ENABLE_LIVE"], "engine=", env["TAFA_ENGINE"])

    if not errors and not run_step("project validation", [sys.executable, "scripts/validate_project.py"], env):
        errors.append("project validation failed")
    if not errors and args.with_smoke and not run_step("paper/demo smoke test", [sys.executable, "scripts/self_test.py"], env):
        errors.append("paper/demo smoke test failed")

    if errors:
        print("\nM7 RELEASE GATE: FAILED")
        for error in errors:
            print(" -", error)
        return 1
    print("\nM7 RELEASE GATE: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
