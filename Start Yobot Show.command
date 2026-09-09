#!/bin/bash
#
# Start Yobot Show.command
#
# Double-click this to start the offline demo show and open the button page.
# Safe to keep on the Desktop — it finds the project on its own.
#
# Close the Terminal window (or press Ctrl-C) to stop the show.
#
# Version 1.0.0 — 2026-09-02

printf '\033]0;Yobot Show\007'          # names the Terminal window

PORT=5004

say_err() {
    echo ""
    echo "──────────────────────────────────────────────────────────"
    echo "  $1"
    echo "──────────────────────────────────────────────────────────"
    echo ""
    read -p "Press Enter to close this window..."
    exit 1
}

# ── Find the project ────────────────────────────────────────────────────────
# Works from the Desktop, from inside the project, or from the Mac folder.
HERE="$(cd "$(dirname "$0")" && pwd)"
PROJ=""
for CANDIDATE in "$HERE" "$HERE/.." "$HOME/Projects/OhbotPi2" "$HOME/Projects/Ohbot"; do
    if [ -f "$CANDIDATE/show_server.py" ]; then
        PROJ="$(cd "$CANDIDATE" && pwd)"
        break
    fi
done

[ -z "$PROJ" ] && say_err "Could not find the Yobot project (show_server.py).
  Looked next to this file and in ~/Projects/OhbotPi2.
  If the project has moved, edit the paths near the top of this file."

cd "$PROJ" || say_err "Could not open $PROJ"

# ── Yobot's own Python ──────────────────────────────────────────────────────
if [ -x "$HOME/yobot-venv/bin/python3" ]; then
    PYTHON="$HOME/yobot-venv/bin/python3"
else
    PYTHON="python3"
    echo "⚠️  Yobot's own Python was not found — falling back to plain python3."
    echo "   If this fails with 'no module named flask', that is why."
    echo ""
fi

echo "──────────────────────────────────────────────────────────"
echo "  YOBOT SHOW"
echo "  project: $PROJ"
echo "──────────────────────────────────────────────────────────"
echo ""

# ── Is something already holding the robot? ─────────────────────────────────
# Only ONE program can own the USB serial cable. This is the single most
# common reason the robot "isn't found", so check before we start, not after.
BUSY=""
for P in ohbot_chat.py gui_server.py timeline_server.py calibration_server.py; do
    pgrep -f "$P" > /dev/null 2>&1 && BUSY="$BUSY $P"
done
if [ -n "$BUSY" ]; then
    echo "⚠️  Something else is already using the robot:$BUSY"
    echo "   Only one program can hold the USB cable at a time."
    echo "   Stop it from the Launcher page, then run this again."
    echo ""
    read -p "   Press Enter to try anyway, or close this window to stop. "
    echo ""
fi

# ── Is the show already running? ────────────────────────────────────────────
if lsof -ti tcp:$PORT > /dev/null 2>&1; then
    echo "The show is already running. Opening the page instead."
    open "http://localhost:$PORT"
    echo ""
    read -p "Press Enter to close this window..."
    exit 0
fi

# ── Are the recordings there? ───────────────────────────────────────────────
CACHED=$(ls voice_cache/*.wav 2>/dev/null | wc -l | tr -d ' ')
if [ "$CACHED" = "0" ]; then
    echo "⚠️  NOTHING IS RECORDED YET — Yobot will not be able to speak."
    echo ""
    echo "   While you still have internet, run this once:"
    echo "       $PYTHON prerender_cues.py"
    echo ""
    read -p "   Press Enter to start anyway, or close this window. "
    echo ""
else
    echo "Recorded lines: $CACHED"
fi

# ── Which robot's calibration? ──────────────────────────────────────────────
CURRENT=$(cat ohbotData/active_robot.txt 2>/dev/null)
[ -z "$CURRENT" ] && CURRENT="(unnamed)"
echo ""
echo "Calibration currently loaded: $CURRENT"
read -p "Robot name to load, or press Enter to keep $CURRENT: " ROBOT

ARGS=""
if [ -n "$ROBOT" ]; then
    ARGS="--robot $ROBOT"
fi

# ── Go ──────────────────────────────────────────────────────────────────────
echo ""
echo "Starting…"
echo ""

"$PYTHON" show_server.py $ARGS &
SERVER_PID=$!
trap 'kill $SERVER_PID 2>/dev/null' EXIT

# Wait for the server to actually answer before opening the browser, rather
# than guessing with a fixed sleep. Connecting to the robot can take a moment.
for i in $(seq 1 40); do
    if curl -s -o /dev/null "http://localhost:$PORT/api/status"; then
        open "http://localhost:$PORT"
        break
    fi
    kill -0 $SERVER_PID 2>/dev/null || break     # it died — let the log show why
    sleep 0.5
done

wait $SERVER_PID

echo ""
echo "The show has stopped."
read -p "Press Enter to close this window..."
