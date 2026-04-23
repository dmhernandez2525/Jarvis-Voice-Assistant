#!/bin/bash
# Launch Jarvis Pipecat (Option C, full-duplex local).
#
# Starts mlx_audio.server in the background for TTS, verifies Ollama is up,
# then runs the Pipecat pipeline. Kills the TTS server on exit.

set -e

cd "$(dirname "$0")"
VENV="${JARVIS_VENV:-$HOME/venvs/local-ai}"

if [ ! -f "$VENV/bin/activate" ]; then
    echo "ERROR: venv not found at $VENV"
    exit 1
fi

source "$VENV/bin/activate"

# --- Preflight: Ollama --------------------------------------------------

if ! curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    echo "ERROR: Ollama not reachable on 127.0.0.1:11434"
    echo "Start it with: ollama serve"
    exit 1
fi

for m in gemma4:26b; do
    if ! ollama list | grep -q "^$m"; then
        echo "ERROR: model $m is not pulled. Run: ollama pull $m"
        exit 1
    fi
done

# --- Start mlx_audio.server for TTS ------------------------------------

# Use env override JARVIS_TTS_BASE_URL to skip starting our own server
# (e.g. if you want to point at a persistent server elsewhere).
if [ -z "$JARVIS_TTS_BASE_URL" ] || [ "$JARVIS_TTS_BASE_URL" = "http://127.0.0.1:8000/v1" ]; then
    # Check if already running on the expected port. curl returns exit 22 for 4xx but
    # we treat any HTTP response as "something is listening" and proceed.
    if curl -fsS -m 2 http://127.0.0.1:8000/v1/models >/dev/null 2>&1; then
        echo "mlx_audio.server already running on 127.0.0.1:8000, reusing"
    else
        echo "Starting mlx_audio.server on 127.0.0.1:8000..."
        TTS_LOG="$HOME/Library/Logs/Jarvis-Gemma4/mlx_audio_server.log"
        mkdir -p "$(dirname "$TTS_LOG")"

        # Bind to loopback explicitly (audit flagged 0.0.0.0 as HIGH).
        mlx_audio.server --host 127.0.0.1 --port 8000 \
            >"$TTS_LOG" 2>&1 &
        TTS_PID=$!

        # Wait for the server to be ready (max 30s).
        for i in $(seq 1 30); do
            if curl -fsS -m 1 http://127.0.0.1:8000/v1/models >/dev/null 2>&1; then
                echo "mlx_audio.server ready (pid=$TTS_PID)"
                break
            fi
            sleep 1
        done

        if ! kill -0 "$TTS_PID" 2>/dev/null; then
            echo "ERROR: mlx_audio.server died during startup. See $TTS_LOG"
            exit 1
        fi

        # Ensure we kill the server on any exit path.
        trap "echo 'Stopping mlx_audio.server (pid=$TTS_PID)...'; kill $TTS_PID 2>/dev/null; wait $TTS_PID 2>/dev/null; echo 'stopped'" EXIT INT TERM
    fi
fi

# --- Run Pipecat --------------------------------------------------------

exec python jarvis_pipecat.py "$@"
