import Cocoa
import HotKey
import Carbon.HIToolbox

/// Manages global hotkeys for Jarvis
class HotKeyManager {
    // MARK: - Properties
    private var hotKey: HotKey?

    var onHotKeyPressed: (() -> Void)?

    // MARK: - Initialization
    init() {}

    // MARK: - Setup

    /// Register the default hotkey (Option + Space)
    func registerDefaultHotKey() {
        registerHotKey(key: .space, modifiers: [.option])
    }

    /// Register a custom hotkey
    func registerHotKey(key: Key, modifiers: NSEvent.ModifierFlags) {
        // Unregister existing
        hotKey = nil

        // Create new hotkey
        hotKey = HotKey(key: key, modifiers: modifiers)
        hotKey?.keyDownHandler = { [weak self] in
            self?.onHotKeyPressed?()
        }
    }

    /// Unregister the current hotkey
    func unregisterHotKey() {
        hotKey = nil
    }

    // MARK: - Presets

    /// Common hotkey configurations
    static let presets: [(name: String, key: Key, modifiers: NSEvent.ModifierFlags)] = [
        ("Option + Space", .space, [.option]),
        ("Control + Space", .space, [.control]),
        ("Command + Shift + J", .j, [.command, .shift]),
        ("F12", .f12, []),
    ]
}
