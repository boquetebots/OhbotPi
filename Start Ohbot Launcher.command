#!/bin/bash
# Double-click this file to start the Ohbot Launcher and open it in your browser.
# Close this Terminal window (or press Ctrl-C) to stop the launcher.

cd "/Users/michael/Projects/OhbotPi2" || {
    echo "Could not find /Users/michael/Projects/OhbotPi2"
    read -p "Press Enter to close this window..."
    exit 1
}

# Use Yobot's own Python environment if it exists (has Flask etc. installed),
# otherwise fall back to the Mac's plain python3.
if [ -x "$HOME/yobot-venv/bin/python3" ]; then
    PYTHON="$HOME/yobot-venv/bin/python3"
else
    PYTHON="python3"
fi

echo "Starting Ohbot Launcher (using: $PYTHON)"
echo ""

# Start the launcher server in the background, then open its page in the
# browser once it's had a moment to come up.
"$PYTHON" launcher_server.py &
SERVER_PID=$!

# If this window is closed or Ctrl-C is pressed, stop the server too.
trap "kill $SERVER_PID 2>/dev/null" EXIT

sleep 2
open "http://localhost:5000"

# Keep this window open, showing the server's log, until it's stopped.
wait $SERVER_PID
