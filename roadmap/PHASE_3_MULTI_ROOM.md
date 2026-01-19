# Phase 3: Multi-Room & Satellite Network

## Overview

Deploy Jarvis across multiple rooms with ESP32-S3 and Raspberry Pi satellites, enabling whole-home voice control with room-aware context.

**Goal:** Multi-room voice assistant with satellite devices

---

## Milestones

### M1: Wyoming Protocol Server (Week 1)

- [ ] Full Wyoming protocol implementation
- [ ] Audio streaming endpoints
- [ ] Satellite registration/discovery
- [ ] mTLS certificate management
- [ ] Connection health monitoring
- [ ] Automatic reconnection
- [ ] Protocol versioning

**Wyoming Protocol:**
```
Server (Mac M2 Max)
    ↓ TCP + mTLS
Satellite Registration → Audio Stream → STT/TTS → Response
```

**Acceptance Criteria:**
- Satellites connect reliably
- Audio streams without drops
- Reconnection automatic

### M2: ESP32-S3-BOX-3 Satellite (Week 1-2)

- [ ] ESPHome firmware configuration
- [ ] microWakeWord integration
- [ ] Audio capture (I2S microphone)
- [ ] Audio playback (I2S speaker)
- [ ] LED feedback ring
- [ ] Display status screen
- [ ] Touch button support
- [ ] Wi-Fi configuration portal

**ESP32-S3-BOX-3 Features:**
| Feature | Implementation |
|---------|----------------|
| Wake word | microWakeWord (on-device) |
| Mic | Dual MEMS microphones |
| Speaker | 1W mono speaker |
| Display | 2.4" LCD for status |
| LEDs | RGB ring for feedback |

**Acceptance Criteria:**
- Wake word detected on-device
- Audio quality acceptable
- <10ms wake word latency

### M3: Raspberry Pi Satellite (Week 2)

- [ ] Wyoming satellite client
- [ ] ReSpeaker 4-Mic Array support
- [ ] openWakeWord integration
- [ ] Audio capture pipeline
- [ ] Speaker output
- [ ] LED feedback (via GPIO)
- [ ] One-liner install script
- [ ] Systemd service

**Hardware Options:**
| Component | Options |
|-----------|---------|
| Pi | Raspberry Pi 4/5, Pi Zero 2 W |
| Mic | ReSpeaker 2-Mic, 4-Mic Array |
| Speaker | Any 3.5mm or USB |

**Acceptance Criteria:**
- One-command installation
- Service starts on boot
- LED indicates state

### M4: Room-Aware Context (Week 2-3)

- [ ] Satellite location configuration
- [ ] Room-based device targeting
- [ ] Presence detection integration
- [ ] Context inheritance rules:
  - "Turn on the lights" → room's lights
  - "Turn on all lights" → whole home
- [ ] Recent interaction memory per room
- [ ] Follow-me audio routing

**Context Rules:**
```
Query from Living Room satellite:
  "Turn on the lights" → light.living_room
  "Turn on the kitchen lights" → light.kitchen
  "What's the temperature?" → sensor.living_room_temp
```

**Acceptance Criteria:**
- Room context applied correctly
- Ambiguous commands resolved
- Follow-me works

### M5: Audio Routing & Ducking (Week 3)

- [ ] Response routing to origin satellite
- [ ] Audio ducking during listening
- [ ] Volume normalization
- [ ] Multi-room announcements
- [ ] Intercom functionality
- [ ] Music handoff between rooms
- [ ] Priority audio handling

**Audio Features:**
| Feature | Description |
|---------|-------------|
| Ducking | Lower media during wake |
| Announcements | Broadcast to all rooms |
| Intercom | Room-to-room communication |
| Handoff | Move music between rooms |

**Acceptance Criteria:**
- Audio plays in correct room
- Ducking smooth
- Announcements reach all satellites

### M6: Satellite Management UI (Week 3-4)

- [ ] Web dashboard for satellites
- [ ] Registration approval workflow
- [ ] Health monitoring
- [ ] Firmware update mechanism
- [ ] Configuration management
- [ ] Audio level testing
- [ ] Wake word sensitivity adjustment
- [ ] Room assignment UI

**Dashboard Features:**
| View | Information |
|------|-------------|
| Overview | All satellites, status |
| Detail | Health, logs, settings |
| Audio | Test mic/speaker |
| Config | Room, sensitivity, wake word |

**Acceptance Criteria:**
- All satellites visible
- Health status accurate
- Configuration changes apply

### M7: Offline Resilience (Week 4)

- [ ] Local-only mode for satellites
- [ ] Cached device states
- [ ] Offline command queue
- [ ] Graceful degradation
- [ ] Sync on reconnection
- [ ] Status indicators for offline

**Acceptance Criteria:**
- Basic commands work offline
- Reconnection syncs state
- Users informed of limitations

---

## Technical Requirements

### Satellite Hardware

| Device | Cost | Pros | Cons |
|--------|------|------|------|
| ESP32-S3-BOX-3 | $45 | Integrated, low power | Limited processing |
| Pi 4 + ReSpeaker | $80 | Powerful, flexible | Higher power draw |
| Pi Zero 2 W | $35 | Compact, cheap | Slower processing |

### Network Requirements

| Requirement | Value |
|-------------|-------|
| Protocol | TCP + mTLS |
| Port | 10300 (Wyoming) |
| Bandwidth | ~128 kbps per satellite |
| Latency | <50ms LAN |

### Performance Targets

| Metric | Target |
|--------|--------|
| Wake-to-response | <2s |
| Audio stream start | <100ms |
| Reconnection | <5s |
| Satellite boot | <30s |

---

## Satellite Deployment Guide

```bash
# ESP32-S3-BOX-3
1. Flash ESPHome firmware
2. Connect to Wi-Fi via captive portal
3. Register with Jarvis server
4. Assign to room

# Raspberry Pi
curl -sSL https://jarvis.local/install-satellite.sh | bash
# Follow prompts for room assignment
```

---

## Definition of Done

- [ ] All milestones complete
- [ ] Wyoming server operational
- [ ] ESP32-S3-BOX-3 satellites working
- [ ] Raspberry Pi satellites working
- [ ] Room context applied correctly
- [ ] Audio routing functional
- [ ] Management UI complete
- [ ] Offline mode working
- [ ] 3+ room deployment tested
- [ ] Documentation complete
