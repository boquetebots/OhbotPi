#!/bin/bash
# ============================================================================
#  push_to_github.command
#
#  Commits your work on the Mac and pushes it to GitHub.
#  Double-click this file in Finder, or run it in Terminal.
#
#  It only touches the Mac copy (~/Projects/OhbotPi2). To bring the Pi in
#  line afterwards, run sync_pi_from_github.command.
#
#  Safe to run as often as you like. If there's nothing new it says so.
#
#  Rewritten 2026-08-07. The previous version had a fixed list of files and a
#  hardcoded commit message left over from a single day's work in August 2026
#  — which meant it silently skipped anything new (knowledge_base.py,
#  clubhouse_knowledge.json, venue.py...) and always used the same wrong
#  message. It now picks up everything and asks you what to call it.
# ============================================================================

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'
ok()   { echo -e "  ${GREEN}✓${RESET}  $1"; }
bad()  { echo -e "  ${RED}✗${RESET}  $1"; }
warn() { echo -e "  ${YELLOW}⚠${RESET}   $1"; }
hdr()  { echo -e "\n${BOLD}${CYAN}━━━  $1  ━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"; }

REPO="/Users/michael/Projects/OhbotPi2"
BRANCH="main"

clear
echo ""
echo -e "${BOLD}${CYAN}  Push Ohbot work to GitHub${RESET}"
echo ""

cd "$REPO" || {
    bad "Can't find $REPO — did the folder move?"
    read -p "  Press Return to close."; exit 1;
}

# ── Safety check 1: right branch? ───────────────────────────────────────────
hdr "Checks"

here=$(git rev-parse --abbrev-ref HEAD)
if [ "$here" != "$BRANCH" ]; then
    bad "This folder is on branch '$here', expected '$BRANCH'."
    echo "     Nothing has been changed. Ask Claude before going further."
    read -p "  Press Return to close."; exit 1
fi
ok "On branch $BRANCH"

# ── Safety check 2: has GitHub moved ahead of us? ───────────────────────────
if ! git fetch origin "$BRANCH" --quiet; then
    bad "Couldn't reach GitHub. Check your internet."
    read -p "  Press Return to close."; exit 1
fi

remote_head=$(git rev-parse "origin/$BRANCH")
base=$(git merge-base HEAD "origin/$BRANCH")

if [ "$remote_head" != "$base" ]; then
    bad "GitHub has commits this folder doesn't have yet."
    echo "     Pushing now would be messy. Nothing has been changed."
    echo "     Tell Claude 'GitHub is ahead' and it'll sort it out."
    read -p "  Press Return to close."; exit 1
fi
ok "GitHub is where we expect it"

# ── Stage everything git is allowed to take ─────────────────────────────────
hdr "Gathering your work"

# -A means "every change, everywhere" — new files, edits and deletions.
# Anything listed in .gitignore is still left out, which is how .env and
# library_knowledge.json stay off the public repo.
git add -A
ok "Staged all changes (except anything in .gitignore)"

# ── Safety check 3: are we about to publish a secret? ───────────────────────
# The repo is public. This is the last line of defence.
hdr "Checking for secrets"

SECRETS_FOUND=""
for risky in ".env" "library_knowledge.json" "git_keys.txt" "SSH key regen.txt"; do
    if git diff --cached --name-only | grep -qxF "$risky"; then
        SECRETS_FOUND="$SECRETS_FOUND    $risky\n"
    fi
done

if [ -n "$SECRETS_FOUND" ]; then
    echo ""
    bad "STOPPING — these are about to be published to a PUBLIC repo:"
    echo ""
    echo -e "$SECRETS_FOUND"
    echo "     These contain API keys, or the library's WiFi password and"
    echo "     phone numbers. They should be in .gitignore and aren't."
    echo ""
    echo "     Nothing has been pushed. Unstaging them now..."
    git reset --quiet
    echo ""
    bad "Tell Claude which file appeared here and it'll fix .gitignore."
    read -p "  Press Return to close."; exit 1
fi
ok "No secrets in this commit"

# ── Anything to do? ─────────────────────────────────────────────────────────
if git diff --cached --quiet; then
    echo ""
    ok "Nothing new to commit — everything is already on GitHub."
    echo ""
    read -p "  Press Return to close."; exit 0
fi

# ── Show what's going ───────────────────────────────────────────────────────
hdr "About to commit"

echo ""
git diff --cached --stat | sed 's/^/    /'
echo ""

# ── Ask for a message ───────────────────────────────────────────────────────
hdr "Describe this work"

echo ""
echo "  One short line saying what changed. For example:"
echo "      Clubhouse deployment: local knowledge base and venue prompt"
echo ""
echo -n "  Message: "
read -r COMMIT_MSG

if [ -z "$COMMIT_MSG" ]; then
    COMMIT_MSG="Ohbot update $(date '+%Y-%m-%d')"
    warn "No message given — using: $COMMIT_MSG"
fi

echo ""
echo -n "  Commit and push? (y/n): "
read -r CONFIRM
if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
    echo ""
    echo "  Stopped. Your files are untouched and still staged."
    echo "  Run this again when ready, or 'git reset' to unstage."
    read -p "  Press Return to close."; exit 0
fi

# ── Commit and push ─────────────────────────────────────────────────────────
hdr "Pushing"

git commit -q -m "$COMMIT_MSG"
ok "Committed"

if git push origin "$BRANCH"; then
    echo ""
    ok "Everything is on GitHub"
    echo ""
    echo "  Now at:"
    git log --oneline -1 | sed 's/^/      /'
    echo ""
    echo -e "  ${BOLD}Next:${RESET}"
    echo "    - run sync_pi_from_github.command to update the Pi"
    echo "    - if you changed .env or library_knowledge.json, also run"
    echo "      deploy_local_files.command (git doesn't carry those)"
else
    echo ""
    warn "The commit was saved but the push failed."
    echo ""
    echo "  Often this is just a login prompt that timed out. GitHub wants a"
    echo "  Personal Access Token, not your account password."
    echo ""
    echo "  Try again in Terminal with:"
    echo "      cd $REPO && git push"
fi

echo ""
read -p "  Press Return to close."
