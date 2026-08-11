#!/bin/bash
# ============================================================================
#  restart_gui_mac.command
#
#  Restarts the Sequence Builder / Timeline server ON THIS MAC, running the
#  files straight out of this folder. Then it prints the address to type into
#  the tablet.
#
#  Double-click this file in Finder to run it.
#
#  WHY THIS EXISTS
#  ---------------
#  While the Pi is offsite, the Mac is playing the part of the Pi. There is
#  nothing to copy anywhere — the Mac reads the same files Claude edits, right
#  here in /Users/michael/Projects/OhbotPi2. The only thing that needs to
#  happen after an edit is for the server to be stopped and started again, so
#  it picks up the changes.
#
#  (Edits to the web pages themselves usually only need a browser refresh.
#  Edits to gui_server.py always need this restart.)
#
#  Leave this window OPEN while you're testing — closing it stops the server.
#  Press Control-C in the window to stop.
# ============================================================================

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'
ok()   { echo -e "  ${GREEN}✓${RESET}  $1"; }
bad()  { echo -e "  ${RED}✗${RESET}  $1"; }
warn() { echo -e "  ${YELLOW}⚠${RESET}   $1"; }

DIR="/Users/michael/Projects/OhbotPi2"
cd "$DIR" || { echo "Can't find $DIR"; read -p "Press Return. "; exit 1; }

echo ""
echo -e "${BOLD}${CYAN}  Sequence Builder — running on this Mac${RESET}"
echo -e "  folder: $DIR"
echo ""

# ── Which Python? ───────────────────────────────────────────────────────────
# SETUP_MacOS.md sets up a private Python at ~/yobot-venv. Use it if it's
# there, otherwise fall back to the system one.
if [ -x "$HOME/yobot-venv/bin/python3" ]; then
  PY="$HOME/yobot-venv/bin/python3"
  ok "using Yobot's own Python (~/yobot-venv)"
else
  PY="python3"
  warn "~/yobot-venv not found — using the system python3"
fi

# ── Stop anything already serving on port 5001 ──────────────────────────────
OLD=$(pgrep -f "gui_server.py" 2>/dev/null)
if [ -n "$OLD" ]; then
  kill $OLD 2>/dev/null
  sleep 1
  # still there? insist.
  pgrep -f "gui_server.py" >/dev/null 2>&1 && kill -9 $(pgrep -f "gui_server.py") 2>/dev/null
  ok "stopped the old server"
else
  ok "nothing was running"
fi

# ── The address for the tablet ──────────────────────────────────────────────
IP=$(ipconfig getifaddr en0 2>/dev/null)
[ -z "$IP" ] && IP=$(ipconfig getifaddr en1 2>/dev/null)

echo ""
echo -e "${BOLD}  On this Mac:${RESET}"
echo -e "     http://localhost:5001/gui"
echo ""
if [ -n "$IP" ]; then
  echo -e "${BOLD}  On the tablet (same wifi):${RESET}"
  echo -e "     http://${IP}:5001/gui"
  echo ""
  echo -e "  Useful extras you can add to the end of that address:"
  echo -e "     ${CYAN}?size=1${RESET}      show the screen-size readout"
  echo -e "     ${CYAN}?kiosk=1${RESET}     first tap anywhere goes full screen"
  echo -e "     ${CYAN}?compact=0${RESET}   force the full desktop layout"
else
  warn "Couldn't work out this Mac's wifi address."
  echo "     System Settings -> Wi-Fi -> Details will show it."
fi
echo ""
echo -e "  ${BOLD}Leave this window open.${RESET} Control-C here stops the server."
echo -e "  ─────────────────────────────────────────────────────────────"
echo ""

# ── Go ──────────────────────────────────────────────────────────────────────
exec "$PY" "$DIR/gui_server.py"
