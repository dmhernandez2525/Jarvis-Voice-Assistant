#!/bin/bash
# Setup Python 3.11 for JARVIS Voice Assistant
# This script installs all dependencies using Python 3.11

set -e  # Exit on error

echo "🐍 Setting up Python 3.11 for JARVIS..."
echo ""

# Check Python 3.11 is installed
if ! command -v python3.11 &> /dev/null; then
    echo "❌ Python 3.11 not found. Installing via Homebrew..."
    brew install python@3.11
else
    echo "✓ Python 3.11 found: $(python3.11 --version)"
fi

echo ""
echo "📦 Upgrading pip..."
python3.11 -m pip install --upgrade pip --user

echo ""
echo "📋 Installing dependencies from requirements.txt..."
echo "   This may take 5-10 minutes..."
echo ""

# Install system dependencies first
echo "🔧 Checking system dependencies..."
if ! command -v ffmpeg &> /dev/null; then
    echo "   Installing ffmpeg..."
    brew install ffmpeg
else
    echo "   ✓ ffmpeg already installed"
fi

if ! brew list portaudio &> /dev/null; then
    echo "   Installing portaudio..."
    brew install portaudio
else
    echo "   ✓ portaudio already installed"
fi

echo ""
echo "📦 Installing Python packages..."

# Install packages one by one with progress
packages=(
    "openai-whisper"
    "pyaudio"
    "sounddevice"
    "scipy"
    "numpy"
    "ollama"
    "pvporcupine"
    "flask"
    "pyttsx3"
    "requests"
    "paho-mqtt"
    "TTS"
)

total=${#packages[@]}
current=0

for package in "${packages[@]}"; do
    ((current++))
    echo ""
    echo "[$current/$total] Installing $package..."
    python3.11 -m pip install "$package" --user
done

echo ""
echo "✅ All dependencies installed!"
echo ""

# Create a .python-version file to remember which Python to use
echo "python3.11" > ~/.python-jarvis-version

echo "🎉 Setup complete!"
echo ""
echo "Python version: $(python3.11 --version)"
echo ""
echo "Next steps:"
echo "  1. Test JARVIS: python3.11 jarvis_smart_router.py"
echo "  2. Or run simple version: python3.11 jarvis_optimized.py"
echo ""
