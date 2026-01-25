# Phase 5: Full Duplex Conversation - PersonaPlex Integration

## Overview

Integrate NVIDIA's PersonaPlex to enable natural, human-like conversation with simultaneous listening and speaking capabilities.

**Goal:** Sub-500ms response latency with natural conversation flow

---

## Background: What is PersonaPlex?

PersonaPlex is NVIDIA's open-source **full duplex** conversational AI model that fundamentally changes how voice assistants work:

### Traditional Voice Assistants (Current Jarvis)
```
User speaks → [wait] → Transcription → [wait] → LLM → [wait] → TTS → Assistant speaks
                                    Total: 2-5 seconds
```

### Full Duplex (PersonaPlex)
```
User speaks ←──────────────────────────────────────────→ Assistant responds
              Simultaneous, continuous, bi-directional
                           Total: <500ms
```

### Key Capabilities

| Feature | Description |
|---------|-------------|
| **Full Duplex** | Listens and speaks at the same time |
| **Back-channeling** | Says "uh-huh", "right", "okay" while you speak |
| **Natural Interruption** | You can interrupt mid-sentence naturally |
| **Zero Latency Feel** | Responds so fast it feels like real conversation |
| **Role Play** | Can adopt personas (assistant, customer service, etc.) |

### Technical Specifications

- **Architecture:** Moshi (developed by Kyutai)
- **Parameters:** 7 billion
- **Audio Codec:** MIMI neural audio codec
- **Training Data:** 1,200 hours real conversations + 2,000 hours synthetic
- **License:** Open source (Apache 2.0)
- **Server Port:** 8998 (Mochi server)

---

## Milestones

### M1: PersonaPlex Server Setup (Week 1)

- [ ] Clone PersonaPlex repository from NVIDIA GitHub
- [ ] Install dependencies (opus audio codec, Python packages)
- [ ] Configure HuggingFace token for model download
- [ ] Deploy Mochi server on Mac M2 Max
- [ ] Verify server running on port 8998
- [ ] Test basic web interface interaction
- [ ] Benchmark GPU memory usage (~24GB expected)
- [ ] Document setup process

**Verification:**
```bash
# Server should be accessible at:
curl http://localhost:8998/health
# Web interface at:
open http://localhost:8998
```

**Acceptance Criteria:**
- Server starts without errors
- Web interface loads
- Can have basic conversation through browser

---

### M2: Audio Stream Integration (Week 2)

- [ ] Create Python client for PersonaPlex WebSocket connection
- [ ] Implement bi-directional audio streaming
- [ ] Handle audio format conversion (16kHz mono WAV)
- [ ] Implement connection management (reconnect on failure)
- [ ] Add audio buffer management for smooth playback
- [ ] Create `jarvis_personaplex.py` entry point
- [ ] Test continuous conversation loop

**New Module: `personaplex_client.py`**
```python
class PersonaPlexClient:
    """WebSocket client for PersonaPlex server."""

    def __init__(self, host: str = "localhost", port: int = 8998):
        self.ws_url = f"ws://{host}:{port}/ws"

    async def connect(self) -> None:
        """Establish WebSocket connection."""

    async def send_audio(self, audio_data: bytes) -> None:
        """Stream audio to PersonaPlex."""

    async def receive_audio(self) -> AsyncGenerator[bytes, None]:
        """Receive audio stream from PersonaPlex."""

    async def set_persona(self, system_prompt: str) -> None:
        """Configure assistant persona."""
```

**Acceptance Criteria:**
- Audio streams both directions without dropouts
- Latency <100ms for audio round-trip
- Connection recovers from network issues

---

### M3: Hybrid Routing System (Week 3)

- [ ] Design hybrid architecture (PersonaPlex + Ollama)
- [ ] Implement query complexity detection
- [ ] Route simple queries to PersonaPlex (fast)
- [ ] Route complex queries to Ollama (intelligent)
- [ ] Handle seamless handoff between systems
- [ ] Implement caching for repeated queries
- [ ] Add configuration for routing thresholds

**Routing Logic:**
```python
def route_query(query: str, context: ConversationContext) -> str:
    """Determine which backend to use."""

    # PersonaPlex for:
    # - Simple acknowledgments
    # - Short factual responses
    # - Conversational back-and-forth
    # - Home automation commands

    # Ollama for:
    # - Complex reasoning
    # - Long-form responses
    # - Code generation
    # - Analysis tasks
```

**Routing Examples:**
| Query | Route To | Reason |
|-------|----------|--------|
| "Turn on the lights" | PersonaPlex | Simple command |
| "What's the weather?" | PersonaPlex | Quick factual |
| "Explain quantum physics" | Ollama | Complex reasoning |
| "Write a Python function" | Ollama | Code generation |
| "Yeah, that sounds good" | PersonaPlex | Conversational |

**Acceptance Criteria:**
- 90%+ queries routed to correct backend
- Seamless user experience regardless of backend
- Response time appropriate for query type

---

### M4: Home Assistant Integration (Week 4)

