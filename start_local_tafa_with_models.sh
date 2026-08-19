#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
MODEL_PID=""
DASHBOARD_PID=""

cleanup() {
  [[ -n "$MODEL_PID" ]] && kill "$MODEL_PID" 2>/dev/null || true
  [[ -n "$DASHBOARD_PID" ]] && kill "$DASHBOARD_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

wait_for() {
  local url="$1"
  for _ in $(seq 1 20); do
    if curl --fail --silent "$url" >/dev/null; then
      return 0
    fi
    sleep 0.25
  done
  return 1
}

if [[ ! -f .env ]]; then
  echo "Créez d’abord .env : cp .env.local-model-paper.example .env"
  exit 1
fi

if [[ ! -d third_party/Kronos/.git ]]; then
  echo "Préparez les dépendances : scripts/setup_local_model_server.sh"
  exit 1
fi

MODEL_URL="http://127.0.0.1:${TAFA_MODEL_SERVER_PORT:-8787}/health"
DASHBOARD_URL="http://127.0.0.1:8765/api/health"
if ! curl --fail --silent "$MODEL_URL" >/dev/null; then
  python3 -m model_server.server &
  MODEL_PID=$!
fi
if ! wait_for "$MODEL_URL"; then
  echo "Le serveur de modèles n’a pas démarré."
  exit 1
fi

if ! curl --fail --silent "$DASHBOARD_URL" >/dev/null; then
  python3 web/server.py &
  DASHBOARD_PID=$!
fi
if ! wait_for "$DASHBOARD_URL"; then
  echo "Le dashboard n’a pas démarré."
  exit 1
fi

export TAFA_DASHBOARD_EXTERNAL=true
echo "Endpoints et dashboard actifs ; lancement TAFA en paper trading."
python3 run_elite_final_paper.py
