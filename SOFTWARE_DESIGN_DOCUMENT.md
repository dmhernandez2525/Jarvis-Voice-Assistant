# Software Design Document - Jarvis Voice Assistant

## 1. Overview

### Project Purpose and Goals

The Jarvis Voice Assistant is a fully offline, privacy-focused voice assistant designed to provide a local alternative to cloud-based assistants like Amazon Alexa or Google Assistant. The project leverages state-of-the-art open-source AI models to deliver:

- **Complete offline operation**: All processing happens locally with no data sent to external servers
- **Maximum intelligence**: Uses large language models (up to 72B parameters) for natural conversation
- **Privacy by design**: No cloud dependencies after initial model downloads
- **Extensibility**: Modular architecture supporting multiple operation modes and integrations

### Target Users

- Privacy-conscious users who want voice assistant capabilities without cloud surveillance
- Developers and hobbyists building custom smart home or voice-controlled systems
- Users with high-end hardware (Apple Silicon Macs, workstations) seeking maximum AI capability
- Home automation enthusiasts integrating voice control with Home Assistant

### Key Features

1. **Speech Recognition**: OpenAI Whisper (large model) for state-of-the-art transcription accuracy
2. **Natural Language Understanding**: Qwen 2.5:72b or alternative LLMs via Ollama
3. **Text-to-Speech**: Multiple TTS engines (pyttsx3, Coqui TTS)
4. **Wake Word Detection**: Porcupine (high accuracy) or Whisper-based (no API key required)
5. **Smart Model Routing**: Automatic query complexity analysis to optimize response speed
6. **Home Assistant Integration**: Smart home device control
7. **API Server Mode**: Remote device support for building custom hardware clients
8. **Conversation Memory**: Multi-turn conversation history tracking

---

## 2. Architecture

### High-Level Architecture Diagram

```
+------------------------------------------------------------------+
|                     JARVIS VOICE ASSISTANT                        |
+------------------------------------------------------------------+
|                                                                   |
|  +-------------------+     +-------------------+                  |
|  |  WAKE WORD        |     |  AUDIO CAPTURE    |                  |
|  |  DETECTION        |     |  (sounddevice)    |                  |
|  +-------------------+     +-------------------+                  |
|         |                           |                             |
|         v                           v                             |
|  +-------------------------------------------+                    |
|  |          SPEECH RECOGNITION               |                    |
|  |          (OpenAI Whisper)                 |                    |
|  +-------------------------------------------+                    |
|                      |                                            |
|                      v                                            |
|  +-------------------------------------------+                    |
|  |          SMART ROUTER (optional)          |                    |
|  |   Analyzes query -> selects optimal LLM   |                    |
|  +-------------------------------------------+                    |
|                      |                                            |
|                      v                                            |
|  +-------------------------------------------+                    |
|  |          LLM PROCESSING                   |                    |
|  |          (Ollama: Qwen/Dolphin)           |                    |
|  +-------------------------------------------+                    |
|                      |                                            |
|                      v                                            |
|  +-------------------------------------------+                    |
|  |          TEXT-TO-SPEECH                   |                    |
|  |          (pyttsx3 / Coqui TTS)            |                    |
|  +-------------------------------------------+                    |
|                      |                                            |
|                      v                                            |
|  +-------------------+     +-------------------+                  |
|  |  AUDIO OUTPUT     |     |  HOME ASSISTANT   |                  |
|  |  (Speaker)        |     |  INTEGRATION      |                  |
|  +-------------------+     +-------------------+                  |
|                                                                   |
+------------------------------------------------------------------+
                              |
                              v
+------------------------------------------------------------------+
|                     API SERVER MODE                               |
+------------------------------------------------------------------+
|  +-------------------+     +-------------------+                  |
|  |  /health          |     |  /query           |                  |
|  |  Health check     |     |  Audio -> JSON    |                  |
|  +-------------------+     +-------------------+                  |
|  +-------------------+     +-------------------+                  |
|  |  /query_audio     |     |  /text_query      |                  |
|  |  Audio -> Audio   |     |  Text -> JSON     |                  |
|  +-------------------+     +-------------------+                  |
+------------------------------------------------------------------+
```

### Component Descriptions

| Component | Technology | Purpose |
|-----------|------------|---------|
| Audio Capture | sounddevice, pyaudio | Record microphone input at 16kHz sample rate |
| Wake Word | Porcupine / Whisper | Detect activation phrase "Jarvis" |
| Speech Recognition | OpenAI Whisper | Convert audio to text with high accuracy |
| LLM Processing | Ollama (Qwen, Dolphin) | Generate intelligent responses |
| Text-to-Speech | pyttsx3 / Coqui TTS | Convert responses to spoken audio |
| API Server | Flask | HTTP endpoints for remote clients |
| Home Assistant | requests, paho-mqtt | Smart home device control |

