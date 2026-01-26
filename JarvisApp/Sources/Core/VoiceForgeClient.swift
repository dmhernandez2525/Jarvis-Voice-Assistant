import Foundation

class VoiceForgeClient {
    // MARK: - Properties
    private let baseURL: URL
    private var activeVoiceProfile: VoiceProfile?

    // MARK: - Initialization
    init(host: String = "localhost", port: Int = 8765) {
        self.baseURL = URL(string: "http://\(host):\(port)")!
    }

    // MARK: - Health Check
    func checkHealth() async throws -> Bool {
        let url = baseURL.appendingPathComponent("health")
        let (_, response) = try await URLSession.shared.data(from: url)

        guard let httpResponse = response as? HTTPURLResponse else {
            return false
        }

        return httpResponse.statusCode == 200
    }

    // MARK: - Voice Profile Management
    func setVoiceProfile(_ profile: VoiceProfile) {
        self.activeVoiceProfile = profile
    }

    func clearVoiceProfile() {
        self.activeVoiceProfile = nil
    }

    // MARK: - Speech Generation
    func generateSpeech(text: String, language: String = "English") async throws -> URL {
        if let profile = activeVoiceProfile {
            return try await generateClonedSpeech(text: text, profile: profile)
        } else {
            return try await generateCustomSpeech(text: text, speaker: "Ryan", language: language)
        }
    }

    func generateClonedSpeech(text: String, profile: VoiceProfile) async throws -> URL {
        let url = baseURL.appendingPathComponent("generate/clone")

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let body: [String: Any] = [
            "text": text,
            "language": profile.language,
            "ref_audio_path": profile.referenceAudioPath,
            "ref_text": profile.referenceText
        ]

        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw VoiceForgeError.requestFailed
        }

        let result = try JSONDecoder().decode(GenerateResponse.self, from: data)

        guard let outputPath = result.outputPath else {
            throw VoiceForgeError.noOutputPath
        }

        return URL(fileURLWithPath: outputPath)
    }

    func generateCustomSpeech(text: String, speaker: String, language: String = "English", instruct: String? = nil) async throws -> URL {
        let url = baseURL.appendingPathComponent("generate/custom")

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        var body: [String: Any] = [
            "text": text,
            "language": language,
            "speaker": speaker
        ]

        if let instruct = instruct {
            body["instruct"] = instruct
        }

        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw VoiceForgeError.requestFailed
        }

        let result = try JSONDecoder().decode(GenerateResponse.self, from: data)

        guard let outputPath = result.outputPath else {
            throw VoiceForgeError.noOutputPath
        }

        return URL(fileURLWithPath: outputPath)
    }

    func generateDesignedVoice(text: String, description: String, language: String = "English") async throws -> URL {
        let url = baseURL.appendingPathComponent("generate/design")

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let body: [String: Any] = [
            "text": text,
            "language": language,
            "instruct": description
        ]

        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw VoiceForgeError.requestFailed
        }

        let result = try JSONDecoder().decode(GenerateResponse.self, from: data)

        guard let outputPath = result.outputPath else {
            throw VoiceForgeError.noOutputPath
        }

        return URL(fileURLWithPath: outputPath)
    }

    // MARK: - Available Options
    func getAvailableSpeakers() async throws -> [String] {
        let url = baseURL.appendingPathComponent("speakers")
        let (data, _) = try await URLSession.shared.data(from: url)
        let result = try JSONDecoder().decode(SpeakersResponse.self, from: data)
        return result.speakers
    }

    func getAvailableLanguages() async throws -> [String] {
        let url = baseURL.appendingPathComponent("languages")
        let (data, _) = try await URLSession.shared.data(from: url)
        let result = try JSONDecoder().decode(LanguagesResponse.self, from: data)
        return result.languages
    }
}

// MARK: - Response Models
struct GenerateResponse: Codable {
    let status: String
    let outputPath: String?
    let sampleRate: Int?

    enum CodingKeys: String, CodingKey {
        case status
        case outputPath = "output_path"
        case sampleRate = "sample_rate"
    }
}

struct SpeakersResponse: Codable {
    let speakers: [String]
}

struct LanguagesResponse: Codable {
    let languages: [String]
}

// MARK: - Voice Profile
struct VoiceProfile: Codable {
    let name: String
    let referenceAudioPath: String
    let referenceText: String
    let language: String

    init(name: String, referenceAudioPath: String, referenceText: String, language: String = "English") {
        self.name = name
        self.referenceAudioPath = referenceAudioPath
        self.referenceText = referenceText
        self.language = language
    }
}

// MARK: - Errors
enum VoiceForgeError: Error, LocalizedError {
    case requestFailed
    case noOutputPath
    case serverNotAvailable

    var errorDescription: String? {
        switch self {
        case .requestFailed:
            return "VoiceForge request failed"
        case .noOutputPath:
            return "No output path in VoiceForge response"
        case .serverNotAvailable:
            return "VoiceForge server is not available"
        }
    }
}
