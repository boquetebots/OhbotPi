#!/bin/bash
# ============================================================================
#  deploy_local_files.command
#
#  Copies the handful of files that git deliberately does NOT carry from the
#  Mac to the Pi. Double-click this file in Finder to run it.
#
#  WHY THIS EXISTS
#  ---------------
#  Some files are kept out of GitHub on purpose, because the repo is public:
#
#    .env                     your OpenAI and Azure API keys
#    library_knowledge.json   library facts — INCLUDING the guest WiFi password
#                             and the library's phone and WhatsApp numbers
#
#  And some are kept out because they describe THIS machine, and sharing them
#  would let the Mac overwrite the Pi's own settings:
#
#    ohbotData/active_robot.txt   which robot profile is loaded
#    ohbotData/language.txt       English or Spanish
#
#  All of these still need to be ON THE PI for the robot to work properly.
#  Yobot cannot answer library questions without library_knowledge.json.
#  So: git carries the code, and this script carries the rest.
#
#  Run this after every fresh Pi build, and any time you edit one of the
#  files listed above.
# ============================================================================

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'
ok()   { echo -e "  ${GREEN}✓${RESET}  $1"; }
bad()  { echo -e "  ${RED}✗${RESET}  $1"; }
warn() { echo -e "  ${YELLOW}⚠${RESET}   $1"; }

# ── Where things live ───────────────────────────────────────────────────────
MACDIR="/Users/michael/Projects/OhbotPi2"
PIUSER="yobot"
PIDIR="/home/yobot/Projects/Ohbot"

clear
echo ""
echo -e "${BOLD}${CYAN}  Copy local-only files to the Pi${RESET}"
echo ""
echo "  These files are kept off GitHub on purpose (they hold passwords),"
echo "  so they have to be copied across by hand. That's what this does."
echo ""

# ── Which Pi? ───────────────────────────────────────────────────────────────
echo -e "  ${BOLD}What is the Pi's address?${RESET}"
echo "  Press Enter to use pibot.local, or type an IP like 192.168.50.155"
echo ""
echo -n "  Address [pibot.local]: "
read -r PIHOST
if [ -z "$PIHOST" ]; then PIHOST="pibot.local"; fi
echo ""

# ── Can we reach it? ────────────────────────────────────────────────────────
echo "  Checking we can reach $PIHOST ..."
if ! ssh -o ConnectTimeout=8 -o BatchMode=yes "$PIUSER@$PIHOST" "echo ok" &>/dev/null; then
    echo ""
    bad "Can't reach $PIUSER@$PIHOST"
    echo ""
    echo "  Things to try, in order:"
    echo ""
    echo "    1. Use the IP address instead of pibot.local. If you don't know"
    echo "       it, listen to the robot — it says its address out loud about"
    echo "       30 seconds after you plug it in."
    echo ""
    echo "    2. Make sure the Mac and the Pi are on the same WiFi."
    echo ""
    echo "    3. If you just rebuilt the Pi, the Mac may be refusing to connect"
    echo "       because the machine changed. Clear the old record with:"
    echo "           ssh-keygen -R $PIHOST"
    echo "       then run this script again."
    echo ""
    echo "  Press Enter to close."
    read -r
    exit 1
fi
ok "Connected to $PIUSER@$PIHOST"
echo ""

# ── Copy each file ──────────────────────────────────────────────────────────
# Format: "source path relative to MACDIR"
FILES=(
  ".env"
  "library_knowledge.json"
  "ohbotData/active_robot.txt"
  "ohbotData/language.txt"
)

COPIED=0
SKIPPED=0

echo -e "  ${BOLD}Copying:${RESET}"
echo ""

for f in "${FILES[@]}"; do
    SRC="$MACDIR/$f"

    if [ ! -f "$SRC" ]; then
        warn "$f — not on the Mac, skipping"
        SKIPPED=$((SKIPPED+1))
        continue
    fi

    # Make sure the folder exists on the Pi before copying into it.
    SUBDIR=$(dirname "$f")
    if [ "$SUBDIR" != "." ]; then
        ssh "$PIUSER@$PIHOST" "mkdir -p '$PIDIR/$SUBDIR'" 2>/dev/null
    fi

    if scp -q "$SRC" "$PIUSER@$PIHOST:$PIDIR/$f" 2>/dev/null; then
        ok "$f"
        COPIED=$((COPIED+1))
    else
        bad "$f — copy failed"
        SKIPPED=$((SKIPPED+1))
    fi
done

# ── Lock down the keys file ─────────────────────────────────────────────────
echo ""
ssh "$PIUSER@$PIHOST" "chmod 600 '$PIDIR/.env' 2>/dev/null" 2>/dev/null
ok "API keys file locked to your user only"

# ── Report ──────────────────────────────────────────────────────────────────
echo ""
echo -e "  ${BOLD}Copied $COPIED file(s). Skipped $SKIPPED.${RESET}"
echo ""

if [ "$COPIED" -gt 0 ]; then
    echo "  The robot needs a restart to pick these up. Do it from the"
    echo "  Launcher page, or run this on the Pi:"
    echo ""
    echo "      systemctl --user restart ohbot-launcher"
    echo ""
fi

echo "  Press Enter to close."
read -r
