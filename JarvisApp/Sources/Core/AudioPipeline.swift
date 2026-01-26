import Foundation
import AVFoundation

class AudioPipeline {
    // MARK: - Properties
    var onAudioCaptured: ((Data) -> Void)?
    var onAudioLevelUpdated: ((Float) -> Void)?

    // Capture engine
    private var captureEngine: AVAudioEngine?
    private var inputNode: AVAudioInputNode?
    private var isCapturing = false

    // Playback engine (persistent to avoid memory leaks)
    private var playbackEngine: AVAudioEngine?
    private var playerNode: AVAudioPlayerNode?
    private var audioPlayer: AVAudioPlayer?

    private let sampleRate: Double = 16000
    private let channels: AVAudioChannelCount = 1
    private let bufferSize: AVAudioFrameCount = 1024

    // MARK: - Audio Capture
    func startCapture() throws {
        guard !isCapturing else { return }

        logInfo("Starting audio capture", category: .audio)

        captureEngine = AVAudioEngine()
        guard let engine = captureEngine else {
            logError("Failed to create capture engine")
            throw AudioPipelineError.engineInitFailed
        }

        inputNode = engine.inputNode
        guard let inputNode = inputNode else {
            logError("Input node not available")
            throw AudioPipelineError.inputNodeNotAvailable
        }

        // Get the native format
        let inputFormat = inputNode.inputFormat(forBus: 0)
        logDebug("Input format: \(inputFormat.sampleRate)Hz, \(inputFormat.channelCount) channels", category: .audio)

        // Create the output format we want (16kHz mono)
        guard let outputFormat = AVAudioFormat(
            commonFormat: .pcmFormatFloat32,
            sampleRate: sampleRate,
            channels: channels,
            interleaved: false
        ) else {
            logError("Failed to create output format")
            throw AudioPipelineError.formatCreationFailed
        }

        // Create a converter
        guard let converter = AVAudioConverter(from: inputFormat, to: outputFormat) else {
            logError("Failed to create audio converter")
            throw AudioPipelineError.converterCreationFailed
        }

        // Install tap on input node
        inputNode.installTap(onBus: 0, bufferSize: bufferSize, format: inputFormat) { [weak self] buffer, time in
            self?.processInputBuffer(buffer, converter: converter, outputFormat: outputFormat)
        }

        try engine.start()
        isCapturing = true
        logInfo("Audio capture started successfully", category: .audio)
    }

    func stopCapture() {
        guard isCapturing else { return }

        logInfo("Stopping audio capture", category: .audio)
        captureEngine?.inputNode.removeTap(onBus: 0)
        captureEngine?.stop()
        captureEngine = nil
        isCapturing = false
    }

    private var audioChunkCount = 0

    private func processInputBuffer(_ inputBuffer: AVAudioPCMBuffer, converter: AVAudioConverter, outputFormat: AVAudioFormat) {
        // Calculate the output frame capacity
        let ratio = outputFormat.sampleRate / inputBuffer.format.sampleRate
        let outputFrameCapacity = AVAudioFrameCount(Double(inputBuffer.frameLength) * ratio)

        guard let outputBuffer = AVAudioPCMBuffer(pcmFormat: outputFormat, frameCapacity: outputFrameCapacity) else {
            logWarning("Failed to create output buffer", category: .audio)
            return
        }

        var error: NSError?
        let status = converter.convert(to: outputBuffer, error: &error) { inNumPackets, outStatus in
            outStatus.pointee = .haveData
            return inputBuffer
        }

        guard status != .error, error == nil else {
            logError("Audio conversion error", error: error)
            return
        }

        // Convert to Data
        if let channelData = outputBuffer.floatChannelData?[0] {
            let frameLength = Int(outputBuffer.frameLength)
            let data = Data(bytes: channelData, count: frameLength * MemoryLayout<Float>.size)

            // Calculate RMS audio level for visualization
            var sumOfSquares: Float = 0
            for i in 0..<frameLength {
                let sample = channelData[i]
                sumOfSquares += sample * sample
            }
            let rms = sqrt(sumOfSquares / Float(frameLength))
            // Scale RMS to 0-1 range (typical speech RMS is 0.01-0.3)
            let normalizedLevel = min(1.0, rms * 5.0)
            onAudioLevelUpdated?(normalizedLevel)

            // Log every 50th chunk to see activity
            audioChunkCount += 1
            if audioChunkCount % 50 == 0 {
                logInfo("Audio captured: chunk #\(audioChunkCount), \(data.count) bytes, level: \(normalizedLevel)", category: .audio)
            }

            onAudioCaptured?(data)
        }
    }

