#!/bin/bash
# ============================================================================
#  deploy_gui_page.command
#
#  Pushes JUST the two Sequence Builder / Timeline web pages from the Mac to
#  the Pi, then restarts the GUI so the change goes live.
#
#  Double-click this file in Finder to run it.
#
#  WHY THIS EXISTS
#  ---------------
#  When we're tweaking how the page LOOKS, the loop is: Claude edits the file
#  on the Mac, you run this, you refresh the tablet, you say what's still
#  wrong. Going through GitHub for that would be three extra steps each time.
#  This is the short way round. Nothing else on the Pi is touched.
# ============================================================================

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'
ok()   { echo -e "  ${GREEN}✓${RESET}  $1"; }
bad()  { echo -e "  ${RED}✗${RESET}  $1"; }
warn() { echo -e "  ${YELLOW}⚠${RESET}   $1"; }

MACDIR="/Users/michael/Projects/OhbotPi2"
PIUSER="yobot"
PIHOST="192.168.50.155"
PIDIR="/home/yobot/Projects/Ohbot"

echo ""
echo -e "${BOLD}${CYAN}  Deploy GUI pages to the Pi${RESET}"
echo -e "  ${PIUSER}@${PIHOST}:${PIDIR}"
echo ""

# ── Is the Pi awake? ────────────────────────────────────────────────────────
if ! ping -c 1 -W 2000 "$PIHOST" > /dev/null 2>&1; then
  bad "Can't reach the Pi at $PIHOST."
  echo "     Is it powered on and on the same network?"
  echo ""
  read -p "  Press Return to close. "
  exit 1
fi
ok "Pi is reachable"

# ── Copy the pages ──────────────────────────────────────────────────────────
FAILED=0
for f in gui/index.html gui/timeline.html gui/icon-192.png gui/icon-512.png i18n.js gui_server.py; do
  if [ ! -f "$MACDIR/$f" ]; then
    warn "$f not found on the Mac — skipped"
    continue
  fi
  if scp -q "$MACDIR/$f" "${PIUSER}@${PIHOST}:${PIDIR}/$f"; then
    ok "copied $f"
  else
    bad "failed to copy $f"
    FAILED=1
  fi
done

if [ "$FAILED" = "1" ]; then
  echo ""
  bad "Something didn't copy. Nothing was restarted."
  read -p "  Press Return to close. "
  exit 1
fi

# ── Restart the GUI so it serves the new files ──────────────────────────────
echo ""
if ssh "${PIUSER}@${PIHOST}" "systemctl --user restart ohbot-gui" 2>/dev/null; then
  ok "GUI restarted"
else
  warn "Couldn't restart the GUI service."
  echo "     It may not be running right now — start it from the Launcher page."
fi

echo ""
echo -e "${BOLD}${GREEN}  Done.${RESET}"
echo ""
echo -e "  Now on the tablet, ${BOLD}hard-refresh${RESET} the page or you'll just see"
echo -e "  the old cached copy:"
echo ""
echo -e "     http://${PIHOST}:5001/gui"
echo ""
echo -e "  In Chrome on Android: tap ⋮ → the circular-arrow refresh, or open"
echo -e "  the page in a new Incognito tab to be certain."
echo ""
read -p "  Press Return to close. "
