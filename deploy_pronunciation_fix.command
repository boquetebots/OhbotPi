#!/bin/bash
# ============================================================================
#  deploy_pronunciation_fix.command
#
#  Copies the two pronunciation files to the Pi and offers to run the test.
#  Double-click this file in Finder to run it.
#
#  WHAT IT COPIES
#  --------------
#    ohbot_azure.py          holds the PHONEME_FIXES table (the actual fix)
#    test_pronunciation.py   makes before/after WAVs so you can hear it
#
#  These two ARE tracked by git, so the "proper" route is push-to-GitHub then
#  sync_pi_from_github.command. This script is the shortcut for when you just
#  want to hear a pronunciation change straight away. Push to git afterwards
#  so the Pi and the Mac don't drift apart.
#
#  Nothing here touches the motors or the serial cable, so it is safe to run
#  while the Greeter or the GUI is up.
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
echo -e "${BOLD}${CYAN}  Send the pronunciation fix to the Pi${RESET}"
echo ""
echo "  Teaches the English voice to say Boquete and Rincón properly."
echo ""

# ── Which Pi? ───────────────────────────────────────────────────────────────
echo -e "  ${BOLD}What is the Pi's address?${RESET}"
echo "  Press Enter to use pibot.local, or type an IP like 192.168.50.155"
echo ""
echo -n "  Address [pibot.local]: "
read -r PIHOST
if [ -z "$PIHOST" ]; then PIHOST="pibot.local"; fi
echo ""

# ── One shared SSH connection, so you type the password once ────────────────
# Do NOT add BatchMode=yes — it means "never ask for a password", which makes
# the script unusable until an SSH key exists.
CTL="/tmp/ohbot-ssh-%r@%h:%p"
SSH_OPTS=(-o ConnectTimeout=10
          -o ControlMaster=auto
          -o ControlPath="$CTL"
          -o ControlPersist=300)

echo "  Connecting to $PIUSER@$PIHOST ..."
echo "  (type your Pi password if it asks)"
echo ""

if ! ssh "${SSH_OPTS[@]}" "$PIUSER@$PIHOST" "echo ok" >/dev/null; then
    echo ""
    bad "Can't reach $PIUSER@$PIHOST"
    echo ""
    echo "  Things to try, in order:"
    echo ""
    echo "    1. Make sure the Mac and the Pi are on the same WiFi."
    echo ""
    echo "    2. Find the Pi's address — run this on the Pi:"
    echo "           hostname -I"
    echo "       or just listen; the robot says it aloud when it boots."
    echo ""
    echo "    3. If the Mac complains the machine has changed, clear the old"
    echo "       record and try again:"
    echo "           ssh-keygen -R $PIHOST"
    echo ""
    echo "  Press Enter to close."
    read -r
    exit 1
fi
ok "Connected to $PIUSER@$PIHOST"
echo ""

# ── Back up what's already there, then copy ─────────────────────────────────
FILES=(
  "ohbot_azure.py"
  "test_pronunciation.py"
)

echo -e "  ${BOLD}Copying:${RESET}"
echo ""

COPIED=0
FAILED=0

for f in "${FILES[@]}"; do
    SRC="$MACDIR/$f"

    if [ ! -f "$SRC" ]; then
        bad "$f — not on the Mac"
        FAILED=$((FAILED+1))
        continue
    fi

    # Keep one backup of the previous version, so a bad edit is undoable.
    ssh "${SSH_OPTS[@]}" "$PIUSER@$PIHOST" \
        "[ -f '$PIDIR/$f' ] && cp '$PIDIR/$f' '$PIDIR/$f.bak'" 2>/dev/null

    if scp -q -o ControlPath="$CTL" "$SRC" "$PIUSER@$PIHOST:$PIDIR/$f"; then
        ok "$f"
        COPIED=$((COPIED+1))
    else
        bad "$f — copy failed"
        FAILED=$((FAILED+1))
    fi
done

echo ""

if [ "$FAILED" -gt 0 ]; then
    bad "Something didn't copy — stopping here."
    ssh -O exit -o ControlPath="$CTL" "$PIUSER@$PIHOST" 2>/dev/null
    echo ""
    echo "  Press Enter to close."
    read -r
    exit 1
fi

echo "  (The previous versions were saved on the Pi as .bak files,"
echo "   in case you need to go back.)"
echo ""

# ── Offer to run the test ───────────────────────────────────────────────────
echo -e "  ${BOLD}Generate the test sound files now?${RESET}"
echo "  This makes 'before' and 'after' recordings so you can hear the change."
echo ""
echo -n "  Run the test? [Y/n]: "
read -r RUNTEST
echo ""

if [ "$RUNTEST" = "n" ] || [ "$RUNTEST" = "N" ]; then
    echo "  Skipped. To run it later, on the Pi:"
    echo "      cd ~/Projects/Ohbot && source venv/bin/activate"
    echo "      python3 test_pronunciation.py"
    ssh -O exit -o ControlPath="$CTL" "$PIUSER@$PIHOST" 2>/dev/null
    echo ""
    echo "  Press Enter to close."
    read -r
    exit 0
fi

echo -e "  ${BOLD}${CYAN}--- running on the Pi ---${RESET}"
echo ""
ssh "${SSH_OPTS[@]}" "$PIUSER@$PIHOST" \
    "cd '$PIDIR' && source venv/bin/activate && python3 test_pronunciation.py"
TESTRESULT=$?
echo ""
echo -e "  ${BOLD}${CYAN}--- end ---${RESET}"
echo ""

if [ "$TESTRESULT" -ne 0 ]; then
    bad "The test didn't finish. Read the messages above."
    ssh -O exit -o ControlPath="$CTL" "$PIUSER@$PIHOST" 2>/dev/null
    echo ""
    echo "  Press Enter to close."
    read -r
    exit 1
fi

# ── Offer to play them through the Pi's speaker ─────────────────────────────
echo -e "  ${BOLD}Play them now through the robot's speaker?${RESET}"
echo "  You'll hear each sentence twice — the old way, then the new way."
echo ""
echo -n "  Play? [Y/n]: "
read -r PLAY
echo ""

if [ "$PLAY" != "n" ] && [ "$PLAY" != "N" ]; then
    for name in boquete rincon rincones all_together; do
        echo -e "  ${BOLD}$name${RESET}"
        echo "    before ..."
        ssh "${SSH_OPTS[@]}" "$PIUSER@$PIHOST" \
            "aplay -q '$PIDIR/pronunciation_tests/${name}_before.wav'" 2>/dev/null
        sleep 1
        echo "    after  ..."
        ssh "${SSH_OPTS[@]}" "$PIUSER@$PIHOST" \
            "aplay -q '$PIDIR/pronunciation_tests/${name}_after.wav'" 2>/dev/null
        echo ""
        sleep 1
    done
fi

ssh -O exit -o ControlPath="$CTL" "$PIUSER@$PIHOST" 2>/dev/null

echo ""
echo -e "  ${BOLD}Done.${RESET}"
echo ""
echo "  'rincones' should have sounded the SAME both times — that word was"
echo "  already correct and the fix is supposed to leave it alone."
echo ""
echo "  If a word still sounds wrong, don't edit anything yourself — ask"
echo "  Claude, and point at HANDOFF_pronunciation_guide.md."
echo ""
echo "  The robot itself picks up the change on its next restart:"
echo "      systemctl --user restart ohbot-server ohbot-conversation"
echo ""
echo "  Press Enter to close."
read -r