- [ ] Connect PersonaPlex to Home Assistant entity list
- [ ] Train PersonaPlex on device control vocabulary
- [ ] Implement natural language device commands
- [ ] Add room context awareness
- [ ] Handle multi-step home automation
- [ ] Create "scenes" through conversation
- [ ] Test reliability of device control

**Conversation Flow:**
```
User: "It's getting dark"
PersonaPlex: "Want me to turn on some lights?"
User: "Yeah, in the living room"
PersonaPlex: "Done. Anything else?"
User: "Actually, dim them a bit"
PersonaPlex: "How's that?" [dims to 70%]
User: "Perfect"
PersonaPlex: "Great!"
```

**Supported Commands:**
- Lights: on/off, brightness, color
- Climate: temperature, mode, fan
- Locks: lock/unlock
- Media: play/pause/volume
- Scenes: activate predefined scenes
- Queries: "Is the garage door open?"

**Acceptance Criteria:**
- Device commands execute <1 second
- Natural language understood 95%+ of time
- Multi-turn device control works smoothly

---

### M5: Multi-Room PersonaPlex (Week 5-6)

- [ ] Extend satellite protocol for PersonaPlex audio
- [ ] Implement room-aware PersonaPlex instances
- [ ] Handle "follow me" conversation across rooms
- [ ] Prevent multiple rooms responding simultaneously
- [ ] Optimize audio streaming for network latency
- [ ] Test with multiple satellite devices

**Architecture:**
```
                    ┌─────────────────┐
                    │  PersonaPlex    │
                    │  Server (Mac)   │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
       ┌──────┴──────┐ ┌─────┴─────┐ ┌──────┴──────┐
       │  Kitchen    │ │  Bedroom  │ │   Office    │
       │  Satellite  │ │ Satellite │ │  Satellite  │
       └─────────────┘ └───────────┘ └─────────────┘
```

**Acceptance Criteria:**
- Conversation continues across rooms
- Only one room responds at a time
- Audio quality maintained over network

---

### M6: Performance Optimization (Week 7)

- [ ] Profile end-to-end latency
- [ ] Optimize audio buffer sizes
- [ ] Reduce model loading time
- [ ] Implement response caching
- [ ] A/B test PersonaPlex vs traditional mode
- [ ] Gather user feedback on conversation quality
- [ ] Document final performance metrics

**Target Metrics:**
| Metric | Target | Stretch |
|--------|--------|---------|
| Response latency | <500ms | <300ms |
| Back-channel timing | <100ms | <50ms |
| Interruption detection | <200ms | <100ms |
| Device command execution | <1s | <500ms |

**Acceptance Criteria:**
- All latency targets met
- User preference for PersonaPlex mode (survey)
- Production-ready stability

---

## Technical Requirements

### Hardware

| Component | Requirement | Our Setup |
|-----------|-------------|-----------|
| GPU VRAM | 24GB minimum | 96GB unified (M2 Max) ✓ |
| System RAM | 32GB | 96GB ✓ |
| Storage | 50GB | 1TB+ ✓ |
| Network | Gigabit | Gigabit ✓ |

### Software Dependencies

```bash
# System packages
brew install opus  # Audio codec

# Python packages
pip install websockets aiohttp numpy sounddevice

# PersonaPlex specific
git clone https://github.com/NVIDIA/PersonaPlex
cd PersonaPlex
pip install -e .

# HuggingFace for model download
export HF_TOKEN=your_token_here
```

### Configuration

```yaml
# config/personaplex.yaml
personaplex:
  server:
    host: "localhost"
    port: 8998
  audio:
    sample_rate: 16000
    channels: 1
    format: "pcm_s16le"
  persona:
    name: "Jarvis"
    system_prompt: |
      You are Jarvis, a helpful home assistant.
      You control smart home devices and answer questions.
      Be concise and friendly.
  routing:
    complexity_threshold: 0.7
    ollama_fallback: true
```

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Model accuracy lower than Ollama | Medium | Hybrid routing for complex queries |
| High GPU memory usage | Low | Mac M2 Max has 96GB - plenty |
| Network latency for satellites | Medium | Optimize audio compression |
| PersonaPlex model updates | Low | Pin to stable version |
| Integration complexity | Medium | Incremental milestones |

---

## Success Criteria

### Functional
- [ ] Natural conversation without noticeable lag
- [ ] Back-channeling feels natural
- [ ] Interruption works smoothly
- [ ] Home Assistant commands execute reliably
- [ ] Multi-room conversation functional

### Performance
- [ ] 90% of responses <500ms
- [ ] 95% device command success rate
- [ ] <1% conversation drops/errors
- [ ] Runs stable for 24+ hours

### User Experience
- [ ] Users prefer PersonaPlex mode in A/B test
- [ ] Conversation feels "natural" (>4/5 rating)
- [ ] Setup time <30 minutes for new users

---

## Definition of Done

- [ ] All milestones complete
- [ ] PersonaPlex server running 24/7
- [ ] Hybrid routing operational
- [ ] Home Assistant integration working
- [ ] Multi-room support functional
- [ ] Performance targets met
- [ ] Documentation complete
- [ ] User testing completed