### Mode Descriptions

1. **Interactive Mode** (`voice_assistant.py`)
   - Push-to-talk operation (press Enter to record)
   - 5-second recording window
   - Suitable for testing and development

2. **Wake Word Mode** (`jarvis_with_wakeword.py`, `jarvis_simple_wakeword.py`)
   - Always-listening mode with "Jarvis" wake word
   - Two variants: Porcupine (fast, requires API key) or Whisper-based (no key needed)
   - Hands-free operation

3. **Server Mode** (`voice_assistant_server.py`)
   - Flask-based HTTP API
   - Accepts audio from remote devices
   - Returns JSON or audio responses
   - Enables building custom hardware clients (e.g., Raspberry Pi)

4. **Smart Router Mode** (`jarvis_smart_router.py`)
   - Analyzes query complexity
   - Routes to optimal model (7b/32b/72b) based on task
   - Balances speed vs intelligence

5. **Home Assistant Mode** (`jarvis_homeassistant.py`)
   - Integrates with Home Assistant API
   - Controls lights, switches, thermostats, locks
   - Combines voice control with smart home automation

---

## 3. Module Design

### voice_assistant.py - Core Voice Assistant

**Purpose**: Base implementation of the voice assistant with push-to-talk interaction.

**Responsibilities**:
- Initialize Whisper, Ollama, and TTS engines
- Record audio from microphone
- Transcribe speech to text
- Generate LLM responses
- Speak responses via TTS

**Key Functions**:
| Function | Description |
|----------|-------------|
| `__init__()` | Initialize models (Whisper, Ollama, pyttsx3) |
| `listen(duration)` | Record audio for specified duration |
| `transcribe(audio)` | Convert audio to text using Whisper |
| `get_response(text)` | Get LLM response from Ollama |
| `speak(text)` | Convert text to speech and play |
| `run_interactive()` | Main loop for push-to-talk mode |

### voice_assistant_server.py - API Server

**Purpose**: Expose voice assistant capabilities via HTTP API for remote clients.

**Responsibilities**:
- Host Flask web server on port 5000
- Process audio uploads
- Return JSON or audio responses
- Handle concurrent requests

**Key Endpoints**:
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check and model status |
| `/query` | POST | Audio in, JSON out |
| `/query_audio` | POST | Audio in, audio out |
| `/text_query` | POST | Text in, JSON out |

### jarvis_with_wakeword.py - Porcupine Wake Word

**Purpose**: Always-listening assistant using Porcupine for fast wake word detection.

**Responsibilities**:
- Stream audio for continuous monitoring
- Detect "Jarvis" wake word via Porcupine
- Transition to command recording after detection
- Clean up Porcupine resources on exit

**Key Functions**:
| Function | Description |
|----------|-------------|
| `listen_for_wakeword()` | Continuous audio stream with Porcupine processing |
| `run()` | Main loop: wake word -> record -> transcribe -> respond |

### jarvis_simple_wakeword.py - Energy-Based Wake Word

**Purpose**: Wake word detection without external API dependencies.

**Responsibilities**:
- Energy-based voice activity detection
- Whisper verification of wake word
- 100% offline operation

**Key Functions**:
| Function | Description |
|----------|-------------|
| `listen_for_wakeword()` | Energy detection + Whisper verification loop |

**Tunable Parameters**:
- `wake_threshold`: Audio energy threshold (default: 0.005)
- `wake_duration`: Recording duration for wake word check (default: 1.5s)

### jarvis_smart_router.py - Intelligent Model Routing

**Purpose**: Optimize response time by routing queries to appropriate model sizes.

**Responsibilities**:
- Analyze query complexity using fast 7b model
- Route simple queries to fast model (dolphin-mistral:7b)
- Route moderate queries to balanced model (qwen2.5:32b)
- Route complex queries to powerful model (qwen2.5:72b)
- Track routing statistics

**Key Functions**:
| Function | Description |
|----------|-------------|
| `analyze_query_complexity(text)` | Classify query as SIMPLE/MODERATE/COMPLEX |
| `get_smart_response(text)` | Route to appropriate model and get response |
| `print_stats()` | Display routing statistics |

### jarvis_homeassistant.py - Smart Home Integration

**Purpose**: Control Home Assistant devices via voice commands.

