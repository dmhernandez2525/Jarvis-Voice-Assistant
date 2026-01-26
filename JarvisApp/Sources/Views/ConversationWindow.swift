import Cocoa

class ConversationWindowController: NSWindowController {
    static let shared = ConversationWindowController()

    private var conversationView: ConversationView!

    private init() {
        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 400, height: 500),
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )

        window.title = "Jarvis"
        window.center()
        window.isReleasedWhenClosed = false
        window.minSize = NSSize(width: 350, height: 400)

        // Make it float above other windows
        window.level = .floating

        super.init(window: window)

        conversationView = ConversationView(frame: window.contentView!.bounds)
        conversationView.autoresizingMask = [.width, .height]
        window.contentView = conversationView
    }

    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }

    func show() {
        window?.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    func hide() {
        window?.orderOut(nil)
    }

    func updateState(_ state: JarvisState) {
        DispatchQueue.main.async {
            self.conversationView.updateState(state)
        }
    }

    func addUserMessage(_ text: String) {
        DispatchQueue.main.async {
            self.conversationView.addMessage(text, isUser: true)
        }
    }

    func addAssistantMessage(_ text: String) {
        DispatchQueue.main.async {
            self.conversationView.addMessage(text, isUser: false)
        }
    }

    /// Update the streaming assistant message (creates new bubble if none exists)
    func updateStreamingMessage(_ text: String) {
        DispatchQueue.main.async {
            self.conversationView.updateStreamingMessage(text)
        }
    }

    /// Finalize the streaming message
    func finalizeStreamingMessage() {
        DispatchQueue.main.async {
            self.conversationView.finalizeStreamingMessage()
        }
    }

    func clearMessages() {
        DispatchQueue.main.async {
            self.conversationView.clearMessages()
        }
    }

    func updateAudioLevel(_ level: Float) {
        DispatchQueue.main.async {
            self.conversationView.updateAudioLevel(CGFloat(level))
        }
    }

    func updateStatusDetail(_ detail: String) {
        DispatchQueue.main.async {
            self.conversationView.updateStatusDetail(detail)
        }
    }
}

class ConversationView: NSView {
    // MARK: - UI Components
    private var statusLabel: NSTextField!
    private var statusIndicator: NSView!
    private var waveformView: WaveformView!
    private var scrollView: NSScrollView!
    private var messagesStack: NSStackView!
    private var stopButton: NSButton!

    private var currentState: JarvisState = .idle

    /// The current streaming message bubble (if any)
    private var streamingMessageView: MessageBubbleView?

    override init(frame frameRect: NSRect) {
        super.init(frame: frameRect)
        setupUI()
    }

    required init?(coder: NSCoder) {
        super.init(coder: coder)
        setupUI()
    }

    private func setupUI() {
        wantsLayer = true
        layer?.backgroundColor = NSColor.windowBackgroundColor.cgColor

        // Status indicator (colored dot)
        statusIndicator = NSView(frame: NSRect(x: 20, y: frame.height - 40, width: 12, height: 12))
        statusIndicator.wantsLayer = true
        statusIndicator.layer?.cornerRadius = 6
        statusIndicator.layer?.backgroundColor = NSColor.systemGray.cgColor
        addSubview(statusIndicator)

        // Status label
        statusLabel = NSTextField(labelWithString: "Idle")
        statusLabel.frame = NSRect(x: 40, y: frame.height - 43, width: 200, height: 20)
        statusLabel.font = NSFont.systemFont(ofSize: 14, weight: .medium)
        statusLabel.textColor = NSColor.labelColor
        addSubview(statusLabel)

        // Waveform visualization
        waveformView = WaveformView(frame: NSRect(x: 20, y: frame.height - 100, width: frame.width - 40, height: 50))
        waveformView.autoresizingMask = [.width]
        addSubview(waveformView)

        // Messages scroll view
        scrollView = NSScrollView(frame: NSRect(x: 20, y: 70, width: frame.width - 40, height: frame.height - 180))
        scrollView.autoresizingMask = [.width, .height]
        scrollView.hasVerticalScroller = true
        scrollView.hasHorizontalScroller = false
        scrollView.borderType = .noBorder
        scrollView.backgroundColor = NSColor.clear

        messagesStack = NSStackView(frame: scrollView.bounds)
        messagesStack.orientation = .vertical
        messagesStack.alignment = .leading
        messagesStack.spacing = 12
        messagesStack.translatesAutoresizingMaskIntoConstraints = false

        let clipView = NSClipView()
        clipView.documentView = messagesStack
        clipView.drawsBackground = false
        scrollView.contentView = clipView

        addSubview(scrollView)

        // Stop button
        stopButton = NSButton(frame: NSRect(x: frame.width/2 - 60, y: 20, width: 120, height: 36))
        stopButton.title = "Stop"
        stopButton.bezelStyle = .rounded
        stopButton.autoresizingMask = [.minXMargin, .maxXMargin]
        stopButton.target = self
        stopButton.action = #selector(stopButtonPressed)
        stopButton.isHidden = true
        addSubview(stopButton)

        // Add welcome message
        addMessage("Hello! Press Option+Space or click Start Conversation to begin.", isUser: false)
    }

