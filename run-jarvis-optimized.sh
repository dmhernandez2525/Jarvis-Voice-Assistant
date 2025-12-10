#!/bin/bash
# Run JARVIS Optimized (with timing metrics) using Python 3.11
# Usage: ./run-jarvis-optimized.sh

cd "$(dirname "$0")"
exec python3.11 jarvis_optimized.py "$@"
