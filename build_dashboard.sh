#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p web/dist web/src
if [[ ! -f web/src/input.css ]]; then
  printf '@tailwind base;\n@tailwind components;\n@tailwind utilities;\n' > web/src/input.css
fi
if command -v tailwindcss >/dev/null 2>&1; then
  TW=tailwindcss
elif [[ -x ./bin/tailwindcss ]]; then
  TW=./bin/tailwindcss
else
  echo "Installe le CLI Tailwind standalone dans ./bin/tailwindcss"
  echo "https://github.com/tailwindlabs/tailwindcss/releases"
  exit 1
fi
"$TW" -i ./web/src/input.css -o ./web/dist/tafa.css --minify
echo "OK → web/dist/tafa.css ($(wc -c < web/dist/tafa.css) bytes)"
