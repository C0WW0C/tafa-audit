#!/usr/bin/env python3
# ============================================================
# TAFA V8 — OKX DEMO LAUNCHER
# ✅ Production-ready entry point
# ============================================================

import os
import sys
from pathlib import Path

# Setup paths
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Environment
os.environ.setdefault("TAFA_MODE", "PAPER")
os.environ.setdefault("OKX_DEMO", "1")
os.environ.setdefault("TAFA_DASHBOARD_HOST", "127.0.0.1")

import logging
from bot_v8_core import BotV8
from dashboard_v8 import start_dashboard

logger = logging.getLogger("TAFA_V8_Main")
logger.setLevel(logging.INFO)


def main():
    """
    Launch TAFA V8 bot + dashboard.
    
    Usage:
        python run_v8_okx_demo.py [--symbol BTC-USDC] [--port 8765]
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="TAFA V8 OKX Demo Bot")
    parser.add_argument("--symbol", default="BTC-USDC", help="Trading symbol")
    parser.add_argument("--port", type=int, default=8765, help="Dashboard port")
    parser.add_argument("--demo", action="store_true", default=True, help="Demo mode")
    
    args = parser.parse_args()
    
    logger.info("="*60)
    logger.info(f"TAFA V8 — OKX DEMO BOT")
    logger.info(f"Symbol: {args.symbol}")
    logger.info(f"Mode: {'DEMO' if args.demo else 'LIVE'}")
    logger.info(f"Dashboard: http://127.0.0.1:{args.port}/api/health")
    logger.info("="*60)
    
    # Start dashboard
    start_dashboard(port=args.port)
    
    # Start bot
    bot = BotV8(symbol=args.symbol, demo=args.demo)
    
    try:
        bot.run_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        bot.stop()
        logger.info("Goodbye!")


if __name__ == "__main__":
    main()
