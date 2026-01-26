import Foundation
import WebSocketKit
import NIOCore
import NIOPosix
import NIOSSL

class PersonaPlexClient {
    // MARK: - Properties
    var onAudioReceived: ((Data) -> Void)?
    var onTranscriptionReceived: ((String) -> Void)?
    var onResponseReceived: ((String) -> Void)?
    /// Called with accumulated text for partial updates (streaming display)
    var onPartialResponse: ((String) -> Void)?
    var onStateChanged: ((PersonaPlexState) -> Void)?
    var onError: ((Error) -> Void)?

    private let host: String
    private let port: Int
    private let useSSL: Bool
    private var webSocket: WebSocket?
    private var eventLoopGroup: EventLoopGroup?

    private(set) var isConnected = false
    private(set) var currentState: PersonaPlexState = .disconnected

    /// Buffer to accumulate partial text responses
    private var responseBuffer = ""

    // MARK: - State
    enum PersonaPlexState: String {
        case disconnected
        case connecting
        case connected
        case listening
        case processing
        case speaking
        case error
        case user_speaking    // User is talking
        case assistant_speaking  // Assistant is responding
        case thinking         // Ollama is processing complex query
    }

    // MARK: - Initialization
    // Connect to proxy on 8999 instead of PersonaPlex directly on 8998
    // The proxy handles opus encoding/decoding and protocol translation
    init(host: String = "localhost", port: Int = 8999, useSSL: Bool = false) {
        self.host = host
        self.port = port
        self.useSSL = useSSL
    }

    deinit {
        disconnect()
    }

    // MARK: - Connection
    func connect(textPrompt: String = "", voicePrompt: String = "") async throws {
        guard !isConnected else { return }

        setState(.connecting)
        logInfo("Connecting to PersonaPlex at \(host):\(port) (SSL: \(useSSL))", category: .network)

        eventLoopGroup = MultiThreadedEventLoopGroup(numberOfThreads: 1)
        guard let group = eventLoopGroup else {
            setState(.error)
            throw PersonaPlexError.connectionFailed
        }

        let promise = group.next().makePromise(of: Void.self)
        let scheme = useSSL ? "wss" : "ws"

        // Connect to proxy which handles the PersonaPlex protocol
        let urlString = "\(scheme)://\(host):\(port)/ws"
        logDebug("PersonaPlex proxy URL: \(urlString)", category: .network)

        // Configure WebSocket client
        var configuration = WebSocketClient.Configuration()
        if useSSL {
            // Allow self-signed certificates for local development
            var tlsConfig = TLSConfiguration.makeClientConfiguration()
            tlsConfig.certificateVerification = .none
            configuration.tlsConfiguration = tlsConfig
        }

        WebSocket.connect(
            to: urlString,
            configuration: configuration,
            on: group
        ) { [weak self] ws in
            self?.webSocket = ws
            self?.isConnected = true
            self?.setState(.connected)
            self?.setupWebSocketHandlers(ws)
            logInfo("Connected to PersonaPlex successfully", category: .network)
            promise.succeed(())
        }.whenFailure { [weak self] error in
            self?.setState(.error)
            logError("Failed to connect to PersonaPlex", error: error)
            promise.fail(error)
        }

        try await promise.futureResult.get()
    }

    /// Callback for state changes with optional detail message
    var onStateChangedWithDetail: ((PersonaPlexState, String?) -> Void)?

    private func setState(_ state: PersonaPlexState, detail: String? = nil) {
        currentState = state
        onStateChanged?(state)
        onStateChangedWithDetail?(state, detail)
    }

    func disconnect() {
        guard isConnected || webSocket != nil else { return }

        logInfo("Disconnecting from PersonaPlex", category: .network)
        isConnected = false
        _ = webSocket?.close()
        webSocket = nil
        try? eventLoopGroup?.syncShutdownGracefully()
        eventLoopGroup = nil
        setState(.disconnected)
    }

    private var binaryReceiveCount = 0

