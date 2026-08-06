# Running Yobot on the Mac

**Date:** August 3, 2026
**What this covers:** everything needed to run Yobot from the MacBook instead of the Pi.

---

## What Got Built

| File | What it is |
|------|-----------|
| `yobot_core.py` | **New.** The shared robot library. Detects Pi / Mac / Windows automatically and picks the right audio player, serial port style, and settings. All the motor, LED, eye, and lip-sync code lives here now. |
| `ohbot_pi.py` | Now a 3-line forwarder to yobot_core. Every existing program on the Pi keeps working, unchanged. |
| `yobot_mac.py` | **New.** The Mac launcher — test mode, speech mode, and the full conversation bot. |
| `ohbot_azure.py` | Updated: uses the **default Mac microphone and speaker** automatically. On the Pi, the mic is now a setting (`AZURE_MIC_DEVICE` in .env) instead of buried in code. |
| `ohbot_chat.py` | Updated: on a Mac, **press Enter to wake** a sleeping Yobot (replaces the GPIO button). Chime plays through the cross-platform player. |
| `ohbotchat_server.py` | Updated: loads the API keys from .env itself, so it runs by hand on any machine. |

All files live in the Pi project folder as always — the Mac runs them straight off the shared folder (`/Volumes/Projects/Ohbot`). One copy of the code, both machines use it.

**Important:** the Pi must stay powered on (its services stopped, but the Pi itself on), because the Mac reads the files from the Pi's shared folder.

---

## One-Time Mac Setup (do once)

**Step 1 — Create Yobot's own Python environment (a "venv").** This is a private sandbox just for Yobot's packages — it avoids the Mac's "externally-managed-environment" complaints entirely. Open Terminal and paste these two lines:

```
python3 -m venv ~/yobot-venv
~/yobot-venv/bin/pip install pyserial lxml httpx flask openai azure-cognitiveservices-speech
```

From now on, always run Yobot with `~/yobot-venv/bin/python3` instead of plain `python3` — that's the whole trick, no "activating" needed. (The commands below are already written that way.)

**Step 2 — Microphone permission.** The first time Yobot listens, macOS will pop up *"Terminal would like to access the microphone"* — click **Allow**. If you accidentally click Don't Allow, fix it in System Settings → Privacy & Security → Microphone → turn on Terminal.

That's it. No API key copying needed — the `.env` file is already in the shared folder and the code finds it automatically.

---

## Every Time: Handing Yobot to the Mac

1. Stop the Pi's services (paste in Terminal):
   ```
   ssh michael@192.168.50.155 "sudo systemctl stop ohbot-server ohbot-conversation"
   ```
2. Unplug Yobot's **USB cable from the Pi** and plug it into the **Mac**.
3. Run the hardware test (first time, or any time something seems off):
   ```
   cd /Volumes/Projects/Ohbot && ~/yobot-venv/bin/python3 yobot_mac.py test
   ```
   Head moves + eye colors change = success.

## The Web Pages on the Mac

Each page is served by its own program. Start the one you want, then open the address in the Mac's browser. `localhost` just means "this computer" — it replaces the Pi's `192.168.50.155`.

| Page | Start it with | Then open |
|------|--------------|-----------|
| **Launcher** (buttons for everything else) | `~/yobot-venv/bin/python3 launcher_server.py` | http://localhost:5000 |
| **Sequence Builder** | `~/yobot-venv/bin/python3 gui_server.py` | http://localhost:5001/gui |
| **Timeline** | (same server as above) | http://localhost:5001/timeline |
| **Calibration** | `~/yobot-venv/bin/python3 calibration_server.py` | http://localhost:5003/calibration |

Run them from the project folder: `cd /Volumes/Projects/Ohbot` first. Ctrl-C stops a server.

**The Launcher page is the easy way** — start just that one, and its buttons start and stop the others for you. Two differences from the Pi version:

- **Shut Down / Restart buttons are hidden** on the Mac (a web page shouldn't be able to switch off your laptop).
- Starting the **conversation bot** opens a **new Terminal window** so you can see it and press Enter to wake it. Close that window or press Ctrl-C in it to stop the bot.

**Port note:** calibration moved from 5002 to **5003**. On the Pi, calibration and the conversation brain server both used 5002 and never noticed, because they never ran at the same time. On the Mac they can, so they now have separate ports. Ports are: 5000 launcher, 5001 GUI/Timeline, 5002 brain server, 5003 calibration.

## The Three Ways to Run It

```
~/yobot-venv/bin/python3 yobot_mac.py test                     ← moves only, no internet needed
~/yobot-venv/bin/python3 yobot_mac.py say "Hello from my Mac"  ← voice + lip sync test
~/yobot-venv/bin/python3 yobot_mac.py                          ← the full conversation bot
```

Do them in that order on the first day — each one tests a little more.

In the full bot: talk to Yobot normally. When it falls asleep, **press Enter** to wake it. **Ctrl-C** quits.

## Handing Yobot Back to the Pi

1. Quit the bot on the Mac (Ctrl-C).
2. Plug the USB cable back into the Pi.
3. Restart the services:
   ```
   ssh michael@192.168.50.155 "sudo systemctl start ohbot-server ohbot-conversation"
   ```

---

## Troubleshooting

**"Robot not found"** — same old friend, same fix: unplug the USB cable, wait 5 seconds, plug back in, run again. Also check the cable went into the Mac, not the Pi.

**No sound** — check the Mac isn't muted and the right output is chosen in System Settings → Sound. Yobot uses whatever the Mac's default speaker is.

**Bot doesn't hear you** — almost always the microphone permission (see one-time setup above), or the wrong input device selected in System Settings → Sound → Input.

**"AZURE_SPEECH_KEY not found"** — the Mac can't see the shared folder's .env file. Make sure you're running from `/Volumes/Projects/Ohbot` and the Pi is on.

**Brain server didn't start** — run it by hand to see the real error: `~/yobot-venv/bin/python3 ohbotchat_server.py`

**"No module named ..." errors** — you probably ran plain `python3` instead of `~/yobot-venv/bin/python3`. The venv's python is the one with all the packages.

---

## What's NOT Ported Yet

- Windows (`yobot_win.py`) — waits until a real PC is available for testing
- Auto-start on boot (that's a Pi thing; on the Mac you just run it when you want it)

## What Changed on the Pi

Nothing you have to do — but two files were updated and behave slightly differently:

- **`launcher_server.py`** still uses the systemd services on the Pi exactly as before. It checks at startup whether the services are installed and only then uses them; it prints which mode it's in when it starts.
- **`calibration_server.py`** now runs on port **5003** instead of 5002 (the launcher page's calibration link was updated to match). Its "Stop & Exit" button still stops the systemd service on the Pi, and simply exits the program everywhere else.

If the Pi has an `ohbot-calibration` systemd service that hardcodes port 5002 anywhere, it doesn't matter — the port lives in the Python file, not the service.
