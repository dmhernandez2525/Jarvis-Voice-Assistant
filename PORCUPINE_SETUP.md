# Porcupine Wake Word Setup Guide

## Option 1: Simple Wake Word (No Key Required)

Use `jarvis_simple_wakeword.py` - works 100% offline, no signup needed:

```bash
python3 jarvis_simple_wakeword.py
```

**How it works:**
- Listens for loud sounds (energy detection)
- Uses Whisper to verify "Jarvis" was said
- 100% offline, no API keys needed
- Slightly slower than Porcupine (uses Whisper for verification)

---

## Option 2: Porcupine Wake Word (Better Accuracy)

For better wake word accuracy, get a free Porcupine access key:

### Step 1: Sign Up for Free Account

1. Go to: https://console.picovoice.ai/signup
2. Create a free account (email + password)
3. Verify your email

### Step 2: Get Your Access Key

1. Log in to: https://console.picovoice.ai/
2. Click on "Access Keys" in the left menu
3. Copy your access key (looks like: `abc123...`)

### Step 3: Update jarvis_with_wakeword.py

Edit the file and add your access key:

```python
# Line 35 - Add your access key
self.porcupine = pvporcupine.create(
    access_key='YOUR_ACCESS_KEY_HERE',  # Paste your key
    keywords=['jarvis']
)
```

### Step 4: Run JARVIS

```bash
python3 jarvis_with_wakeword.py
```

---

## Comparison

| Feature | Simple Wake Word | Porcupine Wake Word |
|---------|------------------|---------------------|
| **Accuracy** | Good | Excellent |
| **Speed** | Slower (~1-2s delay) | Fast (<0.1s) |
| **Setup** | None | Free signup required |
| **Offline** | 100% | 100% (after setup) |
| **API Key** | Not needed | Free key required |

---

## Troubleshooting

### "access_key required" Error

**Problem:** Running `jarvis_with_wakeword.py` without access key

**Solution:** Either:
1. Use `jarvis_simple_wakeword.py` instead (no key needed)
2. Get free key from Picovoice and update the code

### Porcupine Key Not Working

**Problem:** Key invalid or expired

**Solution:**
1. Check you copied the entire key
2. Make sure quotes are correct: `access_key='abc123...'`
3. Generate a new key at https://console.picovoice.ai/

---

## Which Should I Use?

**Use Simple Wake Word if:**
- You want zero setup and 100% offline
- You don't want to create any accounts
- You're okay with 1-2 second delay for wake word detection

**Use Porcupine Wake Word if:**
- You want the fastest, most accurate wake word detection
- You're willing to create a free account
- You want instant wake word response (<0.1s)

---

## Free Tier Limits

Porcupine free tier includes:
- Unlimited offline use
- Up to 3 access keys
- No expiration
- No credit card required

The access key works completely offline after initial setup.
