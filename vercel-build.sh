#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

# Generate the static site
python3 control-plane/scripts/generate_site.py

if [[ ! -f docs/index.html ]]; then
  echo "ERROR: docs/index.html was not generated" >&2
  exit 1
fi

# Copy the generated index.html to the Vercel output directory
mkdir -p control-plane/api/ui
cp -f docs/index.html control-plane/api/ui/index.html
