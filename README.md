# Voice Assistant - Maximum Intelligence Edition

A powerful voice assistant using:
- **Whisper Large** - State-of-the-art speech recognition
- **Qwen 2.5:72b** - Maximum intelligence LLM (671B parameters)
- **pyttsx3** - Text-to-speech

## Hardware Requirements

- **Minimum RAM**: 96 GB (for Qwen 2.5:72b)
- **Storage**: ~60 GB
- **Recommended**: Apple M2 Max or similar

## Installation

1. Install dependencies:
```bash
cd ~/voice-assistant
pip3 install -r requirements.txt
```

2. Install additional audio libraries (macOS):
```bash
brew install portaudio
```

## Usage

### Wake Word Mode ("Jarvis")

**RECOMMENDED - Two Options:**

**Option 1: Simple Wake Word (No Setup Required)**
```bash
python3 jarvis_simple_wakeword.py
```
- 100% offline, no API key needed
- Uses Whisper to detect "Jarvis"
- Slightly slower (~1-2s wake word detection)

**Option 2: Porcupine Wake Word (Best Accuracy)**
```bash
python3 jarvis_with_wakeword.py
```
- Requires free Porcupine access key (see `PORCUPINE_SETUP.md`)
- Fastest wake word detection (<0.1s)
- Still 100% offline after setup

**With Home Assistant Integration:**
```bash
python3 jarvis_homeassistant.py
```
(Also requires Porcupine access key)

### Interactive Mode (Local Mac)

Run the basic voice assistant on this Mac (no wake word):

```bash
python3 voice_assistant.py
```

Press Enter to record 5 seconds of audio, then the assistant will respond.

### API Server Mode (For Remote Devices)

Run as a server that remote devices can connect to:

```bash
python3 voice_assistant_server.py
```

Server runs on `http://0.0.0.0:5000`

#### API Endpoints:

1. **Health Check**
   ```bash
   curl http://SERVER_IP:5000/health
   ```

2. **Text Query** (for testing)
   ```bash
   curl -X POST http://SERVER_IP:5000/text_query \
     -H "Content-Type: application/json" \
     -d '{"text": "What is the capital of France?"}'
   ```

3. **Audio Query** (returns JSON with text)
   ```bash
   curl -X POST http://SERVER_IP:5000/query \
     -F "audio=@recording.wav"
   ```

4. **Audio Query** (returns spoken audio)
   ```bash
   curl -X POST http://SERVER_IP:5000/query_audio \
     -F "audio=@recording.wav" \
     -o response.wav
   ```

### Test Client

Test the server from any device on your network:

```bash
# Update SERVER_URL in test_client.py to your server's IP
python3 test_client.py
```

## For Custom Hardware Integration

### Hardware Setup

For custom Echo-like devices with microphone and speaker:

1. **Microphone** → Record audio (WAV format, 16kHz recommended)
2. **Send audio** → POST to `/query_audio` endpoint
3. **Receive audio** → Play response through speaker

### Example with Raspberry Pi

```python
import requests
import pyaudio

SERVER = "http://192.168.1.100:5000"

# Record audio
# ... your recording code ...

# Send to server
with open('recording.wav', 'rb') as f:
    response = requests.post(
        f"{SERVER}/query_audio",
        files={'audio': f}
    )

# Play response
# ... play response.content as audio ...
```

### Wake Word Detection (Optional)

For always-on devices, add wake word detection before sending to server:
- Use **Porcupine** or **Snowboy** for local wake word detection
- Only send audio to server after wake word detected

## Network Configuration

1. Find your Mac's IP address:
   ```bash
   ifconfig | grep inet
   ```

2. Ensure port 5000 is accessible on your network

3. For multiple devices, consider:
   - Static IP for the server
   - Router port forwarding (if needed)
   - Firewall rules

## Performance

- **Response Time**: 2-5 seconds typical
  - Transcription: 0.5-1s
  - LLM inference: 1-3s
  - TTS: 0.5-1s

- **Concurrent Requests**: Server handles one request at a time
  - For multiple devices, consider request queuing

## Future Enhancements

1. **Wake word detection** for always-on mode
2. **Voice cloning** for custom TTS voices
3. **Context memory** for multi-turn conversations
4. **Smart home integration** (HomeKit, Home Assistant)
5. **Multiple language support**

## Troubleshooting

- **"No module named 'pyaudio'"**: Install portaudio first: `brew install portaudio`
- **Slow responses**: Normal for 72B model, reduce to 32B for faster responses
- **Memory issues**: Ensure no other heavy applications running

## Model Selection

To use different models, edit the scripts:

**Faster responses** (less intelligent):
- Change `qwen2.5:72b` → `qwen2.5:32b` or `qwen2.5:14b`

**Better transcription** (larger size):
- Keep `whisper large`

**Faster transcription** (lower accuracy):
- Change `whisper large` → `whisper medium` or `whisper small`
