#!/bin/bash
# Run PersonaPlex server

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PERSONAPLEX_DIR="$SCRIPT_DIR/personaplex"

# Check for HF_TOKEN
if [ -z "$HF_TOKEN" ]; then
    echo "ERROR: HF_TOKEN environment variable not set"
    echo "Set it with: export HF_TOKEN=your_huggingface_token"
    echo "Or add to ~/.zshrc: echo 'export HF_TOKEN=your_token' >> ~/.zshrc"
    exit 1
fi

cd "$PERSONAPLEX_DIR"
source venv/bin/activate

echo "Starting PersonaPlex server on port 8998..."
echo "Web UI will be available at: http://localhost:8998"
echo ""
echo "Note: First response may be slow as the model warms up."
echo "Press Ctrl+C to stop."
echo ""

# Run with CPU for Apple Silicon (no CUDA)
python -m moshi.server \
    --device cpu \
    --port 8998 \
    --host 0.0.0.0
