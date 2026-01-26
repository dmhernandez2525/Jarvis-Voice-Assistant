#!/bin/bash
# PersonaPlex Setup Script for macOS
# This script sets up NVIDIA's PersonaPlex full-duplex AI

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PERSONAPLEX_DIR="$SCRIPT_DIR/personaplex"

echo "========================================"
echo "PersonaPlex Setup for Jarvis Voice Assistant"
echo "========================================"
echo ""

# Check for Homebrew
if ! command -v brew &> /dev/null; then
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# Install Opus codec
echo "Installing Opus audio codec..."
brew install opus 2>/dev/null || echo "Opus already installed"

# Check for Python 3.10+
PYTHON_CMD=""
if command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
elif command -v python3.10 &> /dev/null; then
    PYTHON_CMD="python3.10"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    echo "ERROR: Python 3.10+ is required"
    echo "Install with: brew install python@3.11"
    exit 1
fi

echo "Using Python: $PYTHON_CMD ($($PYTHON_CMD --version))"

# Clone PersonaPlex if not exists
if [ ! -d "$PERSONAPLEX_DIR" ]; then
    echo "Cloning PersonaPlex repository..."
    git clone https://github.com/NVIDIA/personaplex.git "$PERSONAPLEX_DIR"
else
    echo "PersonaPlex directory exists, updating..."
    cd "$PERSONAPLEX_DIR"
    git pull origin main || true
fi

cd "$PERSONAPLEX_DIR"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    $PYTHON_CMD -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install PyTorch for macOS (CPU with MPS fallback)
echo "Installing PyTorch for macOS..."
pip install torch torchvision torchaudio

# Install accelerate for CPU offload support
echo "Installing accelerate for memory management..."
pip install accelerate

# Install PersonaPlex
echo "Installing PersonaPlex..."
if [ -d "moshi" ]; then
    pip install ./moshi
else
    pip install -e .
fi

# Install additional dependencies
pip install websockets aiohttp numpy

# Check for HuggingFace token
if [ -z "$HF_TOKEN" ]; then
    echo ""
    echo "========================================"
    echo "IMPORTANT: HuggingFace Token Required"
    echo "========================================"
    echo ""
    echo "1. Go to: https://huggingface.co/nvidia/personaplex-7b-v1"
    echo "2. Accept the model license"
    echo "3. Go to: https://huggingface.co/settings/tokens"
    echo "4. Create a token with 'read' permission"
    echo "5. Set the token in your environment:"
    echo ""
    echo "   export HF_TOKEN=your_token_here"
    echo ""
    echo "Or add to ~/.zshrc or ~/.bashrc for persistence."
    echo ""
fi

# Create run script
cat > "$SCRIPT_DIR/run_personaplex.sh" << 'EOF'
#!/bin/bash
# Run PersonaPlex server

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PERSONAPLEX_DIR="$SCRIPT_DIR/personaplex"

# Check for HF_TOKEN
if [ -z "$HF_TOKEN" ]; then
    echo "ERROR: HF_TOKEN environment variable not set"
    echo "Set it with: export HF_TOKEN=your_huggingface_token"
    exit 1
fi

cd "$PERSONAPLEX_DIR"
source venv/bin/activate

# Create SSL directory
SSL_DIR=$(mktemp -d)

echo "Starting PersonaPlex server on port 8998..."
echo "Web UI will be available at: https://localhost:8998"
echo ""

# Run with CPU offload for Mac (no NVIDIA GPU)
# Use --device cpu for Apple Silicon or --device mps if MPS works
python -m moshi.server \
    --ssl "$SSL_DIR" \
    --cpu-offload \
    --port 8998 \
    --host 0.0.0.0
EOF

chmod +x "$SCRIPT_DIR/run_personaplex.sh"

echo ""
echo "========================================"
echo "PersonaPlex Setup Complete!"
echo "========================================"
echo ""
echo "To start PersonaPlex server:"
echo "  1. Set HuggingFace token: export HF_TOKEN=your_token"
echo "  2. Run: ./run_personaplex.sh"
echo ""
echo "The server will be available at:"
echo "  - Web UI: https://localhost:8998"
echo "  - WebSocket: wss://localhost:8998/ws"
echo ""