**Responsibilities**:
- Parse voice commands for smart home intent
- Map commands to Home Assistant API calls
- Support lights, switches, thermostats, locks, covers
- Fall back to LLM for non-smart-home queries

**Key Functions**:
| Function | Description |
|----------|-------------|
| `control_homeassistant(command_text)` | Parse and execute smart home commands |
| `get_response(text)` | Route to HA or LLM based on command type |

### context_manager.py - Multi-Project Context System

**Purpose**: Manage conversation trees and project contexts for long-running interactions.

**Responsibilities**:
- Create and manage multiple projects
- Track conversation trees with branching
- Store conversation chunks as markdown
- Enable navigation through conversation history

**Key Classes and Functions**:
| Component | Description |
|-----------|-------------|
| `ContextManager` | Main class for project/tree management |
| `create_project()` | Initialize new project with root goal |
| `create_branch()` | Branch conversation tree |
| `create_chunk()` | Store conversation segment |
| `show_tree()` | Visualize conversation tree |
| `cli()` | Command-line interface |

### jarvis_v2.py - Enhanced Assistant with Memory

**Purpose**: Improved version with conversation history and visual feedback.

**Responsibilities**:
- Maintain conversation history (last 10 messages)
- Visual countdown during recording
- Microphone calibration
- Suppress FP16 warnings

**Key Features**:
- `conversation_history[]`: List of user/assistant messages
- `calibrate_microphone()`: Help users adjust audio levels
- Visual countdown in `listen()` method

---

## 4. Voice Processing Pipeline

### Audio Capture

```
Microphone Input
      |
      v
+------------------+
| sounddevice.rec  |
| Sample Rate: 16kHz|
| Channels: 1      |
| dtype: float32   |
+------------------+
      |
      v
NumPy Array (float32)
```

**Configuration**:
- Sample rate: 16000 Hz (optimal for Whisper)
- Channels: 1 (mono)
- Recording duration: 5-15 seconds depending on mode

### Speech Recognition (Whisper)

```
Audio Array
      |
      v
+------------------+
| Save as temp WAV |
| (scipy.io.wavfile)|
+------------------+
      |
      v
+------------------+
| whisper.transcribe|
| Model: large     |
| Language: en     |
+------------------+
      |
      v
Transcribed Text
```

**Model Options**:
| Model | Size | Accuracy | Speed |
|-------|------|----------|-------|
| tiny | 39M | Low | Fastest |
| base | 74M | Fair | Fast |
| small | 244M | Good | Moderate |
| medium | 769M | Very Good | Slower |
| large | 1550M | Best | Slowest |

### LLM Processing (Ollama)

```
Transcribed Text
      |
      v
+------------------+
| System Prompt    |
| (persona setup)  |
+------------------+
      |
      v
+------------------+
| ollama.generate  |
| Model: qwen2.5   |
| Options:         |
|  - temperature   |
|  - top_p         |
+------------------+
      |
      v
Response Text
```

**LLM Options**:
| Parameter | Default | Purpose |
|-----------|---------|---------|
| temperature | 0.8 | Creativity level (0.0-2.0) |
| top_p | 0.9 | Nucleus sampling threshold |
| stream | False | Streaming vs batch response |

### Text-to-Speech

**Option 1: pyttsx3 (Default)**
```
Response Text
      |
      v
+------------------+
| pyttsx3.say()    |
| Rate: 175 wpm    |
+------------------+
      |
      v
Speaker Output
```

**Option 2: Coqui TTS (Open Source)**
```
Response Text
      |
      v
+------------------+
| TTS.tts_to_file  |
| Model: tacotron2 |
+------------------+
      |
      v
+------------------+
| sounddevice.play |
+------------------+
      |
      v
Speaker Output
```

---

## 5. Wake Word Detection

### Porcupine Integration

**How it works**:
1. Audio stream with fixed frame length (512 samples)
2. Each frame processed by Porcupine engine
3. Returns keyword index (-1 = no detection, 0+ = keyword detected)
4. Sub-100ms detection latency

**Configuration**:
```python
porcupine = pvporcupine.create(
    access_key='YOUR_KEY',
    keywords=['jarvis']
)
frame_length = porcupine.frame_length  # 512 samples
```

**Pros**:
- Very fast detection (<100ms)
- High accuracy
- Low CPU usage

**Cons**:
- Requires free API key from Picovoice
- Binary dependency (not pure Python)

### Simple Wake Word Fallback

**How it works**:
1. Continuous short recordings (1.5s clips)
2. Energy-based voice activity detection
3. If energy > threshold, run Whisper transcription
4. Check if "jarvis" appears in transcription

