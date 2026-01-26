import Cocoa

/// Controller for the status bar menu item
class StatusBarController {
    // MARK: - Properties
    private var statusItem: NSStatusItem
    private var menu: NSMenu

    var onToggleListening: (() -> Void)?
    var onModeSelected: ((ConversationMode) -> Void)?
    var onVoiceProfileSelected: ((String?) -> Void)?
    var onOpenSettings: (() -> Void)?
    var onQuit: (() -> Void)?

    private var stateMenuItem: NSMenuItem?
    private var modeMenuItems: [ConversationMode: NSMenuItem] = [:]
    private var serverMenuItems: [String: NSMenuItem] = [:]

    // MARK: - Initialization
    init() {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        menu = NSMenu()

        setupStatusItem()
        setupMenu()
    }

    // MARK: - Setup
    private func setupStatusItem() {
        if let button = statusItem.button {
            button.image = NSImage(systemSymbolName: "mic.slash", accessibilityDescription: "Jarvis")
            button.action = #selector(statusItemClicked)
            button.target = self
        }
        statusItem.menu = menu
    }

    private func setupMenu() {
        // State indicator
        stateMenuItem = NSMenuItem(title: "Status: Idle", action: nil, keyEquivalent: "")
        stateMenuItem?.isEnabled = false
        menu.addItem(stateMenuItem!)

        menu.addItem(NSMenuItem.separator())

        // Toggle listening
        let toggleItem = NSMenuItem(
            title: "Start Listening",
            action: #selector(toggleListening),
            keyEquivalent: " "
        )
        toggleItem.keyEquivalentModifierMask = [.option]
        toggleItem.target = self
        menu.addItem(toggleItem)

        menu.addItem(NSMenuItem.separator())

        // Mode submenu
        let modeMenu = NSMenu()
        for mode in ConversationMode.allCases {
            let item = NSMenuItem(
                title: mode.displayName,
                action: #selector(modeMenuItemClicked(_:)),
                keyEquivalent: ""
            )
            item.target = self
            item.representedObject = mode
            item.toolTip = mode.description
            modeMenu.addItem(item)
            modeMenuItems[mode] = item
        }

        let modeMenuItem = NSMenuItem(title: "Mode", action: nil, keyEquivalent: "")
        modeMenuItem.submenu = modeMenu
        menu.addItem(modeMenuItem)

        // Voice profile submenu
        let voiceMenu = NSMenu()
        let defaultVoice = NSMenuItem(
            title: "Default (Ryan)",
            action: #selector(voiceProfileClicked(_:)),
            keyEquivalent: ""
        )
        defaultVoice.target = self
        defaultVoice.state = .on
        voiceMenu.addItem(defaultVoice)

        let voiceMenuItem = NSMenuItem(title: "Voice", action: nil, keyEquivalent: "")
        voiceMenuItem.submenu = voiceMenu
        menu.addItem(voiceMenuItem)

        menu.addItem(NSMenuItem.separator())

        // Server status submenu
        let serverMenu = NSMenu()
        let servers = ["Orchestrator", "VoiceForge", "PersonaPlex", "Ollama"]
        for server in servers {
            let item = NSMenuItem(title: "\(server): Unknown", action: nil, keyEquivalent: "")
            item.isEnabled = false
            serverMenu.addItem(item)
            serverMenuItems[server] = item
        }

        let serverMenuItem = NSMenuItem(title: "Servers", action: nil, keyEquivalent: "")
        serverMenuItem.submenu = serverMenu
        menu.addItem(serverMenuItem)

        menu.addItem(NSMenuItem.separator())

        // Settings
        let settingsItem = NSMenuItem(
            title: "Settings...",
            action: #selector(openSettings),
            keyEquivalent: ","
        )
        settingsItem.target = self
        menu.addItem(settingsItem)

        // Quit
        let quitItem = NSMenuItem(
            title: "Quit Jarvis",
            action: #selector(quit),
            keyEquivalent: "q"
        )
        quitItem.target = self
        menu.addItem(quitItem)
    }

