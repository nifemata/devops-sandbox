#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf labs/01-golden-path/template
rsync -a --exclude .git --exclude __pycache__ --exclude .pytest_cache --exclude .venv sample-app/hello/ labs/01-golden-path/template/
echo "template synced from sample-app/hello"
