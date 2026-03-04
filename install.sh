#!/bin/bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_NAME="com.claude-tg-bridge.plist"
PLIST_DST="$HOME/Library/LaunchAgents/$PLIST_NAME"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python3"

echo "=== Claude TG Bridge Installer ==="

# Create venv if needed
if [ ! -d "$PROJECT_DIR/.venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$PROJECT_DIR/.venv"
fi

echo "Installing dependencies..."
"$PROJECT_DIR/.venv/bin/pip" install -q -r "$PROJECT_DIR/requirements.txt"

# Create logs dir
mkdir -p "$PROJECT_DIR/logs"

# Generate plist with correct paths
echo "Generating LaunchAgent plist..."
cat > "$PLIST_DST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.claude-tg-bridge</string>
    <key>ProgramArguments</key>
    <array>
        <string>${VENV_PYTHON}</string>
        <string>${PROJECT_DIR}/bot.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${PROJECT_DIR}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    <key>ThrottleInterval</key>
    <integer>10</integer>
    <key>StandardOutPath</key>
    <string>${PROJECT_DIR}/logs/stdout.log</string>
    <key>StandardErrorPath</key>
    <string>${PROJECT_DIR}/logs/stderr.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
PLIST

# Unload existing if present
if launchctl list 2>/dev/null | grep -q "com.claude-tg-bridge"; then
    echo "Unloading existing service..."
    launchctl unload "$PLIST_DST" 2>/dev/null || true
fi

echo "Loading service..."
launchctl load "$PLIST_DST"

echo ""
echo "Done! Bot is running."
echo "  Logs: $PROJECT_DIR/logs/"
echo "  Stop: launchctl unload $PLIST_DST"
echo "  Start: launchctl load $PLIST_DST"
