import Foundation
import AVFoundation

protocol JarvisCoreDelegate: AnyObject {
    func jarvisCore(_ core: JarvisCore, didChangeState state: JarvisState)
    func jarvisCore(_ core: JarvisCore, didReceiveTranscription text: String)
    func jarvisCore(_ core: JarvisCore, didReceiveResponse text: String)
    func jarvisCore(_ core: JarvisCore, didEncounterError error: Error)
}

class JarvisCore {
    // MARK: - Properties
    weak var delegate: JarvisCoreDelegate?

    private(set) var isActive = false
    private(set) var currentMode: ConversationMode = .hybrid

    private let audioPipeline: AudioPipeline
    private let personaPlexClient: PersonaPlexClient
    private let orchestratorClient: OrchestratorClient
    private let voiceForgeClient: VoiceForgeClient

    private var conversationTask: Task<Void, Never>?

    // MARK: - Initialization
    init() {
        self.audioPipeline = AudioPipeline()
        self.personaPlexClient = PersonaPlexClient()
        self.orchestratorClient = OrchestratorClient()
        self.voiceForgeClient = VoiceForgeClient()

        setupCallbacks()
    }

    private func setupCallbacks() {
        // Handle audio from PersonaPlex
        personaPlexClient.onAudioReceived = { [weak self] audioData in
            self?.audioPipeline.playAudio(audioData)
        }

        // Handle transcriptions
        personaPlexClient.onTranscriptionReceived = { [weak self] text in
            guard let self = self else { return }
            self.delegate?.jarvisCore(self, didReceiveTranscription: text)
        }

        // Handle responses
        personaPlexClient.onResponseReceived = { [weak self] text in
            guard let self = self else { return }
            self.delegate?.jarvisCore(self, didReceiveResponse: text)
        }

        // Handle audio capture
        audioPipeline.onAudioCaptured = { [weak self] audioData in
            guard let self = self else { return }
            Task {
                await self.processAudio(audioData)
            }
        }
    }

    // MARK: - Conversation Control
    func startConversation() async throws {
        guard !isActive else { return }

        delegate?.jarvisCore(self, didChangeState: .listening)

        switch currentMode {
        case .fullDuplex:
            try await startFullDuplexMode()
        case .hybrid:
            try await startHybridMode()
        case .legacy:
            try await startLegacyMode()
        }

        isActive = true
    }

    func stopConversation() {
        guard isActive else { return }

        conversationTask?.cancel()
        conversationTask = nil

        personaPlexClient.disconnect()
        audioPipeline.stopCapture()

        isActive = false
        delegate?.jarvisCore(self, didChangeState: .idle)
    }

    func setMode(_ mode: ConversationMode) {
        let wasActive = isActive
        if wasActive {
            stopConversation()
        }

        currentMode = mode

        if wasActive {
            Task {
                try? await startConversation()
            }
        }
    }

    // MARK: - Mode-Specific Start Methods
    private func startFullDuplexMode() async throws {
        // Connect to PersonaPlex WebSocket
        try await personaPlexClient.connect()

        // Start audio capture
        try audioPipeline.startCapture()

        // Stream audio directly to PersonaPlex
        conversationTask = Task {
            while !Task.isCancelled && isActive {
                // PersonaPlex handles the full duplex loop
                try? await Task.sleep(nanoseconds: 100_000_000) // 100ms
            }
        }
    }

    private func startHybridMode() async throws {
        // Connect to PersonaPlex for simple queries
        try await personaPlexClient.connect()

        // Start audio capture
        try audioPipeline.startCapture()

        // Hybrid mode: PersonaPlex for simple, Ollama for complex
        conversationTask = Task {
            while !Task.isCancelled && isActive {
                try? await Task.sleep(nanoseconds: 100_000_000) // 100ms
            }
        }
    }

    private func startLegacyMode() async throws {
        // Legacy mode: Traditional STT -> LLM -> TTS pipeline
        try audioPipeline.startCapture()

        conversationTask = Task {
            while !Task.isCancelled && isActive {
                try? await Task.sleep(nanoseconds: 100_000_000) // 100ms
            }
        }
    }

    // MARK: - Audio Processing
    private func processAudio(_ audioData: Data) async {
        switch currentMode {
        case .fullDuplex:
            // Stream directly to PersonaPlex
            try? await personaPlexClient.sendAudio(audioData)

        case .hybrid:
            // Stream to PersonaPlex, but route complex queries to Ollama
            try? await personaPlexClient.sendAudio(audioData)

        case .legacy:
            // Send to orchestrator for traditional processing
            await processWithOrchestrator(audioData)
        }
    }

    private func processWithOrchestrator(_ audioData: Data) async {
        delegate?.jarvisCore(self, didChangeState: .processing)

        do {
            // Send audio to orchestrator
            let response = try await orchestratorClient.processAudio(audioData)

            delegate?.jarvisCore(self, didReceiveTranscription: response.transcription)
            delegate?.jarvisCore(self, didReceiveResponse: response.response)

            // Generate speech with VoiceForge
            delegate?.jarvisCore(self, didChangeState: .speaking)
            let audioURL = try await voiceForgeClient.generateSpeech(text: response.response)
            audioPipeline.playAudioFile(audioURL)

            delegate?.jarvisCore(self, didChangeState: .listening)
        } catch {
            delegate?.jarvisCore(self, didEncounterError: error)
        }
    }
}
