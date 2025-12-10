# JARVIS Performance Guide and Model Options

## Performance Timing Breakdown

The new `jarvis_optimized.py` includes detailed timing for each step:

```
Wake word verification: ~500-1000ms
Recording: 15000ms (15 seconds)
Transcription: ~2000-5000ms
LLM inference: ~3000-8000ms (varies by response length)
Text-to-speech: ~1000-3000ms
TOTAL: ~21-27 seconds
```

### Bottleneck Analysis

Based on the timing data you'll see:

1. **Recording (15s)** - This is user input time, not a bottleneck
2. **LLM Inference (3-8s)** - Usually the SLOWEST step
3. **Transcription (2-5s)** - Second slowest
4. **Wake word verification (0.5-1s)** - Fast enough
5. **TTS (1-3s)** - Fast enough

---

## Faster Model Options

### Current Setup
- **Qwen 2.5:72b** (~47GB)
- Intelligence: ⭐⭐⭐⭐⭐ (Maximum)
- Speed: ⭐⭐ (Slowest, 3-8s per response)

### Faster Alternatives

#### 1. Qwen 2.5:32b (Recommended Upgrade)
```bash
ollama pull qwen2.5:32b
```
- Size: ~20GB
- Intelligence: ⭐⭐⭐⭐½ (Excellent)
- Speed: ⭐⭐⭐⭐ (2-4s per response)
- **2-3x faster than 72b with minimal quality loss**

#### 2. Qwen 2.5:14b (Balanced)
```bash
ollama pull qwen2.5:14b
```
- Size: ~9GB
- Intelligence: ⭐⭐⭐⭐ (Very Good)
- Speed: ⭐⭐⭐⭐½ (1-2s per response)
- **5x faster than 72b, still highly intelligent**

#### 3. Qwen 2.5:7b (Fast)
```bash
ollama pull qwen2.5:7b
```
- Size: ~4.7GB
- Intelligence: ⭐⭐⭐½ (Good)
- Speed: ⭐⭐⭐⭐⭐ (0.5-1s per response)
- **10x faster than 72b, great for quick responses**

#### 4. Llama 3.3:70b (Alternative)
```bash
ollama pull llama3.3:70b
```
- Size: ~43GB
- Intelligence: ⭐⭐⭐⭐⭐ (Maximum)
- Speed: ⭐⭐½ (Similar to Qwen 72b)
- Different training, may have different strengths

---

## Uncensored Models (No Content Filtering)

If you want responses without safety restrictions:

### Dolphin Models (Uncensored)

#### 1. Dolphin-Mixtral:8x22b
```bash
ollama pull dolphin-mixtral:8x22b
```
- Size: ~90GB (won't fit in 96GB RAM, needs ~110GB total)
- Intelligence: ⭐⭐⭐⭐⭐
- Filtering: None
- Speed: Slow

#### 2. Dolphin-Mistral:7b
```bash
ollama pull dolphin-mistral:7b
```
- Size: ~4GB
- Intelligence: ⭐⭐⭐½
- Filtering: None (uncensored)
- Speed: ⭐⭐⭐⭐⭐ (Very fast)
- **Best for uncensored responses with good speed**

#### 3. WizardLM-Uncensored:13b
```bash
ollama pull wizardlm-uncensored:13b
```
- Size: ~7GB
- Intelligence: ⭐⭐⭐⭐
- Filtering: None
- Speed: ⭐⭐⭐⭐

---

## Changing Models

Edit `jarvis_optimized.py` line 161:

```python
jarvis = JarvisAssistant(
    model_name="qwen2.5:32b",  # Change this
    whisper_model="large"
)
```

Or download and use uncensored model:

```python
jarvis = JarvisAssistant(
    model_name="dolphin-mistral:7b",  # No content filtering
    whisper_model="large"
)
```

---

## Faster Whisper Options

Current: **Whisper Large** (most accurate, slowest)

### Speed vs Accuracy Trade-off

| Model | Speed | Accuracy | Best For |
|-------|-------|----------|----------|
| `large` | ⭐⭐ (2-5s) | ⭐⭐⭐⭐⭐ | Maximum accuracy |
| `medium` | ⭐⭐⭐ (1-3s) | ⭐⭐⭐⭐ | Balanced |
| `small` | ⭐⭐⭐⭐ (0.5-1.5s) | ⭐⭐⭐ | Fast transcription |
| `base` | ⭐⭐⭐⭐⭐ (0.3-1s) | ⭐⭐ | Speed over accuracy |

To change Whisper model:

```python
jarvis = JarvisAssistant(
    model_name="qwen2.5:32b",
    whisper_model="medium"  # Change this
)
```

---

## Recommended Configurations

### 1. Maximum Intelligence (Current)
```python
model_name="qwen2.5:72b"
whisper_model="large"
```
- Total time: ~25-30s per interaction
- Best quality

### 2. Balanced Performance
```python
model_name="qwen2.5:32b"
whisper_model="medium"
```
- Total time: ~18-22s per interaction
- Great quality, 40% faster

### 3. Speed Optimized
```python
model_name="qwen2.5:14b"
whisper_model="small"
```
- Total time: ~16-19s per interaction
- Good quality, 50% faster

### 4. Maximum Speed
```python
model_name="qwen2.5:7b"
whisper_model="base"
```
- Total time: ~15-17s per interaction
- Acceptable quality, 60% faster

### 5. Uncensored + Fast
```python
model_name="dolphin-mistral:7b"
whisper_model="medium"
```
- Total time: ~16-19s
- No content filtering, fast responses

---

## Hardware Limitations

Your Mac M2 Max (96GB RAM) can run:

✅ **Can run comfortably:**
- Qwen 2.5:72b (47GB)
- Llama 3.3:70b (43GB)
- Qwen 2.5:32b (20GB)
- Any model under 80GB

❌ **Cannot run:**
- Models requiring >90GB
- Dolphin-Mixtral:8x22b (90GB - too close to limit)
- DeepSeek-V3 (404GB)

💡 **Sweet spot:** 32b-72b models (20-50GB)

---

## Using the Optimized Version

```bash
cd ~/Desktop/Jarvis-Voice-Assistant
python3 jarvis_optimized.py
```

Features:
- 15 second recording
- Detailed timing metrics
- Less restrictive responses
- Performance analysis

Watch the timing output to see where bottlenecks are!

---

## About Content Filtering

The original Qwen 2.5:72b has built-in safety training that makes it refuse certain content.

`jarvis_optimized.py` includes:
1. System prompt that encourages direct responses
2. Temperature=0.8 for more creative answers
3. No explicit content filtering in the code

However, the model itself may still refuse based on its training. For truly unrestricted responses, use an uncensored model like:
- `dolphin-mistral:7b` (recommended)
- `wizardlm-uncensored:13b`
- Other "dolphin" or "uncensored" models

This is your personal local system - you have full control over what models and settings you use.
