import './App.css'

function App() {
  return (
    <div className="app">
      <header className="hero">
        <nav className="nav">
          <div className="logo">Jarvis</div>
          <div className="nav-links">
            <a href="#features">Features</a>
            <a href="#modes">Modes</a>
            <a href="#api">API</a>
            <a href="#hardware">Hardware</a>
            <a href="#coming-soon" className="coming-soon-link">Coming Soon</a>
            <a href="https://github.com/dmhernandez2525/Jarvis-Voice-Assistant" target="_blank" rel="noopener noreferrer" className="github-link">GitHub</a>
          </div>
        </nav>
        <div className="hero-content">
          <div className="badge">100% Offline</div>
          <h1>Your Personal AI Voice Assistant</h1>
          <p className="tagline">Powerful voice assistant using Whisper for speech recognition and Qwen for maximum intelligence. No cloud required.</p>
          <div className="hero-buttons">
            <a href="https://github.com/dmhernandez2525/Jarvis-Voice-Assistant" className="btn btn-primary">Get Started</a>
            <a href="#features" className="btn btn-secondary">Learn More</a>
          </div>
        </div>
      </header>

      <section className="tech-stack">
        <h2>Powered By</h2>
        <div className="tech-grid">
          <div className="tech-card">
            <h3>Whisper Large</h3>
            <p>State-of-the-art speech recognition from OpenAI</p>
          </div>
          <div className="tech-card">
            <h3>Qwen 2.5:72b</h3>
            <p>Maximum intelligence LLM with 72B parameters</p>
          </div>
          <div className="tech-card">
            <h3>pyttsx3</h3>
            <p>Offline text-to-speech synthesis</p>
          </div>
        </div>
      </section>

      <section id="features" className="features">
        <h2>Features</h2>
        <div className="feature-grid">
          <div className="feature-card">
            <div className="feature-icon">🔒</div>
            <h3>Fully Offline</h3>
            <p>All processing happens locally. Your conversations never leave your device.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🎤</div>
            <h3>Wake Word Detection</h3>
            <p>Say "Jarvis" to activate. Two options: simple (no setup) or Porcupine (fastest).</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🧠</div>
            <h3>Maximum Intelligence</h3>
            <p>Powered by Qwen 2.5:72b with 72 billion parameters for complex reasoning.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🌐</div>
            <h3>API Server Mode</h3>
            <p>Run as a server for remote devices. Perfect for custom hardware projects.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🏠</div>
            <h3>Home Assistant</h3>
            <p>Optional integration with Home Assistant for smart home control.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">⚡</div>
            <h3>Fast Response</h3>
            <p>2-5 second typical response time with hardware acceleration.</p>
          </div>
        </div>
      </section>

      <section id="modes" className="modes">
        <h2>Operating Modes</h2>
        <div className="mode-grid">
          <div className="mode-card">
            <h3>Simple Wake Word</h3>
            <p className="mode-badge">No Setup Required</p>
            <pre><code>python3 jarvis_simple_wakeword.py</code></pre>
            <ul>
              <li>100% offline, no API key needed</li>
              <li>Uses Whisper to detect "Jarvis"</li>
              <li>~1-2s wake word detection</li>
            </ul>
          </div>
          <div className="mode-card recommended">
            <h3>Porcupine Wake Word</h3>
            <p className="mode-badge">Best Accuracy</p>
            <pre><code>python3 jarvis_with_wakeword.py</code></pre>
            <ul>
              <li>Fastest wake word detection (&lt;0.1s)</li>
              <li>Requires free Porcupine access key</li>
              <li>Still 100% offline after setup</li>
            </ul>
          </div>
          <div className="mode-card">
            <h3>Interactive Mode</h3>
            <p className="mode-badge">For Testing</p>
            <pre><code>python3 voice_assistant.py</code></pre>
            <ul>
              <li>No wake word required</li>
              <li>Press Enter to record</li>
              <li>5 second recording window</li>
            </ul>
          </div>
          <div className="mode-card">
            <h3>Server Mode</h3>
            <p className="mode-badge">For Remote Devices</p>
            <pre><code>python3 voice_assistant_server.py</code></pre>
            <ul>
              <li>REST API on port 5000</li>
              <li>Perfect for Raspberry Pi clients</li>
              <li>Audio and text endpoints</li>
            </ul>
          </div>
        </div>
      </section>

      <section id="api" className="api-section">
        <h2>API Endpoints</h2>
        <p className="section-description">Run in server mode to access these endpoints from any device on your network.</p>
        <div className="api-grid">
          <div className="api-card">
            <h3>Health Check</h3>
            <pre><code>GET /health</code></pre>
            <p>Check if the server is running</p>
          </div>
          <div className="api-card">
            <h3>Text Query</h3>
            <pre><code>POST /text_query</code></pre>
            <p>Send text, receive text response</p>
          </div>
          <div className="api-card">
            <h3>Audio Query (JSON)</h3>
            <pre><code>POST /query</code></pre>
            <p>Send audio, receive JSON with transcription and response</p>
          </div>
          <div className="api-card">
            <h3>Audio Query (Audio)</h3>
            <pre><code>POST /query_audio</code></pre>
            <p>Send audio, receive spoken audio response</p>
          </div>
        </div>
        <div className="code-example">
          <h3>Example: Text Query</h3>
          <pre><code>{`curl -X POST http://SERVER_IP:5000/text_query \\
  -H "Content-Type: application/json" \\
  -d '{"text": "What is the capital of France?"}'`}</code></pre>
        </div>
      </section>

      <section id="hardware" className="hardware">
        <h2>Hardware Requirements</h2>
        <div className="req-grid">
          <div className="req-card minimum">
            <h3>Minimum</h3>
            <ul>
              <li><strong>RAM:</strong> 96 GB (for Qwen 2.5:72b)</li>
              <li><strong>Storage:</strong> ~60 GB</li>
              <li><strong>CPU:</strong> Modern multi-core</li>
            </ul>
          </div>
          <div className="req-card recommended">
            <h3>Recommended</h3>
            <ul>
              <li><strong>Apple M2 Max</strong> or similar</li>
              <li><strong>Unified Memory:</strong> 96GB+</li>
              <li><strong>Fast SSD:</strong> 500GB+</li>
            </ul>
          </div>
          <div className="req-card alternative">
            <h3>Lighter Options</h3>
            <ul>
              <li><strong>Qwen 2.5:32b</strong> - 64GB RAM</li>
              <li><strong>Qwen 2.5:14b</strong> - 32GB RAM</li>
              <li><strong>Qwen 2.5:7b</strong> - 16GB RAM</li>
            </ul>
          </div>
        </div>
      </section>

      <section className="custom-hardware">
        <h2>Custom Hardware Integration</h2>
        <p className="section-description">Build your own Echo-like device with a Raspberry Pi or similar hardware.</p>
        <div className="integration-steps">
          <div className="integration-step">
            <div className="step-number">1</div>
            <h3>Record Audio</h3>
            <p>Capture audio from microphone (WAV format, 16kHz recommended)</p>
          </div>
          <div className="integration-step">
            <div className="step-number">2</div>
            <h3>Send to Server</h3>
            <p>POST audio to /query_audio endpoint</p>
          </div>
          <div className="integration-step">
            <div className="step-number">3</div>
            <h3>Play Response</h3>
            <p>Stream the audio response through speaker</p>
          </div>
        </div>
        <div className="code-example">
          <h3>Raspberry Pi Example</h3>
          <pre><code>{`import requests

SERVER = "http://192.168.1.100:5000"

# Send audio to server
with open('recording.wav', 'rb') as f:
    response = requests.post(
        f"{SERVER}/query_audio",
        files={'audio': f}
    )

# Play response.content as audio`}</code></pre>
        </div>
      </section>

      <section className="performance">
        <h2>Performance</h2>
        <div className="perf-grid">
          <div className="perf-card">
            <h3>Response Time</h3>
            <p className="perf-value">2-5 seconds</p>
            <ul>
              <li>Transcription: 0.5-1s</li>
              <li>LLM inference: 1-3s</li>
              <li>TTS: 0.5-1s</li>
            </ul>
          </div>
          <div className="perf-card">
            <h3>Model Options</h3>
            <table>
              <thead>
                <tr><th>Model</th><th>Speed</th><th>Intelligence</th></tr>
              </thead>
              <tbody>
                <tr><td>72b</td><td>Slower</td><td>Maximum</td></tr>
                <tr><td>32b</td><td>Medium</td><td>High</td></tr>
                <tr><td>14b</td><td>Fast</td><td>Good</td></tr>
                <tr><td>7b</td><td>Fastest</td><td>Basic</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <section id="coming-soon" className="coming-soon">
        <h2>Coming Soon: Full Duplex Conversation</h2>
        <div className="coming-soon-badge">PersonaPlex Integration</div>
        <p className="section-description">
          We're integrating NVIDIA's PersonaPlex - an open-source full duplex AI that will revolutionize how you interact with Jarvis.
        </p>
        <div className="coming-soon-grid">
          <div className="coming-soon-card">
            <div className="comparison">
              <div className="comparison-item current">
                <h4>Current</h4>
                <p>Turn-based conversation</p>
                <p className="metric">2-5 second latency</p>
              </div>
              <div className="comparison-arrow">→</div>
              <div className="comparison-item future">
                <h4>With PersonaPlex</h4>
                <p>Simultaneous listening & speaking</p>
                <p className="metric">&lt;500ms latency</p>
              </div>
            </div>
          </div>
          <div className="coming-soon-features">
            <div className="csf-item">
              <span className="csf-icon">🔄</span>
              <div>
                <h4>Full Duplex</h4>
                <p>Listens and speaks at the same time, just like a real conversation</p>
              </div>
            </div>
            <div className="csf-item">
              <span className="csf-icon">💬</span>
              <div>
                <h4>Active Listening</h4>
                <p>Says "uh-huh", "right", "okay" while you speak - feels natural</p>
              </div>
            </div>
            <div className="csf-item">
              <span className="csf-icon">✋</span>
              <div>
                <h4>Natural Interruption</h4>
                <p>Interrupt mid-sentence naturally, no need to wait</p>
              </div>
            </div>
            <div className="csf-item">
              <span className="csf-icon">⚡</span>
              <div>
                <h4>Near-Zero Latency</h4>
                <p>Responses feel instant, like talking to another person</p>
              </div>
            </div>
          </div>
        </div>
        <p className="coming-soon-note">
          <strong>Technical Details:</strong> 7B parameter model based on Moshi architecture, runs locally on 24GB+ VRAM (Mac M2 Max compatible), open source under Apache 2.0 license.
        </p>
      </section>

      <section className="installation">
        <h2>Quick Start</h2>
        <div className="install-steps">
          <div className="install-step">
            <h3>1. Clone & Install</h3>
            <pre><code>{`git clone https://github.com/dmhernandez2525/Jarvis-Voice-Assistant.git
cd Jarvis-Voice-Assistant
pip3 install -r requirements.txt`}</code></pre>
          </div>
          <div className="install-step">
            <h3>2. Install Audio Libraries (macOS)</h3>
            <pre><code>brew install portaudio</code></pre>
          </div>
          <div className="install-step">
            <h3>3. Run Jarvis</h3>
            <pre><code>python3 jarvis_simple_wakeword.py</code></pre>
          </div>
        </div>
      </section>

      <footer className="footer">
        <div className="footer-content">
          <div className="footer-section">
            <h3>Jarvis Voice Assistant</h3>
            <p>Fully offline AI voice assistant for privacy-conscious users.</p>
          </div>
          <div className="footer-section">
            <h3>Links</h3>
            <a href="https://github.com/dmhernandez2525/Jarvis-Voice-Assistant">GitHub Repository</a>
            <a href="https://github.com/dmhernandez2525/Jarvis-Voice-Assistant/blob/main/LICENSE">MIT License</a>
          </div>
        </div>
        <div className="footer-bottom">
          <p>MIT License - Open Source</p>
        </div>
      </footer>
    </div>
  )
}

export default App
