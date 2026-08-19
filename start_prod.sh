#!/usr/bin/env bash
# TAFA V10 — démarrage prod (paper par défaut)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p data logs

export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
export TAFA_MODE="${TAFA_MODE:-DEMO}"
export ENABLE_LIVE="${ENABLE_LIVE:-false}"

echo "[1/3] health_v10"
python3 health_v10.py || { echo "Health FAILED — abort"; exit 1; }

if [[ ! -f web/dist/tafa.css ]]; then
  echo "WARN: web/dist/tafa.css manquant — le style peut être cassé. Lance scripts/build_dashboard.sh"
fi

echo "[2/3] bot V10"
python3 run_v10.py >> logs/tafa_v10.log 2>&1 &
BOT_PID=$!
echo $BOT_PID > data/bot.pid
sleep 1
if ! kill -0 "$BOT_PID" 2>/dev/null; then
  echo "Bot mort au démarrage — voir logs/tafa_v10.log"
  exit 1
fi

echo "[3/3] dashboard :8765"
echo "  → http://127.0.0.1:8765/"
exec python3 web/server.py
