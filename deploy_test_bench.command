#!/bin/bash
# ============================================================================
#  deploy_test_bench.command
#
#  Copies the TWO TEST FILES to the Pi and nothing else. Double-click in Finder.
#
#      chat_test.py     the typing test bench
#      reword.py        the rewording engine (switched off)
#
#  WHY THIS IS SEPARATE FROM deploy_local_files.command
#  ----------------------------------------------------
#  deploy_local_files.command also copies library_knowledge.json — which would
#  push the edited keywords onto the live robot. This script deliberately does
#  NOT touch the JSON files, the .env, or anything the robot runs on. It copies
#  two test scripts that nothing else calls.
#
#  So it is safe to run at any time, including the morning of a demo. When you
#  are happy with the keyword edits and want them on the robot, run
#  deploy_local_files.command instead.
#
#  THEN, on the Pi:
#      ssh yobot@pibot.local
#      cd ~/Projects/Ohbot
#      python3 chat_test.py --vs
# ============================================================================

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'
ok()   { echo -e "  ${GREEN}✓${RESET}  $1"; }
bad()  { echo -e "  ${RED}✗${RESET}  $1"; }
warn() { echo -e "  ${YELLOW}⚠${RESET}   $1"; }

MACDIR="/Users/michael/Projects/OhbotPi2"
PIUSER="yobot"
PIDIR="/home/yobot/Projects/Ohbot"

clear
echo ""
echo -e "${BOLD}${CYAN}  Copy the test bench to the Pi${RESET}"
echo ""
echo "  Copies chat_test.py and reword.py only."
echo "  Does NOT touch the JSON files or anything the robot runs on."
echo ""

echo -e "  ${BOLD}What is the Pi's address?${RESET}"
echo "  Press Enter to use pibot.local, or type an IP like 192.168.50.155"
echo ""
echo -n "  Address [pibot.local]: "
read -r PIHOST
if [ -z "$PIHOST" ]; then PIHOST="pibot.local"; fi
echo ""

# One shared SSH connection so you type the password once, not three times.
# (Do NOT add BatchMode=yes — see the note in deploy_local_files.command.)
CTL="/tmp/ohbot-ssh-%r@%h:%p"
SSH_OPTS=(-o ConnectTimeout=10
          -o ControlMaster=auto
          -o ControlPath="$CTL"
          -o ControlPersist=120)

echo "  Connecting to $PIUSER@$PIHOST ..."
echo "  (type your Pi password if it asks)"
echo ""

if ! ssh "${SSH_OPTS[@]}" "$PIUSER@$PIHOST" "echo ok" >/dev/null; then
    echo ""
    bad "Can't reach $PIUSER@$PIHOST"
    echo ""
    echo "  Same troubleshooting as deploy_local_files.command:"
    echo "    - is the Pi on the same WiFi?"
    echo "    - is the address right? Run 'hostname -I' on the Pi, or listen"
    echo "      to what the robot says when it boots."
    echo "    - if the Mac complains the machine changed: ssh-keygen -R $PIHOST"
    echo ""
    echo "  Press Enter to close."
    read -r
    exit 1
fi
ok "Connected to $PIUSER@$PIHOST"
echo ""

FILES=("chat_test.py" "reword.py")
COPIED=0

echo -e "  ${BOLD}Copying:${RESET}"
echo ""

for f in "${FILES[@]}"; do
    SRC="$MACDIR/$f"
    if [ ! -f "$SRC" ]; then
        warn "$f — not on the Mac, skipping"
        continue
    fi
    if scp -q -o ControlPath="$CTL" "$SRC" "$PIUSER@$PIHOST:$PIDIR/$f"; then
        ok "$f"
        COPIED=$((COPIED+1))
    else
        bad "$f — copy failed"
    fi
done

echo ""

# ── Check the Pi can actually run it ────────────────────────────────────────
echo -e "  ${BOLD}Checking the Pi has what it needs:${RESET}"
echo ""
ssh "${SSH_OPTS[@]}" "$PIUSER@$PIHOST" \
    "cd '$PIDIR' && python3 -c \"
import importlib, sys
for m in ('openai',):
    try:
        importlib.import_module(m); print('  ok', m)
    except ImportError:
        print('  MISSING', m)
\"" 2>/dev/null || warn "couldn't check — try running the bench and see"

echo ""
echo -e "  ${BOLD}${GREEN}Copied $COPIED file(s).${RESET}"
echo ""
echo -e "  ${BOLD}Now run it on the Pi:${RESET}"
echo ""
echo -e "      ${CYAN}ssh $PIUSER@$PIHOST${RESET}"
echo -e "      ${CYAN}cd ~/Projects/Ohbot${RESET}"
echo -e "      ${CYAN}python3 chat_test.py --vs${RESET}"
echo ""
echo "  --vs shows the canned answer AND what the AI would say, side by side."
echo "  Add --doctor instead if anything looks wrong."
echo ""
echo "  Note: the Pi still has the OLD keyword lists. That's on purpose — this"
echo "  script doesn't deploy them. Run deploy_local_files.command when you're"
echo "  ready for the robot to use the new ones."
echo ""
echo "  Press Enter to close."
read -r
