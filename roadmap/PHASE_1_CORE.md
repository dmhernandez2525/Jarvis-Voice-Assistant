# Phase 1: Core Voice Pipeline

## Overview

Build the voice interaction loop using Whisper.cpp with CoreML acceleration, Kokoro TTS, and the Wyoming protocol for satellite communication.

**Goal:** Sub-2-second latency voice command → response flow

---

## Milestones

### M1: Whisper.cpp + CoreML Integration (Week 1)

- [ ] Install Whisper.cpp with CoreML and Metal acceleration
- [ ] Download and configure large-v3 model
- [ ] Integrate Silero VAD for voice activity detection
- [ ] Implement 16kHz audio capture pipeline
- [ ] Benchmark: 10s audio → <1s processing

**Acceptance Criteria:**
- Whisper.cpp running with CoreML acceleration (8-12x faster than CPU)
- Silero VAD correctly detecting speech boundaries
- Real-time transcription display during recording

### M2: Kokoro TTS Integration (Week 1-2)

- [ ] Install Kokoro-82M TTS engine
- [ ] Configure sentence-level streaming from LLM
- [ ] Implement stream2sentence buffering
- [ ] Add speech rate and voice selection
- [ ] Integrate Piper as fallback (904 voices)

**Acceptance Criteria:**
- TTS synthesis <0.3s for typical responses
- Natural prosody with sentence-level chunking
- Multiple voice options available

### M3: Wyoming Protocol Server (Week 2)

- [ ] Implement Wyoming JSONL-over-TCP protocol
- [ ] Create audio streaming endpoints
- [ ] Add STT, TTS, and intent recognition handlers
- [ ] Support satellite device registration
- [ ] Implement mTLS for secure communication

**Acceptance Criteria:**
- Wyoming protocol server accepting connections
- Audio streaming from satellite devices works
- Secure communication via mTLS

### M4: Wake Word Integration (Week 2-3)

- [ ] Configure microWakeWord for ESP32-S3 satellites
- [ ] Setup openWakeWord as server fallback
- [ ] Train custom "Hey Jarvis" wake word
- [ ] Implement sub-10ms detection latency (on-device)
- [ ] Add false positive filtering

**Acceptance Criteria:**
- Wake word detection <10ms on satellite devices
- False positive rate <1%
- Custom wake word trained and working

### M5: End-to-End Pipeline (Week 3)

- [ ] Connect all components: Wake → STT → TTS
- [ ] Implement acknowledgment sounds ("Got it")
- [ ] Add visual feedback (LED ring on satellites)
- [ ] Measure and optimize total latency
- [ ] Create performance monitoring dashboard

**Acceptance Criteria:**
- Full voice loop working end-to-end
- Total latency <2s for simple responses
- Time-to-first-audio <500ms

---

## Technical Requirements

### M2 Max Optimization

```bash
# Whisper.cpp with CoreML + Metal
cmake -B build \
  -DWHISPER_COREML=ON \
  -DWHISPER_METAL=ON

# Download models
./models/download-ggml-model.sh large-v3
./models/download-vad-model.sh silero-v6.2.0
```

### Audio Pipeline Configuration

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Sample Rate | 16kHz | Whisper optimal input |
| Channels | 1 (mono) | Voice-optimized |
| VAD Threshold | 0.5 | Speech probability |
| Min Speech | 250ms | Minimum utterance |
| Min Silence | 600ms | Avoid cutting off users |
| Speech Pad | 400ms | Buffer before/after |

### Latency Targets

| Stage | Target | Measurement Point |
|-------|--------|-------------------|
| Wake word | <10ms | Detection to signal |
| Audio capture | <50ms | End of speech detection |
| STT processing | <1s | 10s audio → text |
| TTS synthesis | <300ms | Text → first audio |
| **Total** | **<2s** | Wake to response |

---

## Dependencies

### New Python Packages

```txt
whisper-cpp-python>=0.1.0
kokoro-tts>=1.0.0
silero-vad>=6.0.0
stream2sentence>=1.0.0
wyoming>=1.0.0
```

### System Dependencies

```bash
# macOS
brew install cmake portaudio ffmpeg

# CoreML + Metal support requires Xcode CLT
xcode-select --install
```

### Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM | 16 GB | 32+ GB |
| Storage | 10 GB | 20 GB |
| Processor | M1 | M2 Max |
| Satellites | 1 | 3-5 |

---

## Definition of Done

- [ ] All milestones complete
- [ ] Whisper.cpp with CoreML achieving 8x+ speedup
- [ ] Kokoro TTS <300ms synthesis
- [ ] Wyoming protocol server operational
- [ ] Wake word detection <10ms on satellites
- [ ] End-to-end latency <2s
- [ ] Unit tests for core components
- [ ] Performance benchmarks documented
