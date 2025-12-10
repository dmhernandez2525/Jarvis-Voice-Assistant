# Shared Notes System with Claude

## How It Works

**The Reality:** I (Claude) can't monitor files in the background 24/7 like a daemon process. I only "wake up" when you send me a message.

**The Solution:** A shared notes file that you can edit anytime, and I'll check automatically while I'm working:

- **At the start of any work session** - I check if notes should be read
- **Between planning steps** - I periodically check if 10+ minutes have passed
- **When file is modified** - The system detects changes and prompts me to read
- **On your request** - You can always say "check notes" for immediate reading

---

## Automatic Checking System

### How Automatic Checking Works

The system uses two files to track when notes should be read:

1. **`.notes_tracker`** - Stores timestamps of last check and last modification
2. **`check-notes-auto.sh`** - Script that determines if notes should be read

**When I Check Notes Automatically:**

- ✅ **Every 10+ minutes** while actively working on tasks
- ✅ **When you modify the notes file** - System detects changes
- ✅ **At the beginning** of any work session
- ✅ **Between major tasks** or planning phases
- ✅ **When you request** - Just say "check notes"

**The Check Logic:**

```bash
# I should read notes if EITHER:
# 1. 10+ minutes have passed since last check
# 2. Notes file was modified since last check
```

**Behind the Scenes:**

When I'm working on tasks, I'll periodically run:
```bash
bash ~/Desktop/Jarvis-Voice-Assistant/check-notes-auto.sh
```

If the script says `SHOULD_READ=yes`, I'll:
1. Read your notes from `DANIEL_NOTES.md`
2. Incorporate your thoughts into my current context
3. Update the tracker with the current timestamp
4. Continue working with your context in mind

**What This Means for You:**

You can edit the notes file anytime, and I'll pick up your thoughts during my natural workflow pauses. No need to explicitly tell me every time - just update the notes and I'll see them within 10 minutes (or sooner if I'm between tasks).

---

## Quick Start

### Opening Your Notes

**Option 1: Double-click to open**
- Double-click `open-notes.command` on your Desktop/Jarvis-Voice-Assistant folder
- Opens in TextEdit automatically

**Option 2: Open manually**
- File location: `~/Desktop/Jarvis-Voice-Assistant/DANIEL_NOTES.md`
- Open with any text editor (TextEdit, VS Code, etc.)

**Option 3: Use Mac Notes app**
1. Open Notes app
2. File → Import → Select `DANIEL_NOTES.md`
3. Edit directly in Notes
4. Saves automatically

---

## How to Use

### When You Update Notes:

Just tell me in chat:
- "check notes"
- "read my notes"
- "what do my notes say?"
- "check DANIEL_NOTES"

I'll immediately read the file and incorporate your thoughts.

### What to Put in Notes:

**✅ Good for notes:**
- Background context ("I'm building a chatbot for my business")
- Current mood/mindset ("Focused on performance today")
- Ideas for later ("Maybe add voice cloning?")
- Reminders for yourself ("Remember to test on Raspberry Pi")
- Questions to ask me later
- Things you're thinking about while I'm working

**❌ Not good for notes:**
- Urgent requests (just message me directly)
- Complex multi-step tasks (use chat for those)
- Time-sensitive information

---

## Example Workflow

**You're working and thinking:**

1. You have an idea: "What if JARVIS could control my lights?"
2. Open notes (double-click `open-notes.command`)
3. Add to notes:
   ```
   ## Ideas
   - JARVIS light control via voice
   - Maybe integrate with Philips Hue?
   - Need to research Home Assistant more
   ```
4. Save and close

**Later, when we're chatting:**

You: "check notes"

Me: *reads file* "I see you're thinking about JARVIS controlling lights via voice, maybe with Philips Hue integration. I already included Home Assistant integration in `jarvis_homeassistant.py` which supports Hue! Want me to show you how to set it up?"

---

## Mac Notes Integration

### Method 1: Import Once
```
1. Open Notes app
2. File → Import
3. Select DANIEL_NOTES.md
4. Edit in Notes app
```

**Pros:** Nice Notes app interface, iCloud sync
**Cons:** Changes won't be in the .md file (I won't see them)

### Method 2: Use as Plain Text (Recommended)
```
1. Keep DANIEL_NOTES.md as plain text
2. Edit with TextEdit or any editor
3. Optionally: Create an Apple Note that says "See ~/Desktop/Jarvis-Voice-Assistant/DANIEL_NOTES.md"
```

**Pros:** I can read your changes, stays in sync
**Cons:** Not in Notes app directly

### Method 3: Hybrid Approach
```
1. Edit DANIEL_NOTES.md when you want ME to see something
2. Use regular Notes app for your personal notes
3. Copy relevant parts to DANIEL_NOTES.md when needed
```

**Pros:** Best of both worlds
**Cons:** Manual copying

---

## Tips

1. **Update timestamp**: Add date/time at bottom when you edit so I know it's fresh
2. **Clear when done**: Remove old ideas after we discuss them
3. **Be casual**: Write like you're thinking out loud, not formal instructions
4. **No pressure**: Don't feel obligated to use it - regular chat works great too!

---

## Example Notes File

```markdown
# Daniel's Notes for Claude

## Current Thoughts
- The 72b model is too slow for simple questions
- Smart router idea sounds perfect
- Want to test this on actual hardware soon

## Context/Background
- Building this to replace Alexa/Echo
- Have a Raspberry Pi 4 ready to test
- Wife wants one in the kitchen

## Ideas / Future Plans
- Voice cloning to sound like JARVIS from Iron Man?
- Add weather integration
- Recipe assistant feature?

## Questions / Reminders
- How much power does Pi 4 draw 24/7?
- Need to buy microphone array
- Ask about wake word sensitivity tuning

**Last Updated:** Dec 9, 2024 10:45 PM
```

---

## Alternative: Use Comments in Code

You can also add comments in the Python files:
```python
# TODO: Daniel wants to add weather here
# NOTE: Make this faster if possible
# IDEA: Could we cache common responses?
```

I'll see these when working on the code!

---

## The Mental Model

Think of this notes file as:
- **A whiteboard** where you jot ideas
- **Context** for our conversations
- **Your thoughts** captured between our chats
- **A reminder** of what you were thinking

When you say "check notes," I'll read it and we'll be on the same page!
