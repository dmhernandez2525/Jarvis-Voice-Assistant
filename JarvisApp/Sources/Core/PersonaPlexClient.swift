import Foundation
import WebSocketKit
import NIOCore
import NIOPosix

class PersonaPlexClient {
    // MARK: - Properties
    var onAudioReceived: ((Data) -> Void)?
    var onTranscriptionReceived: ((String) -> Void)?
    var onResponseReceived: ((String) -> Void)?

    private let host: String
    private let port: Int
    private var webSocket: WebSocket?
    private var eventLoopGroup: EventLoopGroup?

    private var isConnected = false

    // MARK: - Initialization
    init(host: String = "localhost", port: Int = 8998) {
        self.host = host
        self.port = port
    }

    deinit {
        disconnect()
    }

    // MARK: - Connection
    func connect() async throws {
        guard !isConnected else { return }

        eventLoopGroup = MultiThreadedEventLoopGroup(numberOfThreads: 1)
        guard let group = eventLoopGroup else {
            throw PersonaPlexError.connectionFailed
        }

        let promise = group.next().makePromise(of: Void.self)

        WebSocket.connect(
            to: "ws://\(host):\(port)/ws",
            on: group
        ) { [weak self] ws in
            self?.webSocket = ws
            self?.isConnected = true
            self?.setupWebSocketHandlers(ws)
            promise.succeed(())
        }.whenFailure { error in
            promise.fail(error)
        }

        try await promise.futureResult.get()
    }

    func disconnect() {
        isConnected = false
        _ = webSocket?.close()
        webSocket = nil
        try? eventLoopGroup?.syncShutdownGracefully()
        eventLoopGroup = nil
    }

    private func setupWebSocketHandlers(_ ws: WebSocket) {
        // Handle binary messages (audio)
        ws.onBinary { [weak self] ws, buffer in
            let data = Data(buffer: buffer)
            self?.onAudioReceived?(data)
        }

        // Handle text messages (transcriptions, responses)
        ws.onText { [weak self] ws, text in
            self?.handleTextMessage(text)
        }

        // Handle close
        ws.onClose.whenComplete { [weak self] _ in
            self?.isConnected = false
        }
    }

    private func handleTextMessage(_ text: String) {
        // Parse JSON message from PersonaPlex
        guard let data = text.data(using: .utf8),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            return
        }

        if let type = json["type"] as? String {
            switch type {
            case "transcription":
                if let content = json["text"] as? String {
                    onTranscriptionReceived?(content)
                }
            case "response":
                if let content = json["text"] as? String {
                    onResponseReceived?(content)
                }
            default:
                break
            }
        }
    }

    // MARK: - Sending Data
    func sendAudio(_ audioData: Data) async throws {
        guard isConnected, let ws = webSocket else {
            throw PersonaPlexError.notConnected
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

    var errorDescription: String? {
        switch self {
        case .connectionFailed:
            return "Failed to connect to PersonaPlex server"
        case .notConnected:
            return "Not connected to PersonaPlex server"
        case .sendFailed:
            return "Failed to send data to PersonaPlex"
        }
    }
}
