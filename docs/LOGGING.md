# Jarvis Voice Assistant - Logging Standards

This document outlines the logging standards and practices for the Jarvis Voice Assistant project.

## Overview

All applications in this project should implement comprehensive logging for:
- Debugging during development
- Crash analysis in production
- Monitoring system health
- Tracking user interactions (privacy-respecting)

## Swift App Logging (JarvisApp)

### Logger Location
- **Class**: `JarvisLogger` in `JarvisApp/Sources/Utils/Logger.swift`
- **Log Files**: `~/Library/Application Support/JarvisApp/Logs/`
- **Retention**: 7 days (auto-cleanup of older logs)

### Log Levels

| Level | Usage | Example |
|-------|-------|---------|
| `debug` | Detailed debugging info, not for production | "Buffer size: 1024 bytes" |
| `info` | Normal operational events | "Audio capture started" |
| `warning` | Recoverable issues | "Server disconnected, retrying..." |
| `error` | Errors that need attention | "Failed to initialize audio engine" |
| `critical` | Crashes or fatal errors | "CRASH: Null pointer in audio callback" |

### Categories

| Category | Usage |
|----------|-------|
| `.general` | Application lifecycle, mode changes |
| `.audio` | Audio capture, playback, processing |
| `.network` | Server connections, API calls |
| `.ui` | User interface events |
| `.error` | Error tracking (used with error/critical levels) |

### Usage

```swift
// Import is not needed - global functions available everywhere

// Basic logging
logDebug("Processing buffer")
logInfo("Conversation started", category: .audio)
logWarning("Server response slow", category: .network)
logError("Connection failed", error: someError)
logCrash("Fatal: Audio engine corrupted")

// Direct logger access
JarvisLogger.shared.log(.info, category: .network, "Custom message")
JarvisLogger.shared.flush()  // Force write to disk
```

### Log File Format

```
================================================================================
JARVIS VOICE ASSISTANT LOG
Started: 2025-01-25 19:30:00.000
Version: 1.0
OS: macOS 15.2.0
================================================================================

[2025-01-25 19:30:00.123] [INFO] [General] [AppDelegate.swift:25] applicationDidFinishLaunching(_:) - JarvisApp starting up
[2025-01-25 19:30:00.456] [DEBUG] [Audio] [AudioPipeline.swift:35] startCapture() - Input format: 48000.0Hz, 1 channels
[2025-01-25 19:30:01.789] [ERROR] [Network] [ServerManager.swift:120] startOrchestrator() - Failed to start orchestrator | Error: No such file
```

### Viewing Logs

1. **From the app**: Menu Bar > View Logs... (Cmd+L)
2. **From Finder**: `~/Library/Application Support/JarvisApp/Logs/`
3. **From Console.app**: Filter by "com.jarvis.voiceassistant"

## Python Backend Logging

### Configuration

All Python modules use the standard `logging` module with consistent configuration:

```python
import logging

# In main entry point (jarvis_orchestrator.py)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# In other modules
logger = logging.getLogger(__name__)
```

### Log Levels

| Level | Usage |
|-------|-------|
| `DEBUG` | Detailed debugging info |
| `INFO` | Normal operational events |
| `WARNING` | Recoverable issues |
| `ERROR` | Errors that need attention |
| `CRITICAL` | Fatal errors |

### Usage

```python
logger.debug(f"Processing query: {text[:50]}...")
logger.info(f"Server started on port {port}")
logger.warning(f"Retry attempt {retry_count}")
logger.error(f"Failed to connect: {e}")
logger.critical(f"Database corruption detected")
```

## Best Practices

### DO:
- Log at function entry for complex operations
- Log errors with full context (error message, stack trace)
- Use appropriate log levels
- Include relevant variables in log messages
- Log state changes (mode switches, connections)
- Redact sensitive data (tokens, passwords)

### DON'T:
- Log in tight loops (performance impact)
- Log full audio/binary data
- Log sensitive information (API keys, user data)
- Use print() instead of logging
- Ignore logged warnings/errors

### Sensitive Data

Never log:
- API keys or tokens
- User credentials
- Personal information
- Full audio content
- IP addresses (unless necessary for debugging)

Redact when necessary:
```swift
logInfo("Token: \(token.prefix(8))...[REDACTED]")
```

```python
logger.info(f"API key: {api_key[:8]}...[REDACTED]")
```

## Crash Reports

### Swift Crashes

Crashes are logged with full stack trace:

```swift
logCrash("Fatal error in audio processing")
```

Output:
```
********************************************************************************
CRASH REPORT
Time: 2025-01-25 19:30:00.000
Location: AudioPipeline.swift:150 processInputBuffer(_:converter:outputFormat:)
Message: Fatal error in audio processing

Stack Trace:
0   JarvisApp                           0x0000000100001234 ...
1   JarvisApp                           0x0000000100005678 ...
...
********************************************************************************
```

### Python Exceptions

Use exc_info for full traceback:

```python
try:
    # ... operation
except Exception as e:
    logger.error(f"Operation failed: {e}", exc_info=True)
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `JARVIS_LOG_LEVEL` | Minimum log level | INFO |
| `JARVIS_LOG_FILE` | Custom log file path | Auto-generated |
| `JARVIS_LOG_CONSOLE` | Also log to console | true (debug) |

## Integration with Monitoring

Logs can be forwarded to external monitoring services:

1. **Console.app** (macOS): Uses os_log, visible in Console.app
2. **File export**: Log files can be uploaded for analysis
3. **Future**: Integration with services like Sentry, DataDog

## Troubleshooting

### No logs appearing
1. Check log directory exists: `ls ~/Library/Application\ Support/JarvisApp/Logs/`
2. Check file permissions
3. Verify Logger is initialized (app startup)

### Logs too verbose
- Set log level to INFO or WARNING
- Filter by category in code

### Logs missing crash info
- Ensure `logCrash()` is called before app terminates
- Check `flush()` is called in termination handler
