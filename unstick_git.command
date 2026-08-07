#!/bin/bash
# ============================================================================
#  unstick_git.command
#
#  Fixes the "git is stuck" problem. Double-click this file in Finder.
#
#  THE SYMPTOM
#  -----------
#  Git suddenly refuses to do anything useful. You might see:
#
#      fatal: Unable to create '.../.git/index.lock': File exists.
#      Another git process seems to be running in this repository
#
#  ...or, more sneakily, no error at all — just a push that cheerfully says
#  "nothing new to commit" when you know perfectly well that you changed
#  something. That silent version is the dangerous one.
#
#  THE CAUSE
#  ---------
#  While git works, it makes a temporary file called .git/index.lock and
#  deletes it when finished. It's a "do not disturb" sign, there to stop two
#  git commands trampling each other. If a git command is interrupted — or is
#  run by a tool that can't clean up after itself, which is what happens when
#  Claude inspects the folder — the sign gets left hanging on the door. From
#  then on git assumes something else is busy and refuses to write anything.
#
#  THE FIX
#  -------
#  Move the leftover file out of the way. That's all this script does.
#
#  IS IT SAFE?
#  -----------
#  Yes, as long as you don't have another git operation genuinely running
#  right this second (a commit in progress in another window, say). It touches
#  nothing but the lock files. Your work, your history and your files are not
#  affected. The old locks are renamed rather than deleted, so even that is
#  reversible.
#
#  Written 2026-08-07.
# ============================================================================

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'
ok()   { echo -e "  ${GREEN}✓${RESET}  $1"; }
bad()  { echo -e "  ${RED}✗${RESET}  $1"; }
warn() { echo -e "  ${YELLOW}⚠${RESET}   $1"; }
hdr()  { echo -e "\n${BOLD}${CYAN}━━━  $1  ━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"; }

MACDIR="/Users/michael/Projects/OhbotPi2"
PIUSER="yobot"
DEFAULT_PIHOST="pibot.local"

clear
echo ""
echo -e "${BOLD}${CYAN}  Unstick git${RESET}"
echo ""
echo "  Clears leftover lock files that stop git from saving your work."
echo ""

TOTAL_CLEARED=0

# ── Clear locks in one folder ───────────────────────────────────────────────
clear_locks_here() {
    local dir="$1"
    local label="$2"

    if [ ! -d "$dir/.git" ]; then
        warn "$label — no git folder found at $dir, skipping"
        return
    fi

    # Look for every kind of lock git makes, not just index.lock.
    local locks
    locks=$(find "$dir/.git" -maxdepth 3 -name "*.lock" ! -name "*.trash_*" 2>/dev/null)

    if [ -z "$locks" ]; then
        ok "$label — nothing stuck, git is healthy"
        return
    fi

    echo ""
    warn "$label — found leftover locks:"
    echo ""
    echo "$locks" | sed "s|$dir/||" | sed 's/^/       /'
    echo ""

    local n=0
    while IFS= read -r l; do
        [ -z "$l" ] && continue
        # Renaming works where deleting sometimes doesn't, so try that first.
        if mv "$l" "$l.trash_$RANDOM" 2>/dev/null; then
            n=$((n+1))
        elif rm -f "$l" 2>/dev/null; then
            n=$((n+1))
        else
            bad "couldn't clear $l"
        fi
    done <<< "$locks"

    if [ "$n" -gt 0 ]; then
        ok "$label — cleared $n lock(s)"
        TOTAL_CLEARED=$((TOTAL_CLEARED+n))
    fi
}

# ── The Mac ─────────────────────────────────────────────────────────────────
hdr "The Mac folder"
clear_locks_here "$MACDIR" "OhbotPi2"

# Prove it actually works now, rather than just hoping.
if [ -d "$MACDIR/.git" ]; then
    if (cd "$MACDIR" && git status --porcelain >/dev/null 2>&1); then
        ok "Checked — git can write again"
        echo ""
        echo "  Outstanding changes on the Mac:"
        CHANGES=$(cd "$MACDIR" && git status --porcelain)
        if [ -z "$CHANGES" ]; then
            echo "      (none — everything is committed)"
        else
            echo "$CHANGES" | sed 's/^/      /'
        fi
    else
        bad "Git still isn't happy. Show Claude this:"
        (cd "$MACDIR" && git status 2>&1 | head -5 | sed 's/^/      /')
    fi
fi

# ── The Pi ──────────────────────────────────────────────────────────────────
hdr "The Pi"

echo ""
echo -n "  Check the Pi too? (y/n): "
read -r DO_PI

if [[ "$DO_PI" == "y" || "$DO_PI" == "Y" ]]; then
    echo ""
    echo -n "  Pi address [$DEFAULT_PIHOST]: "
    read -r PIHOST
    if [ -z "$PIHOST" ]; then PIHOST="$DEFAULT_PIHOST"; fi

    echo ""
    if ssh -o ConnectTimeout=8 "$PIUSER@$PIHOST" "
        cd ~/Projects/Ohbot 2>/dev/null || exit 3
        locks=\$(find .git -maxdepth 3 -name '*.lock' ! -name '*.trash_*' 2>/dev/null)
        if [ -z \"\$locks\" ]; then
            echo '  OK — nothing stuck on the Pi'
        else
            echo \"\$locks\" | sed 's/^/  clearing /'
            echo \"\$locks\" | xargs -r rm -f
            echo '  cleared'
        fi
    " 2>/dev/null; then
        ok "Pi checked"
    else
        RC=$?
        if [ $RC -eq 3 ]; then
            warn "Couldn't find ~/Projects/Ohbot on the Pi"
        else
            warn "Couldn't reach $PIUSER@$PIHOST — skipped"
            echo "     (If the Pi is still on the old build, the user is"
            echo "      'michael', not 'yobot'.)"
        fi
    fi
else
    ok "Skipped the Pi"
fi

# ── Done ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${CYAN}══════════════════════════════════════════════════════${RESET}"
if [ "$TOTAL_CLEARED" -gt 0 ]; then
    echo -e "  ${GREEN}Cleared $TOTAL_CLEARED lock(s). Try your push again.${RESET}"
else
    echo -e "  ${GREEN}Nothing was stuck.${RESET}"
    echo ""
    echo "  If git is still misbehaving, the cause is something else —"
    echo "  copy the exact message and show it to Claude."
fi
echo -e "${BOLD}${CYAN}══════════════════════════════════════════════════════${RESET}"
echo ""
read -p "  Press Return to close."
