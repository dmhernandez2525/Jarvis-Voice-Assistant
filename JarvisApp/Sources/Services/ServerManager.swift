import Foundation

protocol ServerManagerDelegate: AnyObject {
    func serverManager(_ manager: ServerManager, serverDidStart name: String, port: Int)
    func serverManager(_ manager: ServerManager, serverDidStop name: String, port: Int)
}

class ServerManager {
    // MARK: - Properties
    weak var delegate: ServerManagerDelegate?

    private var orchestratorProcess: Process?
    private var voiceforgeProcess: Process?
    private var personaplexProcess: Process?

    private var healthCheckTimer: Timer?

    private let jarvisRoot: URL
    private let voiceforgeRoot: URL
    private let pythonPath: String
    private let dockerPath: String

    // MARK: - Initialization
    init() {
        // Find project roots from environment variables or defaults
        let homeDir = FileManager.default.homeDirectoryForCurrentUser

        // JARVIS_ROOT can be set via environment variable
        // Falls back to finding it relative to the app bundle or using a default location
        if let jarvisEnv = ProcessInfo.processInfo.environment["JARVIS_ROOT"] {
            self.jarvisRoot = URL(fileURLWithPath: jarvisEnv)
            logInfo("Using JARVIS_ROOT from environment: \(jarvisEnv)", category: .network)
        } else if let bundlePath = Bundle.main.executablePath {
            // Try to find jarvis root relative to the app (development builds)
            let bundleURL = URL(fileURLWithPath: bundlePath)
            let possibleRoot = bundleURL
                .deletingLastPathComponent() // debug
                .deletingLastPathComponent() // .build
                .deletingLastPathComponent() // JarvisApp
            if FileManager.default.fileExists(atPath: possibleRoot.appendingPathComponent("jarvis_orchestrator.py").path) {
                self.jarvisRoot = possibleRoot
                logInfo("Auto-detected JARVIS_ROOT: \(possibleRoot.path)", category: .network)
            } else {
                // Fallback to default location
                self.jarvisRoot = homeDir.appendingPathComponent("Desktop/Projects/PersonalProjects/jarvis-voice-assistant")
                logWarning("Using default JARVIS_ROOT location. Set JARVIS_ROOT env var for custom path.", category: .network)
            }
        } else {
            self.jarvisRoot = homeDir.appendingPathComponent("Desktop/Projects/PersonalProjects/jarvis-voice-assistant")
            logWarning("Using default JARVIS_ROOT location. Set JARVIS_ROOT env var for custom path.", category: .network)
        }

        // VOICEFORGE_ROOT can be set via environment variable
        if let voiceforgeEnv = ProcessInfo.processInfo.environment["VOICEFORGE_ROOT"] {
            self.voiceforgeRoot = URL(fileURLWithPath: voiceforgeEnv)
            logInfo("Using VOICEFORGE_ROOT from environment: \(voiceforgeEnv)", category: .network)
        } else {
            self.voiceforgeRoot = homeDir.appendingPathComponent("Desktop/Projects/PersonalProjects/voiceforge")
            logWarning("Using default VOICEFORGE_ROOT location. Set VOICEFORGE_ROOT env var for custom path.", category: .network)
        }

        // Python path from environment or common locations
        self.pythonPath = ProcessInfo.processInfo.environment["PYTHON_PATH"]
            ?? ServerManager.findExecutable("python3")
            ?? "/usr/bin/python3"
        logDebug("Python path: \(self.pythonPath)", category: .network)

        // Docker path from environment or common locations
        self.dockerPath = ProcessInfo.processInfo.environment["DOCKER_PATH"]
            ?? ServerManager.findExecutable("docker")
            ?? "/usr/local/bin/docker"
        logDebug("Docker path: \(self.dockerPath)", category: .network)
    }

    /// Find executable in common paths
    private static func findExecutable(_ name: String) -> String? {
        let paths = [
            "/usr/local/bin/\(name)",
            "/usr/bin/\(name)",
            "/opt/homebrew/bin/\(name)",
            "/opt/local/bin/\(name)"
        ]
        return paths.first { FileManager.default.isExecutableFile(atPath: $0) }
    }

    deinit {
        stopAllServers()
    }

    // MARK: - Server Management
    func startAllServers() {
        startOrchestrator()
        startVoiceForge()
        startPersonaPlex()

        // Start health check polling
        healthCheckTimer = Timer.scheduledTimer(withTimeInterval: 5.0, repeats: true) { [weak self] _ in
            self?.performHealthChecks()
        }
    }

    func stopAllServers() {
        healthCheckTimer?.invalidate()
        healthCheckTimer = nil

        stopProcess(&orchestratorProcess, name: "Orchestrator", port: 5001)
        stopProcess(&voiceforgeProcess, name: "VoiceForge", port: 8765)
        stopProcess(&personaplexProcess, name: "PersonaPlex", port: 8998)
    }