**Configuration**:
```python
wake_threshold = 0.005  # Energy threshold
wake_duration = 1.5     # Seconds per clip
```

**Pros**:
- 100% offline, no API key
- Uses existing Whisper model
- Pure Python

**Cons**:
- Slower detection (1-2s latency)
- Higher CPU usage (continuous Whisper calls)
- More false positives possible

### Sensitivity Tuning

**Energy Threshold**:
- Lower value = more sensitive (may trigger on background noise)
- Higher value = less sensitive (may miss quiet commands)
- Default: 0.005
- Recommended range: 0.001 - 0.05

**Calibration** (jarvis_v2.py):
```python
def calibrate_microphone(self):
    # Record sample
    audio = sd.rec(...)
    energy = np.abs(audio).mean()

    # Adjust threshold to 70% of voice level
    self.wake_threshold = energy * 0.7
```

---

## 6. API Design

### Server Endpoints

#### GET /health

**Purpose**: Health check and status information

**Response**:
```json
{
    "status": "healthy",
    "model": "qwen2.5:72b"
}
```

#### POST /query

**Purpose**: Process audio and return text response

**Request**:
- Content-Type: multipart/form-data
- Body: `audio` field with WAV file

**Response** (200):
```json
{
    "transcription": "What is the capital of France?",
    "response": "The capital of France is Paris."
}
```

**Error Response** (400/500):
```json
{
    "error": "No audio file provided"
}
```

#### POST /query_audio

**Purpose**: Process audio and return audio response

**Request**:
- Content-Type: multipart/form-data
- Body: `audio` field with WAV file

**Response** (200):
- Content-Type: audio/wav
- Body: WAV audio file with spoken response

#### POST /text_query

**Purpose**: Process text query (useful for testing)

**Request**:
```json
{
    "text": "What is the capital of France?"
}
```

**Response** (200):
```json
{
    "response": "The capital of France is Paris."
}
```

### Client Example

```python
import requests

SERVER = "http://192.168.1.100:5000"

# Record audio and save to file
# ... recording code ...

# Send to server
with open('recording.wav', 'rb') as f:
    response = requests.post(
        f"{SERVER}/query_audio",
        files={'audio': f}
    )

# Play response audio
# response.content contains WAV data
```

---

## 7. Dependencies

### Core Python Libraries

| Library | Version | Purpose |
|---------|---------|---------|
| openai-whisper | latest | Speech recognition |
| sounddevice | latest | Audio recording/playback |
| scipy | latest | WAV file I/O |
| numpy | latest | Audio array processing |
| ollama | latest | LLM integration |
| pyttsx3 | latest | Text-to-speech (system voices) |

### Optional Libraries

| Library | Version | Purpose |
|---------|---------|---------|
| pvporcupine | latest | Wake word detection (Porcupine) |
| TTS | latest | Coqui TTS (open-source alternative) |
| flask | latest | API server |
| requests | latest | HTTP client (Home Assistant) |
| paho-mqtt | latest | MQTT client (Home Assistant) |
| pyaudio | latest | Alternative audio library |

### System Dependencies

| Dependency | Platform | Purpose |
|------------|----------|---------|
| portaudio | macOS/Linux | Audio I/O backend |
| ffmpeg | All | Audio format handling |

**Installation (macOS)**:
```bash
brew install portaudio ffmpeg
```

### Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM | 32 GB | 96+ GB (for 72b model) |
| Storage | 20 GB | 60+ GB |
| CPU/GPU | Apple M1 | Apple M2 Max or better |
| Microphone | Built-in | USB/External |

**Model Memory Requirements**:
| Model | VRAM/RAM |
|-------|----------|
| Whisper large | ~3 GB |
| qwen2.5:7b | ~8 GB |
| qwen2.5:32b | ~20 GB |
| qwen2.5:72b | ~45 GB |

---

## 8. Configuration

### Environment Variables

The project primarily uses hardcoded defaults but can be extended with:

| Variable | Default | Purpose |
|----------|---------|---------|
| HOME_ASSISTANT_URL | http://localhost:8123 | Home Assistant server |
| HOME_ASSISTANT_TOKEN | None | HA long-lived access token |
| PORCUPINE_ACCESS_KEY | None | Picovoice API key |

### Model Selection Options

**Whisper Models** (speech recognition):
```python
# In __init__:
self.whisper = whisper.load_model("large")  # Options: tiny, base, small, medium, large
```

**LLM Models** (via Ollama):
```python
# In __init__:
self.ollama_model = "qwen2.5:72b"  # Or: qwen2.5:32b, qwen2.5:14b, dolphin-mistral:7b
```

