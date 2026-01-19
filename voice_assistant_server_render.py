#!/usr/bin/env python3
"""
Voice Assistant API Server - Render Stub
Note: Full voice processing requires Docker deployment with system dependencies.
This is a minimal stub for Render deployment.
"""

from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "message": "Voice API stub - Full functionality requires Docker deployment",
        "docs": "https://github.com/dmhernandez2525/Jarvis-Voice-Assistant"
    })

@app.route('/', methods=['GET'])
def index():
    """Landing page"""
    return jsonify({
        "service": "Jarvis Voice Assistant API",
        "status": "stub",
        "note": "Full voice processing requires Docker deployment with ffmpeg and portaudio",
        "endpoints": {
            "/health": "Health check",
            "/": "This page"
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