    func restartAllServers() {
        stopAllServers()
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) { [weak self] in
            self?.startAllServers()
        }
    }

    // MARK: - Individual Server Start
    private func startOrchestrator() {
        let scriptPath = jarvisRoot.appendingPathComponent("jarvis_orchestrator.py")

        guard FileManager.default.fileExists(atPath: scriptPath.path) else {
            logError("Orchestrator script not found at \(scriptPath.path)")
            return
        }

        // Use venv python if available
        let venvPython = jarvisRoot.appendingPathComponent("venv/bin/python")
        let actualPythonPath: String
        if FileManager.default.isExecutableFile(atPath: venvPython.path) {
            actualPythonPath = venvPython.path
            logInfo("Using venv Python for Orchestrator", category: .network)
        } else {
            actualPythonPath = pythonPath
            logWarning("Venv not found, using system Python for Orchestrator", category: .network)
        }

        logInfo("Starting Orchestrator from \(scriptPath.path)", category: .network)

        orchestratorProcess = Process()
        orchestratorProcess?.executableURL = URL(fileURLWithPath: actualPythonPath)
        orchestratorProcess?.arguments = [scriptPath.path]
        orchestratorProcess?.currentDirectoryURL = jarvisRoot

        orchestratorProcess?.terminationHandler = { [weak self] process in
            logWarning("Orchestrator terminated with code \(process.terminationStatus)", category: .network)
            DispatchQueue.main.async {
                guard let self = self else { return }
                self.delegate?.serverManager(self, serverDidStop: "Orchestrator", port: 5001)
            }
        }

        do {
            try orchestratorProcess?.run()
            DispatchQueue.main.asyncAfter(deadline: .now() + 2.0) { [weak self] in
                guard let self = self else { return }
                self.delegate?.serverManager(self, serverDidStart: "Orchestrator", port: 5001)
            }
        } catch {
            logError("Failed to start orchestrator", error: error)
        }
    }

    private func startVoiceForge() {
        let scriptPath = voiceforgeRoot.appendingPathComponent("python-backend/server.py")

        guard FileManager.default.fileExists(atPath: scriptPath.path) else {
            logError("VoiceForge script not found at \(scriptPath.path)")
            return
        }

        logInfo("Starting VoiceForge from \(scriptPath.path)", category: .network)

        voiceforgeProcess = Process()
        voiceforgeProcess?.executableURL = URL(fileURLWithPath: pythonPath)
        voiceforgeProcess?.arguments = [scriptPath.path]
        voiceforgeProcess?.currentDirectoryURL = voiceforgeRoot.appendingPathComponent("python-backend")

        voiceforgeProcess?.terminationHandler = { [weak self] process in
            logWarning("VoiceForge terminated with code \(process.terminationStatus)", category: .network)
            DispatchQueue.main.async {
                guard let self = self else { return }
                self.delegate?.serverManager(self, serverDidStop: "VoiceForge", port: 8765)
            }
        }

        do {
            try voiceforgeProcess?.run()
            DispatchQueue.main.asyncAfter(deadline: .now() + 3.0) { [weak self] in
                guard let self = self else { return }
                self.delegate?.serverManager(self, serverDidStart: "VoiceForge", port: 8765)
            }
        } catch {
            logError("Failed to start VoiceForge", error: error)
        }
    }

    private func startPersonaPlex() {
        logInfo("Starting PersonaPlex server (native mode)", category: .network)

        // PersonaPlex runs natively on macOS (not Docker - no GPU passthrough on Mac)
        let runScript = jarvisRoot.appendingPathComponent("run_personaplex.sh")

        // Check if setup has been done
        let personaplexDir = jarvisRoot.appendingPathComponent("personaplex")
        let venvPath = personaplexDir.appendingPathComponent("venv/bin/python")

        guard FileManager.default.fileExists(atPath: personaplexDir.path) else {
            logWarning("PersonaPlex not installed. Run ./setup_personaplex.sh first", category: .network)
            logInfo("PersonaPlex will be skipped - using Legacy mode is recommended", category: .network)
            // Don't fail - just skip PersonaPlex and let the app use legacy mode
            return
        }

        // Check for HF_TOKEN
        if ProcessInfo.processInfo.environment["HF_TOKEN"] == nil {
            logWarning("HF_TOKEN not set - PersonaPlex requires HuggingFace authentication", category: .network)
            logInfo("Set HF_TOKEN environment variable to enable PersonaPlex", category: .network)
            return
        }

        // Check if PersonaPlex is already running by checking the port
        if isPortInUse(8998) {
            logInfo("PersonaPlex already running on port 8998", category: .network)
            delegate?.serverManager(self, serverDidStart: "PersonaPlex", port: 8998)
            return
        }

        // Start PersonaPlex using the run script if it exists
        if FileManager.default.fileExists(atPath: runScript.path) {
            startPersonaPlexWithScript(runScript)
        } else if FileManager.default.fileExists(atPath: venvPath.path) {
            // Start directly using the venv
            startPersonaPlexDirect(personaplexDir: personaplexDir, venvPath: venvPath)
        } else {
            logWarning("PersonaPlex venv not found. Run ./setup_personaplex.sh first", category: .network)
        }
    }

    private func startPersonaPlexWithScript(_ scriptPath: URL) {
        logInfo("Starting PersonaPlex with script: \(scriptPath.path)", category: .network)

        personaplexProcess = Process()
        personaplexProcess?.executableURL = URL(fileURLWithPath: "/bin/bash")
        personaplexProcess?.arguments = [scriptPath.path]
        personaplexProcess?.currentDirectoryURL = jarvisRoot
        personaplexProcess?.environment = ProcessInfo.processInfo.environment

        // Capture output for logging
        let outputPipe = Pipe()
        let errorPipe = Pipe()
        personaplexProcess?.standardOutput = outputPipe
        personaplexProcess?.standardError = errorPipe

        personaplexProcess?.terminationHandler = { [weak self] process in
            logWarning("PersonaPlex terminated with code \(process.terminationStatus)", category: .network)
            DispatchQueue.main.async {
                guard let self = self else { return }
                self.delegate?.serverManager(self, serverDidStop: "PersonaPlex", port: 8998)
            }
        }

        do {
            try personaplexProcess?.run()
            // Give it time to start up before checking
            DispatchQueue.main.asyncAfter(deadline: .now() + 10.0) { [weak self] in
                guard let self = self else { return }
                self.delegate?.serverManager(self, serverDidStart: "PersonaPlex", port: 8998)
            }
        } catch {
            logError("Failed to start PersonaPlex", error: error)
        }
    }

    private func startPersonaPlexDirect(personaplexDir: URL, venvPath: URL) {
        logInfo("Starting PersonaPlex directly with venv", category: .network)

        personaplexProcess = Process()
        personaplexProcess?.executableURL = venvPath
        personaplexProcess?.arguments = [
            "-m", "moshi.server",
            "--port", "8998",
            "--host", "0.0.0.0",
            "--cpu-offload"  // Required for Mac (no NVIDIA GPU)
        ]
        personaplexProcess?.currentDirectoryURL = personaplexDir
        personaplexProcess?.environment = ProcessInfo.processInfo.environment

        personaplexProcess?.terminationHandler = { [weak self] process in
            logWarning("PersonaPlex terminated with code \(process.terminationStatus)", category: .network)
            DispatchQueue.main.async {
                guard let self = self else { return }
                self.delegate?.serverManager(self, serverDidStop: "PersonaPlex", port: 8998)
            }
        }

        do {
            try personaplexProcess?.run()
            DispatchQueue.main.asyncAfter(deadline: .now() + 15.0) { [weak self] in
                guard let self = self else { return }
                self.delegate?.serverManager(self, serverDidStart: "PersonaPlex", port: 8998)
            }
        } catch {
            logError("Failed to start PersonaPlex", error: error)
        }
    }

    private func isPortInUse(_ port: Int) -> Bool {
        let checkProcess = Process()
        checkProcess.executableURL = URL(fileURLWithPath: "/usr/sbin/lsof")
        checkProcess.arguments = ["-i", ":\(port)", "-P", "-n"]

        let pipe = Pipe()
        checkProcess.standardOutput = pipe
        checkProcess.standardError = FileHandle.nullDevice

        do {
            try checkProcess.run()
            checkProcess.waitUntilExit()
            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            let output = String(data: data, encoding: .utf8) ?? ""
            return !output.isEmpty
        } catch {
            return false
        }
    }

    // MARK: - Stop Process
    private func stopProcess(_ process: inout Process?, name: String, port: Int) {
        if let p = process, p.isRunning {
            p.terminate()
        }
        process = nil
        delegate?.serverManager(self, serverDidStop: name, port: port)
    }

    // MARK: - Health Checks
    private func performHealthChecks() {
        Task {
            // Check Orchestrator
            await checkServer(url: "http://localhost:5001/health", name: "Orchestrator", port: 5001)

            // Check VoiceForge
            await checkServer(url: "http://localhost:8765/health", name: "VoiceForge", port: 8765)

            // Check Ollama
            await checkServer(url: "http://localhost:11434/api/tags", name: "Ollama", port: 11434)

            // Check PersonaPlex (no /health endpoint, check root which returns HTML)
            await checkServer(url: "http://localhost:8998/", name: "PersonaPlex", port: 8998)
        }
    }

    private func checkServer(url: String, name: String, port: Int) async {
        guard let url = URL(string: url) else { return }

        do {
            let (_, response) = try await URLSession.shared.data(from: url)
            let isOnline = (response as? HTTPURLResponse)?.statusCode == 200

            await MainActor.run {
                if isOnline {
                    delegate?.serverManager(self, serverDidStart: name, port: port)
                } else {
                    delegate?.serverManager(self, serverDidStop: name, port: port)
                }
            }
        } catch {
            await MainActor.run {
                delegate?.serverManager(self, serverDidStop: name, port: port)
            }
        }
    }
}
