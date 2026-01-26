import Foundation
import AVFoundation

protocol JarvisCoreDelegate: AnyObject {
    func jarvisCore(_ core: JarvisCore, didChangeState state: JarvisState)
    func jarvisCore(_ core: JarvisCore, didChangeState state: JarvisState, detail: String?)
    func jarvisCore(_ core: JarvisCore, didReceiveTranscription text: String)
    func jarvisCore(_ core: JarvisCore, didReceiveResponse text: String)
    func jarvisCore(_ core: JarvisCore, didReceivePartialResponse text: String)
    func jarvisCore(_ core: JarvisCore, didEncounterError error: Error)
    func jarvisCore(_ core: JarvisCore, didUpdateAudioLevel level: Float)
}

class JarvisCore {
    // MARK: - Properties
    weak var delegate: JarvisCoreDelegate?

    private(set) var isActive = false
    private(set) var currentMode: ConversationMode = .fullDuplex  // Default to PersonaPlex for best experience

    private let audioPipeline: AudioPipeline
    private let personaPlexClient: PersonaPlexClient
    private let orchestratorClient: OrchestratorClient
    private let voiceForgeClient: VoiceForgeClient

    private var conversationTask: Task<Void, Never>?

    // Audio buffer for Legacy mode (push-to-talk)
    private var audioBuffer = Data()
    private var isRecording = false

    // Service availability flags
    private var personaPlexAvailable = false
    private var ollamaAvailable = false

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

        // Handle complete responses
        personaPlexClient.onResponseReceived = { [weak self] text in
            guard let self = self else { return }
            self.delegate?.jarvisCore(self, didReceiveResponse: text)
        }

        // Handle partial/streaming responses
        personaPlexClient.onPartialResponse = { [weak self] text in
            guard let self = self else { return }
            self.delegate?.jarvisCore(self, didReceivePartialResponse: text)
        }

        // Handle PersonaPlex state changes
        personaPlexClient.onStateChanged = { [weak self] state in
            guard let self = self else { return }
            switch state {
            case .listening:
                self.delegate?.jarvisCore(self, didChangeState: .listening)
            case .processing, .thinking:
                self.delegate?.jarvisCore(self, didChangeState: .processing)
            case .speaking, .assistant_speaking:
                self.delegate?.jarvisCore(self, didChangeState: .speaking)
            case .user_speaking:
                self.delegate?.jarvisCore(self, didChangeState: .listening)
            case .error:
                self.delegate?.jarvisCore(self, didChangeState: .error("PersonaPlex error"))
            default:
                break
            }
        }

        // Handle PersonaPlex state changes with detail
        personaPlexClient.onStateChangedWithDetail = { [weak self] state, detail in
            guard let self = self else { return }
            var jarvisState: JarvisState
            switch state {
            case .listening, .user_speaking:
                jarvisState = .listening
            case .processing, .thinking:
                jarvisState = .processing
            case .speaking, .assistant_speaking:
                jarvisState = .speaking
            case .error:
                jarvisState = .error("PersonaPlex error")
            default:
                jarvisState = .idle
            }
            self.delegate?.jarvisCore(self, didChangeState: jarvisState, detail: detail)
        }

        // Handle PersonaPlex errors
        personaPlexClient.onError = { [weak self] error in
            guard let self = self else { return }
            logError("PersonaPlex error", error: error)
            self.delegate?.jarvisCore(self, didEncounterError: error)
        }

        // Handle audio capture
        audioPipeline.onAudioCaptured = { [weak self] audioData in
            guard let self = self else { return }
            Task {
                await self.processAudio(audioData)
            }
        }

        // Handle audio level updates for visualization
        audioPipeline.onAudioLevelUpdated = { [weak self] level in
            guard let self = self else { return }
            self.delegate?.jarvisCore(self, didUpdateAudioLevel: level)
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
        logInfo("Starting Full Duplex mode (PersonaPlex)", category: .audio)

        // Try to connect to PersonaPlex
        do {
            try await personaPlexClient.connect()
            personaPlexAvailable = true
            logInfo("PersonaPlex connected successfully", category: .network)
        } catch {
            logWarning("PersonaPlex not available: \(error.localizedDescription)", category: .network)
            personaPlexAvailable = false

            // Fall back to legacy mode
            logInfo("Falling back to Legacy mode", category: .audio)
            delegate?.jarvisCore(self, didEncounterError: PersonaPlexError.serverNotRunning)
            try await startLegacyMode()
            return
        }

        // Start audio capture
        try audioPipeline.startCapture()

        // Stream audio directly to PersonaPlex
        conversationTask = Task {
            while !Task.isCancelled && isActive {
                // PersonaPlex handles the full duplex loop via WebSocket
                try? await Task.sleep(nanoseconds: 100_000_000) // 100ms
            }
        }
    }

    private func startHybridMode() async throws {
        logInfo("Starting Hybrid mode (PersonaPlex + Ollama)", category: .audio)

        // Try to connect to PersonaPlex
        do {
            try await personaPlexClient.connect()
            personaPlexAvailable = true
            logInfo("PersonaPlex connected for hybrid mode", category: .network)
        } catch {
            logWarning("PersonaPlex not available, hybrid mode will use Ollama only", category: .network)
            personaPlexAvailable = false
        }

        // Check Ollama availability
        ollamaAvailable = await checkOllamaAvailability()

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
        logInfo("Starting Legacy mode (Ollama + VoiceForge)", category: .audio)

        // Check Ollama availability
        ollamaAvailable = await checkOllamaAvailability()

        if !ollamaAvailable {
            logError("Ollama is not available - cannot start legacy mode")
            throw OrchestratorError.serverNotAvailable
        }

        // Legacy mode: Traditional STT -> LLM -> TTS pipeline
        try audioPipeline.startCapture()

        conversationTask = Task {
            while !Task.isCancelled && isActive {
                try? await Task.sleep(nanoseconds: 100_000_000) // 100ms
            }
        }
    }

    private func checkOllamaAvailability() async -> Bool {
        guard let url = URL(string: "http://localhost:11434/api/tags") else {
            return false
        }

        do {
            let (_, response) = try await URLSession.shared.data(from: url)
            return (response as? HTTPURLResponse)?.statusCode == 200
        } catch {
            return false
        }
    }

    // MARK: - Audio Processing
    private var audioSendCount = 0

    private func processAudio(_ audioData: Data) async {
        audioSendCount += 1

        // Log every 50th send to see activity
        if audioSendCount % 50 == 0 {
            logInfo("processAudio: sending chunk #\(audioSendCount), \(audioData.count) bytes, mode: \(currentMode)", category: .audio)
        }

        switch currentMode {
        case .fullDuplex:
            // Stream directly to PersonaPlex
            do {
                try await personaPlexClient.sendAudio(audioData)
            } catch {
                if audioSendCount % 100 == 0 {
                    logError("Failed to send audio to PersonaPlex", error: error)
                }
            }

        case .hybrid:
            // Stream to PersonaPlex, but route complex queries to Ollama
            do {
                try await personaPlexClient.sendAudio(audioData)
            } catch {
                if audioSendCount % 100 == 0 {
                    logError("Failed to send audio in hybrid mode", error: error)
                }
            }

        case .legacy:
            // Buffer audio for later processing (push-to-talk style)
            audioBuffer.append(audioData)
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
