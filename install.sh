#!/bin/bash
# ============================================================
#  install.sh — Ohbot Project Installer
#
#  Run this once on a fresh Raspberry Pi to install everything.
#  It will ask you for your API keys and set everything up
#  so Ohbot starts automatically on every boot.
#
#  Usage:
#    cd ~/Projects/Ohbot
#    bash install.sh
#
#  Re-running this script is safe — it skips steps already done.
# ============================================================

set -e  # Stop immediately if anything goes wrong

# ── Colours ─────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

ok()   { echo -e "  ${GREEN}✓${RESET}  $1"; }
warn() { echo -e "  ${YELLOW}⚠${RESET}   $1"; }
err()  { echo -e "  ${RED}✗${RESET}  $1"; }
hdr()  { echo -e "\n${BOLD}${CYAN}━━━  $1  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"; }

# ── Settings ─────────────────────────────────────────────────
PROJECT_DIR="$HOME/Projects/Ohbot"
VENV_DIR="$PROJECT_DIR/venv"
VENV_PYTHON="$VENV_DIR/bin/python3"
VENV_PIP="$VENV_DIR/bin/pip"
ENV_FILE="$PROJECT_DIR/.env"
USER_SERVICE_DIR="$HOME/.config/systemd/user"
CURRENT_USER="$(whoami)"

# ── Banner ────────────────────────────────────────────────────
clear
echo ""
echo -e "${BOLD}${CYAN}"
echo "  ╔══════════════════════════════════════════════════╗"
echo "  ║                                                  ║"
echo "  ║         🤖  Ohbot Installer                      ║"
echo "  ║                                                  ║"
echo "  ║  This will set up Ohbot on your Raspberry Pi     ║"
echo "  ║  and configure it to start automatically.        ║"
echo "  ║                                                  ║"
echo "  ╚══════════════════════════════════════════════════╝"
echo -e "${RESET}"
echo -e "  Running as: ${BOLD}$CURRENT_USER${RESET}"
echo -e "  Install to: ${BOLD}$PROJECT_DIR${RESET}"
echo ""
echo -e "  ${YELLOW}Press Enter to begin, or Ctrl-C to cancel.${RESET}"
read -r


# ════════════════════════════════════════════════════════════
#  STEP 1 — Check this is a Raspberry Pi
# ════════════════════════════════════════════════════════════
hdr "Step 1 — Checking hardware"

if grep -qi "raspberry pi" /proc/cpuinfo 2>/dev/null; then
    PI_MODEL=$(grep "Model" /proc/cpuinfo 2>/dev/null | head -1 | cut -d: -f2 | xargs)
    ok "Running on Raspberry Pi: $PI_MODEL"
else
    warn "This doesn't look like a Raspberry Pi."
    warn "The installer will continue, but Ohbot hardware (USB serial) may not work."
    echo ""
    echo -n "  Continue anyway? (y/n): "
    read -r CONTINUE_ANYWAY
    if [[ "$CONTINUE_ANYWAY" != "y" && "$CONTINUE_ANYWAY" != "Y" ]]; then
        echo "  Cancelled."
        exit 0
    fi
fi


# ════════════════════════════════════════════════════════════
#  STEP 2 — Check Python 3
# ════════════════════════════════════════════════════════════
hdr "Step 2 — Checking Python"

if ! command -v python3 &>/dev/null; then
    err "Python 3 is not installed."
    echo ""
    echo "  Install it with:"
    echo "    sudo apt update && sudo apt install python3 python3-pip python3-venv -y"
    echo ""
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
ok "$PYTHON_VERSION found"

# Check python3-venv is available
if ! python3 -m venv --help &>/dev/null; then
    warn "python3-venv not found — installing it now..."
    sudo apt update -qq
    sudo apt install python3-venv -y -qq
    ok "python3-venv installed"
else
    ok "python3-venv available"
fi


# ════════════════════════════════════════════════════════════
#  STEP 3 — Check project files are here
# ════════════════════════════════════════════════════════════
hdr "Step 3 — Checking project files"

