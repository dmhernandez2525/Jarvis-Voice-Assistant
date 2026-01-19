# Jarvis Voice Assistant - Upgrade Plan

## Overview

This document outlines a comprehensive modernization plan for the Jarvis Voice Assistant project. Each upgrade is designed to be implemented as a separate PR, allowing for incremental improvements while maintaining stability.

---

## Current Tech Stack Analysis

### Dependencies (from requirements.txt)

| Component | Current | Issue |
|-----------|---------|-------|
| Python | 3.x (unspecified) | Should target 3.11/3.12 LTS |
| Speech Recognition | openai-whisper | Good, but slow |
| LLM Integration | ollama | Good choice for local models |
| Audio Processing | pyaudio, sounddevice, scipy, numpy | Functional but synchronous |
| Wake Word | pvporcupine | Proprietary, requires license |
| Web Server | flask | Synchronous, limited typing |
| TTS | pyttsx3 | Low quality, limited voices |
| HTTP Client | requests, paho-mqtt | Blocking operations |

### Code Analysis

- **Synchronous architecture**: All operations block the main thread
- **No type hints**: Limited IDE support and runtime validation
- **No linting/formatting**: Inconsistent code style
- **Duplicated code**: Multiple jarvis_*.py files with similar implementations
- **No tests**: No automated testing infrastructure
- **Global state**: Flask server uses global model instances

---

## Upgrade Phases

### Phase 1: Python Environment Modernization

**PR #1: Python 3.11/3.12 LTS Target**

```bash
# pyproject.toml (new file)
[project]
name = "jarvis-voice-assistant"
version = "2.0.0"
requires-python = ">=3.11"
```

**Changes:**
1. Create `pyproject.toml` with modern Python packaging
2. Add Python version constraint (>=3.11)
3. Update `setup_python311.sh` for 3.12 support
4. Document Python installation requirements
5. Add `.python-version` file for pyenv compatibility

**Benefits:**
- 10-60% performance improvement (Python 3.11 speedups)
- Better error messages with fine-grained tracebacks
- Native support for `tomllib` (no external TOML parser needed)
- Improved typing with `Self` type and `TypedDict` improvements

---

### Phase 2: Code Quality Infrastructure

**PR #2: Add Ruff for Linting and Formatting**

```toml
# pyproject.toml additions
[tool.ruff]
line-length = 100
target-version = "py311"
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # Pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "UP",  # pyupgrade
    "ARG", # flake8-unused-arguments
    "SIM", # flake8-simplify
]
ignore = ["E501"]  # Line too long (handled by formatter)

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

**Changes:**
1. Add ruff configuration to `pyproject.toml`
2. Add pre-commit hooks for automated linting
3. Run initial `ruff --fix` on all Python files
4. Add `ruff format` for consistent formatting
5. Add CI workflow for linting checks

**Benefits:**
- 10-100x faster than flake8 + black combined
- Single tool for linting AND formatting
- Automatic code fixes for common issues
- Consistent code style across all files

---

**PR #3: Add MyPy for Type Checking**

```toml
# pyproject.toml additions
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_ignores = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
strict_optional = true
plugins = ["pydantic.mypy"]

[[tool.mypy.overrides]]
module = ["whisper.*", "ollama.*", "pvporcupine.*", "TTS.*"]
ignore_missing_imports = true
```

**Changes:**
1. Add type hints to all function signatures
2. Create `py.typed` marker file
3. Add mypy configuration
4. Create type stubs for untyped dependencies
5. Add CI workflow for type checking

**Example transformation:**
```python
# Before
def transcribe(self, audio):
    result = self.whisper.transcribe(temp_path)
    text = result["text"].strip()
    return text

# After
def transcribe(self, audio: np.ndarray) -> str:
    result: dict[str, Any] = self.whisper.transcribe(temp_path)
    text: str = result["text"].strip()
    return text
```

**Benefits:**
- Catch type errors before runtime
- Better IDE autocomplete and refactoring
- Self-documenting code
- Easier maintenance and onboarding

---

### Phase 3: Speech Recognition Upgrade

**PR #4: Replace openai-whisper with faster-whisper**

```python
# Before
import whisper
self.whisper = whisper.load_model("large")
result = self.whisper.transcribe(temp_path)

