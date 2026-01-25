# Jarvis Voice Assistant - Feature Roadmap

## Vision

Transform Jarvis from a proof-of-concept voice assistant into a production-ready, fully local, privacy-respecting smart home AI assistant that rivals commercial alternatives while keeping all data on-device.

---

## Phase 1: Core Voice Pipeline (v2.0)

**Goal:** Reliable, low-latency voice interaction loop

### 1.1 Wake Word Detection
- [ ] Sub-100ms wake word detection latency
- [ ] Multiple wake word support ("Jarvis", "Hey Jarvis", "Computer")
- [ ] Configurable sensitivity levels
- [ ] Wake word training for custom phrases
- [ ] False positive rate < 1%

### 1.2 Speech-to-Text (STT)
- [ ] faster-whisper integration (3-4x speedup)
- [ ] Streaming transcription (show words as spoken)
- [ ] Voice Activity Detection (VAD) for automatic recording end
- [ ] Multi-language support
- [ ] Speaker diarization (identify who's speaking)
- [ ] Noise cancellation preprocessing

### 1.3 LLM Integration
- [ ] Smart router fully operational (7b/32b/72b routing)
- [ ] Conversation memory (context window management)
- [ ] System prompt customization
- [ ] Function calling support for tool use
- [ ] Streaming responses (speak while generating)
- [ ] Token budget management

### 1.4 Text-to-Speech (TTS)
- [ ] Piper TTS integration (natural voices)
- [ ] Multiple voice personas
- [ ] Emotion/prosody control
- [ ] SSML support for fine control
- [ ] Interruptible playback
- [ ] Audio ducking during listening

### 1.5 Latency Targets

| Component | Current | Target |
|-----------|---------|--------|
| Wake word | 500-1000ms | <100ms |
| STT | 2-5s | 0.5-1.5s |
| LLM (simple) | 3-8s | 0.5-1s |
| LLM (complex) | 5-8s | 3-5s |
| TTS | 1-3s | 0.5-1s |
| **Total (simple)** | ~15s | ~3s |
| **Total (complex)** | ~20s | ~8s |

---

## Phase 2: Home Automation (v2.5)

**Goal:** Comprehensive smart home control rivaling commercial assistants

### 2.1 Home Assistant Integration
- [ ] Full entity discovery and caching
- [ ] Natural language device control
  - "Turn on the living room lights"
  - "Set the thermostat to 72"
  - "Lock the front door"
  - "Is the garage door open?"
- [ ] Scene and automation triggers
- [ ] Device state queries
- [ ] Area/room-based control
- [ ] Entity grouping support

### 2.2 Supported Device Types

| Category | Examples | Commands |
|----------|----------|----------|
| Lighting | Hue, LIFX, Wiz | On/off, brightness, color, scenes |
| Climate | Nest, Ecobee | Temperature, mode, fan, schedule |
| Security | Ring, Wyze, locks | Arm/disarm, lock/unlock, status |
| Media | TVs, speakers | Play, pause, volume, input |
| Covers | Blinds, garage | Open, close, position |
| Sensors | Motion, temp, door | Query status |
| Switches | Smart plugs | On/off, schedule |

### 2.3 Advanced Commands
- [ ] Conditional commands: "If it's after sunset, turn on the porch light"
- [ ] Scheduled commands: "Turn off all lights in 30 minutes"
- [ ] Chained commands: "I'm leaving" (triggers away mode)
- [ ] Query commands: "What's the temperature in the bedroom?"
- [ ] Relative commands: "Make it warmer" / "Dim the lights a bit"

### 2.4 Entity Resolution
- [ ] Fuzzy matching for device names
- [ ] Context-aware device selection (room context)
- [ ] Alias support ("TV" -> "living_room_tv")
- [ ] Disambiguation prompts when needed

### 2.5 MQTT Integration
- [ ] Direct MQTT device control (bypass HA for speed)
- [ ] MQTT discovery for auto-configuration
- [ ] Real-time state subscriptions
- [ ] Presence detection via MQTT

---

## Phase 3: Skills System (v3.0)

**Goal:** Extensible plugin architecture for custom functionality

### 3.1 Skill Architecture

```python
# skills/weather.py
from jarvis.skills import Skill, intent

class WeatherSkill(Skill):
    """Get weather information."""

    name = "weather"
    triggers = ["weather", "forecast", "temperature outside"]

    @intent("get_weather")
    async def get_weather(self, location: str = None) -> str:
        """Get current weather for a location."""
        location = location or self.config.default_location
        data = await self.api.get_weather(location)
        return f"It's {data.temp} degrees and {data.condition} in {location}"

    @intent("get_forecast")
    async def get_forecast(self, days: int = 3) -> str:
        """Get weather forecast."""
        ...
```

### 3.2 Built-in Skills

| Skill | Description | Example Commands |
|-------|-------------|------------------|
| Timer | Set/manage timers | "Set a timer for 5 minutes" |
| Alarm | Set/manage alarms | "Wake me up at 7am" |
| Reminder | Location/time reminders | "Remind me to call mom at 3pm" |
| Weather | Current/forecast weather | "What's the weather tomorrow?" |
| News | News headlines | "What's in the news?" |
| Calendar | Google/Apple calendar | "What's on my calendar today?" |
| Music | Spotify/local control | "Play some jazz" |
| Shopping | Shopping lists | "Add milk to my shopping list" |
| Notes | Quick notes | "Take a note: buy flowers" |
| Math | Calculations | "What's 15% of 85?" |
| Convert | Unit conversions | "Convert 100 miles to kilometers" |
| Define | Dictionary/wiki | "Define serendipity" |
| Translate | Translation | "How do you say hello in Spanish?" |

### 3.3 Custom Skill Development
- [ ] Skill generator CLI: `jarvis skill create my_skill`
- [ ] Hot reload during development
- [ ] Skill marketplace/sharing
- [ ] Sandboxed execution
- [ ] Skill dependencies management
- [ ] Configuration UI for skills

### 3.4 Intent Recognition
- [ ] Local intent classification model
- [ ] Slot filling for parameters
- [ ] Fallback to LLM for complex intents
- [ ] Intent confidence scoring
- [ ] Multi-turn conversation support

### 3.5 Skill Configuration

```yaml
# skills/weather/config.yaml
weather:
  api_provider: "openweathermap"  # or "weatherapi", "accuweather"
  api_key: "${WEATHER_API_KEY}"
  default_location: "San Francisco, CA"
  units: "imperial"  # or "metric"
  cache_ttl: 300  # seconds
```

---

## Phase 4: Multi-Room/Multi-Device (v4.0)

**Goal:** Distributed voice assistants throughout the home

### 4.1 Architecture

```
                    ┌─────────────────┐
                    │   Main Server   │
                    │   (Mac/Linux)   │
                    │  - LLM (72b)    │
                    │  - Whisper      │
                    │  - Skills       │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
       ┌──────┴──────┐ ┌─────┴─────┐ ┌──────┴──────┐
       │  Satellite  │ │ Satellite │ │  Satellite  │
       │   Kitchen   │ │  Bedroom  │ │   Office    │
       │ (Pi/ESP32)  │ │ (Pi/ESP32)│ │ (Pi/ESP32)  │
       └─────────────┘ └───────────┘ └─────────────┘
```

### 4.2 Satellite Devices

**Supported Hardware:**
- Raspberry Pi 4/5 with ReSpeaker mic array
- ESP32-S3 with INMP441 microphone
- Custom hardware with any USB microphone
- Repurposed tablets/phones

**Satellite Responsibilities:**
- Wake word detection (local, low-latency)
- Audio capture and streaming
- Audio playback
- LED feedback
- Optional: Local VAD

### 4.3 Communication Protocol

```python
# Satellite -> Server
{
    "type": "audio_stream",
    "device_id": "kitchen_satellite",
    "room": "kitchen",
    "audio": "<base64 encoded audio>",
    "sample_rate": 16000,
    "channels": 1
}

# Server -> Satellite
{
    "type": "response_audio",
    "device_id": "kitchen_satellite",
    "audio": "<base64 encoded audio>",
    "metadata": {
        "response_text": "The lights are now on",
        "duration_ms": 1200
    }
}
```

### 4.4 Room Context
- [ ] Automatic room detection via device ID
- [ ] Room-aware responses: "Turn on the lights" -> "kitchen_lights"
- [ ] Follow-me mode: Continue conversation across rooms
- [ ] Room-specific settings (volume, voice, wake word sensitivity)
- [ ] Multi-room audio playback

### 4.5 Sync and Coordination
- [ ] Wake word suppression (prevent multiple devices responding)
- [ ] Audio routing (respond from nearest device)
- [ ] Shared conversation context
- [ ] Device health monitoring
- [ ] Automatic failover

### 4.6 Setup Flow
1. Flash satellite firmware
2. Satellite broadcasts on local network
3. Server discovers satellite
4. User names satellite and assigns room
5. Satellite auto-configures

---

## Competitive Analysis

### Commercial Assistants

| Feature | Alexa | Google Home | Siri | Jarvis (Target) |
|---------|-------|-------------|------|-----------------|
| Privacy | Low | Low | Medium | **High (local)** |
| Wake word | Good | Good | Good | Good |
| STT accuracy | Excellent | Excellent | Good | Good |
| Response quality | Good | Good | Good | **Excellent (local LLM)** |
| Smart home | Excellent | Excellent | Good | **Good** |
| Skills/Actions | 100k+ | 1M+ | Limited | **Extensible** |
| Customization | Limited | Limited | Very Limited | **Full** |
| Cost | $$$$ | $$$$ | Included | **One-time** |
| Offline | No | No | Partial | **Yes** |

### Open Source Alternatives

| Project | Pros | Cons | Status |
|---------|------|------|--------|
| **Mycroft** | Mature, good skills | Cloud STT, abandoned | Discontinued |
| **Rhasspy** | Fully local, flexible | Complex setup | Active |
| **Home Assistant Voice** | HA integration, Wyoming | Limited LLM | Active |
| **OpenVoiceOS** | Mycroft fork, active | Early development | Active |
| **Willow** | ESP32, low cost | Limited processing | Active |

### Jarvis Differentiators

1. **Local LLM Intelligence**
   - Run 72b parameter models locally
   - No cloud dependency
   - Unlimited, uncensored conversations

2. **Smart Routing**
   - Adaptive model selection
   - Fast for simple, powerful for complex
   - Best of both worlds

3. **Privacy First**
   - All processing on-device
   - No data sent to cloud
   - Full control over data

4. **Customizable**
   - Open source, hackable
   - Custom wake words
   - Extensible skills

5. **Quality TTS**
   - Natural-sounding voices
   - Multiple personas
   - Emotion support

---

## Success Metrics

### Phase 1 (Core Voice)
- [ ] 95% wake word accuracy
- [ ] <3s response time for simple queries
- [ ] >90% transcription accuracy
- [ ] Natural-sounding TTS

### Phase 2 (Home Automation)
- [ ] Control 95% of common device types
- [ ] <500ms device command latency
- [ ] 98% command success rate
- [ ] Works without internet

### Phase 3 (Skills)
- [ ] 10+ built-in skills
- [ ] <1 hour to create custom skill
- [ ] Skill hot reload working
- [ ] Intent accuracy >90%

### Phase 4 (Multi-Room)
- [ ] Support 10+ satellites
- [ ] <50ms wake word to listen
- [ ] <5s total response time
- [ ] 99.9% uptime

---

## Timeline

| Phase | Version | Target | Duration |
|-------|---------|--------|----------|
| Phase 1 | v2.0 | Q2 2025 | 3 months |
| Phase 2 | v2.5 | Q3 2025 | 2 months |
| Phase 3 | v3.0 | Q4 2025 | 3 months |
| Phase 4 | v4.0 | Q1 2026 | 3 months |
| **Phase 5** | **v5.0** | **Q2 2026** | **2 months** |

---

## Phase 5: Full Duplex Conversation - PersonaPlex Integration (v5.0)

**Goal:** Natural, human-like conversation with simultaneous listening/speaking

### 5.1 PersonaPlex Core Integration

NVIDIA's PersonaPlex is an open-source full duplex conversational AI that fundamentally changes voice interaction:

| Feature | Current Jarvis | With PersonaPlex |
|---------|----------------|------------------|
| Conversation Model | Turn-based | **Full duplex** (simultaneous) |
| Response Latency | 2-5 seconds | **<500ms** |
| Active Listening | None | **Back-channeling** ("uh-huh", "okay") |
| Interruption Handling | Must wait | **Natural mid-sentence** |
| Wake Word → Response | ~3-8 seconds total | **<1 second** |

### 5.2 Technical Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PERSONAPLEX MODE                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌──────────────┐        ┌──────────────────────┐         │
│   │   User       │◄──────►│     PersonaPlex      │         │
│   │   Audio      │  Full  │   (7B Moshi Model)   │         │
│   │   Stream     │ Duplex │   Port 8998          │         │
│   └──────────────┘        └──────────────────────┘         │
│                                    │                        │
│                                    │ Complex queries        │
│                                    ▼                        │
│                           ┌──────────────────────┐         │
│                           │   Ollama (Qwen 72B)  │         │
│                           │   Deep reasoning     │         │
│                           └──────────────────────┘         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 5.3 Feature Checklist

- [ ] PersonaPlex server deployment on Mac M2 Max
- [ ] Mochi server running on port 8998
- [ ] Audio stream integration (bi-directional)
- [ ] Back-channeling responses during user speech
- [ ] Natural interruption handling
- [ ] Hybrid routing: PersonaPlex for conversation, Ollama for complex reasoning
- [ ] Home Assistant command routing through PersonaPlex
- [ ] Role-play personas (customer service, assistant, etc.)
- [ ] Latency benchmarking (<500ms target)
- [ ] Fallback to traditional mode if PersonaPlex unavailable

### 5.4 Implementation Milestones

| Milestone | Description | Duration |
|-----------|-------------|----------|
| M1 | PersonaPlex server setup & testing | 1 week |
| M2 | Audio stream integration | 1 week |
| M3 | Hybrid routing (PersonaPlex + Ollama) | 1 week |
| M4 | Home Assistant integration | 1 week |
| M5 | Multi-room PersonaPlex support | 2 weeks |
| M6 | Performance optimization & testing | 1 week |

### 5.5 Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| VRAM | 24GB | 32GB+ |
| RAM | 32GB | 64GB+ |
| Storage | 50GB | 100GB |
| GPU | Apple M2 Pro | Apple M2 Max/Ultra |

**Note:** Mac M2 Max with 96GB unified memory exceeds all requirements.

### 5.6 Use Cases

**Conversational Assistant:**
```
User: "Hey Jarvis, I'm thinking about..."
PersonaPlex: "Uh-huh..." [back-channel while user continues]
User: "...maybe going to the store later"
PersonaPlex: "Sure, what do you need to pick up?"
User: "Actually wait, first can you—"
PersonaPlex: [stops immediately, listens]
User: "—turn on the kitchen lights"
PersonaPlex: "Done. Now, about that store trip?"
```

**Home Assistant Integration:**
```
User: "It's getting dark in here and also kind of warm"
PersonaPlex: "I'll dim the lights and lower the thermostat. How's 72 degrees?"
User: "Actually make it 70"
PersonaPlex: "Got it, 70 degrees. Anything else?"
```

### 5.7 Success Metrics

- [ ] Response latency <500ms for 90% of interactions
- [ ] Back-channeling sounds natural (user survey)
- [ ] Interruption detection accuracy >95%
- [ ] Hybrid routing selects correct model 90%+ of time
- [ ] User preference for PersonaPlex mode over traditional (A/B test)

---

## Research Areas

See `RESEARCH_PROMPT.md` for detailed research questions including:
- Local LLM optimization for voice
- Natural conversation flow
- Low-latency audio streaming
- Satellite hardware options

---

## Contributing

1. Pick a feature from the roadmap
2. Create a GitHub issue
3. Discuss implementation approach
4. Submit PR with tests
5. Document changes

Priority labels:
- `P0`: Critical for next release
- `P1`: Important, schedule soon
- `P2`: Nice to have
- `P3`: Future consideration
