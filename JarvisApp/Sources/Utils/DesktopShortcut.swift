import Foundation
import AppKit

/// Manages desktop shortcut creation for JarvisApp
class DesktopShortcut {
    // MARK: - Properties
    private static let shortcutCreatedKey = "JarvisDesktopShortcutCreated"
    private static let appName = "Jarvis"

    // MARK: - Public Methods

    /// Create desktop shortcut on first run
    static func createIfNeeded() {
        // Check if already created
        if UserDefaults.standard.bool(forKey: shortcutCreatedKey) {
            return
        }

        // Get the executable path (works for both debug and release builds)
        guard let executablePath = Bundle.main.executablePath else {
            print("Could not determine executable path")
            return
        }

        let appPath = Bundle.main.bundlePath

        // Create alias on desktop
        let desktopPath = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Desktop")
            .appendingPathComponent("\(appName).app")

        do {
            // For debug builds, create a shell script launcher instead of alias
            if appPath.contains(".build") {
                try createLauncherScript(executablePath: executablePath, desktopPath: desktopPath)
            } else {
                try createAlias(from: executablePath, to: desktopPath.path)
            }

            // Mark as created
            UserDefaults.standard.set(true, forKey: shortcutCreatedKey)
            print("Desktop shortcut created: \(desktopPath.path)")

        } catch {
            print("Failed to create desktop shortcut: \(error)")
        }
    }

    /// Remove desktop shortcut
    static func remove() {
        let desktopPath = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Desktop")
            .appendingPathComponent("\(appName).app")

        try? FileManager.default.removeItem(at: desktopPath)
        UserDefaults.standard.set(false, forKey: shortcutCreatedKey)
    }

    /// Reset first-run flag (for testing)
    static func resetFirstRun() {
        UserDefaults.standard.set(false, forKey: shortcutCreatedKey)
    }

    // MARK: - Private Methods

    private static func createAlias(from source: String, to destination: String) throws {
        let sourceURL = URL(fileURLWithPath: source)
        let destinationURL = URL(fileURLWithPath: destination)

        // Remove existing if present
        try? FileManager.default.removeItem(at: destinationURL)

        // Create alias using NSWorkspace
        let data = try sourceURL.bookmarkData(
            options: .suitableForBookmarkFile,
            includingResourceValuesForKeys: nil,
            relativeTo: nil
        )

        try URL.writeBookmarkData(data, to: destinationURL)
    }

    private static func createLauncherScript(executablePath: String, desktopPath: URL) throws {
        // For development builds, create a simple app bundle wrapper
        let appBundlePath = desktopPath

        // Create app bundle structure
        let contentsPath = appBundlePath.appendingPathComponent("Contents")
        let macOSPath = contentsPath.appendingPathComponent("MacOS")
        let resourcesPath = contentsPath.appendingPathComponent("Resources")

        try FileManager.default.createDirectory(at: macOSPath, withIntermediateDirectories: true)
        try FileManager.default.createDirectory(at: resourcesPath, withIntermediateDirectories: true)

        // Create launcher script
        let launcherPath = macOSPath.appendingPathComponent("Jarvis")
        let launcherContent = """
        #!/bin/bash
        exec "\(executablePath)"
        """
        try launcherContent.write(to: launcherPath, atomically: true, encoding: .utf8)

        // Make executable
        try FileManager.default.setAttributes(
            [.posixPermissions: 0o755],
            ofItemAtPath: launcherPath.path
        )

        // Create Info.plist
        let plistPath = contentsPath.appendingPathComponent("Info.plist")
        let plistContent = """
        <?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
        <plist version="1.0">
        <dict>
            <key>CFBundleExecutable</key>
            <string>Jarvis</string>
            <key>CFBundleIdentifier</key>
            <string>com.jarvis.voiceassistant</string>
            <key>CFBundleName</key>
            <string>Jarvis</string>
            <key>CFBundleDisplayName</key>
            <string>Jarvis Voice Assistant</string>
            <key>CFBundleVersion</key>
            <string>1.0</string>
            <key>CFBundleShortVersionString</key>
            <string>1.0</string>
            <key>LSUIElement</key>
            <true/>
            <key>NSHighResolutionCapable</key>
            <true/>
            <key>CFBundleIconFile</key>
            <string>AppIcon</string>
        </dict>
        </plist>
        """
        try plistContent.write(to: plistPath, atomically: true, encoding: .utf8)

        // Copy icon if available - check multiple locations
        let iconDest = resourcesPath.appendingPathComponent("AppIcon.icns")
        let possibleIconPaths = [
            // Relative to executable (debug builds)
            URL(fileURLWithPath: executablePath)
                .deletingLastPathComponent()
                .deletingLastPathComponent()
                .deletingLastPathComponent()
                .appendingPathComponent("Resources")
                .appendingPathComponent("JarvisIcon.icns"),
            // JarvisApp/Resources directory
            URL(fileURLWithPath: executablePath)
                .deletingLastPathComponent()
                .deletingLastPathComponent()
                .deletingLastPathComponent()
                .deletingLastPathComponent()
                .appendingPathComponent("JarvisApp")
                .appendingPathComponent("Resources")
                .appendingPathComponent("JarvisIcon.icns"),
            // Current working directory
            URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
                .appendingPathComponent("Resources")
                .appendingPathComponent("JarvisIcon.icns")
        ]

        for iconSource in possibleIconPaths {
            if FileManager.default.fileExists(atPath: iconSource.path) {
                try? FileManager.default.copyItem(at: iconSource, to: iconDest)
                break
            }
        }
    }
}
