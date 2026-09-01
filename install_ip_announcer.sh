#!/bin/bash
# ============================================================================
#  install_ip_announcer.sh
#
#  Makes the robot say its own network address out loud every time it boots,
#  and write that address to the SD card where you can read it.
#
#  Run this ONCE on the Pi, after install.sh:
#
#      cd ~/Projects/Ohbot
#      bash install_ip_announcer.sh
#
#  Running it again is safe.
# ============================================================================

set -e

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'
BOLD='\033[1m'; RESET='\033[0m'
ok()   { echo -e "  ${GREEN}✓${RESET}  $1"; }
warn() { echo -e "  ${YELLOW}⚠${RESET}   $1"; }
hdr()  { echo -e "\n${BOLD}${CYAN}━━━  $1  ━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"; }

PROJECT_DIR="$HOME/Projects/Ohbot"
SERVICE_DIR="$HOME/.config/systemd/user"
SCRIPT="$PROJECT_DIR/announce_ip.py"

echo ""
echo -e "${BOLD}${CYAN}  Yobot — IP Announcer setup${RESET}"
echo ""

# ── Check the script is actually here ───────────────────────────────────────
hdr "Step 1 — Checking files"

if [ ! -f "$SCRIPT" ]; then
    echo "  Can't find announce_ip.py in $PROJECT_DIR"
    echo "  Make sure you ran this from inside the Ohbot folder."
    exit 1
fi
ok "announce_ip.py found"

# ── Install espeak-ng (the offline voice) ───────────────────────────────────
hdr "Step 2 — Installing the offline voice"

if command -v espeak-ng &>/dev/null; then
    ok "espeak-ng already installed"
else
    echo "  Installing espeak-ng (this is the robotic voice that reads"
    echo "  the address aloud — it works with no internet and no API keys)..."
    sudo apt update -qq
    sudo apt install espeak-ng -y -qq
    ok "espeak-ng installed"
fi

# ── Let the Pi write to its own boot partition ──────────────────────────────
hdr "Step 3 — Allowing writes to the SD card boot partition"

# We want the address file on the boot partition because that partition can be
# read on a Mac or PC just by putting the SD card in. By default that partition
# is owned by root, so a normal user cannot write to it. This gives our user
# permission to write that ONE file, and nothing else.

BOOT_DIR=""
for candidate in /boot/firmware /boot; do
    if [ -d "$candidate" ]; then BOOT_DIR="$candidate"; break; fi
done

if [ -n "$BOOT_DIR" ]; then
    sudo touch "$BOOT_DIR/YOBOT_IP.txt" 2>/dev/null || true
    sudo chown "$(whoami)" "$BOOT_DIR/YOBOT_IP.txt" 2>/dev/null || true
    if [ -w "$BOOT_DIR/YOBOT_IP.txt" ]; then
        ok "Can write $BOOT_DIR/YOBOT_IP.txt"
    else
        warn "Couldn't get write access to $BOOT_DIR — the address will still"
        warn "be saved in the project folder and your home folder."
    fi
else
    warn "No boot partition found — skipping (not a problem)"
fi

# ── Install the service ─────────────────────────────────────────────────────
hdr "Step 4 — Setting it to run at every boot"

mkdir -p "$SERVICE_DIR"

cat > "$SERVICE_DIR/ohbot-announce-ip.service" << EOF
[Unit]
Description=Speak this Pi's network address out loud at boot
After=network-online.target sound.target
Wants=network-online.target

[Service]
Type=oneshot
WorkingDirectory=$PROJECT_DIR
# Give the WiFi and the USB speaker a moment to finish waking up.
ExecStartPre=/bin/sleep 20
ExecStart=/usr/bin/python3 $PROJECT_DIR/announce_ip.py
RemainAfterExit=no
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
EOF

ok "Service file written"

systemctl --user daemon-reload
systemctl --user enable ohbot-announce-ip.service
ok "Enabled — it will run on every boot from now on"

# ── Make sure it survives with nobody logged in ─────────────────────────────
# (install.sh already does this, but it costs nothing to be sure)
sudo loginctl enable-linger "$(whoami)" 2>/dev/null || true
ok "Confirmed it runs even when nobody is logged in"

# ── Offer to test it right now ──────────────────────────────────────────────
hdr "Step 5 — Test it"

echo ""
echo -n "  Try it now, so you can hear what it sounds like? (y/n): "
read -r TEST_NOW

if [[ "$TEST_NOW" == "y" || "$TEST_NOW" == "Y" ]]; then
    echo ""
    echo "  Listen to the robot's speaker..."
    echo ""
    python3 "$SCRIPT"
else
    ok "Skipped. Test it any time with:  python3 $SCRIPT"
fi

echo ""
echo -e "${BOLD}${GREEN}  Done.${RESET}"
echo ""
echo "  From now on, about half a minute after you plug the robot in,"
echo "  it will say its own address out loud. Twice."
echo ""
echo "  If you miss it, the same address is written to all of these:"
echo "      ${BOOT_DIR:-/boot}/YOBOT_IP.txt   (readable by putting the SD card in your Mac)"
echo "      $PROJECT_DIR/last_known_ip.txt"
echo "      $HOME/YOBOT_IP.txt"
echo ""
echo "  To hear it again without rebooting:"
echo "      systemctl --user start ohbot-announce-ip"
echo ""
echo "  To turn the talking off but keep the files:"
echo "      python3 $SCRIPT --quiet"
echo ""
