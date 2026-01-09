#!/bin/bash
set -e

# Generate the static site
python control-plane/scripts/generate_site.py

# Copy the generated index.html to the Vercel output directory
cp docs/index.html control-plane/api/ui/index.html
