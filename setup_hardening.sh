#!/bin/bash
# ============================================================
#  setup_hardening.sh — Power-Loss Hardening (for existing installs)
#
#  Fresh installs get this automatically from install.sh (Step 10).
#  Run this script instead if Ohbot was already installed before
#  that step existed, and you want to add the same protection
#  without reinstalling everything.
#
#  Run this ONCE on the Raspberry Pi itself (not via SAMBA):
#    cd ~/Projects/Ohbot
#    bash setup_hardening.sh
#
#  What it does:
#    1. Enables the Pi's hardware watchdog (auto-reboots if frozen)
#    2. (Optional) Enables the Overlay Filesystem — makes the SD
#       card read-only so a power cut can never corrupt it.
# ============================================================

set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

echo -e "${BOLD}"
echo "  ╔══════════════════════════════════════════╗"
echo "  ║   Ohbot Power Loss Hardening Setup       ║"
echo "  ╚══════════════════════════════════════════╝"
echo -e "${RESET}"

# ── Step 1: Hardware Watchdog ────────────────────────────────
echo -e "${YELLOW}Step 1: Enabling hardware watchdog...${RESET}"
echo "  The watchdog is a safety timer built into the Pi. If the Pi freezes"
echo "  for more than 15 seconds, it automatically reboots itself."
echo ""

SYSTEMD_CONF="/etc/systemd/system.conf"

sudo sed -i '/^RuntimeWatchdogSec=/d' "$SYSTEMD_CONF"
sudo sed -i '/^ShutdownWatchdogSec=/d' "$SYSTEMD_CONF"
sudo sed -i '/^\[Manager\]/a RuntimeWatchdogSec=15\nShutdownWatchdogSec=5min' "$SYSTEMD_CONF"

echo -e "  ${GREEN}✓ Watchdog enabled${RESET} — Pi reboots itself if frozen for >15 seconds"
echo "  (takes effect after your next reboot)"

# ── Step 2: Overlay Filesystem (optional) ───────────────────
echo ""
echo -e "${YELLOW}Step 2 (Optional): Overlay Filesystem${RESET}"
echo ""
echo -e "  ${BOLD}This is the strongest protection against SD card corruption.${RESET}"
echo "  It makes the SD card completely read-only while the Pi is running."
echo "  All file writes go to RAM instead and are discarded on reboot —"
echo "  the SD card is never touched, so it can never be corrupted."
echo ""
echo -e "  ${RED}⚠  IMPORTANT: When overlay is ON, changes you make to bot files"
echo "     via SAMBA or SSH will be lost on reboot.${RESET}"
echo ""
echo "  To update the bot after enabling overlay, you must:"
echo "    1. SSH into the Pi"
echo "    2. Run:  sudo raspi-config nonint do_overlayfs 0"
echo "    3. Run:  sudo reboot"
echo "    4. Make your changes (SAMBA or SSH now work normally)"
echo "    5. SSH back in and run:  sudo raspi-config nonint do_overlayfs 1"
echo "    6. Run:  sudo reboot"
echo ""
echo "  Recommended: enable overlay only when the bot is stable and"
echo "  you're done making frequent changes."
echo ""
read -r -p "  Enable overlay filesystem now? (y/N): " OVERLAY_CHOICE

NEED_REBOOT=false

if [[ "$OVERLAY_CHOICE" =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "  ${YELLOW}Enabling overlay filesystem...${RESET}"
    if command -v raspi-config &>/dev/null; then
        sudo raspi-config nonint do_overlayfs 1
        echo -e "  ${GREEN}✓ Overlay filesystem will be active after reboot${RESET}"
        NEED_REBOOT=true
    else
        echo -e "  ${RED}raspi-config not found — are you running this on the Pi?${RESET}"
        echo "  You can enable it manually:"
        echo "    sudo raspi-config → Performance Options → Overlay FS"
    fi
else
    echo "  Skipped. You can enable it later with:"
    echo "    sudo raspi-config nonint do_overlayfs 1  (then sudo reboot)"
fi

# ── Done ─────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════╗${RESET}"
echo -e "${GREEN}║  Hardening setup complete!               ║${RESET}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${RESET}"
echo ""

if [[ "$NEED_REBOOT" == true ]]; then
    echo -e "  ${YELLOW}A reboot is required to activate the overlay filesystem.${RESET}"
    echo "  (The watchdog also needs a reboot to take effect if this is the"
    echo "  first time you've run this script.)"
    echo ""
    read -r -p "  Reboot now? (y/N): " REBOOT_NOW
    if [[ "$REBOOT_NOW" =~ ^[Yy]$ ]]; then
        echo "  Rebooting..."
        sudo reboot
    else
        echo "  Reboot later with:  sudo reboot"
    fi
else
    echo "  Reboot when convenient to activate the watchdog:  sudo reboot"
fi
