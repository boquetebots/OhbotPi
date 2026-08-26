#!/bin/bash
# Double-click this file to start the Ohbot Launcher and open it in your browser.
# Close this Terminal window (or press Ctrl-C) to stop the launcher.

# --- Find the project folder ------------------------------------------------
# Works whether this file sits in the Mac folder or in the main project folder.
HERE="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$HERE/launcher_server.py" ]; then
    PROJ="$HERE"
elif [ -f "$HERE/../launcher_server.py" ]; then
    PROJ="$(cd "$HERE/.." && pwd)"
else
    echo "Could not find the Yobot project files."
    echo "Looked in: $HERE"
    echo "       and: $HERE/.."
    echo
    echo "This file belongs in the project's Mac folder."
    read -p "Press Enter to close this window..."
    exit 1
fi

cd "$PROJ" || exit 1

# Use Yobot's own Python environment if it exists, otherwise plain python3.
if [ -x "$HOME/yobot-venv/bin/python3" ]; then
    PYTHON="$HOME/yobot-venv/bin/python3"
else
    PYTHON="python3"
fi

echo "Starting Ohbot Launcher"
echo "   project: $PROJ"
echo "   python : $PYTHON"
echo ""

"$PYTHON" launcher_server.py &
SERVER_PID=$!
trap "kill $SERVER_PID 2>/dev/null" EXIT

sleep 2
open "http://localhost:5000"

wait $SERVER_PID