    // MARK: - Audio Playback

    /// Initialize playback engine (call once, reuse for all playback)
    private func ensurePlaybackEngine() throws {
        guard playbackEngine == nil else { return }

        logDebug("Initializing playback engine", category: .audio)

        let engine = AVAudioEngine()
        let node = AVAudioPlayerNode()

        engine.attach(node)

        // Create format for connection
        guard let format = AVAudioFormat(
            commonFormat: .pcmFormatFloat32,
            sampleRate: sampleRate,
            channels: channels,
            interleaved: false
        ) else {
            throw AudioPipelineError.formatCreationFailed
        }

        engine.connect(node, to: engine.mainMixerNode, format: format)

        try engine.start()

        self.playbackEngine = engine
        self.playerNode = node

        logInfo("Playback engine initialized", category: .audio)
    }

    func playAudio(_ audioData: Data) {
        logDebug("Playing audio data: \(audioData.count) bytes", category: .audio)

        // Convert raw audio data to playable format
        // This assumes the data is already in the correct format (16kHz mono Float32)
        guard let format = AVAudioFormat(
            commonFormat: .pcmFormatFloat32,
            sampleRate: sampleRate,
            channels: channels,
            interleaved: false
        ) else {
            logError("Failed to create audio format for playback")
            return
        }

        let frameCount = audioData.count / MemoryLayout<Float>.size
        guard let buffer = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: AVAudioFrameCount(frameCount)) else {
            logError("Failed to create playback buffer")
            return
        }

        buffer.frameLength = AVAudioFrameCount(frameCount)

        audioData.withUnsafeBytes { rawBufferPointer in
            if let channelData = buffer.floatChannelData?[0],
               let source = rawBufferPointer.bindMemory(to: Float.self).baseAddress {
                channelData.update(from: source, count: frameCount)
            }
        }

        // Play using AVAudioEngine
        playBuffer(buffer)
    }

    func playAudioFile(_ url: URL) {
        logInfo("Playing audio file: \(url.lastPathComponent)", category: .audio)
        do {
            audioPlayer = try AVAudioPlayer(contentsOf: url)
            audioPlayer?.play()
        } catch {
            logError("Failed to play audio file", error: error)
        }
    }

    private func playBuffer(_ buffer: AVAudioPCMBuffer) {
        do {
            // Ensure playback engine is initialized (reused across calls)
            try ensurePlaybackEngine()

            guard let node = playerNode else {
                logError("Player node not available")
                return
            }

            // For streaming audio, schedule buffers to queue up (don't stop previous!)
            // This allows seamless playback of consecutive buffers
            node.scheduleBuffer(buffer)

            // Start playing if not already playing
            if !node.isPlaying {
                node.play()
            }

        } catch {
            logError("Failed to play buffer", error: error)
        }
    }

    /// Stop playback and cleanup
    func stopPlayback() {
        logDebug("Stopping playback", category: .audio)
        playerNode?.stop()
        audioPlayer?.stop()
    }

    /// Cleanup all audio resources
    func cleanup() {
        logInfo("Cleaning up audio pipeline", category: .audio)
        stopCapture()
        stopPlayback()

        playbackEngine?.stop()
        playbackEngine = nil
        playerNode = nil
        audioPlayer = nil
    }

    deinit {
        cleanup()
    }
}

// MARK: - Errors
enum AudioPipelineError: Error, LocalizedError {
    case engineInitFailed
    case inputNodeNotAvailable
    case formatCreationFailed
    case converterCreationFailed

    var errorDescription: String? {
        switch self {
        case .engineInitFailed:
            return "Failed to initialize audio engine"
        case .inputNodeNotAvailable:
            return "Audio input node not available"
        case .formatCreationFailed:
            return "Failed to create audio format"
        case .converterCreationFailed:
            return "Failed to create audio converter"
        }
    }
}
