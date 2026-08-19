#!/usr/bin/env python3
"""TAFA simple launcher — bot + dashboard in SEPARATE processes (not same thread).

Usage:
  python3 launch_tafa.py
  python3 launch_tafa.py --panel          # Streamlit Elite Panel (default)
  python3 launch_tafa.py --web            # web desk on :8765
  python3 launch_tafa.py --panel --web    # both UIs + bot
  python3 launch_tafa.py --bot-only
  python3 launch_tafa.py --dashboard-only

Ctrl+C stops every child process.
"""
from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOGS = ROOT / "logs"
DATA = ROOT / "data"
LOGS.mkdir(parents=True, exist_ok=True)
DATA.mkdir(parents=True, exist_ok=True)

children: list[subprocess.Popen] = []


def _env(extra: dict | None = None) -> dict:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONUNBUFFERED"] = "1"
    if extra:
        env.update(extra)
    return env


def _spawn(name: str, cmd: list[str], log_name: str, env: dict | None = None) -> subprocess.Popen:
    log_path = LOGS / log_name
    log_f = open(log_path, "ab", buffering=0)
    print(f"  ▶ {name}")
    print(f"      cmd  {' '.join(cmd)}")
    print(f"      log  {log_path}")
    proc = subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        env=env or _env(),
        stdout=log_f,
        stderr=subprocess.STDOUT,
        start_new_session=True,  # own process group — not same thread
    )
    proc._tafa_log = log_f  # type: ignore[attr-defined]
    proc._tafa_name = name  # type: ignore[attr-defined]
    children.append(proc)
    return proc


def _stop_all(signum=None, frame=None) -> None:
    print("\n■ Arrêt de tous les processus…")
    for proc in reversed(children):
        name = getattr(proc, "_tafa_name", f"pid={proc.pid}")
        if proc.poll() is not None:
            continue
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except Exception:
            try:
                proc.terminate()
            except Exception:
                pass
        print(f"  ■ SIGTERM {name} (pid {proc.pid})")
    deadline = time.time() + 8
    for proc in children:
        remaining = max(0.1, deadline - time.time())
        try:
            proc.wait(timeout=remaining)
        except Exception:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        log_f = getattr(proc, "_tafa_log", None)
        if log_f:
            try:
                log_f.close()
            except Exception:
                pass
    # cleanup pid file if bot left it
    pid_file = DATA / "bot.pid"
    try:
        if pid_file.exists():
            pid_file.unlink()
    except Exception:
        pass
    print("■ Terminé.")
    sys.exit(0)


def main() -> int:
    ap = argparse.ArgumentParser(description="TAFA launcher — bot + dashboard (processus séparés)")
    ap.add_argument("--panel", action="store_true", help="Streamlit Elite Panel (:8501)")
    ap.add_argument("--web", action="store_true", help="Dashboard web desk (:8765)")
    ap.add_argument("--bot-only", action="store_true")
    ap.add_argument("--dashboard-only", action="store_true")
    ap.add_argument("--no-bot", action="store_true", help="alias dashboard-only")
    args = ap.parse_args()

    # defaults: bot + panel
    if not any([args.panel, args.web, args.bot_only, args.dashboard_only, args.no_bot]):
        args.panel = True

    want_bot = not (args.dashboard_only or args.no_bot)
    if args.bot_only:
        args.panel = False
        args.web = False
        want_bot = True

    signal.signal(signal.SIGINT, _stop_all)
    signal.signal(signal.SIGTERM, _stop_all)

    py = sys.executable
    print("=" * 56)
    print(" TAFA LAUNCHER — processus séparés (pas le même thread)")
    print("=" * 56)

    if want_bot:
        # Bot must NOT embed dashboard when we launch UI externally
        _spawn(
            "BOT run_v10",
            [py, str(ROOT / "run_v10.py")],
            "launch_bot.log",
            env=_env({"TAFA_DASHBOARD_EXTERNAL": "true"}),
        )
        time.sleep(1.2)

    if args.panel and not args.bot_only:
        # Streamlit Elite Panel Control — own process
        _spawn(
            "DASHBOARD Streamlit panel",
            [
                py, "-m", "streamlit", "run", str(ROOT / "control_panel.py"),
                "--server.headless", "true",
                "--server.port", "8501",
                "--browser.gatherUsageStats", "false",
            ],
            "launch_panel.log",
        )

    if args.web and not args.bot_only:
        _spawn(
            "DASHBOARD web desk",
            [py, str(ROOT / "web" / "server.py")],
            "launch_web.log",
        )

    if not children:
        print("Rien à lancer. Utilise --panel / --web / --bot-only")
        return 1

    print("-" * 56)
    if want_bot:
        print(" Bot paper     : actif (logs/launch_bot.log)")
    if args.panel and not args.bot_only:
        print(" Elite Panel   : http://127.0.0.1:8501")
    if args.web and not args.bot_only:
        print(" Desk / Elite  : http://127.0.0.1:8765/desk")
        print("                 http://127.0.0.1:8765/")
    print(" Ctrl+C        : stop bot + dashboard")
    print("-" * 56)

    # Supervise: if bot dies, report; keep UI until Ctrl+C
    try:
        while True:
            time.sleep(1.0)
            for proc in list(children):
                code = proc.poll()
                if code is not None:
                    name = getattr(proc, "_tafa_name", "child")
                    print(f"! {name} s'est arrêté (code {code}). Voir logs/.")
                    children.remove(proc)
            if want_bot and not any("BOT" in getattr(p, "_tafa_name", "") for p in children):
                print("Bot arrêté — Ctrl+C pour fermer le reste, ou relance.")
                want_bot = False  # warn once
            if not children:
                print("Tous les processus sont terminés.")
                break
    except KeyboardInterrupt:
        _stop_all()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