**TTS Configuration**:
```python
# pyttsx3
self.tts.setProperty('rate', 175)  # Words per minute

# Coqui TTS
self.tts = TTS("tts_models/en/ljspeech/tacotron2-DDC")
```

### Audio Configuration

```python
self.sample_rate = 16000      # Hz (optimal for Whisper)
self.wake_threshold = 0.005   # Energy detection threshold
self.wake_duration = 1.5      # Seconds for wake word check
self.command_duration = 15    # Seconds for command recording
```

---

## 9. Testing Strategy

### Test Types

1. **Unit Tests**
   - Individual function testing
   - Mock audio input/output
   - Mock Ollama responses

2. **Integration Tests**
   - End-to-end pipeline testing
   - API endpoint testing
   - Model loading verification

3. **Manual Testing**
   - Wake word detection accuracy
   - Transcription quality
   - Response relevance
   - TTS clarity

### Test Client

`test_client.py` provides manual testing utilities:

```python
# Test health endpoint
test_health()

# Test text query
test_text_query()

# Test audio query (requires microphone)
test_audio_query()
```

### Coverage Goals

| Component | Target Coverage |
|-----------|-----------------|
| Audio Pipeline | 80% |
| API Endpoints | 90% |
| Wake Word | Manual testing |
| LLM Integration | Integration tests |
| TTS | Manual testing |

### Testing Commands

```bash
# Run test client
python3 test_client.py

# Test specific mode
python3 test_client.py text   # Text query only
python3 test_client.py audio  # Audio query with mic
```

---

## 10. Future Considerations

### Planned Improvements

1. **Voice Cloning**
   - Custom TTS voices using voice samples
   - Integration with RVC or similar voice cloning models

2. **Multi-Language Support**
   - Whisper already supports 99 languages
   - Add multilingual LLM support
   - Localized TTS voices

3. **Streaming Responses**
   - Stream LLM output as it generates
   - Start TTS before full response complete
   - Reduce perceived latency

4. **Context Memory Persistence**
   - Save conversation history to disk
   - Resume sessions across restarts
   - Project-based memory isolation

5. **Voice Activity Detection**
   - Replace fixed recording duration
   - Detect end of speech automatically
   - More natural interaction flow

6. **GPU Acceleration**
   - CUDA support for Whisper
   - Metal acceleration for Apple Silicon
   - Parallel model loading

### Known Limitations

1. **Hardware Requirements**
   - 72B model requires 96+ GB RAM
   - Not suitable for low-end devices

2. **Single Request Processing**
   - Server handles one request at a time
   - No request queuing implemented

3. **Wake Word Accuracy**
   - Simple wake word has higher false positive rate
   - Porcupine requires API key

4. **TTS Quality**
   - pyttsx3 uses system voices (robotic)
   - Coqui TTS requires additional dependencies

5. **Latency**
   - 2-5 seconds typical response time
   - Dominated by LLM inference

### Architecture Extensibility

The modular design supports future additions:

- **Plugin System**: Add new capabilities (calendar, weather, etc.)
- **Custom Wake Words**: Train Porcupine with custom phrases
- **Alternative LLMs**: Swap Ollama for other providers
- **WebSocket Support**: Real-time streaming connections
- **Raspberry Pi Client**: Dedicated lightweight client hardware

---

## Appendix A: File Reference

| File | Purpose |
|------|---------|
| `voice_assistant.py` | Core push-to-talk assistant |
| `voice_assistant_server.py` | Flask API server |
| `jarvis_with_wakeword.py` | Porcupine wake word version |
| `jarvis_simple_wakeword.py` | Whisper-based wake word |
| `jarvis_full_opensource.py` | Fully open-source stack |
| `jarvis_smart_router.py` | Intelligent model routing |
| `jarvis_homeassistant.py` | Home Assistant integration |
| `jarvis_optimized.py` | Performance metrics version |
| `jarvis_uncensored.py` | Dolphin-mistral uncensored |
| `jarvis_v2.py` | Enhanced with memory |
| `context_manager.py` | Multi-project context system |
| `init_jarvis_context.py` | Context initialization |
| `test_client.py` | API testing utilities |
| `requirements.txt` | Python dependencies |

## Appendix B: Quick Start Commands

```bash
# Install dependencies
brew install portaudio ffmpeg
pip3 install -r requirements.txt

# Run simple wake word mode (no API key needed)
python3 jarvis_simple_wakeword.py

# Run with Porcupine wake word (faster)
python3 jarvis_with_wakeword.py

# Run as API server
python3 voice_assistant_server.py

# Run smart router mode
python3 jarvis_smart_router.py
```
