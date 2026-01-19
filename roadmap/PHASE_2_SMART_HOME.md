# Phase 2: LLM Integration & Smart Home Control

## Overview

Add natural language understanding with function-calling LLMs and full Home Assistant integration for smart home control.

**Goal:** Natural conversation with reliable device control

---

## Milestones

### M1: LLM Deployment (Week 1)

- [ ] Deploy Qwen2.5-7B-Instruct via Ollama
- [ ] Configure Q5_K_M quantization for quality
- [ ] Implement dynamic model loading (3B → 7B → 32B)
- [ ] Add conversation context window (8K tokens)
- [ ] Setup Hermes 2 Pro 8B for function calling

**Acceptance Criteria:**
- Qwen2.5-7B running at 50-60 tok/s
- Dynamic model switching based on query complexity
- Conversation memory across turns

### M2: Function Calling Implementation (Week 1-2)

- [ ] Define Home Assistant function schemas
- [ ] Implement device control functions
- [ ] Add entity resolution for fuzzy matching
- [ ] Create disambiguation dialogs
- [ ] Handle multi-function calls

**Function Schema:**
```json
{
  "name": "control_device",
  "description": "Control a smart home device",
  "parameters": {
    "device_id": {"type": "string"},
    "action": {"type": "string", "enum": ["on", "off", "toggle", "set"]},
    "value": {"type": "number"}
  }
}
```

**Acceptance Criteria:**
- Function calling accuracy >85%
- Entity resolution with >80% fuzzy match threshold
- Disambiguation prompts when needed

### M3: Home Assistant Integration (Week 2-3)

- [ ] Implement WebSocket API connection
- [ ] Add real-time state subscriptions
- [ ] Create local entity cache (5s TTL)
- [ ] Support all device domains:
  - Lights (on/off, brightness, color)
  - Climate (temperature, mode, fan)
  - Locks (lock/unlock, status)
  - Covers (open/close, position)
  - Media (play/pause, volume)
  - Sensors (query status)
- [ ] Implement graceful degradation when HA offline

**Acceptance Criteria:**
- Control 95% of common device types
- <500ms device command latency
- Works offline with cached state
- Graceful error messages

### M4: Natural Language Understanding (Week 3)

- [ ] Handle ambiguous commands with context
  - Room context from satellite location
  - Recent interaction context (last 5 min)
  - Presence detection integration
- [ ] Support relative commands ("warmer", "dimmer")
- [ ] Implement routine/scene triggers
- [ ] Add conditional commands ("if after sunset...")
- [ ] Support scheduled commands ("in 30 minutes...")

**Command Examples:**
- "Turn on the lights" → Uses satellite room context
- "Make it warmer" → +2°F from current setpoint
- "I'm going to bed" → Triggers bedtime routine
- "Is the house secure?" → Checks locks, garage, alarm

**Acceptance Criteria:**
- Ambiguous commands resolved via context
- Relative commands work naturally
- Routines trigger reliably

### M5: Conversation Memory & Polish (Week 4)

- [ ] Implement ConversationSummaryBuffer pattern
- [ ] Summarize every 10-15 exchanges
- [ ] Add per-user conversation history
- [ ] Create helpful error messages
- [ ] Add latency-hiding techniques:
  - Acknowledgment sounds
  - Filler phrases for long processing
  - Parallel processing pipeline

**Error Message Examples:**
- "I couldn't find 'living room lamp'. Did you mean 'living room light'?"
- "The thermostat isn't responding. Last reading was 72°F."
- "The front door is already locked. Everything is secure."

**Acceptance Criteria:**
- Conversation context maintained across turns
- Helpful, natural error messages
- Latency hidden with acknowledgments

---

## Technical Requirements

### LLM Configuration

| Model | Use Case | Quantization | Speed |
|-------|----------|--------------|-------|
| Llama 3.2 3B | Fast commands | Q4_K_M | 80-100 tok/s |
| Qwen2.5-7B | Conversation | Q5_K_M | 50-60 tok/s |
| Hermes 2 Pro 8B | Function calling | Q5_K_M | 45-55 tok/s |
| Qwen2.5-32B | Complex reasoning | Q4_K_M | 15-20 tok/s |

### Home Assistant Setup

```python
# WebSocket connection
uri = "ws://homeassistant.local:8123/api/websocket"

# Entity caching
cache_ttl = 5  # seconds
subscribe_events = ["state_changed"]
```

### Function Calling Reliability

| Model Size | Accuracy | Use For |
|------------|----------|---------|
| 3B | 70-80% | Simple commands only |
| 7B | 85-90% | Simple-moderate |
| 8B (Hermes) | 90% | All function calls |
| 13B+ | 95%+ | Complex orchestration |

---

## Supported Device Types

| Category | Domain | Commands |
|----------|--------|----------|
| Lighting | light.* | on, off, brightness, color, temperature |
| Climate | climate.* | temperature, mode, fan, humidity |
| Locks | lock.* | lock, unlock, status |
| Covers | cover.* | open, close, stop, position |
| Media | media_player.* | play, pause, stop, volume, source |
| Switches | switch.* | on, off, toggle |
| Sensors | sensor.* | query value |
| Binary | binary_sensor.* | query state |

---

## Definition of Done

- [ ] All milestones complete
- [ ] Qwen2.5-7B at 50+ tok/s with Q5_K_M
- [ ] Function calling accuracy >85%
- [ ] Control 95% of device types
- [ ] <500ms command latency
- [ ] Conversation memory working
- [ ] Graceful offline operation
- [ ] 80%+ test coverage
- [ ] Documentation updated
