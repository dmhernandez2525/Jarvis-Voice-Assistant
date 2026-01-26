import Foundation

/// Represents a Home Assistant device/entity
struct HADevice: Codable {
    let entityId: String
    let friendlyName: String
    let domain: String
    let state: String
    let isOn: Bool

    enum CodingKeys: String, CodingKey {
        case entityId = "entity_id"
        case friendlyName = "friendly_name"
        case domain
        case state
        case isOn = "is_on"
    }
}

/// Result of a smart home command
struct SmartHomeResult: Codable {
    let success: Bool
    let isSmartHome: Bool
    let message: String
    let action: String?
    let entities: [[String: Any]]?

    enum CodingKeys: String, CodingKey {
        case success
        case isSmartHome = "is_smart_home"
        case message
        case action
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        success = try container.decode(Bool.self, forKey: .success)
        isSmartHome = try container.decodeIfPresent(Bool.self, forKey: .isSmartHome) ?? false
        message = try container.decode(String.self, forKey: .message)
        action = try container.decodeIfPresent(String.self, forKey: .action)
        entities = nil // Entities are parsed separately if needed
    }
}

/// Client for Home Assistant integration via the orchestrator
class HomeAssistantClient {
    // MARK: - Properties
    private let orchestratorURL: URL
    private let session: URLSession

    // MARK: - Initialization
    init(orchestratorHost: String = "127.0.0.1", orchestratorPort: Int = 5000) {
        guard let url = URL(string: "http://\(orchestratorHost):\(orchestratorPort)") else {
            preconditionFailure("Invalid orchestrator URL")
        }
        self.orchestratorURL = url

        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        config.timeoutIntervalForResource = 60
        self.session = URLSession(configuration: config)
    }

    // MARK: - Public Methods

    /// Check if Home Assistant is connected and healthy
    func checkHealth() async throws -> Bool {
        let url = orchestratorURL.appendingPathComponent("/smart_home/health")
        let (data, response) = try await session.data(from: url)

        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            return false
        }

        let json = try JSONSerialization.jsonObject(with: data) as? [String: Any]
        return json?["connected"] as? Bool ?? false
    }

    /// Get list of Home Assistant devices
    func getDevices(domain: String? = nil) async throws -> [HADevice] {
        var urlComponents = URLComponents(url: orchestratorURL.appendingPathComponent("/smart_home/devices"), resolvingAgainstBaseURL: false)

        if let domain = domain {
            urlComponents?.queryItems = [URLQueryItem(name: "domain", value: domain)]
        }

        guard let url = urlComponents?.url else {
            throw HomeAssistantError.invalidURL
        }

        let (data, response) = try await session.data(from: url)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw HomeAssistantError.invalidResponse
        }

        if httpResponse.statusCode == 400 {
            throw HomeAssistantError.notEnabled
        }

        guard httpResponse.statusCode == 200 else {
            throw HomeAssistantError.requestFailed(statusCode: httpResponse.statusCode)
        }

        struct DevicesResponse: Codable {
            let devices: [HADevice]
            let count: Int
        }

        let devicesResponse = try JSONDecoder().decode(DevicesResponse.self, from: data)
        return devicesResponse.devices
    }

    /// Process a smart home command (natural language)
    func processCommand(_ command: String) async throws -> SmartHomeResult {
        let url = orchestratorURL.appendingPathComponent("/smart_home")

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let body = ["command": command]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw HomeAssistantError.invalidResponse
        }

        if httpResponse.statusCode == 400 {
            let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
            let error = json?["error"] as? String ?? "Bad request"
            throw HomeAssistantError.commandFailed(error)
        }

        if httpResponse.statusCode == 401 {
            throw HomeAssistantError.notConfigured
        }

        guard httpResponse.statusCode == 200 else {
            throw HomeAssistantError.requestFailed(statusCode: httpResponse.statusCode)
        }

        return try JSONDecoder().decode(SmartHomeResult.self, from: data)
    }

    /// Turn on a device
    func turnOn(entityId: String) async throws -> Bool {
        return try await processCommand("turn on \(entityId)").success
    }

    /// Turn off a device
    func turnOff(entityId: String) async throws -> Bool {
        return try await processCommand("turn off \(entityId)").success
    }

    /// Toggle a device
    func toggle(entityId: String) async throws -> Bool {
        return try await processCommand("toggle \(entityId)").success
    }
}

// MARK: - Errors

enum HomeAssistantError: LocalizedError {
    case notEnabled
    case notConfigured
    case invalidURL
    case invalidResponse
    case requestFailed(statusCode: Int)
    case commandFailed(String)

    var errorDescription: String? {
        switch self {
        case .notEnabled:
            return "Home Assistant integration is not enabled"
        case .notConfigured:
            return "Home Assistant token not configured"
        case .invalidURL:
            return "Invalid URL"
        case .invalidResponse:
            return "Invalid response from server"
        case .requestFailed(let statusCode):
            return "Request failed with status code \(statusCode)"
        case .commandFailed(let message):
            return message
        }
    }
}
