import Cocoa
import HotKey

class AppDelegate: NSObject, NSApplicationDelegate {
    // MARK: - Properties
    private var statusItem: NSStatusItem!
    private var jarvisCore: JarvisCore!
    private var hotKey: HotKey?
    private var serverManager: ServerManager!

    // Status icons
    private let iconIdle = NSImage(systemSymbolName: "waveform", accessibilityDescription: "Jarvis Idle")
    private let iconListening = NSImage(systemSymbolName: "waveform.circle.fill", accessibilityDescription: "Jarvis Listening")
    private let iconProcessing = NSImage(systemSymbolName: "brain", accessibilityDescription: "Jarvis Processing")
    private let iconSpeaking = NSImage(systemSymbolName: "speaker.wave.2.fill", accessibilityDescription: "Jarvis Speaking")
    private let iconError = NSImage(systemSymbolName: "exclamationmark.triangle", accessibilityDescription: "Jarvis Error")

    // MARK: - Application Lifecycle
    func applicationDidFinishLaunching(_ notification: Notification) {
        logInfo("JarvisApp starting up", category: .general)
        logInfo("System: \(ProcessInfo.processInfo.operatingSystemVersionString)", category: .general)

        setupStatusBar()
        logDebug("Status bar initialized", category: .ui)

        setupHotKey()
        logDebug("Hotkey registered (Option+Space)", category: .ui)

        setupCore()
        logDebug("JarvisCore initialized", category: .general)

        startServers()
        logInfo("Server manager started", category: .network)

        // Create desktop shortcut on first run
        DesktopShortcut.createIfNeeded()

        logInfo("JarvisApp startup complete", category: .general)
    }

    func applicationWillTerminate(_ notification: Notification) {
        logInfo("JarvisApp shutting down", category: .general)
        jarvisCore?.stopConversation()
        serverManager?.stopAllServers()
        JarvisLogger.shared.flush()
        logInfo("JarvisApp terminated", category: .general)
    }

    // MARK: - Setup Methods
    private func setupStatusBar() {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)

        if let button = statusItem.button {
            // Try to use SF Symbol, fall back to text if not available
            if let icon = iconIdle {
                button.image = icon
                button.image?.isTemplate = true
                logDebug("Using SF Symbol icon", category: .ui)
            } else {
                // Fallback to text title if SF Symbol not available
                button.title = "J"
                logWarning("SF Symbol not available, using text fallback", category: .ui)
            }
        } else {
            logError("Failed to get status item button")
        }

        let menu = NSMenu()

        // Status header
        let statusItem = NSMenuItem(title: "Jarvis - Idle", action: nil, keyEquivalent: "")
        statusItem.isEnabled = false
        statusItem.tag = 100 // For updating later
        menu.addItem(statusItem)

        menu.addItem(NSMenuItem.separator())

