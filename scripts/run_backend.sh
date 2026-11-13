#!/usr/bin/env bash
set -e

# Alpha Research Pilot - Backend Daemon Startup
cd "$(dirname "$0")/.."

if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

export PYTHONPATH=backend
echo "Starting Alpha Research Pilot Daemon on http://127.0.0.1:8765..."
python3 backend/app/main.py
