import Foundation
import AVFoundation

class AudioPipeline {
    // MARK: - Properties
    var onAudioCaptured: ((Data) -> Void)?

    private var audioEngine: AVAudioEngine?
    private var audioPlayer: AVAudioPlayer?
    private var inputNode: AVAudioInputNode?

    private let sampleRate: Double = 16000
    private let channels: AVAudioChannelCount = 1
    private let bufferSize: AVAudioFrameCount = 1024

    private var isCapturing = false

    // MARK: - Audio Capture
    func startCapture() throws {
        guard !isCapturing else { return }

        audioEngine = AVAudioEngine()
        guard let engine = audioEngine else {
            throw AudioPipelineError.engineInitFailed
        }

        inputNode = engine.inputNode
        guard let inputNode = inputNode else {
            throw AudioPipelineError.inputNodeNotAvailable
        }

        // Get the native format
        let inputFormat = inputNode.inputFormat(forBus: 0)

        // Create the output format we want (16kHz mono)
        guard let outputFormat = AVAudioFormat(
            commonFormat: .pcmFormatFloat32,
            sampleRate: sampleRate,
            channels: channels,
            interleaved: false
        ) else {
            throw AudioPipelineError.formatCreationFailed
        }

        // Create a converter
        guard let converter = AVAudioConverter(from: inputFormat, to: outputFormat) else {
            throw AudioPipelineError.converterCreationFailed
        }

        // Install tap on input node
        inputNode.installTap(onBus: 0, bufferSize: bufferSize, format: inputFormat) { [weak self] buffer, time in
            self?.processInputBuffer(buffer, converter: converter, outputFormat: outputFormat)
        }

        try engine.start()
        isCapturing = true
    }

    func stopCapture() {
        guard isCapturing else { return }

        audioEngine?.inputNode.removeTap(onBus: 0)
        audioEngine?.stop()
        audioEngine = nil
        isCapturing = false
    }

    private func processInputBuffer(_ inputBuffer: AVAudioPCMBuffer, converter: AVAudioConverter, outputFormat: AVAudioFormat) {
        // Calculate the output frame capacity
        let ratio = outputFormat.sampleRate / inputBuffer.format.sampleRate
        let outputFrameCapacity = AVAudioFrameCount(Double(inputBuffer.frameLength) * ratio)

        guard let outputBuffer = AVAudioPCMBuffer(pcmFormat: outputFormat, frameCapacity: outputFrameCapacity) else {
            return
        }

        var error: NSError?
        let status = converter.convert(to: outputBuffer, error: &error) { inNumPackets, outStatus in
            outStatus.pointee = .haveData
            return inputBuffer
        }

        guard status != .error, error == nil else {
            print("Conversion error: \(error?.localizedDescription ?? "unknown")")
            return
        }

        // Convert to Data
        if let channelData = outputBuffer.floatChannelData?[0] {
            let frameLength = Int(outputBuffer.frameLength)
            let data = Data(bytes: channelData, count: frameLength * MemoryLayout<Float>.size)
            onAudioCaptured?(data)
        }
    }

    // MARK: - Audio Playback
    func playAudio(_ audioData: Data) {
        // Convert raw audio data to playable format
        // This assumes the data is already in the correct format (16kHz mono Float32)
        guard let format = AVAudioFormat(
            commonFormat: .pcmFormatFloat32,
            sampleRate: sampleRate,
            channels: channels,
            interleaved: false
        ) else { return }

        let frameCount = audioData.count / MemoryLayout<Float>.size
        guard let buffer = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: AVAudioFrameCount(frameCount)) else {
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
        do {
            audioPlayer = try AVAudioPlayer(contentsOf: url)
            audioPlayer?.play()
        } catch {
            print("Failed to play audio file: \(error)")
        }
    }

    private func playBuffer(_ buffer: AVAudioPCMBuffer) {
        // For real-time playback, we'd use a separate AVAudioEngine for output
        // This is a simplified implementation
        let playerEngine = AVAudioEngine()
        let playerNode = AVAudioPlayerNode()

        playerEngine.attach(playerNode)
        playerEngine.connect(playerNode, to: playerEngine.mainMixerNode, format: buffer.format)

        do {
            try playerEngine.start()
            playerNode.scheduleBuffer(buffer, completionHandler: nil)
            playerNode.play()
        } catch {
            print("Failed to play buffer: \(error)")
        }
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
