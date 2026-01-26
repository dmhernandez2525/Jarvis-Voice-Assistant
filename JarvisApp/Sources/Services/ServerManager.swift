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

        stopProcess(&orchestratorProcess, name: "Orchestrator", port: 5000)
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

        logInfo("Starting Orchestrator from \(scriptPath.path)", category: .network)

        orchestratorProcess = Process()
        orchestratorProcess?.executableURL = URL(fileURLWithPath: pythonPath)
        orchestratorProcess?.arguments = [scriptPath.path]
        orchestratorProcess?.currentDirectoryURL = jarvisRoot

        orchestratorProcess?.terminationHandler = { [weak self] process in
            logWarning("Orchestrator terminated with code \(process.terminationStatus)", category: .network)
            DispatchQueue.main.async {
                guard let self = self else { return }
                self.delegate?.serverManager(self, serverDidStop: "Orchestrator", port: 5000)
            }
        }

        do {
            try orchestratorProcess?.run()
            DispatchQueue.main.asyncAfter(deadline: .now() + 2.0) { [weak self] in
                guard let self = self else { return }
                self.delegate?.serverManager(self, serverDidStart: "Orchestrator", port: 5000)
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
        logInfo("Checking PersonaPlex Docker container", category: .network)

        // PersonaPlex runs in Docker
        // Check if Docker is running and the container exists
        let checkProcess = Process()
        checkProcess.executableURL = URL(fileURLWithPath: dockerPath)
        checkProcess.arguments = ["ps", "-q", "-f", "name=personaplex"]

        let pipe = Pipe()
        checkProcess.standardOutput = pipe

        do {
            try checkProcess.run()
            checkProcess.waitUntilExit()

            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            let output = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""

            if output.isEmpty {
                // Container not running, start it
                logInfo("PersonaPlex container not running, starting...", category: .network)
                startPersonaPlexDocker()
            } else {
                // Container already running
                logInfo("PersonaPlex container already running", category: .network)
                delegate?.serverManager(self, serverDidStart: "PersonaPlex", port: 8998)
            }
        } catch {
            logError("Docker check failed", error: error)
            // Try to start anyway
            startPersonaPlexDocker()
        }
    }

    private func startPersonaPlexDocker() {
        logInfo("Starting PersonaPlex Docker container", category: .network)

        personaplexProcess = Process()
        personaplexProcess?.executableURL = URL(fileURLWithPath: dockerPath)
        personaplexProcess?.arguments = [
            "run", "-d",
            "--name", "personaplex",
            "-p", "8998:8998",
            "--rm",
            "personaplex:latest"
        ]

        personaplexProcess?.terminationHandler = { [weak self] process in
            if process.terminationStatus == 0 {
                logInfo("PersonaPlex Docker started successfully", category: .network)
                DispatchQueue.main.async {
                    guard let self = self else { return }
                    self.delegate?.serverManager(self, serverDidStart: "PersonaPlex", port: 8998)
                }
            } else {
                logWarning("PersonaPlex Docker exited with code \(process.terminationStatus)", category: .network)
            }
        }

        do {
            try personaplexProcess?.run()
        } catch {
            logError("Failed to start PersonaPlex Docker", error: error)
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
            await checkServer(url: "http://localhost:5000/health", name: "Orchestrator", port: 5000)

            // Check VoiceForge
            await checkServer(url: "http://localhost:8765/health", name: "VoiceForge", port: 8765)

            // Check Ollama
            await checkServer(url: "http://localhost:11434/api/tags", name: "Ollama", port: 11434)

            // Check PersonaPlex (WebSocket health endpoint)
            await checkServer(url: "http://localhost:8998/health", name: "PersonaPlex", port: 8998)
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
