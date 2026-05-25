#!/bin/bash
# Install or refresh ~/Desktop/Jarvis.app so double-clicking the icon
# launches the Pipecat full-duplex variant in iTerm2 (or Terminal as
# fallback).
#
# Idempotent: safe to re-run. Preserves an existing AppIcon.icns; only
# the MacOS/Jarvis launcher script is rewritten.
#
# To point the icon at a different variant instead (for example, the
# older one-shot gemma4 router), set:
#   JARVIS_ICON_TARGET=run-jarvis-gemma4.sh ./scripts/install-desktop-icon.sh

set -e

APP=~/Desktop/Jarvis.app
TARGET_SCRIPT="${JARVIS_ICON_TARGET:-run-jarvis-pipecat.sh}"

if [ ! -d "$APP" ]; then
    echo "Creating fresh Jarvis.app bundle at $APP"
    mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

    # Minimal Info.plist marking this as a menu-bar-style (LSUIElement)
    # app so it doesn't show in the Dock.
    cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>Jarvis</string>
    <key>CFBundleIdentifier</key>
    <string>com.jarvis.voiceassistant</string>
    <key>CFBundleName</key>
    <string>Jarvis</string>
    <key>CFBundleDisplayName</key>
    <string>Jarvis Voice Assistant</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>LSUIElement</key>
    <true/>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
</dict>
</plist>
PLIST
fi

# If there's already a launcher that isn't the standard Pipecat or Gemma
# wrapper, preserve it as a .legacy backup before overwriting.
EXEC="$APP/Contents/MacOS/Jarvis"
if [ -f "$EXEC" ] && [ ! -f "$APP/Contents/MacOS/Jarvis.legacy" ]; then
    cp "$EXEC" "$APP/Contents/MacOS/Jarvis.legacy"
    echo "Existing launcher saved as Jarvis.legacy"
fi

# Write the new launcher.
cat > "$EXEC" <<LAUNCHER
#!/bin/bash
# Jarvis.app desktop launcher. Installed by
#   ~/Desktop/Projects/Jarvis-Voice-Assistant/scripts/install-desktop-icon.sh
# Launches: $TARGET_SCRIPT

set -e

SCRIPT="\$HOME/Desktop/Projects/Jarvis-Voice-Assistant/$TARGET_SCRIPT"

if [ ! -x "\$SCRIPT" ]; then
    osascript -e "display alert \"Jarvis launch failed\" message \"$TARGET_SCRIPT not found or not executable at:\\n\$SCRIPT\" as critical"
    exit 1
fi

if [ -d "/Applications/iTerm.app" ]; then
    /usr/bin/osascript <<OSA
tell application "iTerm"
    activate
    create window with default profile
    tell current session of current window
        write text "cd \\"\$HOME/Desktop/Projects/Jarvis-Voice-Assistant\\" && ./$TARGET_SCRIPT"
    end tell
end tell
OSA
else
    /usr/bin/osascript <<OSA
tell application "Terminal"
    activate
    do script "cd \\"\$HOME/Desktop/Projects/Jarvis-Voice-Assistant\\" && ./$TARGET_SCRIPT"
end tell
OSA
fi
LAUNCHER

chmod +x "$EXEC"
touch "$APP"

echo ""
echo "=== Installed ==="
echo "  App:     $APP"
echo "  Target:  $TARGET_SCRIPT"
echo ""
echo "Double-click $APP on the Desktop to launch."
echo "The AppIcon (if any) at $APP/Contents/Resources/AppIcon.icns is preserved."
