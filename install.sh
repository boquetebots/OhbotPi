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

if [ ! -f "$PROJECT_DIR/ohbot_server.py" ]; then
    err "Can't find ohbot_server.py in $PROJECT_DIR"
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

mkdir -p "$USER_SERVICE_DIR"

# ── ohbot-server service ─────────────────────────────────────
cat > "$USER_SERVICE_DIR/ohbot-server.service" << EOF
[Unit]
Description=Ohbot Flask Server (OpenAI + Intent Detection)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$PROJECT_DIR
EnvironmentFile=$ENV_FILE
ExecStart=$VENV_PYTHON $PROJECT_DIR/ohbot_server.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
EOF

ok "ohbot-server service installed"

# ── ohbot-conversation service ───────────────────────────────
cat > "$USER_SERVICE_DIR/ohbot-conversation.service" << EOF
[Unit]
Description=Ohbot Conversation Loop
After=ohbot-server.service
Requires=ohbot-server.service

[Service]
Type=simple
WorkingDirectory=$PROJECT_DIR
EnvironmentFile=$ENV_FILE
ExecStartPre=/bin/sleep 10
ExecStart=$VENV_PYTHON $PROJECT_DIR/ohbot_conversation.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
EOF

ok "ohbot-conversation service installed"

systemctl --user daemon-reload
ok "systemd reloaded"

systemctl --user enable ohbot-server.service
systemctl --user enable ohbot-conversation.service
ok "Services enabled — will start automatically on every boot"


# ════════════════════════════════════════════════════════════
#  STEP 10 — Start Ohbot now
# ════════════════════════════════════════════════════════════
hdr "Step 10 — Start Ohbot"

echo ""
echo -n "  Start Ohbot right now? (y/n): "
read -r START_NOW

if [[ "$START_NOW" == "y" || "$START_NOW" == "Y" ]]; then
    systemctl --user start ohbot-server.service
    echo "  Waiting for server to start up (8 seconds)..."
    sleep 8
    systemctl --user start ohbot-conversation.service
    sleep 3
    ok "Ohbot is running!"
    echo ""
    echo "  ── Server status ───────────────────────────────────"
    systemctl --user status ohbot-server.service --no-pager -l 2>/dev/null | head -8 | sed 's/^/    /'
    echo ""
    echo "  ── Conversation status ─────────────────────────────"
    systemctl --user status ohbot-conversation.service --no-pager -l 2>/dev/null | head -8 | sed 's/^/    /'
else
    ok "Skipped — start Ohbot later with:"
    echo "    systemctl --user start ohbot-server"
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
echo "  Ohbot will now start automatically on every boot."
echo ""
echo -e "  ${BOLD}Useful commands:${RESET}"
echo ""
echo "    Watch Ohbot's logs live:"
echo "      journalctl --user -u ohbot-server -f"
echo "      journalctl --user -u ohbot-conversation -f"
echo ""
echo "    Stop Ohbot:"
echo "      systemctl --user stop ohbot-server ohbot-conversation"
echo ""
echo "    Start Ohbot:"
echo "      systemctl --user start ohbot-server"
echo ""
echo "    Restart after making changes:"
echo "      systemctl --user restart ohbot-server ohbot-conversation"
echo ""
echo "    Open the GUI in a browser:"
echo "      http://$(hostname -I 2>/dev/null | awk '{print $1}'):5001/gui"
echo ""
echo "    Edit your API keys:"
echo "      nano $ENV_FILE"
echo ""
echo -e "  ${YELLOW}Tip:${RESET} If Ohbot says 'robot not found', unplug and replug the USB"
echo "  cable, then run:  systemctl --user restart ohbot-server ohbot-conversation"
echo ""
