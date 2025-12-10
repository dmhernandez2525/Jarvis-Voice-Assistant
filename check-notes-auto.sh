#!/bin/bash
# Automatic notes checker for Claude
# Returns whether notes should be read based on time elapsed

NOTES_FILE="$HOME/Desktop/Jarvis-Voice-Assistant/DANIEL_NOTES.md"
TRACKER_FILE="$HOME/Desktop/Jarvis-Voice-Assistant/.notes_tracker"

# Get current time
CURRENT_TIME=$(date +%s)

# Get last checked time
if [ -f "$TRACKER_FILE" ]; then
    source "$TRACKER_FILE"
else
    LAST_CHECKED=0
fi

# Convert LAST_CHECKED to timestamp if not numeric
if [[ ! "$LAST_CHECKED" =~ ^[0-9]+$ ]]; then
    LAST_CHECKED=0
fi

# Calculate time difference in minutes
TIME_DIFF=$(( (CURRENT_TIME - LAST_CHECKED) / 60 ))

# Get file modification time
if [ -f "$NOTES_FILE" ]; then
    FILE_MOD_TIME=$(stat -f %m "$NOTES_FILE" 2>/dev/null || stat -c %Y "$NOTES_FILE" 2>/dev/null)

    # Check if notes were modified since last check
    if [ "$LAST_CHECKED" != "0" ] && [ "$FILE_MOD_TIME" -gt "$LAST_CHECKED" ]; then
        echo "SHOULD_READ=yes (notes modified)"
        echo "REASON=Notes file was modified since last check"
        echo "TIME_SINCE_CHECK=${TIME_DIFF} minutes"
        exit 0
    fi
else
    echo "SHOULD_READ=no (file not found)"
    exit 1
fi

# Check if 10+ minutes have passed
if [ "$TIME_DIFF" -ge 10 ]; then
    echo "SHOULD_READ=yes (10+ minutes)"
    echo "REASON=10+ minutes elapsed since last check"
    echo "TIME_SINCE_CHECK=${TIME_DIFF} minutes"
    exit 0
else
    echo "SHOULD_READ=no"
    echo "REASON=Only ${TIME_DIFF} minutes since last check"
    echo "TIME_SINCE_CHECK=${TIME_DIFF} minutes"
    exit 1
fi
