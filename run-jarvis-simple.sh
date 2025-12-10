#!/bin/bash
# Run JARVIS with simple wake word using Python 3.11
# Usage: ./run-jarvis-simple.sh

cd "$(dirname "$0")"
exec python3.11 jarvis_simple_wakeword.py "$@"
