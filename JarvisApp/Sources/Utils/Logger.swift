import Foundation
import os.log

/// Centralized logging system for JarvisApp
/// Logs to both Console.app (via os_log) and file for crash debugging
final class JarvisLogger {
    // MARK: - Singleton
    static let shared = JarvisLogger()

    // MARK: - Properties
    private let subsystem = "com.jarvis.voiceassistant"
    private let fileManager = FileManager.default
    private var logFileHandle: FileHandle?
    private let logQueue = DispatchQueue(label: "com.jarvis.logger", qos: .utility)
    private let dateFormatter: DateFormatter

    // OS Log categories
    private let generalLog: OSLog
    private let audioLog: OSLog
    private let networkLog: OSLog
    private let uiLog: OSLog
    private let errorLog: OSLog

    // MARK: - Log Levels
    enum Level: String {
        case debug = "DEBUG"
        case info = "INFO"
        case warning = "WARN"
        case error = "ERROR"
        case critical = "CRITICAL"

        var osLogType: OSLogType {
            switch self {
            case .debug: return .debug
            case .info: return .info
            case .warning: return .default
            case .error: return .error
            case .critical: return .fault
            }
        }
    }

    // MARK: - Categories
    enum Category: String {
        case general = "General"
        case audio = "Audio"
        case network = "Network"
        case ui = "UI"
        case error = "Error"
    }

    // MARK: - Initialization
    private init() {
        dateFormatter = DateFormatter()
        dateFormatter.dateFormat = "yyyy-MM-dd HH:mm:ss.SSS"

        // Initialize OS logs
        generalLog = OSLog(subsystem: subsystem, category: "General")
        audioLog = OSLog(subsystem: subsystem, category: "Audio")
        networkLog = OSLog(subsystem: subsystem, category: "Network")
        uiLog = OSLog(subsystem: subsystem, category: "UI")
        errorLog = OSLog(subsystem: subsystem, category: "Error")

        // Setup file logging
        setupFileLogging()

        // Log startup
        log(.info, category: .general, "JarvisApp Logger initialized")
        log(.info, category: .general, "Log file: \(logFilePath?.path ?? "None")")
    }

    // MARK: - File Logging Setup
    private var logDirectory: URL? {
        guard let appSupport = fileManager.urls(for: .applicationSupportDirectory, in: .userDomainMask).first else {
            return nil
        }
        return appSupport.appendingPathComponent("JarvisApp/Logs")
    }

    private var logFilePath: URL? {
        guard let dir = logDirectory else { return nil }
        let fileName = "jarvis_\(dateFormatter.string(from: Date()).replacingOccurrences(of: ":", with: "-").replacingOccurrences(of: " ", with: "_")).log"
        return dir.appendingPathComponent(fileName)
    }

    private func setupFileLogging() {
        guard let logDir = logDirectory, let logPath = logFilePath else {
            os_log("Failed to determine log directory", log: errorLog, type: .error)
            return
        }

        do {
            // Create logs directory
            try fileManager.createDirectory(at: logDir, withIntermediateDirectories: true)

            // Create log file
            if !fileManager.fileExists(atPath: logPath.path) {
                fileManager.createFile(atPath: logPath.path, contents: nil)
            }

            // Open file handle
            logFileHandle = try FileHandle(forWritingTo: logPath)
            logFileHandle?.seekToEndOfFile()

            // Write header
            let header = """
            ================================================================================
            JARVIS VOICE ASSISTANT LOG
            Started: \(dateFormatter.string(from: Date()))
            Version: 1.0
            OS: \(ProcessInfo.processInfo.operatingSystemVersionString)
            ================================================================================

            """
            if let data = header.data(using: .utf8) {
                logFileHandle?.write(data)
            }

            // Cleanup old logs (keep last 7 days)
            cleanupOldLogs()

        } catch {
            os_log("Failed to setup file logging: %{public}@", log: errorLog, type: .error, error.localizedDescription)
        }
    }

    private func cleanupOldLogs() {
        guard let logDir = logDirectory else { return }

        let cutoffDate = Calendar.current.date(byAdding: .day, value: -7, to: Date()) ?? Date()

        do {
            let files = try fileManager.contentsOfDirectory(at: logDir, includingPropertiesForKeys: [.creationDateKey])
            for file in files where file.pathExtension == "log" {
                if let attrs = try? fileManager.attributesOfItem(atPath: file.path),
                   let creationDate = attrs[.creationDate] as? Date,
                   creationDate < cutoffDate {
                    try? fileManager.removeItem(at: file)
                }
            }
        } catch {
            // Ignore cleanup errors
        }
    }

