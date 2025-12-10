# Context Management System Guide

## Overview

The **Multi-Project Context Management System** is a Git-like conversation tracker that preserves context across all your work with Claude. Think of it as version control for conversations.

**Key Features:**
- 🗂️ **Multiple Projects** - Manage different projects (Jarvis, websites, automations)
- 🌳 **Conversation Trees** - Branch off into subtopics, return to main goals
- 💾 **Context Preservation** - Never lose conversation history
- 🧭 **Navigation** - Jump to any previous conversation point
- 📊 **Progress Tracking** - See what's completed, what's active

---

## Concept

### The Problem

When working on complex projects with Claude:
- Conversations go off on tangents
- You lose track of the original goal
- Context gets lost between sessions
- Hard to resume work where you left off
- Can't see the big picture

### The Solution

A conversation tree system where:
- **Main path** = Your primary goal (e.g., "Build JARVIS")
- **Branches** = Subtopics (e.g., "Wake word detection", "Performance")
- **Chunks** = Conversation segments saved as markdown files
- **Navigation** = Jump between any point in the tree
- **Multi-project** = Each project has its own tree

---

## System Architecture

```
~/Desktop/Claude-Projects/               # Root directory
│
├── projects.json                        # Project registry
│
├── projects/                            # All projects
│   │
│   ├── jarvis-voice-assistant/          # Example project
│   │   ├── tree.json                    # Conversation tree
│   │   ├── chunks/                      # Conversation chunks
│   │   │   ├── main-001.md
│   │   │   ├── main-002.md
│   │   │   ├── wake-001.md
│   │   │   └── ...
│   │   └── files/                       # Symlink to actual files
│   │       → ~/Desktop/Jarvis-Voice-Assistant/
│   │
│   ├── website-builder/                 # Future project
│   │   └── ...
│   │
│   └── home-automation/                 # Future project
│       └── ...
│
└── context_manager.py                   # CLI tool
```

---

## Quick Start

### 1. Initialize Your First Project

The Jarvis project has already been initialized with your full conversation history!

```bash
cd ~/Desktop/Jarvis-Voice-Assistant
python3 context_manager.py project list
```

You should see:
```
PROJECTS
======================================================================

jarvis-voice-assistant ← ACTIVE
  Name: Jarvis Voice Assistant
  Goal: Build maximum-intelligence offline voice assistant for home network
  Status: active
  Location: /Users/daniel/Desktop/Jarvis-Voice-Assistant
```

### 2. View the Conversation Tree

```bash
python3 context_manager.py tree
```

Output shows the full conversation tree with all branches:
```
CONVERSATION TREE: jarvis-voice-assistant
======================================================================
Root Goal: Build maximum-intelligence offline voice assistant
Current Node: context-management
======================================================================

● main: Build maximum-intelligence offline voice assistant
   Chunks: 3 | Children: 3
├── ✓ wake-word: Implement wake word detection
├──    Chunks: 2 | Children: 0
├── ✓ performance: Optimize performance
├──    Chunks: 2 | Children: 1
    └── ✓ smart-router: Smart model routing
└── ● collaboration: Collaboration tools
    └── ● context-management: Context management system ← CURRENT
```

**Legend:**
- `●` = Active/in-progress
- `✓` = Completed
- `← CURRENT` = Current location in tree

### 3. Navigate the Tree

Jump to any node:
```bash
# Go to wake word branch
python3 context_manager.py goto wake-word

# Go back to main
python3 context_manager.py goto main

# Go to performance branch
python3 context_manager.py goto performance
```

### 4. Read Conversation Chunks

```bash
# Read a specific chunk
python3 context_manager.py chunk read main-001.md

# Read all chunks from wake-word branch
python3 context_manager.py chunk read wake-001.md
python3 context_manager.py chunk read wake-002.md
```

---

## CLI Commands

### Project Management

**List all projects:**
```bash
python3 context_manager.py project list
```

**Create new project:**
```bash
python3 context_manager.py project create \
  --id my-website \
  --name "My Website" \
  --description "Personal portfolio website" \
  --goal "Build beautiful responsive website" \
  --location ~/Desktop/My-Website
```

**Switch to different project:**
```bash
python3 context_manager.py project use my-website
```

**Show current active project:**
```bash
python3 context_manager.py project current
```

### Tree Navigation

**Show conversation tree:**
```bash
# Text format (default)
python3 context_manager.py tree

# JSON format
python3 context_manager.py tree --format json

# For specific project
python3 context_manager.py tree --project my-website
```

**Navigate to node:**
```bash
python3 context_manager.py goto wake-word
python3 context_manager.py goto main
python3 context_manager.py goto --project my-website homepage
```

### Branching

**Create new branch:**
```bash
# Auto-generated branch ID
python3 context_manager.py branch "Add voice cloning feature"

# Custom branch ID
python3 context_manager.py branch "Add voice cloning" --id voice-clone

# Branch from specific parent
python3 context_manager.py branch "Optimize TTS" --parent performance

# For specific project
python3 context_manager.py branch "New feature" --project my-website
```

