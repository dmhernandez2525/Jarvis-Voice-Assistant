#!/bin/bash
# Quick health check of the Jarvis Gemma 4 router logs.
# Usage:
#   ./run-jarvis-health.sh                 # last 24h summary
#   ./run-jarvis-health.sh --hours 1       # last hour
#   ./run-jarvis-health.sh --tail 50       # last 50 structured events
#   ./run-jarvis-health.sh --crashes       # list crash files
#   ./run-jarvis-health.sh --crashes --show  # plus most recent crash body
#   ./run-jarvis-health.sh --session <id>  # detail for one session

set -e
cd "$(dirname "$0")"
VENV="${JARVIS_VENV:-$HOME/venvs/local-ai}"

# The health tool is pure stdlib, so any Python 3 works, but prefer the venv.
if [ -x "$VENV/bin/python" ]; then
    exec "$VENV/bin/python" jarvis_health.py "$@"
else
    exec python3 jarvis_health.py "$@"
fi