if [ ! -f "$PROJECT_DIR/launcher_server.py" ]; then
    err "Can't find launcher_server.py in $PROJECT_DIR"
    echo ""
    echo "  Make sure you're running this from inside the Ohbot project folder."
    echo "  Example:"
    echo "    cd ~/Projects/Ohbot"
    echo "    bash install.sh"
    echo ""
    exit 1
fi

ok "Project files found in $PROJECT_DIR"

PY_COUNT=$(ls "$PROJECT_DIR"/*.py 2>/dev/null | wc -l)
ok "Found $PY_COUNT Python files"


# ════════════════════════════════════════════════════════════
#  STEP 4 — Check Ohbot USB cable
# ════════════════════════════════════════════════════════════
hdr "Step 4 — Checking Ohbot USB connection"

if ls /dev/ttyACM* &>/dev/null 2>&1 || ls /dev/ttyUSB* &>/dev/null 2>&1; then
    USB_PORT=$(ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null | head -1)
    ok "USB serial device found: $USB_PORT"
    ok "Ohbot cable appears to be connected"
else
    warn "No USB serial device found (/dev/ttyACM* or /dev/ttyUSB*)"
    warn "Make sure the Ohbot USB cable is plugged into the Pi."
    warn "You can continue — just plug it in before starting Ohbot."
fi


# ════════════════════════════════════════════════════════════
#  STEP 5 — Create Python virtual environment
# ════════════════════════════════════════════════════════════
hdr "Step 5 — Setting up Python virtual environment"

if [ -d "$VENV_DIR" ]; then
    ok "Virtual environment already exists — skipping creation"
else
    echo "  Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    ok "Virtual environment created"
fi


# ════════════════════════════════════════════════════════════
#  STEP 6 — Install Python dependencies
# ════════════════════════════════════════════════════════════
hdr "Step 6 — Installing Python packages"

echo "  This may take a few minutes on first install..."
echo ""

"$VENV_PIP" install --upgrade pip --quiet

if [ -f "$PROJECT_DIR/requirements_conversation.txt" ]; then
    echo "  Installing from requirements_conversation.txt..."
    "$VENV_PIP" install -r "$PROJECT_DIR/requirements_conversation.txt" --quiet
    ok "Conversation bot packages installed"
fi

if [ -f "$PROJECT_DIR/requirements.txt" ]; then
    echo "  Installing from requirements.txt..."
    "$VENV_PIP" install -r "$PROJECT_DIR/requirements.txt" --quiet
    ok "Main packages installed"
fi

ok "All Python packages ready"


# ════════════════════════════════════════════════════════════
#  STEP 7 — API Keys
# ════════════════════════════════════════════════════════════
hdr "Step 7 — API Keys"

echo "  Ohbot needs API keys from two services:"
echo ""
echo "    • OpenAI  — for the AI brain (Ohbot talks and thinks)"
echo "    • Azure   — for voice (speech-to-text and text-to-speech)"
echo ""
echo "  If you don't have these yet, press Enter to skip any key"
echo "  and fill it in later by editing: $ENV_FILE"
echo ""

# ── Load existing values if .env already exists ──────────────
EXISTING_OPENAI=""
EXISTING_AZURE_KEY=""
EXISTING_AZURE_REGION="eastus"

if [ -f "$ENV_FILE" ]; then
    warn ".env file already exists — press Enter to keep each existing value"
    echo ""
    EXISTING_OPENAI=$(grep "^OPENAI_API_KEY=" "$ENV_FILE" 2>/dev/null | cut -d= -f2 | xargs)
    EXISTING_AZURE_KEY=$(grep "^AZURE_SPEECH_KEY=" "$ENV_FILE" 2>/dev/null | cut -d= -f2 | xargs)
    EXISTING_AZURE_REGION=$(grep "^AZURE_SPEECH_REGION=" "$ENV_FILE" 2>/dev/null | cut -d= -f2 | xargs)
fi

# ── OpenAI Key ───────────────────────────────────────────────
echo ""
echo -e "  ${BOLD}OpenAI API Key${RESET}"
echo "  Get yours at: https://platform.openai.com/api-keys"
if [ -n "$EXISTING_OPENAI" ]; then
    echo "  Current value: ${EXISTING_OPENAI:0:8}... (hidden)"
fi
echo -n "  Paste your OpenAI key (or Enter to skip/keep): "
read -r INPUT_OPENAI

if [ -z "$INPUT_OPENAI" ] && [ -n "$EXISTING_OPENAI" ]; then
    INPUT_OPENAI="$EXISTING_OPENAI"
    ok "Keeping existing OpenAI key"
elif [ -z "$INPUT_OPENAI" ]; then
    warn "No OpenAI key — AI responses won't work until you add one"
    INPUT_OPENAI="YOUR_OPENAI_KEY_HERE"
else
    ok "OpenAI key saved"
fi

# ── Azure Speech Key ─────────────────────────────────────────
echo ""
echo -e "  ${BOLD}Azure Speech Key${RESET}"
echo "  Get yours at: https://portal.azure.com → Speech Services"
if [ -n "$EXISTING_AZURE_KEY" ]; then
    echo "  Current value: ${EXISTING_AZURE_KEY:0:8}... (hidden)"
fi
echo -n "  Paste your Azure Speech key (or Enter to skip/keep): "
read -r INPUT_AZURE_KEY

if [ -z "$INPUT_AZURE_KEY" ] && [ -n "$EXISTING_AZURE_KEY" ]; then
    INPUT_AZURE_KEY="$EXISTING_AZURE_KEY"
    ok "Keeping existing Azure key"
elif [ -z "$INPUT_AZURE_KEY" ]; then
    warn "No Azure key — voice features won't work until you add one"
    INPUT_AZURE_KEY="YOUR_AZURE_KEY_HERE"
else
    ok "Azure Speech key saved"
fi

# ── Azure Region ─────────────────────────────────────────────
echo ""
echo -e "  ${BOLD}Azure Region${RESET}"
echo "  The region you chose when creating your Azure Speech resource."
echo "  Common values: eastus  westus  westeurope  eastasia"
echo -n "  Enter region [default: $EXISTING_AZURE_REGION]: "
read -r INPUT_AZURE_REGION

if [ -z "$INPUT_AZURE_REGION" ]; then
    INPUT_AZURE_REGION="$EXISTING_AZURE_REGION"
fi
ok "Azure region: $INPUT_AZURE_REGION"

# ── Write .env file ───────────────────────────────────────────
echo ""
echo "  Writing .env file..."

cat > "$ENV_FILE" << EOF
# Ohbot API Keys
# This file is read automatically when Ohbot starts.
# Keep this file private — do not share it or put it on GitHub.

OPENAI_API_KEY=$INPUT_OPENAI
AZURE_SPEECH_KEY=$INPUT_AZURE_KEY
AZURE_SPEECH_REGION=$INPUT_AZURE_REGION
EOF

chmod 600 "$ENV_FILE"
ok ".env file written and secured (private to your user only)"


# ════════════════════════════════════════════════════════════
#  STEP 8 — Enable linger (boot without login)
# ════════════════════════════════════════════════════════════
hdr "Step 8 — Enabling boot-without-login"

sudo loginctl enable-linger "$CURRENT_USER"
ok "Linger enabled — Ohbot starts at boot without anyone logged in"


# ════════════════════════════════════════════════════════════
#  STEP 9 — Install systemd services
# ════════════════════════════════════════════════════════════
hdr "Step 9 — Installing auto-start services"

# How the services work:
#   ohbot-launcher  → starts at boot, serves the web launcher page on port 5000
#   ohbot-server    → started ON DEMAND by the launcher when you pick "Greeter Bot"
#   ohbot-conversation → started ON DEMAND after ohbot-server
#   ohbot-gui       → started ON DEMAND by the launcher when you pick "Sequence Builder"
#
# Only ohbot-launcher is enabled to start at boot.
# The other three are controlled by the launcher web page.

mkdir -p "$USER_SERVICE_DIR"

# ── ohbot-launcher service (starts at boot) ──────────────────
cat > "$USER_SERVICE_DIR/ohbot-launcher.service" << EOF
[Unit]
Description=Ohbot Launcher (web page to choose Greeter or GUI)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$PROJECT_DIR
ExecStart=$VENV_PYTHON $PROJECT_DIR/launcher_server.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
EOF

ok "ohbot-launcher service installed"

# ── ohbot-server service (started on demand by launcher) ─────
cat > "$USER_SERVICE_DIR/ohbot-server.service" << EOF
[Unit]
Description=Ohbot Greeter Bot — Flask API Server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$PROJECT_DIR
EnvironmentFile=$ENV_FILE
ExecStart=$VENV_PYTHON $PROJECT_DIR/ohbotchat_server.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
EOF

ok "ohbot-server service installed"

# ── ohbot-conversation service (started on demand by launcher) ─
cat > "$USER_SERVICE_DIR/ohbot-conversation.service" << EOF
[Unit]
Description=Ohbot Greeter Bot — Conversation Loop
After=ohbot-server.service
Requires=ohbot-server.service

[Service]
Type=simple
WorkingDirectory=$PROJECT_DIR
EnvironmentFile=$ENV_FILE
ExecStartPre=/bin/sleep 10
ExecStart=$VENV_PYTHON $PROJECT_DIR/ohbot_chat.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
EOF

ok "ohbot-conversation service installed"

# ── ohbot-gui service (started on demand by launcher) ─────────
cat > "$USER_SERVICE_DIR/ohbot-gui.service" << EOF
[Unit]
Description=Ohbot Sequence Builder GUI (port 5001)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$PROJECT_DIR
EnvironmentFile=$ENV_FILE
ExecStart=$VENV_PYTHON $PROJECT_DIR/gui_server.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
EOF

ok "ohbot-gui service installed"

# ── Reload systemd and enable ONLY the launcher at boot ──────
systemctl --user daemon-reload
ok "systemd reloaded"

# Make sure ohbot-server and ohbot-conversation are NOT set to auto-start
# (they were previously enabled — disable them if so)
systemctl --user disable ohbot-server.service 2>/dev/null || true
systemctl --user disable ohbot-conversation.service 2>/dev/null || true

# Enable only the launcher to start at boot
systemctl --user enable ohbot-launcher.service
ok "Launcher enabled — will start automatically on every boot"
ok "Greeter and GUI are controlled from the launcher web page (not auto-start)"


# ════════════════════════════════════════════════════════════
#  STEP 9b — Allow launcher to shut down / restart the Pi
# ════════════════════════════════════════════════════════════
hdr "Step 9b — Enabling shutdown and restart buttons"

SUDOERS_FILE="/etc/sudoers.d/ohbot-power"
if [ -f "$SUDOERS_FILE" ]; then
    ok "Power control already configured"
else
    echo "$CURRENT_USER ALL=(ALL) NOPASSWD: /sbin/shutdown, /sbin/reboot" | sudo tee "$SUDOERS_FILE" > /dev/null
    sudo chmod 440 "$SUDOERS_FILE"
    ok "Shutdown and restart buttons enabled for launcher"
fi


# ════════════════════════════════════════════════════════════
#  STEP 10 — Power-loss protection
# ════════════════════════════════════════════════════════════
hdr "Step 10 — Power-loss protection"

echo "  Raspberry Pis use SD cards, which can get corrupted if the power is"
echo "  cut suddenly (someone unplugs it, a breaker trips, etc). Two things"
echo "  help protect against that:"
echo ""
echo "  1. Hardware watchdog — if the Pi ever freezes completely, it reboots"
echo "     itself automatically after 15 seconds instead of staying stuck."
echo ""

SYSTEMD_CONF="/etc/systemd/system.conf"
sudo sed -i '/^RuntimeWatchdogSec=/d;/^ShutdownWatchdogSec=/d' "$SYSTEMD_CONF"
sudo sed -i '/^\[Manager\]/a RuntimeWatchdogSec=15\nShutdownWatchdogSec=5min' "$SYSTEMD_CONF"
ok "Hardware watchdog enabled (takes effect after your next reboot)"

echo ""
echo "  2. Overlay filesystem (optional, stronger protection) — makes the SD"
echo "     card read-only while Ohbot runs, so a power cut can never corrupt"
echo "     it. Nothing is ever written to the card during normal operation."
echo ""
echo -e "  ${YELLOW}Tradeoff:${RESET} once this is on, any file changes made via SAMBA or"
echo "  SSH are lost on reboot unless you temporarily turn overlay off first,"
echo "  make your change, then turn it back on. Most people enable this only"
echo "  once Ohbot is working the way they want and they're done tinkering."
echo ""
echo -n "  Enable overlay filesystem now? (y/N): "
read -r ENABLE_OVERLAY

if [[ "$ENABLE_OVERLAY" == "y" || "$ENABLE_OVERLAY" == "Y" ]]; then
    if command -v raspi-config &>/dev/null; then
        sudo raspi-config nonint do_overlayfs 1
        ok "Overlay filesystem will be active after your next reboot"
    else
        warn "raspi-config not found — skipping overlay (enable manually later if needed)"
    fi
else
    ok "Skipped for now. Enable later any time with:"
    echo "      sudo raspi-config nonint do_overlayfs 1   (then sudo reboot)"
fi


# ════════════════════════════════════════════════════════════
#  STEP 11 — Start the launcher now
# ════════════════════════════════════════════════════════════
hdr "Step 11 — Start the launcher"

echo ""
echo -n "  Start the launcher right now? (y/n): "
read -r START_NOW

if [[ "$START_NOW" == "y" || "$START_NOW" == "Y" ]]; then
    # Stop anything that might be using port 5000
    systemctl --user stop ohbot-server.service 2>/dev/null || true
    systemctl --user stop ohbot-conversation.service 2>/dev/null || true

    systemctl --user start ohbot-launcher.service
    sleep 3
    ok "Launcher is running!"
    echo ""
    echo "  ── Launcher status ─────────────────────────────────"
    systemctl --user status ohbot-launcher.service --no-pager -l 2>/dev/null | head -8 | sed 's/^/    /'
else
    ok "Skipped — start the launcher later with:"
    echo "    systemctl --user start ohbot-launcher"
fi


# ════════════════════════════════════════════════════════════
#  DONE
# ════════════════════════════════════════════════════════════
echo ""
echo -e "${BOLD}${GREEN}"
echo "  ╔══════════════════════════════════════════════════╗"
echo "  ║                                                  ║"
echo "  ║   ✅  Installation complete!                     ║"
echo "  ║                                                  ║"
echo "  ╚══════════════════════════════════════════════════╝"
echo -e "${RESET}"
echo "  The launcher starts automatically on every boot."
echo ""
echo -e "  ${BOLD}Open this in a browser on any computer on the same WiFi:${RESET}"
echo ""
echo "      http://$(hostname -I 2>/dev/null | awk '{print $1}'):5000"
echo "   or http://ohbot.local:5000"
echo ""
echo "  You'll see a page where you can start the Greeter Bot or the GUI."
echo ""
echo -e "  ${BOLD}Useful commands:${RESET}"
echo ""
echo "    Watch the launcher log:"
echo "      journalctl --user -u ohbot-launcher -f"
echo ""
echo "    Watch the greeter bot log:"
echo "      journalctl --user -u ohbot-server -f"
echo "      journalctl --user -u ohbot-conversation -f"
echo ""
echo "    Stop everything:"
echo "      systemctl --user stop ohbot-launcher ohbot-server ohbot-conversation ohbot-gui"
echo ""
echo "    Restart the launcher:"
echo "      systemctl --user restart ohbot-launcher"
echo ""
echo "    Edit your API keys:"
echo "      nano $ENV_FILE"
echo ""
echo -e "  ${YELLOW}Tip:${RESET} If Ohbot says 'robot not found', unplug and replug the USB"
echo "  cable, then use the launcher page to restart whichever mode is running."
echo ""