    private func setupWebSocketHandlers(_ ws: WebSocket) {
        logInfo("Setting up WebSocket handlers", category: .network)

        // Handle binary messages (audio)
        ws.onBinary { [weak self] ws, buffer in
            guard let self = self else { return }
            let data = Data(buffer: buffer)
            self.binaryReceiveCount += 1
            if self.binaryReceiveCount % 50 == 0 {
                logDebug("PersonaPlex received audio: chunk #\(self.binaryReceiveCount), \(data.count) bytes", category: .audio)
            }
            self.onAudioReceived?(data)
        }

        // Handle text messages (transcriptions, responses)
        ws.onText { [weak self] ws, text in
            logDebug("PersonaPlex received text message: \(text.prefix(200))", category: .network)
            self?.handleTextMessage(text)
        }

        // Handle close
        ws.onClose.whenComplete { [weak self] result in
            logInfo("PersonaPlex WebSocket closed: \(result)", category: .network)
            self?.isConnected = false
            self?.setState(.disconnected)
        }
    }

    private func handleTextMessage(_ text: String) {
        // Parse JSON message from PersonaPlex
        guard let data = text.data(using: .utf8),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            logDebug("Received non-JSON message from PersonaPlex: \(text.prefix(100))", category: .network)
            return
        }

        if let type = json["type"] as? String {
            switch type {
            case "transcription":
                if let content = json["text"] as? String {
                    logDebug("PersonaPlex transcription: \(content)", category: .audio)
                    onTranscriptionReceived?(content)
                }
            case "response":
                if let content = json["text"] as? String {
                    let isPartial = json["partial"] as? Bool ?? true

                    if isPartial {
                        // Accumulate partial response
                        responseBuffer += content
                        logDebug("PersonaPlex partial: '\(content)' (buffer: \(responseBuffer.count) chars)", category: .audio)
                        // Send accumulated text for streaming display
                        onPartialResponse?(responseBuffer)
                    } else {
                        // Complete response - use the full text from message
                        let finalText = content.isEmpty ? responseBuffer : content
                        logDebug("PersonaPlex complete: \(finalText.prefix(100))", category: .audio)
                        onResponseReceived?(finalText)
                        responseBuffer = ""
                    }
                }
            case "state":
                if let stateStr = json["state"] as? String,
                   let state = PersonaPlexState(rawValue: stateStr) {
                    let detail = json["detail"] as? String
                    setState(state, detail: detail)
                }
            case "error":
                if let message = json["message"] as? String {
                    logError("PersonaPlex error: \(message)")
                    onError?(PersonaPlexError.serverError(message))
                }
            case "backchannel":
                // Back-channel responses (uh-huh, hmm, etc.) - treated as responses
                if let content = json["text"] as? String {
                    logDebug("PersonaPlex backchannel: \(content)", category: .audio)
                    onResponseReceived?(content)
                }
            default:
                logDebug("Unknown PersonaPlex message type: \(type)", category: .network)
            }
        }
    }

    /// Clear the response buffer (call when starting new conversation)
    func clearResponseBuffer() {
        responseBuffer = ""
    }

    // MARK: - Sending Data
    private var sendCount = 0

    func sendAudio(_ audioData: Data) async throws {
        guard isConnected, let ws = webSocket else {
            logWarning("Cannot send audio: not connected (isConnected=\(isConnected), ws=\(webSocket != nil))", category: .network)
            throw PersonaPlexError.notConnected
        }

        sendCount += 1
        if sendCount % 50 == 0 {
            logInfo("PersonaPlex sendAudio: chunk #\(sendCount), \(audioData.count) bytes", category: .network)
        }

        let buffer = ByteBuffer(data: audioData)
        try await ws.send(raw: buffer.readableBytesView, opcode: .binary)
    }

    func sendConfig(persona: String) async throws {
        guard isConnected, let ws = webSocket else {
            throw PersonaPlexError.notConnected
        }

        let config: [String: Any] = [
            "type": "config",
            "persona": persona
        ]

        if let data = try? JSONSerialization.data(withJSONObject: config),
           let text = String(data: data, encoding: .utf8) {
            try await ws.send(text)
        }
    }
}

// MARK: - Errors
enum PersonaPlexError: Error, LocalizedError {
    case connectionFailed
    case notConnected
    case sendFailed
    case serverNotRunning
    case serverError(String)
    case timeout

    var errorDescription: String? {
        switch self {
        case .connectionFailed:
            return "Failed to connect to PersonaPlex server"
        case .notConnected:
            return "Not connected to PersonaPlex server"
        case .sendFailed:
            return "Failed to send data to PersonaPlex"
        case .serverNotRunning:
            return "PersonaPlex server is not running. Please start it with ./run_personaplex.sh"
        case .serverError(let message):
            return "PersonaPlex server error: \(message)"
        case .timeout:
            return "PersonaPlex request timed out"
        }
    }
}
