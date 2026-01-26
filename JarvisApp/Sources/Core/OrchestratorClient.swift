import Foundation

class OrchestratorClient {
    // MARK: - Properties
    private let baseURL: URL

    // MARK: - Initialization
    init(host: String = "localhost", port: Int = 5001) {
        guard let url = URL(string: "http://\(host):\(port)") else {
            preconditionFailure("Invalid Orchestrator URL: http://\(host):\(port)")
        }
        self.baseURL = url
    }

    // MARK: - Health Check
    func checkHealth() async throws -> HealthResponse {
        let url = baseURL.appendingPathComponent("health")
        let (data, response) = try await URLSession.shared.data(from: url)

        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw OrchestratorError.healthCheckFailed
        }

        return try JSONDecoder().decode(HealthResponse.self, from: data)
    }

    // MARK: - Audio Processing
    func processAudio(_ audioData: Data) async throws -> ProcessResponse {
        let url = baseURL.appendingPathComponent("query")

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("audio/wav", forHTTPHeaderField: "Content-Type")
        request.httpBody = audioData

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw OrchestratorError.processingFailed
        }

        return try JSONDecoder().decode(ProcessResponse.self, from: data)
    }

    // MARK: - Text Query (for testing)
    func processText(_ text: String) async throws -> ProcessResponse {
        let url = baseURL.appendingPathComponent("text_query")

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let body: [String: Any] = ["text": text]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw OrchestratorError.processingFailed
        }

        return try JSONDecoder().decode(ProcessResponse.self, from: data)
    }

    // MARK: - Mode Control
    func setMode(_ mode: ConversationMode) async throws {
        let url = baseURL.appendingPathComponent("mode")

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let body: [String: Any] = ["mode": mode.rawValue]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (_, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw OrchestratorError.modeChangeFailed
        }
    }
}

// MARK: - Response Models
struct HealthResponse: Codable {
    let status: String
    let whisperModel: String?
    let ollamaModel: String?
    let personaplexConnected: Bool?
    let voiceforgeConnected: Bool?

    enum CodingKeys: String, CodingKey {
        case status
        case whisperModel = "whisper_model"
        case ollamaModel = "ollama_model"
        case personaplexConnected = "personaplex_connected"
        case voiceforgeConnected = "voiceforge_connected"
    }
}

struct ProcessResponse: Codable {
    let transcription: String
    let response: String
    let processingTime: Double?
    let routedTo: String?

    enum CodingKeys: String, CodingKey {
        case transcription
        case response
        case processingTime = "processing_time"
        case routedTo = "routed_to"
    }
}

// MARK: - Errors
enum OrchestratorError: Error, LocalizedError {
    case healthCheckFailed
    case processingFailed
    case modeChangeFailed
    case serverNotAvailable

    var errorDescription: String? {
        switch self {
        case .healthCheckFailed:
            return "Orchestrator health check failed"
        case .processingFailed:
            return "Failed to process query"
        case .modeChangeFailed:
            return "Failed to change conversation mode"
        case .serverNotAvailable:
            return "Required servers are not available. Please ensure Ollama is running."
        }
    }
}
