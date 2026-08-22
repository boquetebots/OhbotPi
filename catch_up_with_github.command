#!/bin/bash
# ============================================================================
#  catch_up_with_github.command
#
#  Brings the Mac's OhbotPi2 folder in line with GitHub, safely.
#  Double-click this file in Finder.
#
#  WHY THIS EXISTS
#  ---------------
#  On 2026-08-22 push_to_github.command refused to run, saying "GitHub is
#  ahead". It was right. A commit made from the Windows machine on 2026-08-13
#  had not reached the Mac, and a plain `git pull` would have failed on two
#  things at once:
#
#    1. That commit DELETES ohbotData/MotorDefinitionsv21.omd from the repo,
#       on purpose. It is the live calibration file — the one that decides how
#       far this machine's robot may move. It used to be tracked, which meant
#       a pull could hand one robot another robot's mouth. Each machine keeps
#       its own copy now. But the Mac's copy has local edits, and git will not
#       delete a file you have changed. This script sets it aside and puts it
#       back afterwards, untouched.
#
#    2. That commit ADDS check_motors.py, and the Mac already had a loose
#       untracked copy. Git will not write over an untracked file. The two
#       were compared and are identical, so this script moves the loose one
#       to the backup folder and lets git's copy land.
#
#  Nothing is deleted. Everything set aside goes to a dated folder on your
#  Desktop, and the script tells you where.
#
#  AFTER THIS RUNS: double-click push_to_github.command as normal.
# ============================================================================

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'
ok()   { echo -e "  ${GREEN}. ${RESET} $1"; }
bad()  { echo -e "  ${RED}x ${RESET} $1"; }
warn() { echo -e "  ${YELLOW}! ${RESET} $1"; }
hdr()  { echo -e "\n${BOLD}${CYAN}---  $1  ------------------------------${RESET}"; }
finish() { echo ""; echo "  Press Return to close."; read -r _; exit "$1"; }

REPO="/Users/michael/Projects/OhbotPi2"
BRANCH="main"
LIVE_OMD="ohbotData/MotorDefinitionsv21.omd"
STAMP=$(date +%Y%m%d-%H%M%S)
BACKUP="$HOME/Desktop/ohbot_catchup_backup_$STAMP"

clear
echo ""
echo -e "${BOLD}${CYAN}  Catch the Mac up with GitHub${RESET}"
echo ""
echo "  GitHub has one commit the Mac has not got yet. This brings it"
echo "  across without losing your robot's calibration."
echo ""

cd "$REPO" || { bad "Can't find $REPO - did the folder move?"; finish 1; }

# --------------------------------------------------------------------------
hdr "Checks"

HERE=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
if [ "$HERE" != "$BRANCH" ]; then
    bad "This folder is on branch '$HERE', expected '$BRANCH'."
    echo "     Nothing has been changed. Ask Claude before going further."
    finish 1
fi
ok "On branch $BRANCH"

if ! git fetch origin "$BRANCH" --quiet; then
    bad "Couldn't reach GitHub. Check your internet and try again."
    finish 1
fi
ok "Reached GitHub"

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse "origin/$BRANCH")

if [ "$LOCAL" = "$REMOTE" ]; then
    ok "Already up to date - there is nothing to catch up on."
    echo ""
    echo "  If push_to_github.command still complains, tell Claude."
    finish 0
fi

# Is this a straight catch-up, or have the two histories genuinely split?
if ! git merge-base --is-ancestor HEAD "origin/$BRANCH"; then
    bad "The Mac has commits that GitHub does not."
    echo "     That is a real merge, not a simple catch-up, and this script"
    echo "     will not attempt it. Nothing has been changed."
    echo "     Tell Claude 'the histories have split' and it will sort it out."
    finish 1
fi
ok "Straight catch-up - the Mac is simply behind"

echo ""
echo -e "  ${BOLD}What is coming across:${RESET}"
echo ""
git log --oneline HEAD.."origin/$BRANCH" | sed 's/^/      /'
echo ""

echo -n "  Go ahead? (y/n): "
read -r GO
if [ "$GO" != "y" ] && [ "$GO" != "Y" ]; then
    echo ""
    warn "Cancelled. Nothing has been changed."
    finish 0
fi

mkdir -p "$BACKUP"

# --------------------------------------------------------------------------
hdr "Setting your own files aside"

# 1. The live calibration file. Keep the Mac's actual copy, then restore the
#    tracked version so the working tree is clean enough for git to move.
if [ -f "$LIVE_OMD" ]; then
    cp "$LIVE_OMD" "$BACKUP/MotorDefinitionsv21.omd" || {
        bad "Could not back up $LIVE_OMD. Stopping before anything is changed."
        finish 1
    }
    ok "Saved your live calibration to the backup folder"
    git checkout -- "$LIVE_OMD" 2>/dev/null
else
    warn "No live calibration file here - nothing to save"
fi

# 2. The loose untracked check_motors.py.
if [ -f "check_motors.py" ] && ! git ls-files --error-unmatch check_motors.py >/dev/null 2>&1; then
    mv "check_motors.py" "$BACKUP/check_motors.py" \
        && ok "Moved your loose check_motors.py to the backup folder"
fi

# --------------------------------------------------------------------------
hdr "Bringing GitHub's work across"

if git merge --ff-only "origin/$BRANCH"; then
    ok "Caught up. The Mac now matches GitHub."
else
    bad "Git refused. Nothing was lost - your files are in:"
    echo "      $BACKUP"
    echo ""
    echo "  Copy the message above and show it to Claude."
    finish 1
fi

# --------------------------------------------------------------------------
hdr "Putting your calibration back"

if [ -f "$BACKUP/MotorDefinitionsv21.omd" ]; then
    mkdir -p ohbotData
    cp "$BACKUP/MotorDefinitionsv21.omd" "$LIVE_OMD" \
        && ok "Your robot's live calibration is back where it belongs"
    echo "       (git now ignores this file on purpose - it is yours alone)"
fi

# --------------------------------------------------------------------------
hdr "What is waiting to be pushed"

echo ""
git status --short | sed 's/^/      /'
echo ""

if [ -f "ohbotData/robots/Rubia.omd" ]; then
    ok "Rubia.omd is here and ready to go to GitHub"
else
    warn "Rubia.omd is NOT in ohbotData/robots/ - did the copy from the Pi run?"
fi

echo ""
echo -e "  ${BOLD}Done.${RESET}"
echo ""
echo "  Anything set aside is in:"
echo "      $BACKUP"
echo "  You can delete that folder once you are happy."
echo ""
echo "  NEXT: double-click push_to_github.command to send Rubia to GitHub."
echo ""
finish 0