    override func layout() {
        super.layout()

        // Update positions on resize
        statusIndicator.frame = NSRect(x: 20, y: frame.height - 40, width: 12, height: 12)
        statusLabel.frame = NSRect(x: 40, y: frame.height - 43, width: 200, height: 20)
        waveformView.frame = NSRect(x: 20, y: frame.height - 100, width: frame.width - 40, height: 50)
        scrollView.frame = NSRect(x: 20, y: 70, width: frame.width - 40, height: frame.height - 180)
        stopButton.frame = NSRect(x: frame.width/2 - 60, y: 20, width: 120, height: 36)
    }

    func updateState(_ state: JarvisState) {
        currentState = state

        switch state {
        case .idle:
            statusLabel.stringValue = "Idle"
            statusIndicator.layer?.backgroundColor = NSColor.systemGray.cgColor
            waveformView.stopAnimating()
            stopButton.isHidden = true

        case .listening:
            statusLabel.stringValue = "Listening..."
            statusIndicator.layer?.backgroundColor = NSColor.systemGreen.cgColor
            waveformView.startAnimating(color: .systemGreen)
            stopButton.isHidden = false
            stopButton.title = "Stop"

        case .processing:
            statusLabel.stringValue = "Thinking..."
            statusIndicator.layer?.backgroundColor = NSColor.systemPurple.cgColor
            waveformView.startAnimating(color: .systemPurple)
            stopButton.isHidden = false
            stopButton.title = "Cancel"

        case .speaking:
            statusLabel.stringValue = "Responding..."
            statusIndicator.layer?.backgroundColor = NSColor.systemOrange.cgColor
            waveformView.startAnimating(color: .systemOrange)
            stopButton.isHidden = false
            stopButton.title = "Interrupt"

        case .error(let message):
            statusLabel.stringValue = "Error: \(message)"
            statusIndicator.layer?.backgroundColor = NSColor.systemRed.cgColor
            waveformView.stopAnimating()
            stopButton.isHidden = true
        }
    }

    /// Update status with custom detail text
    func updateStatusDetail(_ detail: String) {
        statusLabel.stringValue = detail
    }

    func addMessage(_ text: String, isUser: Bool) {
        let messageView = MessageBubbleView(text: text, isUser: isUser)
        messagesStack.addArrangedSubview(messageView)

        // Scroll to bottom
        DispatchQueue.main.async {
            if let documentView = self.scrollView.documentView {
                let newScrollOrigin = NSPoint(x: 0, y: documentView.frame.height - self.scrollView.contentSize.height)
                self.scrollView.contentView.scroll(to: newScrollOrigin)
            }
        }
    }

    func clearMessages() {
        for view in messagesStack.arrangedSubviews {
            messagesStack.removeArrangedSubview(view)
            view.removeFromSuperview()
        }
        streamingMessageView = nil
    }

    /// Update the streaming message with accumulated text
    func updateStreamingMessage(_ text: String) {
        if let existingView = streamingMessageView {
            // Update existing streaming bubble
            existingView.updateText(text)
        } else {
            // Create new streaming bubble
            let messageView = MessageBubbleView(text: text, isUser: false)
            messagesStack.addArrangedSubview(messageView)
            streamingMessageView = messageView
        }

        // Scroll to bottom
        DispatchQueue.main.async {
            if let documentView = self.scrollView.documentView {
                let newScrollOrigin = NSPoint(x: 0, y: documentView.frame.height - self.scrollView.contentSize.height)
                self.scrollView.contentView.scroll(to: newScrollOrigin)
            }
        }
    }

    /// Finalize streaming and clear the streaming reference
    func finalizeStreamingMessage() {
        streamingMessageView = nil
    }

    func updateAudioLevel(_ level: CGFloat) {
        waveformView.updateAudioLevel(level)
    }

    @objc private func stopButtonPressed() {
        NotificationCenter.default.post(name: .stopConversation, object: nil)
    }
}

// MARK: - Message Bubble View
class MessageBubbleView: NSView {
    private var textField: NSTextField!

