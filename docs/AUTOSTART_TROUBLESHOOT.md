# Autostart Troubleshooting Handoff
**Date:** 2026-05-05  
**Project:** Boquete Library Ohbot — Raspberry Pi 4, user: YOUR_USERNAME  
**Status:** ✅ RESOLVED — autostart working correctly after reboot

---

## What We Were Trying to Do
Set up Ohbot to start automatically on every boot (no login, no manual launch) so it's demo-ready for a school group visit. The bot normally runs via `./bot.sh` which uses tmux.

## What Was Done (All Working)
- Added **Rincón Clubhouse** topic to `library_knowledge.json` (English + Spanish)
- Updated intent classifier in `ohbot_server.py` to recognize clubhouse questions
- Added clubhouse phrases to `generate_phrases.py` and ran it successfully — all WAVs generated including `en_rincon_clubhouse` and `es_rincon_clubhouse`
- Added library WiFi (SSID: `ADMINISTRACION`) to Pi via `setup_wifi.sh` — credentials stored on Pi
- Created and installed systemd autostart services (see below)
- API keys written to `/home/YOUR_USERNAME/Projects/Ohbot/.env`

---

## Final Working Setup

The bot runs as **user-level systemd services**, not system-level. This is critical — see "Why" below.

### Service file locations
```
~/.config/systemd/user/ohbot-server.service
~/.config/systemd/user/ohbot-conversation.service
```

### How to check status
```bash
systemctl --user status ohbot-server
systemctl --user status ohbot-conversation
```

### How to view logs
```bash
journalctl --user -u ohbot-server -f
journalctl --user -u ohbot-conversation -f
```

### How to stop/start manually
```bash
systemctl --user stop ohbot-server ohbot-conversation
systemctl --user start ohbot-server
# conversation starts automatically after server (it depends on it)
```

### How to restart after code changes
```bash
systemctl --user restart ohbot-server ohbot-conversation
```

---

## What Went Wrong (Root Cause)

**The problem:** `SPXERR_MIC_NOT_AVAILABLE` — Azure Speech SDK could not open the microphone.

**Why:** The original setup used *system-level* systemd services (`/etc/systemd/system/`). System services start at boot before any user logs in. PulseAudio (the audio layer that Azure Speech SDK uses for microphone access on Linux) is a *user session* service — it only starts when a user logs in. So the bot started, played the pre-recorded greeting WAV (which uses `aplay` and goes through ALSA directly, not PulseAudio), then crashed the moment it tried to open the microphone to listen.

**The fix:** Switch to *user-level* systemd services with `loginctl enable-linger`. Linger allows user services to start at boot without a login, and they run in the full user session context — including PulseAudio — so the microphone works.

---

## Key Fix Steps (for reference / if you ever need to redo this)

```bash
# 1. Allow user services to run at boot without login
sudo loginctl enable-linger YOUR_USERNAME

# 2. Create user service directory
mkdir -p ~/.config/systemd/user/

# 3. Place service files in ~/.config/systemd/user/
#    (see setup_autostart.sh — it now does this automatically)

# 4. IMPORTANT: service files must NOT have a User= line
#    and must have WantedBy=default.target (not multi-user.target)

# 5. Enable services (creates symlinks in default.target.wants/)
systemctl --user daemon-reload
systemctl --user enable ohbot-server ohbot-conversation

# 6. Verify symlinks are in the RIGHT place
ls ~/.config/systemd/user/default.target.wants/
# Should show both ohbot services listed there

# 7. Start and test
systemctl --user start ohbot-server
```

### Common mistakes to avoid
- **Don't use `sudo systemctl`** for these services — they're user services, no sudo needed
- **Don't include `User=YOUR_USERNAME`** in the service file — user services already run as you, and that line causes a GROUP error (exit code 216)
- **`WantedBy=default.target`** not `multi-user.target` — multi-user.target doesn't exist in user context
- If you change `WantedBy=`, you must **disable and re-enable** the service to update the symlinks — just editing the file isn't enough

---

## setup_autostart.sh
`setup_autostart.sh` has been updated to use the correct user-service approach. If you ever need to reinstall autostart from scratch (e.g. on a new Pi), just run:
```bash
cd ~/Projects/Ohbot && bash setup_autostart.sh
```

---

## Manual Launch (still works)
`bot.sh` with tmux still works fine for manual/development sessions. Stop the services first:
```bash
systemctl --user stop ohbot-server ohbot-conversation
./bot.sh
```