    // MARK: - Actions
    @objc private func statusItemClicked() {
        // Click on icon toggles listening
        onToggleListening?()
    }

    @objc private func toggleListening() {
        onToggleListening?()
    }

    @objc private func modeMenuItemClicked(_ sender: NSMenuItem) {
        guard let mode = sender.representedObject as? ConversationMode else { return }
        onModeSelected?(mode)
    }

    @objc private func voiceProfileClicked(_ sender: NSMenuItem) {
        let profileName = sender.title == "Default (Ryan)" ? nil : sender.title
        onVoiceProfileSelected?(profileName)
    }

    @objc private func openSettings() {
        onOpenSettings?()
    }

    @objc private func quit() {
        onQuit?()
    }

    // MARK: - Public Methods

    /// Update the status bar icon based on state
    func updateState(_ state: JarvisState) {
        DispatchQueue.main.async { [weak self] in
            guard let button = self?.statusItem.button else { return }

            let (iconName, tintColor) = self?.iconForState(state) ?? ("mic.slash", nil)
            button.image = NSImage(systemSymbolName: iconName, accessibilityDescription: "Jarvis")

            if let color = tintColor {
                button.contentTintColor = color
            } else {
                button.contentTintColor = nil
            }

            // Update state menu item
            let stateText: String
            switch state {
            case .idle:
                stateText = "Status: Idle"
            case .listening:
                stateText = "Status: Listening..."
            case .processing:
                stateText = "Status: Processing..."
            case .speaking:
                stateText = "Status: Speaking..."
            case .error(let message):
                stateText = "Status: Error - \(message)"
            }
            self?.stateMenuItem?.title = stateText

            // Update toggle menu item
            if let toggleItem = self?.menu.item(withTitle: "Start Listening") ?? self?.menu.item(withTitle: "Stop Listening") {
                toggleItem.title = state == .listening ? "Stop Listening" : "Start Listening"
            }
        }
    }

    private func iconForState(_ state: JarvisState) -> (String, NSColor?) {
        switch state {
        case .idle:
            return ("mic.slash", nil)
        case .listening:
            return ("mic.fill", .systemGreen)
        case .processing:
            return ("brain", .systemBlue)
        case .speaking:
            return ("speaker.wave.3.fill", .systemOrange)
        case .error:
            return ("exclamationmark.triangle", .systemRed)
        }
    }

    /// Update the current mode indicator
    func updateMode(_ mode: ConversationMode) {
        DispatchQueue.main.async { [weak self] in
            for (itemMode, item) in self?.modeMenuItems ?? [:] {
                item.state = (itemMode == mode) ? .on : .off
            }
        }
    }

    /// Update server status
    func updateServerStatus(name: String, isOnline: Bool) {
        DispatchQueue.main.async { [weak self] in
            if let item = self?.serverMenuItems[name] {
                let status = isOnline ? "Online" : "Offline"
                let emoji = isOnline ? "🟢" : "🔴"
                item.title = "\(emoji) \(name): \(status)"
            }
        }
    }

    /// Add voice profiles to menu
    func updateVoiceProfiles(_ profiles: [String]) {
        DispatchQueue.main.async { [weak self] in
            guard let voiceMenuItem = self?.menu.item(withTitle: "Voice"),
                  let voiceMenu = voiceMenuItem.submenu else { return }

            // Remove all except default
            while voiceMenu.items.count > 1 {
                voiceMenu.removeItem(at: 1)
            }

            // Add separator if profiles exist
            if !profiles.isEmpty {
                voiceMenu.addItem(NSMenuItem.separator())
            }

            // Add profile items
            for profile in profiles {
                let item = NSMenuItem(
                    title: profile,
                    action: #selector(self?.voiceProfileClicked(_:)),
                    keyEquivalent: ""
                )
                item.target = self
                voiceMenu.addItem(item)
            }
        }
    }
}
