#!/bin/bash
# ============================================================================
#  setup_pi_logging.sh
#
#  Makes the Pi actually keep its logs.
#
#  WHY THIS EXISTS
#  ---------------
#  On 2026-08-10 the greeter went silent at the Clubhouse and there was no
#  record of it anywhere — `journalctl --user -u ohbot-conversation` replied
#  "No journal files were found". The Pi had been throwing its logs away.
#
#  Raspberry Pi OS ships with journald set to keep logs in memory only, so
#  everything vanishes on reboot, and user services often leave nothing at all.
#  This script switches it to keeping them on disk, with a size cap so the SD
#  card can never fill up.
#
#  This is separate from the log FILES the Python programs now write into
#  ~/Projects/Ohbot/logs/ (that's ohbot_logging.py, no setup needed). Belt and
#  braces: the .log files are the easy ones to read and send; journald catches
#  crashes and startup failures that happen before Python gets going.
#
#  HOW TO RUN IT
#  -------------
#  On the Pi:
#
#      bash ~/Projects/Ohbot/setup_pi_logging.sh
#
#  It will ask for your password (it needs sudo to change a system setting).
#  Run it once. Running it again is harmless.
# ============================================================================

set -u

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'
ok()   { echo -e "  ${GREEN}✓${RESET}  $1"; }
bad()  { echo -e "  ${RED}✗${RESET}  $1"; }
warn() { echo -e "  ${YELLOW}⚠${RESET}   $1"; }
step() { echo -e "\n${BOLD}${CYAN}$1${RESET}"; }

# How much disk the system logs may use in total. 200 MB is plenty of history
# for a robot that prints a few lines a minute, and it's nothing on a 32 GB card.
MAX_USE="200M"

echo -e "${BOLD}"
echo "============================================================"
echo "  Ohbot — make the Pi keep its logs"
echo "============================================================"
echo -e "${RESET}"

# ── sanity: are we actually on a Linux box with systemd? ────────────────────
if ! command -v journalctl >/dev/null 2>&1; then
    bad "journalctl not found — this script is for the Raspberry Pi, not the Mac."
    exit 1
fi

# ── 1. Turn on persistent storage ───────────────────────────────────────────
step "1. Telling journald to keep logs on disk"

CONF="/etc/systemd/journald.conf"

if [ ! -f "$CONF" ]; then
    bad "$CONF not found — unexpected. Stopping so nothing gets broken."
    exit 1
fi

# Back up the original once, so this is always reversible.
if [ ! -f "${CONF}.ohbot-backup" ]; then
    sudo cp "$CONF" "${CONF}.ohbot-backup" && ok "Backed up $CONF"
else
    ok "Backup already exists (${CONF}.ohbot-backup)"
fi

# Set the three settings we care about. Each is replaced if present (commented
# out or not), appended if missing.
set_option() {
    local key="$1" value="$2"
    if sudo grep -qE "^\s*#?\s*${key}=" "$CONF"; then
        sudo sed -i -E "s|^\s*#?\s*${key}=.*|${key}=${value}|" "$CONF"
    else
        echo "${key}=${value}" | sudo tee -a "$CONF" >/dev/null
    fi
    ok "${key}=${value}"
}

set_option "Storage"     "persistent"   # keep logs across reboots
set_option "SystemMaxUse" "$MAX_USE"    # never eat the SD card
set_option "MaxRetentionSec" "1month"   # and never keep forever

# ── 2. Create the directory journald writes into ────────────────────────────
step "2. Creating /var/log/journal"

if [ -d /var/log/journal ]; then
    ok "/var/log/journal already exists"
else
    sudo mkdir -p /var/log/journal && ok "Created /var/log/journal"
fi
sudo systemd-tmpfiles --create --prefix /var/log/journal >/dev/null 2>&1 \
    && ok "Permissions set" \
    || warn "systemd-tmpfiles reported a problem (usually harmless)"

# ── 3. Restart the logging service ──────────────────────────────────────────
step "3. Restarting the logging service"

if sudo systemctl restart systemd-journald; then
    ok "systemd-journald restarted"
else
    bad "Could not restart systemd-journald"
    exit 1
fi

sleep 2

# ── 4. Make sure user services get logged too ───────────────────────────────
step "4. Checking your user services"

# Reading your own user unit's logs needs no special group, but being in
# systemd-journal makes `journalctl` work for system-wide logs as well.
if id -nG "$USER" | tr ' ' '\n' | grep -qx "systemd-journal"; then
    ok "$USER is already in the systemd-journal group"
else
    sudo usermod -aG systemd-journal "$USER" \
        && warn "Added $USER to systemd-journal — LOG OUT AND BACK IN for it to take effect" \
        || warn "Could not add $USER to systemd-journal (not fatal)"
fi

# ── 5. Prove it works ───────────────────────────────────────────────────────
step "5. Testing"

TEST_MSG="ohbot-logging-test-$(date +%s)"
logger "$TEST_MSG"
sleep 1

if journalctl --since "1 minute ago" --no-pager 2>/dev/null | grep -q "$TEST_MSG"; then
    ok "Logs are being recorded"
else
    warn "Couldn't find the test message. Try again after a reboot."
fi

if [ -d /var/log/journal ] && [ -n "$(sudo ls -A /var/log/journal 2>/dev/null)" ]; then
    ok "Logs are being written to disk (they will survive a reboot)"
else
    warn "/var/log/journal is still empty — reboot and check again"
fi

# ── done ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}============================================================${RESET}"
echo -e "${BOLD}  Done.${RESET}"
echo ""
echo "  From now on you have logs in two places:"
echo ""
echo -e "  ${BOLD}1. Plain text files${RESET} — easiest to read and to send to Claude"
echo "       ls ~/Projects/Ohbot/logs/"
echo "       tail -n 60 ~/Projects/Ohbot/logs/greeter-\$(date +%F).log"
echo ""
echo -e "  ${BOLD}2. The system journal${RESET} — catches crashes before Python starts"
echo "       journalctl --user -u ohbot-conversation -n 60 --no-pager"
echo "       journalctl --user -u ohbot-conversation -f        # live, Ctrl-C to stop"
echo ""
echo "  To undo everything this script changed:"
echo "       sudo cp /etc/systemd/journald.conf.ohbot-backup /etc/systemd/journald.conf"
echo "       sudo systemctl restart systemd-journald"
echo -e "${BOLD}============================================================${RESET}"
echo ""
