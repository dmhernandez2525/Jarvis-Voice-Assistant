#!/bin/bash
# Run JARVIS V2 (with conversation history, countdown, fixed TTS)
# Usage: ./run-jarvis-v2.sh

cd "$(dirname "$0")"
exec python3.11 jarvis_v2.py "$@"