        // Start/Stop conversation
        let toggleItem = NSMenuItem(title: "Start Conversation", action: #selector(toggleConversation), keyEquivalent: "")
        toggleItem.tag = 101
        menu.addItem(toggleItem)

        // Hotkey hint
        let hotkeyItem = NSMenuItem(title: "Shortcut: \u{2325}Space", action: nil, keyEquivalent: "")
        hotkeyItem.isEnabled = false
        menu.addItem(hotkeyItem)

        menu.addItem(NSMenuItem.separator())

        // Mode submenu
        let modeMenu = NSMenu()
        modeMenu.addItem(NSMenuItem(title: "Full Duplex (PersonaPlex)", action: #selector(setModeFullDuplex), keyEquivalent: ""))
        modeMenu.addItem(NSMenuItem(title: "Hybrid (PersonaPlex + Ollama)", action: #selector(setModeHybrid), keyEquivalent: ""))
        modeMenu.addItem(NSMenuItem(title: "Legacy (Ollama Only)", action: #selector(setModeLegacy), keyEquivalent: ""))
        let modeItem = NSMenuItem(title: "Mode", action: nil, keyEquivalent: "")
        modeItem.submenu = modeMenu
        menu.addItem(modeItem)

        // Voice profile
        let voiceItem = NSMenuItem(title: "Voice: Default", action: #selector(showVoiceProfiles), keyEquivalent: "")
        voiceItem.tag = 102
        menu.addItem(voiceItem)

        menu.addItem(NSMenuItem.separator())

        // Dashboard
        menu.addItem(NSMenuItem(title: "Show Dashboard...", action: #selector(showDashboard), keyEquivalent: "d"))
        menu.addItem(NSMenuItem(title: "Settings...", action: #selector(showSettings), keyEquivalent: ","))
        menu.addItem(NSMenuItem(title: "View Logs...", action: #selector(viewLogs), keyEquivalent: "l"))

        menu.addItem(NSMenuItem.separator())

        // Server status submenu
        let serverMenu = NSMenu()
        serverMenu.addItem(createServerStatusItem(name: "PersonaPlex", port: 8998))
        serverMenu.addItem(createServerStatusItem(name: "Orchestrator", port: 5001))
        serverMenu.addItem(createServerStatusItem(name: "VoiceForge", port: 8765))
        serverMenu.addItem(createServerStatusItem(name: "Ollama", port: 11434))
        serverMenu.addItem(NSMenuItem.separator())
        serverMenu.addItem(NSMenuItem(title: "Restart All Servers", action: #selector(restartServers), keyEquivalent: ""))
        let serverItem = NSMenuItem(title: "Server Status", action: nil, keyEquivalent: "")
        serverItem.submenu = serverMenu
        menu.addItem(serverItem)

        menu.addItem(NSMenuItem.separator())

        // Quit
        menu.addItem(NSMenuItem(title: "Quit Jarvis", action: #selector(quitApp), keyEquivalent: "q"))

        self.statusItem.menu = menu
    }

    private func createServerStatusItem(name: String, port: Int) -> NSMenuItem {
        let item = NSMenuItem(title: "\u{25CF} \(name) (:\(port))", action: nil, keyEquivalent: "")
        item.tag = 200 + port
        return item
    }

    private func setupHotKey() {
        // Option + Space to toggle conversation
        hotKey = HotKey(key: .space, modifiers: [.option])
        hotKey?.keyDownHandler = { [weak self] in
            self?.toggleConversation()
        }
    }

    private func setupCore() {
        jarvisCore = JarvisCore()
        jarvisCore.delegate = self
    }

    private func startServers() {
        serverManager = ServerManager()
        serverManager.delegate = self
        serverManager.startAllServers()
    }

    // MARK: - Actions
    @objc private func toggleConversation() {
        if jarvisCore.isActive {
            logInfo("Stopping conversation", category: .audio)
            jarvisCore.stopConversation()
            updateState(.idle)
            updateToggleButton(isActive: false)
        } else {
            logInfo("Starting conversation", category: .audio)
            Task {
                do {
                    try await jarvisCore.startConversation()
                    await MainActor.run {
                        logInfo("Conversation started successfully", category: .audio)
                        updateState(.listening)
                        updateToggleButton(isActive: true)
                    }
                } catch {
                    await MainActor.run {
                        logError("Failed to start conversation", error: error)
                        updateState(.error(error.localizedDescription))
                        showError("Failed to start conversation: \(error.localizedDescription)")
                    }
                }
            }
        }
    }

    @objc private func setModeFullDuplex() {
        logInfo("Mode changed to Full Duplex", category: .general)
        jarvisCore.setMode(.fullDuplex)
    }

    @objc private func setModeHybrid() {
        logInfo("Mode changed to Hybrid", category: .general)
        jarvisCore.setMode(.hybrid)
    }

    @objc private func setModeLegacy() {
        logInfo("Mode changed to Legacy", category: .general)
        jarvisCore.setMode(.legacy)
    }

    @objc private func showVoiceProfiles() {
        logDebug("Voice profiles requested (not yet implemented)", category: .ui)
    }

    @objc private func showDashboard() {
        logDebug("Dashboard requested (not yet implemented)", category: .ui)
    }

    @objc private func showSettings() {
        logDebug("Settings requested (not yet implemented)", category: .ui)
    }

    @objc private func viewLogs() {
        logDebug("Opening logs folder", category: .ui)
        if let logPath = JarvisLogger.shared.currentLogPath {
            let logURL = URL(fileURLWithPath: logPath)
            NSWorkspace.shared.selectFile(logPath, inFileViewerRootedAtPath: logURL.deletingLastPathComponent().path)
        } else {
            // Fallback to opening Application Support
            if let appSupport = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first {
                let logsDir = appSupport.appendingPathComponent("JarvisApp/Logs")
                NSWorkspace.shared.open(logsDir)
            }
        }
    }

    @objc private func restartServers() {
        logInfo("Restarting all servers", category: .network)
        serverManager.restartAllServers()
    }

    @objc private func quitApp() {
        logInfo("Quit requested by user", category: .general)
        NSApplication.shared.terminate(nil)
    }

    // MARK: - UI Updates
    private func updateState(_ state: JarvisState) {
        guard let button = statusItem.button else { return }

        switch state {
        case .idle:
            button.image = iconIdle
        case .listening:
            button.image = iconListening
        case .processing:
            button.image = iconProcessing
        case .speaking:
            button.image = iconSpeaking
        case .error:
            button.image = iconError
        }
        button.image?.isTemplate = true

        // Update status text in menu
        if let menu = statusItem.menu,
           let statusItem = menu.item(withTag: 100) {
            statusItem.title = "Jarvis - \(state.description)"
        }
    }

    private func updateToggleButton(isActive: Bool) {
        if let menu = statusItem.menu,
           let toggleItem = menu.item(withTag: 101) {
            toggleItem.title = isActive ? "Stop Conversation" : "Start Conversation"
        }
    }

    private func showError(_ message: String) {
        let alert = NSAlert()
        alert.messageText = "Jarvis Error"
        alert.informativeText = message
        alert.alertStyle = .warning
        alert.addButton(withTitle: "OK")
        alert.runModal()
    }
}

// MARK: - JarvisCoreDelegate
extension AppDelegate: JarvisCoreDelegate {
    func jarvisCore(_ core: JarvisCore, didChangeState state: JarvisState) {
        logDebug("State changed to: \(state.description)", category: .general)
        DispatchQueue.main.async {
            self.updateState(state)
        }
    }

    func jarvisCore(_ core: JarvisCore, didReceiveTranscription text: String) {
        logInfo("User said: \(text)", category: .audio)
    }

    func jarvisCore(_ core: JarvisCore, didReceiveResponse text: String) {
        logInfo("Jarvis response: \(text.prefix(100))...", category: .audio)
    }

    func jarvisCore(_ core: JarvisCore, didEncounterError error: Error) {
        logError("JarvisCore error", error: error)
        DispatchQueue.main.async {
            self.updateState(.error(error.localizedDescription))
            self.showError(error.localizedDescription)
        }
    }
}

// MARK: - ServerManagerDelegate
extension AppDelegate: ServerManagerDelegate {
    func serverManager(_ manager: ServerManager, serverDidStart name: String, port: Int) {
        logInfo("Server started: \(name) on port \(port)", category: .network)
        DispatchQueue.main.async {
            self.updateServerStatus(port: port, isOnline: true)
        }
    }

    func serverManager(_ manager: ServerManager, serverDidStop name: String, port: Int) {
        logWarning("Server stopped: \(name) on port \(port)", category: .network)
        DispatchQueue.main.async {
            self.updateServerStatus(port: port, isOnline: false)
        }
    }

    private func updateServerStatus(port: Int, isOnline: Bool) {
        if let menu = statusItem.menu,
           let serverMenu = menu.item(withTitle: "Server Status")?.submenu,
           let item = serverMenu.item(withTag: 200 + port) {
            let symbol = isOnline ? "\u{2713}" : "\u{2717}"
            let currentTitle = item.title
            // Extract server name from title
            if let nameStart = currentTitle.firstIndex(of: " "),
               let nameEnd = currentTitle.firstIndex(of: "(") {
                let name = String(currentTitle[nameStart..<nameEnd]).trimmingCharacters(in: .whitespaces)
                item.title = "\(symbol) \(name) (:\(port))"
            }
        }
    }
}

