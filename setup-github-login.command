#!/bin/bash
# ============================================================================
#  setup-github-login.command
#
#  Teaches git on this Mac how to log in to GitHub. Double-click this file.
#  You run it ONCE. After that every push just works, in every project.
#
#  WHY THIS EXISTS
#  ---------------
#  Windows has had setup-github-login.bat since 2026-08-12. The Mac never got
#  the matching script, so git here had no credential helper set at all and no
#  ~/.git-credentials file to read. Pushes failed with
#
#      fatal: could not read Username for 'https://github.com'
#
#  which looks like a missing token but is not. The token was here the whole
#  time, sitting in git_keys.txt, with nothing wired up to use it.
#  Written 2026-09-19 after that cost an afternoon.
#
#  WHAT IT DOES
#  ------------
#  1. Finds your token in git_keys.txt
#  2. Tells git to remember logins in a plain file (the "store" helper), the
#     same way Windows does, and turns off the pop-up that can hang a script
#  3. Writes ~/.git-credentials with your token in it
#  4. Tests it against GitHub and says plainly whether it worked
#
#  Your token is never printed on screen, only its first few characters.
# ============================================================================

cd "$(dirname "$0")" || exit 1

echo
echo "  ================================================================"
echo "    Setting up your GitHub login on this Mac"
echo "  ================================================================"
echo

# ── Step 1 — find the token ─────────────────────────────────────────────────
if [ ! -f git_keys.txt ]; then
    echo "  [X] There is no git_keys.txt in this folder."
    echo
    echo "      That is the file that holds your GitHub token. It is kept out"
    echo "      of git on purpose, so it does not travel between machines."
    echo "      Make a new token at:"
    echo "        https://github.com/settings/personal-access-tokens"
    echo "      and paste it into a file called git_keys.txt in this folder,"
    echo "      on a line of its own."
    echo
    read -n 1 -s -r -p "  Press any key to close."
    exit 1
fi

TOKEN=$(grep -m1 -E '^(github_pat_|ghp_)' git_keys.txt | tr -d '[:space:]')

if [ -z "$TOKEN" ]; then
    echo "  [X] No GitHub token found in git_keys.txt."
    echo
    echo "      The token must sit on a line OF ITS OWN, with nothing before"
    echo "      it — no quotes, no 'token:' label, no leading spaces."
    echo "      It starts with github_pat_ or ghp_."
    echo
    read -n 1 -s -r -p "  Press any key to close."
    exit 1
fi

echo "  [ok] Found a token (${TOKEN:0:11}...)"

# ── Step 2 — tell git how to remember it ────────────────────────────────────
#
# The blank entry is the important bit, exactly as on Windows: git collects
# helpers from every settings file it can find, and a blank one wipes the list
# gathered so far. Without it, a helper installed by some other tool can sit in
# front and pop up a window that a double-clicked script cannot answer.
git config --global --unset-all credential.helper 2>/dev/null
git config --global --replace-all credential.helper "" 2>/dev/null
git config --global --add credential.helper store 2>/dev/null
git config --global credential.interactive false 2>/dev/null

echo "  [ok] Told git to remember logins in a file"

# ── Step 3 — trust these folders ────────────────────────────────────────────
git config --global --add safe.directory "$(pwd)" 2>/dev/null
[ -d "$HOME/Projects/Chess" ] && git config --global --add safe.directory "$HOME/Projects/Chess" 2>/dev/null

echo "  [ok] These folders are trusted"

# ── Step 4 — write the login file ───────────────────────────────────────────
printf 'https://boquetebots:%s@github.com\n' "$TOKEN" > "$HOME/.git-credentials"
chmod 600 "$HOME/.git-credentials"

echo "  [ok] Saved your login"

# ── Step 5 — test it ────────────────────────────────────────────────────────
echo
echo "  ... testing the connection to GitHub"
echo

if GIT_TERMINAL_PROMPT=0 git -c credential.interactive=false \
       ls-remote --heads origin >/dev/null 2>&1; then
    echo "  ================================================================"
    echo "    IT WORKED. GitHub knows who you are."
    echo "  ================================================================"
    echo
    echo "    You can now push from any project on this Mac. Try:"
    echo "        push_to_github.command      (here in OhbotPi2)"
    echo "        Push CHESS to GitHub.command   (in the Chess folder)"
else
    echo "  ================================================================"
    echo "    That did not authenticate."
    echo "  ================================================================"
    echo
    echo "    Two reasons this happens:"
    echo
    echo "      1. The token has expired. Tokens have an end date. Make a new"
    echo "         one and replace the line in git_keys.txt."
    echo
    echo "      2. It is a FINE-GRAINED token that does not list this repo."
    echo "         Fine-grained tokens are scoped to particular repositories."
    echo "         One that covers OhbotPi will still be refused by YobotChess"
    echo "         with a 403, which reads like a permissions problem but is"
    echo "         really a scope problem. Check the token's repository list at"
    echo "           https://github.com/settings/personal-access-tokens"
    echo "         and make sure BOTH OhbotPi and YobotChess are ticked."
fi

echo
read -n 1 -s -r -p "  Press any key to close."
echo
