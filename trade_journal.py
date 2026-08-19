# ============================================================
# TAFA V10 — Trade Journal (simple JSONL event logger)
# ============================================================
from __future__ import annotations

import json
import logging
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("trade_journal")
if not logger.handlers:
    # FIX Windows CP1252: force UTF-8 sur la console
    import io as _io
    _con = (_io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
            if sys.platform == "win32" else sys.stdout)
    handler = logging.StreamHandler(stream=_con)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

ROOT = Path(__file__).resolve().parents[1]
JOURNAL_FILE = ROOT / "data" / "journal.jsonl"

# Thread safety
_lock = threading.RLock()


def log_event(event: str, **kwargs: Any) -> Optional[Dict[str, Any]]:
    """
    Enregistre un événement dans le journal JSONL.

    Args:
        event: Nom de l'événement (ex: "boot", "trade", "reject", "error")
        **kwargs: Données additionnelles

    Returns:
        Le dict enregistré, ou None en cas d'échec.
    """
    with _lock:
        entry: Dict[str, Any] = {
            "ts": time.time(),
            "event": event,
        }
        entry.update(kwargs)

        try:
            JOURNAL_FILE.parent.mkdir(parents=True, exist_ok=True)
            with JOURNAL_FILE.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=str) + "\n")
            return entry
        except Exception as exc:
            logger.warning(f"Impossible d'écrire dans le journal: {exc}")
            return None


def get_recent(limit: int = 100) -> list:
    """
    Retourne les derniers événements du journal (du plus récent au plus ancien).

    Args:
        limit: Nombre maximum d'événements à retourner.

    Returns:
        Liste de dictionnaires.
    """
    with _lock:
        if not JOURNAL_FILE.exists():
            return []
        try:
            lines = JOURNAL_FILE.read_text(encoding="utf-8").splitlines()[-limit:]
            events = []
            for line in reversed(lines):
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            return events
        except Exception:
            return []