#!/bin/bash
# ============================================================================
#  tidy_git_folder.command
#
#  Clears junk out of the hidden .git folder. Double-click this file.
#
#  WHAT THE JUNK IS
#  ----------------
#  When a Claude session runs a git command on this Mac, it works on the
#  project folder through a sandbox that is not allowed to DELETE anything.
#  Git writes each object it downloads to a temporary file first, then renames
#  it into place. The rename works. The tidy-up afterwards does not, because
#  that is a delete. So every session that has ever run git here has left a
#  small pile of orphaned temp files behind.
#
#  As of 19 September 2026 there were 186 of them, going back to 3 July,
#  plus one stale "maintenance.lock" that makes git skip its own housekeeping.
#
#  None of it is dangerous. None of it is your work. It is all discarded
#  scratch that git itself would have removed if it had been allowed to.
#
#  WHAT THIS SCRIPT DOES
#  ---------------------
#  1. Deletes the stale maintenance.lock, if it is there.
#  2. Deletes files named  .git/objects/xx/tmp_obj_*  and nothing else.
#     That pattern only ever matches git's own scratch files.
#  3. Runs git's standard housekeeping (git gc) to pack things up tidily.
#
#  It does NOT touch your project files, your commits, your branches, or
#  anything you have not yet committed. It cannot lose work.
#
#  RUN THIS AFTER catch_up_with_github.command, not before.
# ============================================================================

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'
ok()   { echo -e "  ${GREEN}. ${RESET} $1"; }
bad()  { echo -e "  ${RED}x ${RESET} $1"; }
warn() { echo -e "  ${YELLOW}! ${RESET} $1"; }
hdr()  { echo -e "\n${BOLD}${CYAN}---  $1  ------------------------------${RESET}"; }
finish() { echo ""; echo "  Press Return to close."; read -r _; exit "$1"; }

REPO="/Users/michael/Projects/OhbotPi2"

clear
echo ""
echo -e "${BOLD}${CYAN}  Tidy up the .git folder${RESET}"
echo ""
echo "  Clears out git's own leftover scratch files. Your work is not touched."
echo ""

cd "$REPO" || { bad "Can't find $REPO - did the folder move?"; finish 1; }

if [ ! -d ".git" ]; then
    bad "There is no .git folder here. Wrong folder? Nothing was changed."
    finish 1
fi
ok "Found the project at $REPO"

# --------------------------------------------------------------------------
hdr "Before"

BEFORE_TMP=$(find .git/objects -type f -name 'tmp_obj_*' 2>/dev/null | wc -l | tr -d ' ')
BEFORE_SIZE=$(du -sh .git 2>/dev/null | cut -f1)
echo "      orphaned temp files : $BEFORE_TMP"
echo "      size of .git folder : $BEFORE_SIZE"

if [ "$BEFORE_TMP" = "0" ] && [ ! -f ".git/objects/maintenance.lock" ]; then
    echo ""
    ok "Already clean - there is nothing to tidy."
    echo ""
    echo "  Running housekeeping anyway, it does no harm."
fi

# --------------------------------------------------------------------------
hdr "Clearing the stale lock"

if [ -f ".git/objects/maintenance.lock" ]; then
    rm -f ".git/objects/maintenance.lock" \
        && ok "Removed maintenance.lock" \
        || bad "Could not remove maintenance.lock"
else
    ok "No stale lock - nothing to do"
fi

# --------------------------------------------------------------------------
hdr "Clearing orphaned temp files"

# Deliberately narrow: only git's own scratch files, only inside .git/objects.
if [ "$BEFORE_TMP" != "0" ]; then
    find .git/objects -type f -name 'tmp_obj_*' -delete 2>/dev/null
    STILL=$(find .git/objects -type f -name 'tmp_obj_*' 2>/dev/null | wc -l | tr -d ' ')
    REMOVED=$(( BEFORE_TMP - STILL ))
    ok "Removed $REMOVED of $BEFORE_TMP"
    [ "$STILL" != "0" ] && warn "$STILL would not delete - tell Claude"
else
    ok "None to remove"
fi

# --------------------------------------------------------------------------
hdr "Git housekeeping"

echo "  This can take a minute on a big project. Please wait."
echo ""
if git gc --prune=now --quiet 2>&1 | sed 's/^/      /'; then
    ok "Housekeeping done"
else
    warn "Housekeeping reported a problem - copy the text above for Claude"
fi

# --------------------------------------------------------------------------
hdr "After"

AFTER_TMP=$(find .git/objects -type f -name 'tmp_obj_*' 2>/dev/null | wc -l | tr -d ' ')
AFTER_SIZE=$(du -sh .git 2>/dev/null | cut -f1)
echo "      orphaned temp files : $AFTER_TMP   (was $BEFORE_TMP)"
echo "      size of .git folder : $AFTER_SIZE   (was $BEFORE_SIZE)"

# --------------------------------------------------------------------------
hdr "Sanity check"

BR=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
HD=$(git log --oneline -1 2>/dev/null)
ok "Still on branch: $BR"
ok "Still at commit: $HD"
echo ""
echo "  Anything you had not yet committed is still here:"
echo ""
git status --short | sed 's/^/      /'
echo ""
echo -e "  ${BOLD}Done.${RESET} You can delete this script when you are finished with it."
echo ""
finish 0
