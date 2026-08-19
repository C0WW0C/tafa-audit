# ============================================================
# TAFA V7 PRO
# DATABASE CORE FINAL
# SQLite Trading Memory System (version corrigée)
# ============================================================

import sqlite3
import json
import logging
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_log = logging.getLogger("database")
if not _log.handlers:
    # FIX Windows CP1252: force UTF-8 sur la console
    import io as _io
    _con = (_io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
            if sys.platform == "win32" else sys.stdout)
    handler = logging.StreamHandler(stream=_con)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    _log.addHandler(handler)
    _log.setLevel(logging.INFO)

ROOT = Path(__file__).resolve().parents[1]
DATABASE_FILE = ROOT / "tafa_v7.db"

_CONN_TIMEOUT = 10.0
_write_lock = threading.Lock()


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(
        str(DATABASE_FILE),
        check_same_thread=False,
        timeout=_CONN_TIMEOUT
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def init_database() -> None:
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            symbol TEXT,
            side TEXT,
            qty REAL,
            price REAL,
            pnl REAL,
            strategy TEXT,
            mode TEXT
        )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);")

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            order_id TEXT,
            symbol TEXT,
            side TEXT,
            order_type TEXT,
            qty REAL,
            price REAL,
            status TEXT
        )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_timestamp ON orders(timestamp);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_symbol ON orders(symbol);")

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            strategy TEXT,
            signal TEXT,
            confidence REAL,
            regime TEXT,
            metadata TEXT
        )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON signals(timestamp);")

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            balance REAL,
            equity REAL,
            pnl REAL,
            drawdown REAL
        )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_performance_timestamp ON performance(timestamp);")

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            level TEXT,
            message TEXT
        )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp ON system_logs(timestamp);")

        conn.commit()
        _log.info("Base de données initialisée avec succès")
    except Exception as exc:
        _log.error(f"Erreur lors de l'initialisation de la base: {exc}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_trade(
        symbol: str,
        side: str,
        qty: float,
        price: float,
        pnl: float = 0.0,
        strategy: str = "UNKNOWN",
        mode: str = "DEMO"
) -> bool:
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO trades
            (timestamp, symbol, side, qty, price, pnl, strategy, mode)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (_now_iso(), symbol, side, qty, price, pnl, strategy, mode)
        )
        conn.commit()
        return True
    except Exception as exc:
        _log.error(f"save_trade échec: {exc}")
        return False
    finally:
        if conn:
            conn.close()


def save_order(
        order_id: str,
        symbol: str,
        side: str,
        order_type: str,
        qty: float,
        price: float,
        status: str
) -> bool:
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO orders
            (timestamp, order_id, symbol, side, order_type, qty, price, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (_now_iso(), order_id, symbol, side, order_type, qty, price, status)
        )
        conn.commit()
        return True
    except Exception as exc:
        _log.error(f"save_order échec: {exc}")
        return False
    finally:
        if conn:
            conn.close()


def save_signal(
        strategy: str,
        signal: str,
        confidence: float,
        regime: str,
        metadata: Optional[Dict[str, Any]] = None
) -> bool:
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO signals
            (timestamp, strategy, signal, confidence, regime, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                _now_iso(),
                strategy,
                signal,
                confidence,
                regime,
                json.dumps(metadata) if metadata else "{}"
            )
        )
        conn.commit()
        return True
    except Exception as exc:
        _log.error(f"save_signal échec: {exc}")
        return False
    finally:
        if conn:
            conn.close()


def save_performance(
        balance: float,
        equity: float,
        pnl: float,
        drawdown: float
) -> bool:
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO performance
            (timestamp, balance, equity, pnl, drawdown)
            VALUES (?, ?, ?, ?, ?)
            """,
            (_now_iso(), balance, equity, pnl, drawdown)
        )
        conn.commit()
        return True
    except Exception as exc:
        _log.error(f"save_performance échec: {exc}")
        return False
    finally:
        if conn:
            conn.close()


def save_log(
        level: str,
        message: str
) -> bool:
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO system_logs
            (timestamp, level, message)
            VALUES (?, ?, ?)
            """,
            (_now_iso(), level, message)
        )
        conn.commit()
        return True
    except Exception as exc:
        _log.error(f"save_log échec: {exc}")
        return False
    finally:
        if conn:
            conn.close()


def get_trades(limit: int = 100) -> List[Dict[str, Any]]:
    conn = None
    try:
        conn = get_connection()
        rows = conn.execute(
            """
            SELECT * FROM trades
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    except Exception as exc:
        _log.error(f"get_trades échec: {exc}")
        return []
    finally:
        if conn:
            conn.close()


def get_signals(limit: int = 100) -> List[Dict[str, Any]]:
    conn = None
    try:
        conn = get_connection()
        rows = conn.execute(
            """
            SELECT * FROM signals
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    except Exception as exc:
        _log.error(f"get_signals échec: {exc}")
        return []
    finally:
        if conn:
            conn.close()


def get_performance(limit: int = 100) -> List[Dict[str, Any]]:
    conn = None
    try:
        conn = get_connection()
        rows = conn.execute(
            """
            SELECT * FROM performance
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    except Exception as exc:
        _log.error(f"get_performance échec: {exc}")
        return []
    finally:
        if conn:
            conn.close()


def cleanup_old_data(days: int = 30) -> None:
    conn = None
    try:
        conn = get_connection()
        cutoff = datetime.now(timezone.utc).timestamp() - days * 86400
        cursor = conn.cursor()
        for table in ["trades", "orders", "signals", "performance", "system_logs"]:
            cursor.execute(
                f"DELETE FROM {table} WHERE timestamp < ?",
                (datetime.fromtimestamp(cutoff, tz=timezone.utc).isoformat(),)
            )
        conn.commit()
        _log.info(f"Nettoyage des données plus vieilles que {days} jours effectué")
    except Exception as exc:
        _log.error(f"Nettoyage échoué: {exc}")
    finally:
        if conn:
            conn.close()


init_database()