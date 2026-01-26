# Jarvis Voice Assistant - Orchestrator
# Python Flask server for routing queries to Moshi/Ollama/VoiceForge
#
# Build: docker build -t jarvis-orchestrator .
# Run:   docker-compose up -d

FROM python:3.11-slim

LABEL maintainer="Daniel Hernandez"
LABEL description="Jarvis Voice Assistant Orchestrator"

# Install system dependencies including build tools for whisper
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    curl \
    build-essential \
    rustc \
    cargo \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for layer caching
COPY requirements-orchestrator.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-orchestrator.txt

# Copy application code
COPY jarvis_orchestrator.py .
COPY smart_router.py .
COPY personaplex_client.py .
COPY voiceforge_tts.py .
COPY homeassistant_client.py .
COPY config/ ./config/

# Create non-root user
RUN useradd -m jarvis
USER jarvis

# Expose orchestrator port
EXPOSE 5000

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production
ENV OLLAMA_URL=http://ollama:11434

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Start the orchestrator
CMD ["python", "jarvis_orchestrator.py"]
