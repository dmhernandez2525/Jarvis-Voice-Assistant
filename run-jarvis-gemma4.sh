#!/bin/bash
# Run JARVIS Gemma 4 Router variant.
#
# Uses the hardened local-ai venv at ~/venvs/local-ai (Python 3.12, audit-
# pinned torch/transformers/pillow/mlx, parakeet-mlx + mlx-audio installed).
#
# Models pulled via Ollama on the primary account at 127.0.0.1:11434:
#   gemma4:e2b  (router + fast tier)
#   gemma4:e4b  (fast tier alternate)
#   gemma4:26b  (balanced, daily driver)
#   gemma4:31b  (powerful, reasoning-heavy)
#
# Usage: ./run-jarvis-gemma4.sh

set -e

cd "$(dirname "$0")"

VENV="${JARVIS_VENV:-$HOME/venvs/local-ai}"
if [ ! -f "$VENV/bin/activate" ]; then
  echo "ERROR: venv not found at $VENV"
  echo "See ~/Desktop/command-center/research/local-ai-stack/HARDENED_INSTALL_PLAN.md"
  exit 1
fi

# Verify Ollama is reachable before loading anything else.
if ! curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  echo "ERROR: Ollama is not reachable on 127.0.0.1:11434"
  echo "Start it with:  ollama serve"
  exit 1
fi

# Verify the four Gemma 4 models are pulled.
for m in gemma4:e2b gemma4:e4b gemma4:26b gemma4:31b; do
  if ! ollama list | grep -q "^$m"; then
    echo "ERROR: model $m is not pulled. Run: ollama pull $m"
    exit 1
  fi
done

source "$VENV/bin/activate"
exec python jarvis_gemma4_router.py "$@"
