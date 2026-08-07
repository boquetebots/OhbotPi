#!/bin/bash
# ============================================================================
#  sync_pi_from_github.command
#
#  Updates the Pi's copy of the project from GitHub. Double-click to run.
#
#  Use this AFTER push_to_github.command. The usual rhythm is:
#
#      edit on the Mac  ->  push_to_github.command  ->  this script
#
#  What it does, in order:
#      1. Connects to the Pi over SSH
#      2. Warns you if the SD card is in read-only (overlay) mode
#      3. Backs up the Pi's ohbotData folder — calibration lives there
#      4. Shows you anything changed on the Pi that GitHub doesn't know about,
#         and asks before touching it
#      5. Pulls from GitHub
#      6. Offers to restart the robot
#
#  It never deletes your saved sequences or calibration without asking.
#
#  Rewritten 2026-08-07 for the pibot build. The previous version was written
#  for a one-time cleanup in August 2026 and had a fixed list of files to
#  discard, plus the old Pi's username baked in. Both are gone.
# ============================================================================

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'
ok()   { echo -e "  ${GREEN}✓${RESET}  $1"; }
bad()  { echo -e "  ${RED}✗${RESET}  $1"; }
warn() { echo -e "  ${YELLOW}⚠${RESET}   $1"; }
hdr()  { echo -e "\n${BOLD}${CYAN}━━━  $1  ━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"; }

# ── Defaults ────────────────────────────────────────────────────────────────
# Change these two lines if you rename the Pi or the user.
DEFAULT_HOST="pibot.local"
PIUSER="yobot"

clear
echo ""
echo -e "${BOLD}${CYAN}  Update the Pi from GitHub${RESET}"
echo ""

# ── Which Pi? ───────────────────────────────────────────────────────────────
echo "  Press Enter for ${DEFAULT_HOST}, or type an IP address."
echo "  (If you don't know the IP, listen to the robot — it says its"
echo "   address out loud about 30 seconds after you plug it in.)"
echo ""
echo -n "  Pi address [${DEFAULT_HOST}]: "
read -r PIHOST
if [ -z "$PIHOST" ]; then PIHOST="$DEFAULT_HOST"; fi

PI="$PIUSER@$PIHOST"
PIDIR="/home/$PIUSER/Projects/Ohbot"

# ── Set up one shared SSH connection ────────────────────────────────────────
# One connection, reused by everything below, so the password is asked for
# once rather than twice. Do NOT add BatchMode=yes — it blocks the password
# prompt entirely and makes the script unusable without an SSH key.
CTL="/tmp/ohbot-ssh-%r@%h:%p"
SSH_OPTS=(-o ConnectTimeout=10
          -o ControlMaster=auto
          -o ControlPath="$CTL"
          -o ControlPersist=120)

# ── Can we reach it? ────────────────────────────────────────────────────────
hdr "Connecting"

echo "  (type your Pi password if it asks)"
echo ""

if ! ssh "${SSH_OPTS[@]}" "$PI" "echo ok" >/dev/null; then
    echo ""
    bad "Can't reach $PI"
    echo ""
    echo "  Try, in this order:"
    echo "    1. Turn on your phone's hotspot — the Pi will join it, then"
    echo "       connect this Mac to the same hotspot and run this again."
    echo "    2. Use the IP address instead of the .local name."
    echo "    3. If you rebuilt the Pi, clear the stale record:"
    echo "           ssh-keygen -R $PIHOST"
    echo ""
    echo "  See PIBOT_BUILD_CHECKLIST.md, Part 9, for the full list."
    echo ""
    read -p "  Press Return to close."
    exit 1
fi
ok "Connected to $PI"

# ── Everything below runs ON THE PI ─────────────────────────────────────────
# The 'PIDIR=' line is passed in so the remote side knows where to look.

ssh -t "${SSH_OPTS[@]}" "$PI" "PIDIR='$PIDIR' bash -s" <<'REMOTE'
set -u

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'
ok()   { echo -e "  ${GREEN}✓${RESET}  $1"; }
bad()  { echo -e "  ${RED}✗${RESET}  $1"; }
warn() { echo -e "  ${YELLOW}⚠${RESET}   $1"; }
hdr()  { echo -e "\n${BOLD}${CYAN}━━━  $1  ━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"; }

cd "$PIDIR" || { echo "Can't find $PIDIR on the Pi."; exit 1; }

# ── Is the SD card read-only? ───────────────────────────────────────────────
hdr "Checking the SD card is writable"

