#!/bin/bash
# Run JARVIS Uncensored (dolphin-mistral:7b, NO filters) with Python 3.11
# Usage: ./run-jarvis-uncensored.sh

cd "$(dirname "$0")"
exec python3.11 jarvis_uncensored.py "$@"
