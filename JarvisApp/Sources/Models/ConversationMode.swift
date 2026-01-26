import Foundation

/// Conversation modes for Jarvis voice assistant
enum ConversationMode: String, CaseIterable, Codable {
    case fullDuplex = "full_duplex"
    case hybrid = "hybrid"
    case legacy = "legacy"

    var displayName: String {
        switch self {
        case .fullDuplex:
            return "Full Duplex"
        case .hybrid:
            return "Hybrid"
        case .legacy:
            return "Legacy"
        }
    }

    var description: String {
        switch self {
        case .fullDuplex:
            return "PersonaPlex only - <500ms latency, natural conversation"
        case .hybrid:
            return "Smart routing between PersonaPlex and Ollama"
        case .legacy:
            return "Traditional STT -> LLM -> TTS pipeline"
        }
    }

    var icon: String {
        switch self {
        case .fullDuplex:
            return "bolt.fill"
        case .hybrid:
            return "arrow.triangle.branch"
        case .legacy:
            return "waveform"
        }
    }
}

/// Server status for health monitoring
enum ServerStatus: Equatable {
    case unknown
    case online
    case offline
    case error(String)

    var isOnline: Bool {
        if case .online = self {
            return true
        }
        return false
    }

    var displayName: String {
        switch self {
        case .unknown:
            return "Unknown"
        case .online:
            return "Online"
        case .offline:
            return "Offline"
        case .error(let message):
            return "Error: \(message)"
        }
    }
}

/// Jarvis state for UI updates
enum JarvisState: Equatable {
    case idle
    case listening
    case processing
    case speaking
    case error(String)

    var statusIconName: String {
        switch self {
        case .idle:
            return "mic.slash"
        case .listening:
            return "mic.fill"
        case .processing:
            return "brain"
        case .speaking:
            return "speaker.wave.3.fill"
        case .error:
            return "exclamationmark.triangle"
        }
    }
}
