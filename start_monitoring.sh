#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "[1/2] metrics exporter :9108"
python3 scripts/metrics_exporter.py --api "${TAFA_API:-http://127.0.0.1:8765}" --port 9108 &
EXP_PID=$!
echo $EXP_PID > data/metrics_exporter.pid 2>/dev/null || true
sleep 0.5

echo "[2/2] docker compose Grafana+Prometheus"
cd monitoring
docker compose up -d
echo ""
echo "Grafana    → http://127.0.0.1:3000  (admin / tafa)"
echo "Prometheus → http://127.0.0.1:9090"
echo "Metrics    → http://127.0.0.1:9108/metrics"
echo "Exporter PID $EXP_PID"