    // MARK: - Public Logging Methods

    /// Log a message with level and category
    func log(_ level: Level, category: Category = .general, _ message: String, file: String = #file, function: String = #function, line: Int = #line) {
        let timestamp = dateFormatter.string(from: Date())
        let fileName = (file as NSString).lastPathComponent
        let logMessage = "[\(timestamp)] [\(level.rawValue)] [\(category.rawValue)] [\(fileName):\(line)] \(function) - \(message)"

        // Log to OS Log (visible in Console.app)
        let osLog = osLogForCategory(category)
        os_log("%{public}@", log: osLog, type: level.osLogType, message)

        // Log to file
        logQueue.async { [weak self] in
            guard let self = self, let data = (logMessage + "\n").data(using: .utf8) else { return }
            self.logFileHandle?.write(data)
        }

        // Print to stdout in debug builds
        #if DEBUG
        print(logMessage)
        #endif
    }

    /// Log an error with optional Error object
    func logError(_ message: String, error: Error? = nil, file: String = #file, function: String = #function, line: Int = #line) {
        var fullMessage = message
        if let error = error {
            fullMessage += " | Error: \(error.localizedDescription)"
            if let nsError = error as NSError? {
                fullMessage += " | Domain: \(nsError.domain) Code: \(nsError.code)"
                if let underlying = nsError.userInfo[NSUnderlyingErrorKey] as? Error {
                    fullMessage += " | Underlying: \(underlying.localizedDescription)"
                }
            }
        }
        log(.error, category: .error, fullMessage, file: file, function: function, line: line)
    }

    /// Log a crash or critical failure
    func logCrash(_ message: String, file: String = #file, function: String = #function, line: Int = #line) {
        let crashMessage = """

        ********************************************************************************
        CRASH REPORT
        Time: \(dateFormatter.string(from: Date()))
        Location: \((file as NSString).lastPathComponent):\(line) \(function)
        Message: \(message)

        Stack Trace:
        \(Thread.callStackSymbols.joined(separator: "\n"))
        ********************************************************************************

        """

        log(.critical, category: .error, crashMessage, file: file, function: function, line: line)

        // Force flush to disk
        logQueue.sync {
            logFileHandle?.synchronizeFile()
        }
    }

    private func osLogForCategory(_ category: Category) -> OSLog {
        switch category {
        case .general: return generalLog
        case .audio: return audioLog
        case .network: return networkLog
        case .ui: return uiLog
        case .error: return errorLog
        }
    }

    // MARK: - Utility

    /// Get path to current log file
    var currentLogPath: String? {
        return logFilePath?.path
    }

    /// Get all log files
    func getAllLogFiles() -> [URL] {
        guard let logDir = logDirectory else { return [] }
        return (try? fileManager.contentsOfDirectory(at: logDir, includingPropertiesForKeys: nil)
            .filter { $0.pathExtension == "log" }
            .sorted { $0.lastPathComponent > $1.lastPathComponent }) ?? []
    }

    /// Flush logs to disk
    func flush() {
        logQueue.sync {
            logFileHandle?.synchronizeFile()
        }
    }

    deinit {
        log(.info, category: .general, "JarvisApp Logger shutting down")
        flush()
        try? logFileHandle?.close()
    }
}

// MARK: - Convenience Global Functions

/// Quick logging functions
func logDebug(_ message: String, category: JarvisLogger.Category = .general, file: String = #file, function: String = #function, line: Int = #line) {
    JarvisLogger.shared.log(.debug, category: category, message, file: file, function: function, line: line)
}

func logInfo(_ message: String, category: JarvisLogger.Category = .general, file: String = #file, function: String = #function, line: Int = #line) {
    JarvisLogger.shared.log(.info, category: category, message, file: file, function: function, line: line)
}

func logWarning(_ message: String, category: JarvisLogger.Category = .general, file: String = #file, function: String = #function, line: Int = #line) {
    JarvisLogger.shared.log(.warning, category: category, message, file: file, function: function, line: line)
}

func logError(_ message: String, error: Error? = nil, file: String = #file, function: String = #function, line: Int = #line) {
    JarvisLogger.shared.logError(message, error: error, file: file, function: function, line: line)
}

func logCrash(_ message: String, file: String = #file, function: String = #function, line: Int = #line) {
    JarvisLogger.shared.logCrash(message, file: file, function: function, line: line)
}
