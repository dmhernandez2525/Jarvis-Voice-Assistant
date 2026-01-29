# PersonaPlex Setup Guide

PersonaPlex is NVIDIA's full-duplex conversational AI that enables natural conversations with <500ms latency.

## Prerequisites

- macOS with Apple Silicon (M1/M2/M3)
- 32GB+ RAM (96GB recommended for best performance)
- Python 3.10+
- HuggingFace account

## Quick Setup

### 1. Run the Setup Script

The setup script has already been run and installed PersonaPlex. If you need to reinstall:

```bash
cd ~/Desktop/Projects/jarvis-voice-assistant
./setup_personaplex.sh
```

### 2. Configure HuggingFace Authentication

PersonaPlex requires a HuggingFace token to download the model.

1. **Accept the Model License**
   - Go to: https://huggingface.co/nvidia/personaplex-7b-v1
   - Log in or create a HuggingFace account
   - Click "Agree and access repository"

2. **Create an Access Token**
   - Go to: https://huggingface.co/settings/tokens
   - Click "Create new token"
   - Name it (e.g., "jarvis-personaplex")
   - Select "Read" permission
   - Copy the token

3. **Set the Token**

   Option A - Set temporarily (for current terminal session):
   ```bash
   export HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxx
   ```

   Option B - Set permanently (recommended):
   ```bash
   echo 'export HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxx' >> ~/.zshrc
   source ~/.zshrc
   ```

### 3. Start PersonaPlex Server

```bash
cd ~/Desktop/Projects/jarvis-voice-assistant
./run_personaplex.sh
```

The first run will download the model (~15GB). This may take a while depending on your internet connection.

### 4. Start Jarvis App

After PersonaPlex is running, start the Jarvis app:

```bash
cd JarvisApp
./.build/debug/JarvisApp
```

Or double-click the Jarvis icon on your desktop.

## Using PersonaPlex

### Conversation Modes

The Jarvis app supports three modes:

1. **Full Duplex** (PersonaPlex only)
   - Lowest latency (<500ms)
   - Natural back-and-forth conversation
   - Requires PersonaPlex server running

2. **Hybrid** (PersonaPlex + Ollama)
   - Uses PersonaPlex for simple queries
   - Routes complex queries to Ollama
   - Best balance of speed and intelligence

3. **Legacy** (Ollama only)
   - Traditional STT -> LLM -> TTS pipeline
   - No PersonaPlex required
   - Higher latency but works offline

### Switching Modes

Click the Jarvis menu bar icon and select:
**Mode > Full Duplex (PersonaPlex)**

## Troubleshooting

### "HF_TOKEN not set" Error

Make sure your HuggingFace token is set:
```bash
echo $HF_TOKEN
```

If empty, set it:
```bash
export HF_TOKEN=your_token_here
```

### "Failed to connect to PersonaPlex" Error

1. Check if PersonaPlex server is running:
   ```bash
   curl -s http://localhost:8998/health
   ```

2. Start the server if not running:
   ```bash
   ./run_personaplex.sh
   ```

### Model Download Fails

- Check your internet connection
- Verify your HF_TOKEN has read access
- Make sure you accepted the model license at huggingface.co

### High Memory Usage

PersonaPlex with CPU offload uses significant memory. If you experience issues:
- Close other applications
- Ensure 32GB+ free RAM
- The model needs ~24GB for inference

### Audio Issues

- Check microphone permissions in System Settings > Privacy & Security > Microphone
- Ensure Jarvis app has audio input access

## Performance Notes

On Apple Silicon Macs, PersonaPlex runs in CPU mode with memory offloading:
- First response may take 2-3 seconds (model warm-up)
- Subsequent responses: <1 second
- Full duplex conversation with natural timing

For optimal performance:
- Use a Mac with 64GB+ RAM
- Close memory-intensive applications
- Use wired network for model download

## Architecture

```
                     ┌──────────────────────┐
                     │   Jarvis Swift App   │
                     │    (Menu Bar + UI)   │
                     └──────────┬───────────┘
                                │ WebSocket
                                ▼
┌───────────────────────────────────────────────────────┐
│              PersonaPlex Server (:8998)               │
│  Full-duplex conversational AI with <500ms latency   │
│  - Speech-to-Speech in real-time                      │
│  - Natural interruptions and back-channeling          │
│  - Persona and voice control                          │
└───────────────────────────────────────────────────────┘
```

## Related Documentation

- [NVIDIA PersonaPlex Research](https://research.nvidia.com/labs/adlr/personaplex/)
- [HuggingFace Model Page](https://huggingface.co/nvidia/personaplex-7b-v1)
- [GitHub Repository](https://github.com/NVIDIA/personaplex)
