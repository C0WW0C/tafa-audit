# ============================================================
# TAFA V7 PRO
# LOGGER SYSTEM FINAL
# ============================================================

import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime


# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------

LOG_DIR = "logs"

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)


LOG_FILE = os.path.join(
    LOG_DIR,
    f"tafa_v7_{datetime.now().strftime('%Y%m%d')}.log"
)


# ------------------------------------------------------------
# LOGGER FORMAT
# ------------------------------------------------------------

LOG_FORMAT = (
    "%(asctime)s | "
    "%(levelname)s | "
    "%(name)s | "
    "%(message)s"
)


DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


# ------------------------------------------------------------
# CREATE LOGGER
# ------------------------------------------------------------

def get_logger(name="TAFA_V7"):

    logger = logging.getLogger(name)

    if logger.handlers:
        return logger


    logger.setLevel(logging.INFO)


    formatter = logging.Formatter(
        LOG_FORMAT,
        DATE_FORMAT
    )


    # -------------------------------
    # FILE HANDLER
    # -------------------------------

    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=5_000_000,
        backupCount=5,
        encoding="utf-8"
    )

    file_handler.setFormatter(formatter)


    # -------------------------------
    # CONSOLE HANDLER (UTF-8 forcé — Windows CP1252 fix)
    # -------------------------------
    import sys, io
    # Sur Windows, sys.stdout peut être CP1252. On force UTF-8 avec errors='replace'
    # pour ne jamais crasher sur un emoji ou caractère accentué.
    if sys.platform == "win32":
        _stream = io.TextIOWrapper(
            sys.stdout.buffer,
            encoding="utf-8",
            errors="replace",
            line_buffering=True,
        )
    else:
        _stream = sys.stdout

    console_handler = logging.StreamHandler(stream=_stream)

    console_handler.setFormatter(formatter)


    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


    return logger



# ------------------------------------------------------------
# GLOBAL LOGGER
# ------------------------------------------------------------

logger = get_logger()



# ============================================================
# HELPERS TRADING
# ============================================================


def log_trade(
        side,
        symbol,
        qty,
        price,
        pnl=None
):

    message = (
        f"TRADE {side} | "
        f"{symbol} | "
        f"QTY={qty} | "
        f"PRICE={price}"
    )

    if pnl is not None:
        message += f" | PNL={pnl}"

    logger.info(message)



def log_signal(
        strategy,
        signal,
        confidence=None
):

    msg = (
        f"SIGNAL | "
        f"{strategy} | "
        f"{signal}"
    )

    if confidence:
        msg += f" | CONF={confidence}"

    logger.info(msg)



def log_risk(
        event,
        value
):

    logger.warning(
        f"RISK | {event} | VALUE={value}"
    )



def log_error(
        error
):

    logger.exception(
        f"ERROR | {error}"
    )



def log_engine(
        message
):

    logger.info(
        f"ENGINE | {message}"
    )



def log_ai(
        message
):

    logger.info(
        f"AI | {message}"
    )



# ============================================================
# START MESSAGE
# ============================================================

logger.info(
    "===== TAFA V7 PRO LOGGER INITIALIZED ====="
)