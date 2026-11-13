#!/usr/bin/env bash
set -e

# Alpha Research Pilot - Test Runner
cd "$(dirname "$0")/.."

if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

export PYTHONPATH=backend
echo "Running pytest test suite (including 1,500-job software load test)..."
pytest tests/ -v