    init(text: String, isUser: Bool) {
        super.init(frame: .zero)

        wantsLayer = true

        textField = NSTextField(wrappingLabelWithString: text)
        textField.font = NSFont.systemFont(ofSize: 13)
        textField.textColor = isUser ? NSColor.white : NSColor.labelColor
        textField.backgroundColor = NSColor.clear
        textField.isBordered = false
        textField.isEditable = false
        textField.translatesAutoresizingMaskIntoConstraints = false

        let bubble = NSView()
        bubble.wantsLayer = true
        bubble.layer?.cornerRadius = 12
        bubble.layer?.backgroundColor = isUser
            ? NSColor.systemBlue.cgColor
            : NSColor.controlBackgroundColor.cgColor
        bubble.translatesAutoresizingMaskIntoConstraints = false

        addSubview(bubble)
        bubble.addSubview(textField)

        NSLayoutConstraint.activate([
            textField.topAnchor.constraint(equalTo: bubble.topAnchor, constant: 8),
            textField.bottomAnchor.constraint(equalTo: bubble.bottomAnchor, constant: -8),
            textField.leadingAnchor.constraint(equalTo: bubble.leadingAnchor, constant: 12),
            textField.trailingAnchor.constraint(equalTo: bubble.trailingAnchor, constant: -12),
            textField.widthAnchor.constraint(lessThanOrEqualToConstant: 280),

            bubble.topAnchor.constraint(equalTo: topAnchor),
            bubble.bottomAnchor.constraint(equalTo: bottomAnchor),

            heightAnchor.constraint(greaterThanOrEqualToConstant: 30)
        ])

        if isUser {
            bubble.trailingAnchor.constraint(equalTo: trailingAnchor).isActive = true
            bubble.leadingAnchor.constraint(greaterThanOrEqualTo: leadingAnchor, constant: 50).isActive = true
        } else {
            bubble.leadingAnchor.constraint(equalTo: leadingAnchor).isActive = true
            bubble.trailingAnchor.constraint(lessThanOrEqualTo: trailingAnchor, constant: -50).isActive = true
        }
    }

    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }

    /// Update the text content (for streaming messages)
    func updateText(_ text: String) {
        textField.stringValue = text
        needsLayout = true
    }
}

// MARK: - Waveform View
class WaveformView: NSView {
    private var isAnimating = false
    private var animationColor: NSColor = .systemGreen
    private var audioLevel: CGFloat = 0.0  // 0.0 to 1.0
    private var levelHistory: [CGFloat] = []  // Recent levels for visualization
    private let historySize = 50
    private var animationTimer: Timer?

    override init(frame frameRect: NSRect) {
        super.init(frame: frameRect)
        wantsLayer = true
        layer?.cornerRadius = 8
        layer?.backgroundColor = NSColor.controlBackgroundColor.cgColor
        levelHistory = Array(repeating: 0, count: historySize)
    }

    required init?(coder: NSCoder) {
        super.init(coder: coder)
        wantsLayer = true
        layer?.cornerRadius = 8
        layer?.backgroundColor = NSColor.controlBackgroundColor.cgColor
        levelHistory = Array(repeating: 0, count: historySize)
    }

    func startAnimating(color: NSColor) {
        animationColor = color
        isAnimating = true

        // Timer for smooth visual updates
        animationTimer?.invalidate()
        animationTimer = Timer.scheduledTimer(withTimeInterval: 1.0/30.0, repeats: true) { [weak self] timer in
            guard let self = self, self.isAnimating else {
                timer.invalidate()
                return
            }
            self.needsDisplay = true
        }
    }

    func stopAnimating() {
        isAnimating = false
        animationTimer?.invalidate()
        animationTimer = nil
        audioLevel = 0
        levelHistory = Array(repeating: 0, count: historySize)
        needsDisplay = true
    }

    /// Update with actual audio level (0.0 to 1.0)
    func updateAudioLevel(_ level: CGFloat) {
        // Smooth the level with some decay
        audioLevel = max(level, audioLevel * 0.85)

        // Add to history for bar visualization
        levelHistory.append(audioLevel)
        if levelHistory.count > historySize {
            levelHistory.removeFirst()
        }
    }

    override func draw(_ dirtyRect: NSRect) {
        super.draw(dirtyRect)

        guard let context = NSGraphicsContext.current?.cgContext else { return }

        // Background
        context.setFillColor(NSColor.controlBackgroundColor.cgColor)
        context.fill(bounds)

        if isAnimating {
            // Draw level bars based on audio history
            let barWidth: CGFloat = (bounds.width - 20) / CGFloat(historySize)
            let maxBarHeight = bounds.height - 10
            let midY = bounds.height / 2

            for (index, level) in levelHistory.enumerated() {
                let x = 10 + CGFloat(index) * barWidth
                let barHeight = max(2, level * maxBarHeight)

                // Color intensity based on level
                let alpha = 0.3 + level * 0.7
                context.setFillColor(animationColor.withAlphaComponent(alpha).cgColor)

                // Draw bar centered vertically
                let rect = CGRect(
                    x: x,
                    y: midY - barHeight / 2,
                    width: max(1, barWidth - 1),
                    height: barHeight
                )
                context.fill(rect)
            }

            // Draw center line
            context.setStrokeColor(animationColor.withAlphaComponent(0.3).cgColor)
            context.setLineWidth(1)
            context.move(to: CGPoint(x: 10, y: midY))
            context.addLine(to: CGPoint(x: bounds.width - 10, y: midY))
            context.strokePath()
        } else {
            // Draw flat line when idle
            context.setStrokeColor(NSColor.tertiaryLabelColor.cgColor)
            context.setLineWidth(1)
            context.move(to: CGPoint(x: 10, y: bounds.height / 2))
            context.addLine(to: CGPoint(x: bounds.width - 10, y: bounds.height / 2))
            context.strokePath()
        }
    }
}

// MARK: - Notification Names
extension Notification.Name {
    static let stopConversation = Notification.Name("stopConversation")
}
