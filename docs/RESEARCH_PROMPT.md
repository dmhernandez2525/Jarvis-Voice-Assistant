# Jarvis Voice Assistant - Research Prompt

## Purpose

This document provides a structured prompt for a research agent to investigate best practices, competitor analysis, and emerging technologies for building a production-quality local voice assistant.

---

## Research Agent Instructions

You are a research agent tasked with gathering comprehensive information to guide the development of Jarvis, a fully local voice assistant. Your research should be actionable, with specific recommendations backed by evidence.

For each topic, provide:
1. **Current State**: What exists today
2. **Best Practices**: What the experts recommend
3. **Specific Tools/Libraries**: Exact names, versions, links
4. **Trade-offs**: Pros and cons of each approach
5. **Recommendation**: Your suggested path forward

---

## Research Area 1: Open-Source Voice Assistants

### Questions to Answer

**1.1 Mycroft Analysis**
- What led to Mycroft's discontinuation?
- What architectural decisions worked well?
- What were the main pain points users reported?
- What happened to the Mycroft community after shutdown?
- Are there any forks worth watching (OVOS, Neon)?

**1.2 Rhasspy Deep Dive**
- How does Rhasspy's architecture compare to a monolithic assistant?
- What is the Wyoming protocol and how does it work?
- How do users rate Rhasspy's accuracy and latency?
- What hardware configurations are most successful?
- How does Rhasspy handle intent recognition locally?

**1.3 Home Assistant Voice**
- What is the current state of Home Assistant's voice initiative?
- How does the Wyoming protocol enable voice satellites?
- What STT/TTS engines does HA Voice support?
- How is the community responding to HA Voice?
- What are the limitations of HA Voice compared to Alexa/Google?

**1.4 Willow and ESP32 Assistants**
- How viable is ESP32-S3 for wake word + streaming?
- What is Willow's architecture?
- What are the latency characteristics?
- How does audio quality compare to Pi-based solutions?
- What is the total cost for a Willow satellite?

**1.5 Comparative Matrix**
Create a detailed comparison of:
- Mycroft Mark II
- Rhasspy 2.5
- Home Assistant Voice (Wyoming)
- OpenVoiceOS
- Willow
- Jarvis (current state)

Compare on: Setup complexity, STT accuracy, Response latency, Smart home integration, Customizability, Hardware requirements, Active development

---

## Research Area 2: Local LLM Options for Voice

### Questions to Answer

**2.1 Model Selection for Voice Use Cases**
- What model sizes are optimal for voice assistant tasks?
- How do smaller models (7B) compare to larger ones for:
  - Simple factual questions
  - Smart home commands
  - Conversational responses
  - Multi-turn dialogue
- What is the minimum model size that feels "intelligent" to users?

**2.2 Response Latency Optimization**
- What techniques reduce LLM inference time?
  - Quantization (GGUF, GPTQ, AWQ)
  - Speculative decoding
  - Continuous batching
  - KV cache optimization
- What are the latency characteristics of:
  - llama.cpp on Apple Silicon
  - Ollama vs vLLM vs TGI
  - CPU-only inference

**2.3 Conversation Memory**
- How should context windows be managed for voice?
- What is the optimal context length for conversational memory?
- How can we summarize long conversations to fit context limits?
- Should we use RAG for long-term memory?

**2.4 Function Calling for Device Control**
- Which open models support function/tool calling?
- How reliable is function calling in small models?
- What's the best format for defining smart home functions?
- How do we handle function calling errors gracefully?

**2.5 Streaming for Voice**
- How can we stream LLM output to TTS?
- What chunk size is optimal for natural speech?
- How do we handle sentence boundaries in streaming?
- Can we start speaking before generation completes?

**2.6 Model Recommendations**
For a Mac M2 Max with 96GB RAM, recommend:
- Best model for simple commands (fastest)
- Best model for general conversation
- Best model for complex reasoning
- Best uncensored model
- Best function calling model

---

## Research Area 3: Smart Home Integrations

### Questions to Answer

**3.1 Must-Have Integrations**
Based on smart home market data, what are the:
- Top 10 most-owned smart device categories
- Top 5 smart home ecosystems by install base
- Most common voice commands by category
- Devices users most want voice control for

**3.2 Home Assistant Best Practices**
- What is the most reliable way to integrate with HA?
- REST API vs WebSocket vs MQTT - when to use each?
- How to handle HA authentication securely?
- How to cache entity states for faster responses?
- How to handle HA being temporarily unavailable?

**3.3 Direct Device Control**
- When should we bypass HA for direct control?
- What protocols are most reliable? (Z-Wave, Zigbee, WiFi, Thread)
- How to handle devices not in HA?
- Local vs cloud control trade-offs

**3.4 Natural Language Understanding for Smart Home**
Research how commercial assistants parse commands like:
- "Turn on the lights" (which lights?)
- "Make it warmer" (by how much?)
- "I'm going to bed" (what routine?)
- "Is the house secure?" (what to check?)

**3.5 Error Handling**
- How do commercial assistants handle unknown devices?
- What's the best UX for disambiguation?
- How to gracefully handle offline devices?
- How to provide helpful error messages?

---

## Research Area 4: Natural and Responsive Conversation

### Questions to Answer

**4.1 What Makes Voice Assistants Feel Natural?**
Research user experience studies on:
- Optimal response latency (what feels instant?)
- Conversation pacing
- Acknowledgment sounds ("Mm-hmm", "OK")
- Handling interruptions
- Personality consistency

