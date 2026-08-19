#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
python health_v10.py || { echo "Health FAILED"; exit 1; }
echo "Starting TAFA V10..."
exec python run_v10.py
