# Jarvis Voice Assistant

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Swift 5.9+](https://img.shields.io/badge/Swift-5.9+-orange.svg)](https://swift.org/)

A powerful, fully offline voice assistant with **full duplex conversation** support:

- **PersonaPlex** - Full duplex AI with <500ms latency (NEW!)
- **VoiceForge** - Voice cloning and custom TTS (NEW!)
- **Whisper Large** - State-of-the-art speech recognition
- **Qwen 2.5:72b** - Maximum intelligence LLM
- **Native macOS App** - Menu bar app with global hotkey (NEW!)

## What's New: Full Duplex Conversation

Jarvis now supports **full duplex conversation** - talk naturally like you're speaking with a human:

| Feature | Legacy Mode | Full Duplex Mode |
|---------|-------------|------------------|
| Conversation Style | Turn-based | **Simultaneous** |
| Response Latency | 2-5 seconds | **<500ms** |
| Active Listening | None | **Back-channeling** |
| Interruption | Must wait | **Natural interruption** |
| Voice Cloning | None | **Clone any voice** |

## Architecture

```
+----------------------------------+
|   Swift macOS Menu Bar App       |
|   (JarvisApp - Option+Space)     |
+----------------+-----------------+
                 | WebSocket + REST
    +------------+------------+------------+
    v            v            v            v
+--------+  +----------+  +----------+  +--------+
|PersonaP|  |Orchestr. |  |VoiceForge|  | Ollama |
|  :8998 |  |   :5001  |  |   :8765  |  | :11434 |
+--------+  +----------+  +----------+  +--------+
```

## Hardware Requirements

- **Minimum RAM**: 96 GB (for full Qwen 2.5:72b)
- **Storage**: ~60 GB
- **Recommended**: Apple M2 Max or similar with 24GB+ unified memory

## Installation

### 1. Python Dependencies

```bash
pip3 install -r requirements.txt
pip3 install -r requirements-orchestrator.txt
```

### 2. Audio Libraries (macOS)

```bash
brew install portaudio
```

### 3. Swift App (Optional - for native macOS experience)

```bash
cd JarvisApp
swift build
```

## Conversation Modes

### Full Duplex Mode (Recommended)

Uses PersonaPlex for natural, simultaneous conversation with <500ms latency.

```bash
# Start the orchestrator
python3 jarvis_orchestrator.py

# Or use the Swift app (Option+Space hotkey)
./JarvisApp/.build/debug/JarvisApp
```

### Hybrid Mode

Smart routing - simple queries go to PersonaPlex, complex queries to Ollama.

```bash
curl -X POST http://localhost:5001/mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "hybrid"}'
```

### Legacy Mode

Traditional STT -> LLM -> TTS pipeline for maximum intelligence.

```bash
python3 voice_assistant.py
```

## Native macOS App (JarvisApp)

A beautiful menu bar app with:

- **Global Hotkey**: Option+Space to start/stop listening
- **Status Icons**: Visual feedback (idle/listening/processing/speaking)
- **Mode Switching**: Quick toggle between conversation modes
- **Voice Profiles**: Switch between cloned voices
- **Server Management**: Auto-start/stop backend services

### Building the App

```bash
cd JarvisApp
swift build -c release
```

### Running

```bash
# Debug build
swift run

# Or after building
./.build/debug/JarvisApp
```

## Voice Cloning with VoiceForge

Clone any voice from a 3-10 second audio sample:

### 1. Start VoiceForge Server

```bash
# From the voiceforge repository
cd ../voiceforge/python-backend
python3 server.py
```

### 2. Create a Voice Profile

```bash
# Save a voice profile
curl -X POST http://localhost:8765/generate/clone \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, this is my cloned voice",
    "ref_audio_path": "~/voice_profiles/sample.wav",
    "ref_text": "This is a sample of my voice",
    "language": "English"
  }'
```

### 3. Use Voice Profile

Voice profiles are stored in `~/voice_profiles/` and can be selected in the Swift app.

## Orchestrator API

The central orchestrator runs on port 5001 and routes between services:

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check with service status |
| `/status` | GET | Full system status |
| `/mode` | GET/POST | Get or set conversation mode |
| `/query` | POST | Process audio query |
| `/text_query` | POST | Process text query |
| `/tts` | POST | Generate speech |

### Examples

```bash
# Health check
curl http://localhost:5001/health

# Text query
curl -X POST http://localhost:5001/text_query \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello Jarvis"}'

# Audio query
curl -X POST http://localhost:5001/query \
  -F "audio=@recording.wav"

# Change mode
curl -X POST http://localhost:5001/mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "full_duplex"}'
```

## Legacy Modes

### Wake Word Mode ("Jarvis")

**Option 1: Simple Wake Word (No Setup Required)**
```bash
python3 jarvis_simple_wakeword.py
```

**Option 2: Porcupine Wake Word (Best Accuracy)**
```bash
python3 jarvis_with_wakeword.py
```

### API Server Mode

```bash
python3 voice_assistant_server.py
```

## Configuration

Edit `config/jarvis.yaml` to customize:

```yaml
# Conversation Modes
modes:
  full_duplex:
    backend: "personaplex"
  hybrid:
    backends: ["personaplex", "ollama"]
  legacy:
    backend: "ollama"

# LLM Models
models:
  router: "qwen2.5:7b"
  fast: "dolphin-mistral:7b"
  balanced: "qwen2.5:32b"
  powerful: "qwen2.5:72b"

# TTS Settings
defaults:
  tts_speaker: "Ryan"
  tts_language: "English"
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `HF_TOKEN` | HuggingFace token for PersonaPlex | Required |
| `JARVIS_ROOT` | Jarvis project directory | Auto-detected |
| `VOICEFORGE_ROOT` | VoiceForge project directory | Auto-detected |
| `PYTHON_PATH` | Python executable path | `/usr/bin/python3` |
| `DOCKER_PATH` | Docker executable path | `/usr/local/bin/docker` |
| `CORS_ORIGINS` | Allowed CORS origins | `http://localhost:*` |
| `VOICEFORGE_ALLOWED_DIRS` | Allowed voice profile directories | `~/voice_profiles` |
| `HA_URL` | Home Assistant URL | None |
| `HA_TOKEN` | Home Assistant long-lived token | None |

## PersonaPlex Setup (Full Duplex)

PersonaPlex enables full duplex conversation with <500ms latency.

### 1. Run Setup Script

```bash
./setup_personaplex.sh
```

### 2. Configure HuggingFace Token

PersonaPlex requires a HuggingFace token:

1. Accept the model license: https://huggingface.co/nvidia/personaplex-7b-v1
2. Create a token: https://huggingface.co/settings/tokens
3. Set the token:

```bash
echo 'export HF_TOKEN=hf_your_token_here' >> ~/.zshrc
source ~/.zshrc
```

### 3. Start PersonaPlex Server

```bash
./run_personaplex.sh
```

See [docs/PERSONAPLEX_SETUP.md](docs/PERSONAPLEX_SETUP.md) for detailed instructions.

## Performance

| Mode | Response Time | Best For |
|------|---------------|----------|
| Full Duplex | <500ms | Natural conversation |
| Hybrid | 500ms - 3s | General use |
| Legacy | 2-5s | Complex queries |

## Troubleshooting

- **"No module named 'pyaudio'"**: `brew install portaudio`
- **Slow responses**: Reduce model size in config
- **Memory issues**: Close other applications
- **Swift build fails**: Run `swift package resolve` first
- **PersonaPlex not connecting**: Ensure Docker is running

## Project Structure

```
jarvis-voice-assistant/
+-- JarvisApp/                 # Native macOS Swift app
|   +-- Sources/
|   |   +-- Core/              # JarvisCore, AudioPipeline, Clients
|   |   +-- Views/             # StatusBarController
|   |   +-- Services/          # ServerManager, HotKeyManager
|   |   +-- Models/            # ConversationMode, JarvisState
|   +-- Package.swift
+-- config/
|   +-- jarvis.yaml            # Central configuration
+-- voice_profiles/            # Voice cloning profiles
+-- jarvis_orchestrator.py     # Central routing server
+-- personaplex_client.py      # PersonaPlex WebSocket client
+-- voiceforge_tts.py          # VoiceForge TTS wrapper
+-- voice_assistant.py         # Legacy voice assistant
+-- docker-compose.personaplex.yml
```

## License

MIT License - see [LICENSE](LICENSE) for details.