# If the overlay filesystem is switched on, the pull will appear to work and
# then vanish at the next reboot. Catch that before wasting your time.
if findmnt -n -o SOURCE / 2>/dev/null | grep -qi "overlay"; then
    warn "The overlay filesystem is ON — the SD card is read-only."
    echo ""
    echo "     Anything pulled now will disappear at the next reboot."
    echo "     To make the update stick, run these on the Pi first:"
    echo ""
    echo "         sudo raspi-config nonint do_overlayfs 0"
    echo "         sudo reboot"
    echo ""
    echo "     ...then run this script again. Turn overlay back on afterwards."
    echo ""
    echo -n "  Carry on anyway? (y/N): "
    read -r CARRY_ON
    if [[ "$CARRY_ON" != "y" && "$CARRY_ON" != "Y" ]]; then
        echo "  Stopped. Nothing was changed."
        exit 0
    fi
else
    ok "SD card is writable"
fi

# ── Back up calibration ─────────────────────────────────────────────────────
hdr "Backing up calibration"

stamp=$(date +%Y%m%d_%H%M%S)
BACKUP="$HOME/ohbotData_backup_$stamp"
if cp -r ohbotData "$BACKUP" 2>/dev/null; then
    ok "Saved to ~/ohbotData_backup_$stamp"
else
    warn "Couldn't back up ohbotData — continuing, but be careful"
fi

# ── What has changed on the Pi? ─────────────────────────────────────────────
hdr "Checking for changes made on the Pi"

CHANGED=$(git status --porcelain --untracked-files=no 2>/dev/null)

if [ -z "$CHANGED" ]; then
    ok "Nothing changed on the Pi — a clean pull will work"
else
    echo ""
    warn "These files were changed on the Pi and are NOT on GitHub:"
    echo ""
    echo "$CHANGED" | sed 's/^/       /'
    echo ""
    echo "     If you edited these on the Pi on purpose, stop now and push"
    echo "     them from the Pi first, or you will lose that work."
    echo ""
    echo "     If you don't recognise them, they're almost certainly leftovers"
    echo "     and it's safe to discard."
    echo ""
    echo "     (A copy of ohbotData is already backed up either way.)"
    echo ""
    echo -n "  Discard these Pi-side changes and take GitHub's version? (y/N): "
    read -r DISCARD

    if [[ "$DISCARD" == "y" || "$DISCARD" == "Y" ]]; then
        # Only touches files git already tracks. Untracked files — your
        # sequences, .env, library_knowledge.json — are never harmed.
        git checkout -- . && ok "Pi-side changes discarded"
    else
        echo ""
        echo "  Stopped. Nothing was changed."
        echo "  Your Pi-side edits are still there."
        exit 0
    fi
fi

# ── Pull ────────────────────────────────────────────────────────────────────
hdr "Pulling from GitHub"

if git pull --ff-only origin main; then
    echo ""
    ok "Pi updated"
    echo ""
    echo "  Now at:"
    git log --oneline -1 | sed 's/^/      /'
    echo ""
    echo "  Backup left at ~/ohbotData_backup_$stamp — delete it once happy."
else
    echo ""
    bad "The pull didn't go through."
    echo ""
    echo "  Nothing is broken. Your calibration backup is at:"
    echo "      ~/ohbotData_backup_$stamp"
    echo ""
    echo "  Copy the message above and show it to Claude."
    exit 1
fi

# ── Restart ─────────────────────────────────────────────────────────────────
hdr "Restart the robot"

echo ""
echo "  New code doesn't take effect until the services restart."
echo ""
echo -n "  Restart now? (y/n): "
read -r RESTART

if [[ "$RESTART" == "y" || "$RESTART" == "Y" ]]; then
    systemctl --user restart ohbot-launcher 2>/dev/null && ok "Launcher restarted"
    for svc in ohbot-gui ohbot-server ohbot-conversation; do
        if systemctl --user is-active --quiet "$svc" 2>/dev/null; then
            systemctl --user restart "$svc" && ok "$svc restarted"
        fi
    done
    echo ""
    echo "  Open the Launcher: http://$(hostname -I 2>/dev/null | awk '{print $1}'):5000"
else
    echo ""
    echo "  Skipped. Restart from the Launcher page when you're ready."
fi
REMOTE

SSH_RESULT=$?

echo ""
echo -e "${BOLD}${CYAN}══════════════════════════════════════════════════════${RESET}"
if [ $SSH_RESULT -eq 0 ]; then
    echo -e "  ${GREEN}Finished.${RESET}"
    echo ""
    echo "  Reminder: git does NOT carry .env or library_knowledge.json."
    echo "  If you changed either of those on the Mac, also run:"
    echo "      deploy_local_files.command"
else
    echo -e "  ${YELLOW}Finished with problems — see the messages above.${RESET}"
fi
echo -e "${BOLD}${CYAN}══════════════════════════════════════════════════════${RESET}"
echo ""
read -p "  Press Return to close."
