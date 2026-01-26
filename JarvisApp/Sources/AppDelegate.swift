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
        setupStatusBar()
        setupHotKey()
        setupCore()
        startServers()

        // Create desktop shortcut on first run
        DesktopShortcut.createIfNeeded()
    }

    func applicationWillTerminate(_ notification: Notification) {
        jarvisCore?.stopConversation()
        serverManager?.stopAllServers()
    }

    // MARK: - Setup Methods
    private func setupStatusBar() {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)

        if let button = statusItem.button {
            button.image = iconIdle
            button.image?.isTemplate = true
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

        menu.addItem(NSMenuItem.separator())

        // Server status submenu
        let serverMenu = NSMenu()
        serverMenu.addItem(createServerStatusItem(name: "PersonaPlex", port: 8998))
        serverMenu.addItem(createServerStatusItem(name: "Orchestrator", port: 5000))
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
            jarvisCore.stopConversation()
            updateState(.idle)
            updateToggleButton(isActive: false)
        } else {
            Task {
                do {
                    try await jarvisCore.startConversation()
                    await MainActor.run {
                        updateState(.listening)
                        updateToggleButton(isActive: true)
                    }
                } catch {
                    await MainActor.run {
                        updateState(.error(error.localizedDescription))
                        showError("Failed to start conversation: \(error.localizedDescription)")
                    }
                }
            }
        }
    }

    @objc private func setModeFullDuplex() {
        jarvisCore.setMode(.fullDuplex)
    }

    @objc private func setModeHybrid() {
        jarvisCore.setMode(.hybrid)
    }

    @objc private func setModeLegacy() {
        jarvisCore.setMode(.legacy)
    }

    @objc private func showVoiceProfiles() {
        // TODO: Show voice profile selection window
        print("Show voice profiles")
    }

    @objc private func showDashboard() {
        // TODO: Show conversation dashboard window
        print("Show dashboard")
    }

    @objc private func showSettings() {
        // TODO: Show settings window
        print("Show settings")
    }

    @objc private func restartServers() {
        serverManager.restartAllServers()
    }

    @objc private func quitApp() {
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
        DispatchQueue.main.async {
            self.updateState(state)
        }
    }

    func jarvisCore(_ core: JarvisCore, didReceiveTranscription text: String) {
        print("User: \(text)")
    }

    func jarvisCore(_ core: JarvisCore, didReceiveResponse text: String) {
        print("Jarvis: \(text)")
    }

    func jarvisCore(_ core: JarvisCore, didEncounterError error: Error) {
        DispatchQueue.main.async {
            self.updateState(.error(error.localizedDescription))
            self.showError(error.localizedDescription)
        }
    }
}

// MARK: - ServerManagerDelegate
extension AppDelegate: ServerManagerDelegate {
    func serverManager(_ manager: ServerManager, serverDidStart name: String, port: Int) {
        DispatchQueue.main.async {
            self.updateServerStatus(port: port, isOnline: true)
        }
    }

    func serverManager(_ manager: ServerManager, serverDidStop name: String, port: Int) {
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