# After
from faster_whisper import WhisperModel
self.whisper = WhisperModel("large-v3", device="auto", compute_type="auto")
segments, info = self.whisper.transcribe(temp_path, beam_size=5)
text = " ".join([segment.text for segment in segments])
```

**Performance Comparison:**

| Model | openai-whisper | faster-whisper | Speedup |
|-------|----------------|----------------|---------|
| large | 2-5s | 0.5-1.5s | 3-4x |
| medium | 1-3s | 0.3-1s | 3-4x |
| small | 0.5-1.5s | 0.2-0.5s | 2-3x |

**Changes:**
1. Replace `openai-whisper` with `faster-whisper` in requirements
2. Update all transcription calls
3. Add CTranslate2 backend configuration
4. Support VAD (Voice Activity Detection) for better accuracy
5. Add streaming transcription support

**Benefits:**
- 3-4x faster transcription (CTranslate2 optimization)
- Lower memory usage
- Better GPU utilization
- Built-in VAD for automatic silence detection

---

### Phase 4: Web Framework Modernization

**PR #5: Replace Flask with FastAPI**

```python
# Before (Flask)
from flask import Flask, request, jsonify
app = Flask(__name__)

@app.route('/query', methods=['POST'])
def query():
    audio_file = request.files['audio']
    # ... synchronous processing
    return jsonify({"response": answer})

# After (FastAPI)
from fastapi import FastAPI, UploadFile, File
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load models on startup
    app.state.whisper = await load_whisper_model()
    yield
    # Cleanup on shutdown

app = FastAPI(lifespan=lifespan)

@app.post("/query")
async def query(audio: UploadFile = File(...)) -> QueryResponse:
    # ... async processing
    return QueryResponse(transcription=text, response=answer)
```

**Changes:**
1. Replace Flask with FastAPI
2. Add Pydantic models for request/response validation
3. Implement async endpoints
4. Add OpenAPI documentation (automatic)
5. Add WebSocket support for streaming responses
6. Implement proper dependency injection

**New Endpoints:**
```python
@app.post("/query", response_model=QueryResponse)
async def query(audio: UploadFile = File(...)) -> QueryResponse: ...

@app.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket): ...

@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse: ...
```

**Benefits:**
- Automatic OpenAPI/Swagger documentation
- Built-in request validation with Pydantic
- Native async/await support
- Better performance under load
- Type-safe API contracts
- WebSocket support for real-time streaming

---

### Phase 5: Async Architecture

**PR #6: Add Proper async/await Patterns**

```python
# Before
def run_interactive(self):
    while True:
        audio = self.listen(duration=5)  # Blocks
        text = self.transcribe(audio)     # Blocks
        response = self.get_response(text) # Blocks
        self.speak(response)               # Blocks

# After
async def run_interactive(self):
    while True:
        audio = await self.listen_async(duration=5)

        # Parallel processing where possible
        transcription_task = asyncio.create_task(
            self.transcribe_async(audio)
        )

        text = await transcription_task
        response = await self.get_response_async(text)

        # Fire-and-forget TTS while listening for next command
        asyncio.create_task(self.speak_async(response))
```

**Architecture Changes:**
1. Convert all I/O operations to async
2. Use `asyncio.Queue` for audio processing pipeline
3. Implement concurrent wake word detection + command processing
4. Add proper cancellation handling
5. Use `anyio` for framework-agnostic async code

**New Dependencies:**
```toml
dependencies = [
    "anyio>=4.0",
    "httpx>=0.25",  # Async HTTP client (replaces requests)
    "aiomqtt>=1.0", # Async MQTT (replaces paho-mqtt)
]
```

**Benefits:**
- Non-blocking I/O throughout
- Better resource utilization
- Can process multiple requests concurrently
- Lower latency for wake word detection
- Can start TTS while preparing next listen

---

### Phase 6: Text-to-Speech Upgrade

**PR #7: Consider Piper TTS as pyttsx3 Alternative**

```python
# Before (pyttsx3)
import pyttsx3
self.tts = pyttsx3.init()
self.tts.say(text)
self.tts.runAndWait()

# After (Piper)
from piper import PiperVoice

class PiperTTS:
    def __init__(self, model_path: str = "en_US-amy-medium.onnx"):
        self.voice = PiperVoice.load(model_path)

    async def speak(self, text: str) -> None:
        audio = self.voice.synthesize(text)
        await self.play_audio(audio)
```

**Voice Quality Comparison:**

| Engine | Quality | Speed | Naturalness | Offline |
|--------|---------|-------|-------------|---------|
| pyttsx3 | Low | Fast | Robotic | Yes |
| Coqui TTS | High | Medium | Natural | Yes |
| Piper | High | Fast | Natural | Yes |
| Edge TTS | Very High | Medium | Very Natural | No (cloud) |

**Recommended: Piper TTS**

**Benefits:**
- Much higher quality than pyttsx3
- Fast inference (real-time on CPU)
- Multiple voice options
- Fully offline
- Low memory footprint (~50MB per model)
- ONNX runtime for cross-platform support

**Alternative: Keep Coqui TTS for Maximum Quality**
- Already implemented in `jarvis_full_opensource.py`
- Better for longer responses
- More voice customization options

---

### Phase 7: Wake Word Detection

**PR #8: Replace pvporcupine with Open-Source Alternative**

Current pvporcupine requires a license for commercial use. Consider:

**Option A: OpenWakeWord**
```python
from openwakeword import Model

