#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENDOR="$ROOT/third_party/Kronos"

python3 -m pip install -r "$ROOT/requirements-local-inference.txt"

if [[ ! -d "$VENDOR/.git" ]]; then
  mkdir -p "$(dirname "$VENDOR")"
  git clone --depth 1 https://github.com/shiyu-coder/Kronos.git "$VENDOR"
fi

python3 -m pip install -r "$VENDOR/requirements.txt"
echo "Prêt. Lancez : cd '$ROOT' && python3 -m model_server.server"
