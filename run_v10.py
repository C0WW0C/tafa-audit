#!/usr/bin/env python3
# ============================================================
# TAFA V10 PRO — Best-effort production entry
# Circuit breaker · quality gate · journal · paper-first
# ============================================================
from __future__ import annotations

import json
import logging
import os
import signal
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from core import status_bridge
from core.trade_journal import log_event

DATA_DIR = ROOT / "data"
LOGS_DIR = ROOT / "logs"
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ✅ FIX Windows CP1252 : forcer UTF-8 sur la console pour supporter les emojis et caractères Unicode
if sys.platform == "win32":
    import io as _io
    _console_stream = _io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True
    )
else:
    _console_stream = sys.stdout

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "tafa_v10.log", encoding="utf-8"),
        logging.StreamHandler(stream=_console_stream),
    ],
)
logger = logging.getLogger("TAFA_V10")

alive = True
PID_FILE = DATA_DIR / "bot.pid"


def _stop(signum, frame):
    global alive
    logger.info("Stop signal %s", signum)
    alive = False


signal.signal(signal.SIGINT, _stop)
signal.signal(signal.SIGTERM, _stop)


def dashboard_is_external(value: str | None = None) -> bool:
    raw = os.getenv("TAFA_DASHBOARD_EXTERNAL", "false") if value is None else value
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def main() -> int:
    logger.info("=== TAFA X ULTIMATE FINAL START ===")
    startup_mode = "PAPER"
    try:
        import config
        startup_mode = "PAPER" if getattr(config, "PAPER_TRADING", True) else "LIVE"
        logger.info(
            "MODE=%s PAPER=%s ENGINE=%s",
            getattr(config, "MODE", "?"),
            getattr(config, "PAPER_TRADING", True),
            getattr(config, "TAFA_ENGINE", "native"),
        )
        if not getattr(config, "PAPER_TRADING", True):
            logger.warning("LIVE MODE — real capital at risk")
    except Exception as e:
        logger.warning("config: %s", e)

    PID_FILE.write_text(str(os.getpid()), encoding="utf-8")
    external_dashboard = dashboard_is_external()
    if external_dashboard:
        logger.info("Dashboard local géré par le lanceur externe → http://%s:%s", os.getenv("TAFA_DASHBOARD_HOST", "127.0.0.1"), 8765)
    else:
        try:
            from web.server import start_server
            start_server(background=True)
            logger.info("Dashboard local → http://%s:%s", os.getenv("TAFA_DASHBOARD_HOST", "127.0.0.1"), 8765)
        except Exception as exc:
            logger.warning("Dashboard local indisponible : %s", exc)
    status_bridge.publish(
        {
            "running": True,
            "state": "RUNNING",
            "version": "TAFA_X_ULTIMATE_FINAL",
            "cycle": 0,
            "mode": startup_mode,
            "last_signal": "HOLD",
            "pid": os.getpid(),
        },
        merge=True,  # FIX: preserve existing equity/paper/ai fields on restart
    )
    log_event("process_start", pid=os.getpid())

    # Prefer V10 wrapper; fallback router/sim
    engine = None
    try:
        from core.engine_v10 import TAFAEngineV10

        engine = TAFAEngineV10()
        engine.start()
        logger.info("V10 engine online")
    except Exception as exc:
        logger.error("V10 engine failed: %s — abort (no silent sim in V10)", exc)
        log_event("fatal", error=str(exc))
        if PID_FILE.exists():
            PID_FILE.unlink()
        return 1

    sleep_s = float(os.getenv("TAFA_CYCLE_SLEEP", "2.0"))
    try:
        while alive:
            try:
                sig = engine.run_cycle()
                # engine_v10.run_cycle() already calls publish_status(self.status()).
                # FIX: only merge the lifecycle fields that the engine cannot know (PID, running flag).
                status_bridge.publish(
                    {"running": True, "state": "RUNNING", "pid": os.getpid()},
                    merge=True,
                )
                if engine.inner.cycle_count % 30 == 0:
                    st = status_bridge.read()
                    logger.info(
                        "cycle=%s price=%s sig=%s equity=%s circuit=%s",
                        st.get("cycle"),
                        st.get("last_price"),
                        st.get("last_signal"),
                        (st.get("performance") or {}).get("equity"),
                        (st.get("circuit") or {}).get("tripped"),
                    )
            except Exception as e:
                logger.exception("cycle: %s", e)
                log_event("error", error=str(e))
            steps = max(1, int(sleep_s / 0.25))
            for _ in range(steps):
                if not alive:
                    break
                time.sleep(0.25)
    finally:
        try:
            engine.stop()
        except Exception:
            pass
        try:
            status_bridge.publish({"running": False, "state": "STOPPED"}, merge=True)
        except Exception:
            pass
        if PID_FILE.exists():
            PID_FILE.unlink()
        log_event("process_stop")
        logger.info("=== TAFA X ULTIMATE FINAL STOPPED ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