### Chunk Management

**Create new chunk:**
```bash
# Simple content
python3 context_manager.py chunk create "Implemented voice cloning using Coqui TTS"

# For specific node
python3 context_manager.py chunk create "Content..." --node voice-clone

# For specific project
python3 context_manager.py chunk create "Content..." --project my-website
```

**Read chunk:**
```bash
python3 context_manager.py chunk read main-001.md
python3 context_manager.py chunk read --project my-website homepage-001.md
```

---

## Understanding the Tree Structure

### Nodes

Each node in the tree represents a topic or goal:

**Root Node ("main"):**
- Top-level goal for the project
- Always exists
- Starting point for all branches

**Branch Nodes:**
- Subtopics branching off from parent
- Can have their own children (sub-branches)
- Track status (active/completed)

**Node Properties:**
```json
{
  "id": "wake-word",
  "type": "branch",
  "parent": "main",
  "goal": "Implement wake word detection",
  "chunks": ["wake-001.md", "wake-002.md"],
  "children": [],
  "status": "completed",
  "created": "2025-12-09T..."
}
```

### Chunks

Chunks are conversation segments saved as markdown files:

**Chunk Structure:**
```markdown
# Chunk: wake-001.md

**Node:** wake-word
**Goal:** Implement wake word detection
**Created:** 2025-12-09T10:30:00

---

[Your conversation content here]
```

**When to create chunks:**
- Major milestone completed
- Switching topics/branches
- End of work session
- Periodically during long conversations

---

## Example Workflows

### Workflow 1: Working on New Feature

**Scenario:** You want to add voice cloning to JARVIS

```bash
# 1. Make sure you're on the right project
python3 context_manager.py project use jarvis-voice-assistant

# 2. Create a new branch for voice cloning
python3 context_manager.py branch "Add voice cloning feature" --id voice-clone

# 3. Work on implementation...
# (Chat with Claude, implement code)

# 4. Save progress as a chunk
python3 context_manager.py chunk create "Implemented voice cloning using Coqui TTS. Trained on 10 minutes of audio. Works well for short responses."

# 5. View tree to see progress
python3 context_manager.py tree
```

**Result:**
```
● main: Build JARVIS
   ...
└── ● voice-clone: Add voice cloning feature ← CURRENT
    └── Chunks: 1 | Children: 0
```

### Workflow 2: Returning to Previous Work

**Scenario:** You need to remember what you did with wake word detection

```bash
# 1. Navigate to wake-word branch
python3 context_manager.py goto wake-word

# 2. Read the chunks
python3 context_manager.py chunk read wake-001.md
python3 context_manager.py chunk read wake-002.md

# 3. Now you remember: Porcupine vs energy-based detection!

# 4. Go back to what you were working on
python3 context_manager.py goto context-management
```

### Workflow 3: Starting New Project

**Scenario:** You want to build a website

```bash
# 1. Create project folder
mkdir ~/Desktop/My-Website

# 2. Create project in context manager
python3 context_manager.py project create \
  --id my-website \
  --name "My Website" \
  --description "Personal portfolio website" \
  --goal "Build beautiful responsive website with React" \
  --location ~/Desktop/My-Website

# 3. Start working (creates chunks in new project tree)
python3 context_manager.py chunk create "Set up React project with Vite. Installed TailwindCSS."

# 4. Create branches as needed
python3 context_manager.py branch "Design homepage"
python3 context_manager.py branch "Build contact form"

# 5. Switch between projects anytime
python3 context_manager.py project use jarvis-voice-assistant
python3 context_manager.py project use my-website
```

---

## File Formats

### projects.json

Registry of all projects:

```json
{
  "projects": [
    {
      "id": "jarvis-voice-assistant",
      "name": "Jarvis Voice Assistant",
      "description": "Offline voice assistant...",
      "created": "2025-12-09T...",
      "last_active": "2025-12-09T...",
      "root_goal": "Build maximum-intelligence offline voice assistant",
      "file_location": "/Users/daniel/Desktop/Jarvis-Voice-Assistant",
      "status": "active"
    }
  ],
  "active_project": "jarvis-voice-assistant",
  "created": "2025-12-09T...",
  "last_modified": "2025-12-09T..."
}
```

### tree.json

Conversation tree for each project:

```json
{
  "project_id": "jarvis-voice-assistant",
  "root_goal": "Build maximum-intelligence offline voice assistant",
  "created": "2025-12-09T...",
  "nodes": {
    "main": {
      "id": "main",
      "type": "root",
      "goal": "Build maximum-intelligence offline voice assistant",
      "chunks": ["main-001.md", "main-002.md"],
      "children": ["wake-word", "performance"],
      "created": "2025-12-09T..."
    },
    "wake-word": {
      "id": "wake-word",
      "type": "branch",
      "parent": "main",
      "branched_at": "main-001.md",
      "goal": "Implement wake word detection",
      "chunks": ["wake-001.md", "wake-002.md"],
      "children": [],
      "status": "completed",
      "created": "2025-12-09T..."
    }
  },
  "current_node": "wake-word",
  "chunk_counter": {
    "main": 2,
    "wake": 2
  }
}
```

