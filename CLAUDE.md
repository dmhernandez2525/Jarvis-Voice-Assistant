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

## DEPENDENCY SECURITY RULES (MANDATORY)

### Package Installation Policy
- NEVER run `npm install`, `yarn add`, `pnpm add`, `bun add`, or any package
  installation command without explicit approval from the developer.
- NEVER run `npm update`, `yarn upgrade`, `pnpm update`, `bun update`, or any
  package update command. All updates are manual and reviewed.
- NEVER modify package.json dependency versions (dependencies, devDependencies,
  peerDependencies, optionalDependencies) without explicit approval.
- NEVER add new dependencies to the project without explicit approval.
- NEVER run remote-execution commands that download and run a package on the
  fly: `npx`, `pnpm dlx`, `yarn dlx`, `bunx`. Use only packages already
  installed locally in the project's lockfile.

### When a New Package Is Needed
If a task requires a package that is not currently installed:
1. STOP and inform the developer which package and version is needed.
2. Explain WHY the package is needed and whether alternatives exist in the
   current dependency tree.
3. WAIT for the developer to manually install and verify the package.
4. Do NOT suggest running install commands. The developer will handle installation
   through the safe install process.

### When Fixing Dependency Issues
- If `npm audit` or similar shows vulnerabilities, present the findings but
  do NOT auto-fix. The developer will evaluate each update manually.
- If a lockfile conflict occurs, present the conflict but do NOT resolve it
  by running install commands.
- If node_modules is missing, inform the developer. Do NOT run install.

### Lockfile Integrity
- NEVER delete or regenerate package-lock.json, yarn.lock, or pnpm-lock.yaml
  without explicit approval.
- `npm ci --ignore-scripts` may be run ONLY when ALL of the following are true:
  (1) the developer has explicitly approved this command for this session,
  (2) the lockfile on disk is unmodified from the committed version,
  (3) the goal is to restore node_modules so existing tests can run.
  Any other install / restore command requires fresh approval.
- If the lockfile appears corrupted, flag it for manual review.

### Script Execution
- NEVER run lifecycle scripts (preinstall, postinstall, prepare) as part of
  any workflow.
- When running npm commands, always append `--ignore-scripts` unless the
  developer has explicitly approved script execution for a specific package.
- NEVER run remote-execution wrappers (`npx`, `pnpm dlx`, `yarn dlx`, `bunx`)
  for packages that are not already in the project's lockfile.

### Version Pinning
- All new dependencies MUST use exact versions (no ^ or ~ prefixes).
- If you see caret (^) or tilde (~) ranges in package.json, flag them for
  the developer to review but do NOT change them without approval.

### Suspicious Package Detection
- If you encounter any of the following in a project's dependencies, immediately
  alert the developer:
  - plain-crypto-js (any version)
  - @tanstack/setup (not a real package, IOC for Shai-Hulud)
  - Any package with a preinstall/postinstall script that downloads binaries
  - Any package that references sfrclak.com, checkmarx.cx, git-tanstack.com,
    azurestaticprovider.net, getsession.org, litter.catbox.moe, or api.svix.com
  - node-ipc versions 9.1.6, 9.2.3, or 12.0.1
  - axios versions 1.14.1 or 0.30.4
  - @bitwarden/cli@2026.4.0
  - @cap-js/sqlite@2.2.2, @cap-js/postgres@2.2.2, @cap-js/db-service@2.10.1,
    mbt@1.2.48
  - intercom-client@7.0.4 or 7.0.5
  - Unscoped `tanstack@2.0.4` through `tanstack@2.0.7` (brand-squat, distinct
    from the legitimate scoped `@tanstack/*` packages)

### Reference
Security research documents live under the developer's local
`command-center/Security research/` directory. See `npm-mitigation-plan.md`
in that directory for the full plan and incident-response runbook.