model = Model(
    wakeword_models=["hey_jarvis"],
    inference_framework="onnx"
)

prediction = model.predict(audio_frame)
if prediction["hey_jarvis"] > 0.5:
    # Wake word detected
```

**Option B: Whisper-based Detection (Current)**
- Already implemented in optimized version
- Uses energy detection + Whisper verification
- No external dependencies
- More flexible (any word can be wake word)

**Recommendation:** Keep current Whisper-based approach for flexibility, add OpenWakeWord as optional low-latency alternative.

---

### Phase 8: Testing Infrastructure

**PR #9: Add Comprehensive Test Suite**

```
tests/
    conftest.py
    unit/
        test_transcription.py
        test_tts.py
        test_llm_router.py
        test_home_assistant.py
    integration/
        test_voice_pipeline.py
        test_api_server.py
    e2e/
        test_full_conversation.py
```

**Test Framework:**
```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "pytest-cov>=4.0",
    "pytest-mock>=3.0",
    "httpx>=0.25",  # For FastAPI testing
]
```

**Example Tests:**
```python
@pytest.mark.asyncio
async def test_transcription_accuracy():
    """Test that transcription handles common phrases."""
    assistant = JarvisAssistant(whisper_model="tiny")

    # Use pre-recorded test audio
    audio = load_test_audio("hello_jarvis.wav")
    result = await assistant.transcribe_async(audio)

    assert "jarvis" in result.lower()

@pytest.mark.asyncio
async def test_smart_router_classification():
    """Test query complexity classification."""
    router = SmartRouter()

    simple_queries = ["What time is it?", "Tell me a joke"]
    for query in simple_queries:
        complexity = await router.classify(query)
        assert complexity == "simple"
```

---

## Implementation Timeline

| PR | Title | Effort | Priority | Dependencies |
|----|-------|--------|----------|--------------|
| 1 | Python 3.11/3.12 Target | 2h | High | None |
| 2 | Add Ruff Linting | 4h | High | PR #1 |
| 3 | Add MyPy Type Checking | 8h | Medium | PR #2 |
| 4 | faster-whisper Migration | 4h | High | PR #1 |
| 5 | Flask to FastAPI | 8h | Medium | PR #3 |
| 6 | Async Architecture | 16h | Medium | PR #5 |
| 7 | Piper TTS Integration | 4h | Low | PR #1 |
| 8 | OpenWakeWord Option | 4h | Low | PR #1 |
| 9 | Test Infrastructure | 8h | Medium | PR #6 |

**Total Estimated Effort:** ~58 hours

---

## Migration Path

### Quick Wins (Do First)
1. **PR #1**: Python version - immediate 10-60% speedup
2. **PR #4**: faster-whisper - 3-4x transcription speedup
3. **PR #2**: Ruff - cleaner codebase immediately

### Medium Term
4. **PR #3**: Type hints - better maintainability
5. **PR #5**: FastAPI - modern API infrastructure
6. **PR #7**: Piper TTS - better voice quality

### Long Term
7. **PR #6**: Full async - architectural improvement
8. **PR #9**: Tests - prevent regressions
9. **PR #8**: OpenWakeWord - licensing flexibility

---

## Breaking Changes

### API Changes (PR #5)
- Flask endpoints renamed to follow REST conventions
- Request/response schemas enforced via Pydantic
- WebSocket endpoint added for streaming

### Configuration Changes
- Move from inline config to environment variables
- Add `config.yaml` or `.env` support
- Pydantic Settings for validation

### Dependency Changes
- Minimum Python 3.11 required
- New dependencies: faster-whisper, fastapi, piper-tts
- Removed: flask, openai-whisper (optional), pvporcupine (optional)

---

## Rollback Plan

Each PR should be independently revertable. Keep:
- Original `requirements.txt` as `requirements-legacy.txt`
- Original jarvis_*.py files until migration complete
- Feature flags for new implementations

```python
# config.py
USE_FASTER_WHISPER = os.getenv("USE_FASTER_WHISPER", "true") == "true"
USE_PIPER_TTS = os.getenv("USE_PIPER_TTS", "false") == "true"
```

---

## Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Transcription time | 2-5s | 0.5-1.5s | Timing logs |
| Response latency | 5-8s | 2-4s | End-to-end timing |
| Code coverage | 0% | 80% | pytest-cov |
| Type coverage | 0% | 95% | mypy --strict |
| Lint errors | Unknown | 0 | ruff check |

---

## Next Steps

1. Review this plan and prioritize PRs
2. Create GitHub issues for each PR
3. Set up CI/CD pipeline
4. Begin with PR #1 (Python version)
5. Measure baseline performance before changes