**4.2 Commercial Assistant UX Patterns**
Analyze how Alexa/Google/Siri handle:
- Ambiguous commands
- Multi-turn conversations
- Corrections ("No, I meant...")
- Proactive suggestions
- Humor and personality

**4.3 Voice Design Principles**
- What voice characteristics feel trustworthy?
- How does prosody affect perceived intelligence?
- When should the assistant be verbose vs terse?
- How to handle sensitive or error situations?

**4.4 Conversation State Management**
- How long should context persist?
- How to handle topic changes?
- When to ask for clarification vs make assumptions?
- How to gracefully end conversations?

**4.5 Latency Hiding Techniques**
Research techniques to make the assistant feel faster:
- Anticipatory responses
- Filler phrases ("Let me check...")
- Background processing
- Predictive caching
- Parallel processing

---

## Research Area 5: Audio and Hardware

### Questions to Answer

**5.1 Microphone Array Options**
Compare:
- ReSpeaker 2-Mic HAT
- ReSpeaker 4-Mic Array
- Matrix Voice
- USB conference microphones
- Custom I2S solutions

Evaluate on: Beamforming, AEC, Far-field pickup, Cost, Availability

**5.2 Audio Processing Pipeline**
- What noise reduction works best for voice?
- How effective is acoustic echo cancellation (AEC)?
- What sample rate is optimal? (16kHz vs 48kHz)
- How to handle multi-speaker environments?

**5.3 Wake Word Engine Comparison**
Compare:
- Porcupine (Picovoice)
- OpenWakeWord
- Snowboy (archived)
- Mycroft Precise
- Whisper-based detection

Evaluate on: Accuracy, Latency, False positive rate, Customization, Licensing

**5.4 Satellite Hardware Options**
For multi-room deployment, compare:
- Raspberry Pi 4/5
- Raspberry Pi Zero 2 W
- ESP32-S3 (Willow)
- Orange Pi / Rock Pi
- Old Android phones

Evaluate on: Cost, Power consumption, Audio quality, Ease of setup

**5.5 Speaker Selection**
- What speaker size/quality is good enough?
- How important is speaker placement?
- Multi-room audio synchronization options?

---

## Research Area 6: Speech Technologies

### Questions to Answer

**6.1 STT Engine Comparison**
Compare in detail:
- OpenAI Whisper (openai-whisper)
- faster-whisper (CTranslate2)
- Whisper.cpp
- Vosk
- Coqui STT
- Nemo ASR

Evaluate on: Accuracy, Latency, Memory usage, GPU vs CPU, Languages

**6.2 TTS Engine Comparison**
Compare:
- Piper
- Coqui TTS
- VITS
- Bark
- OpenVoice
- Edge TTS (cloud)

Evaluate on: Quality, Latency, Voice options, Customization, Resource usage

**6.3 Voice Activity Detection**
- What VAD works best with Whisper?
- How to detect end of speech accurately?
- Silero VAD vs WebRTC VAD vs Whisper's built-in?
- Optimal settings for conversational speech?

**6.4 Speaker Recognition**
- How viable is local speaker recognition?
- What models/libraries are available?
- How much training data is needed?
- Privacy implications?

---

## Research Area 7: Privacy and Security

### Questions to Answer

**7.1 Local-First Architecture**
- How to ensure no data leaves the device?
- How to handle skills that require internet?
- What metadata might leak to networks?

**7.2 Secure Communication**
- How to secure satellite-to-server communication?
- Certificate management for home network?
- What about mDNS/Bonjour discovery security?

**7.3 Voice Data Handling**
- How long to retain audio recordings?
- How to handle deletion requests?
- Wake word audio storage policy?

---

## Output Format

For each research area, provide a structured report:

```markdown
## [Research Area Name]

### Summary
[2-3 sentence executive summary]

### Key Findings
1. [Finding 1 with evidence]
2. [Finding 2 with evidence]
3. [Finding 3 with evidence]

### Recommendations
- **Immediate**: [Action to take now]
- **Short-term**: [Action for next 3 months]
- **Long-term**: [Action for 6+ months]

### Resources
- [Link 1]: Description
- [Link 2]: Description

### Open Questions
- [Question that needs more research]
```

---

## Priority Order

Research in this order for maximum impact:

1. **Local LLM Options** (most critical for differentiation)
2. **Natural Conversation UX** (most impactful for user experience)
3. **Speech Technologies** (foundation for everything)
4. **Smart Home Integrations** (key use case)
5. **Open-Source Assistants** (learn from others)
6. **Audio Hardware** (for multi-room expansion)
7. **Privacy and Security** (for production readiness)

---

## Deliverables

After completing research, produce:

1. **Executive Summary** (1 page)
   - Top 5 findings
   - Recommended architecture
   - Estimated effort for each phase

2. **Technology Selection Matrix** (spreadsheet)
   - All tools/libraries evaluated
   - Scores on key criteria
   - Final recommendations

3. **Architecture Diagram**
   - Recommended system architecture
   - Data flow
   - Component interactions

4. **Implementation Guide** (per component)
   - Specific library versions
   - Configuration recommendations
   - Common pitfalls to avoid

5. **Competitive Landscape** (presentation)
   - Feature comparison matrix
   - Jarvis positioning
   - Opportunity areas

---

## Notes for Research Agent

- Prioritize recent information (2024-2025)
- Focus on actively maintained projects
- Include specific version numbers
- Note licensing concerns
- Consider Apple Silicon compatibility
- Test claims where possible
- Include community sentiment (Reddit, Discord, forums)
- Document your sources
