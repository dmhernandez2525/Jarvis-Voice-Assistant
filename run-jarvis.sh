#!/bin/bash
# Run JARVIS Smart Router with Python 3.11
# Usage: ./run-jarvis.sh

cd "$(dirname "$0")"
exec python3.11 jarvis_smart_router.py "$@"