---

## Advanced Usage

### Resuming from Previous Context

When starting a fresh Claude session, you can provide conversation history:

**Manual Method:**
1. Navigate to the relevant node
2. Read the chunks for that branch
3. Copy/paste content to Claude in new session

**Future Enhancement:**
Automated context loading script (coming soon!)

### Visualizing the Tree

The `tree` command shows ASCII art, but you can also:

**Export as JSON and visualize:**
```bash
python3 context_manager.py tree --format json > tree.json
# Import into visualization tool
```

**Manual visualization:**
Open chunks folder and browse markdown files

### Merging Branches

Currently manual - copy content from one branch to another:

```bash
# Read chunk from branch
python3 context_manager.py chunk read feature-001.md

# Navigate to target
python3 context_manager.py goto main

# Create new chunk with merged content
python3 context_manager.py chunk create "Merged feature XYZ: ..."
```

---

## Best Practices

### 1. Create Meaningful Branch Names

**Good:**
- "Add voice cloning feature"
- "Optimize database queries"
- "Implement user authentication"

**Bad:**
- "Stuff"
- "Work"
- "Branch 1"

### 2. Chunk at Natural Break Points

Create chunks when:
- ✅ Completing a milestone
- ✅ Switching topics
- ✅ End of day/session
- ✅ Before asking Claude to switch gears

Don't chunk:
- ❌ Mid-conversation
- ❌ Before completing a thought
- ❌ Too frequently (clutters tree)

### 3. Use Descriptive Chunk Content

Include in chunks:
- What was accomplished
- Key decisions made
- Files created/modified
- Next steps
- Errors encountered and solutions

### 4. Keep Tree Clean

- Mark branches as completed when done
- Don't create unnecessary branches
- Use sub-branches for related subtopics

### 5. One Project Per Root Goal

**Good project separation:**
- Project 1: "Build JARVIS voice assistant"
- Project 2: "Create personal website"
- Project 3: "Automate home with Home Assistant"

**Bad (too granular):**
- Project 1: "JARVIS wake word"
- Project 2: "JARVIS TTS"
- Project 3: "JARVIS LLM"
→ These should be branches in one project!

---

## Troubleshooting

### Project not found

```bash
python3 context_manager.py project list
# Verify project ID exists
```

### Cannot create branch

Make sure you're on a valid parent node:
```bash
python3 context_manager.py tree
# Check current node
```

### Chunks not saving

Check permissions:
```bash
ls -la ~/Desktop/Claude-Projects/projects/*/chunks/
```

### Tree looks wrong

View as JSON to debug:
```bash
python3 context_manager.py tree --format json
```

---

## Future Enhancements

Planned features:

1. **Auto-context loading** - Start Claude with full context from any node
2. **Visual tree browser** - Web UI for exploring conversation tree
3. **Search across chunks** - Find specific conversations
4. **Export/import** - Share project trees with others
5. **Merge branches** - Automated branch merging
6. **Statistics** - Track time spent, chunks created, branches completed
7. **Tags** - Tag chunks for easy filtering
8. **Reminders** - Set goals/reminders for project milestones

---

## Integration with Claude

### Current Workflow

1. **Before starting work:**
   ```bash
   # Set active project
   python3 context_manager.py project use jarvis-voice-assistant

   # View tree to remember where you are
   python3 context_manager.py tree

   # Read relevant chunks
   python3 context_manager.py chunk read main-003.md
   ```

2. **During work:**
   - Chat with Claude normally
   - Create branches for new topics
   - Create chunks at milestones

3. **After work session:**
   ```bash
   # Save final chunk
   python3 context_manager.py chunk create "Session summary: ..."

   # View updated tree
   python3 context_manager.py tree
   ```

### Future: Automated Integration

Goal: Claude automatically saves chunks and manages tree

```bash
# Start Claude session with auto-chunking
python3 jarvis_with_context.py

# Claude automatically:
# - Loads context from current node
# - Saves chunks periodically
# - Updates tree structure
# - Suggests branch creation
# - Warns when far from root goal
```

---

## Summary

The Context Management System gives you:

✅ **Never lose context** - All conversations preserved
✅ **Navigate freely** - Jump to any previous point
✅ **See the big picture** - Visual tree of all work
✅ **Multiple projects** - Separate contexts for different work
✅ **Resume anywhere** - Pick up exactly where you left off
✅ **Track progress** - See what's done, what's active

**Think of it as Git for conversations with Claude!**

---

## Quick Reference

```bash
# Project management
python3 context_manager.py project list
python3 context_manager.py project use <project-id>
python3 context_manager.py project current

# Navigation
python3 context_manager.py tree
python3 context_manager.py goto <node-id>

# Branching
python3 context_manager.py branch "<goal>"

# Chunks
python3 context_manager.py chunk create "<content>"
python3 context_manager.py chunk read <chunk-name>
```

---

**Created:** 2025-12-09
**Author:** Claude & Daniel
**Version:** 1.0
