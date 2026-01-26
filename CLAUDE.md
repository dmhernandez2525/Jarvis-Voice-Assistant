# Jarvis Voice Assistant - Development Standards

## Project Overview

Jarvis is a voice assistant with:
- **Swift macOS App** (JarvisApp) - Menu bar app with global hotkey
- **Python Backend** (jarvis_orchestrator.py) - Central routing server
- **PersonaPlex** - Full duplex AI (<500ms latency)
- **VoiceForge** - Voice cloning TTS
- **Home Assistant** - Smart home integration

## Critical Development Rules

### 1. Logging is Mandatory

**Every significant operation must be logged.** See `docs/LOGGING.md` for full details.

**Swift:**
```swift
logInfo("Operation started", category: .audio)
logError("Operation failed", error: error)
logCrash("Fatal error occurred")
```

**Python:**
```python
logger.info("Operation started")
logger.error(f"Operation failed: {e}", exc_info=True)
```

**Minimum logging requirements:**
- All function entry/exit for complex operations
- All errors with full context
- All state changes
- All network requests/responses
- All user interactions

### 2. No Hardcoded Paths

**NEVER commit paths like `/Users/daniel/...`**

Use environment variables:
```swift
ProcessInfo.processInfo.environment["JARVIS_ROOT"]
```

```python
os.environ.get("JARVIS_ROOT")
```

Or relative paths:
```swift
Bundle.main.bundlePath
FileManager.default.homeDirectoryForCurrentUser
```

### 3. Error Handling

**Never silently swallow errors.**

Bad:
```swift
try? riskyOperation()  // Error silently ignored
```

Good:
```swift
do {
    try riskyOperation()
} catch {
    logError("Risky operation failed", error: error)
    // Handle or propagate
}
```

### 4. Thread Safety

- Use `@MainActor` for UI updates
- Use `DispatchQueue` for thread-safe property access
- Use `[weak self]` in closures to avoid retain cycles
- Test async code paths thoroughly

### 5. Memory Management

- Reuse expensive objects (AVAudioEngine, URLSession)
- Avoid creating objects in loops
- Clean up resources in `deinit`
- Use weak references for delegates

## Architecture

```
┌─────────────────────────────────┐
│   JarvisApp (Swift macOS)       │
│   Menu bar with Option+Space    │
└───────────────┬─────────────────┘
                │ HTTP/WebSocket
    ┌───────────┼───────────┬───────────┐
    ▼           ▼           ▼           ▼
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│PersonaPlex│ │Orchestr│ │VoiceForge│ │ Ollama │
│  :8998  │ │  :5000 │ │  :8765  │ │ :11434 │
└─────────┘ └─────────┘ └─────────┘ └─────────┘
                │
                ▼
         ┌───────────┐
         │   Home    │
         │ Assistant │
         └───────────┘
```

## Key Files

### Swift App
- `JarvisApp/Sources/AppDelegate.swift` - Main app entry, menu bar
- `JarvisApp/Sources/Core/JarvisCore.swift` - Conversation coordinator
- `JarvisApp/Sources/Core/AudioPipeline.swift` - Audio capture/playback
- `JarvisApp/Sources/Services/ServerManager.swift` - Backend process management
- `JarvisApp/Sources/Utils/Logger.swift` - Logging system

### Python Backend
- `jarvis_orchestrator.py` - Central routing server
- `personaplex_client.py` - WebSocket client for PersonaPlex
- `voiceforge_tts.py` - VoiceForge TTS wrapper
- `homeassistant_client.py` - Home Assistant integration

### Configuration
- `config/jarvis.yaml` - Main configuration file

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `JARVIS_ROOT` | Path to jarvis-voice-assistant directory | No (auto-detected) |
| `VOICEFORGE_ROOT` | Path to voiceforge directory | No (default: ~/Desktop/...) |
| `HA_URL` | Home Assistant URL | For smart home |
| `HA_TOKEN` | Home Assistant long-lived token | For smart home |
| `PYTHON_PATH` | Path to Python 3 interpreter | No (auto-detected) |
| `DOCKER_PATH` | Path to Docker CLI | No (auto-detected) |

## Testing Checklist

Before committing:
- [ ] Swift app builds: `cd JarvisApp && swift build`
- [ ] Python syntax valid: `python3 -m py_compile *.py`
- [ ] No hardcoded paths: `grep -r "/Users/" --include="*.swift" --include="*.py"`
- [ ] Logging added to new code
- [ ] Error handling present
- [ ] Memory management checked

## Common Issues

### App won't start after quit
- Kill lingering process: `pkill -f JarvisApp`
- Check logs: Menu > View Logs

### Server won't start
- Check ports not in use: `lsof -i :5000`
- Check Python path: `which python3`
- View server logs in terminal

### Audio not working
- Check microphone permissions in System Settings
- Check audio device: `system_profiler SPAudioDataType`

## PR Guidelines

1. Create feature branch: `git checkout -b feature/name`
2. Make changes with proper logging
3. Test locally
4. Push and create PR
5. Wait for CI to pass
6. Merge via GitHub UI

## Resources

- [LOGGING.md](docs/LOGGING.md) - Detailed logging documentation
- [README.md](README.md) - User documentation
- [config/jarvis.yaml](config/jarvis.yaml) - Configuration reference
