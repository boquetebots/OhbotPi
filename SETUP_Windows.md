# Running Yobot on Windows

**Date:** August 12, 2026
**What this covers:** everything needed to run Yobot from a Windows PC instead of the Pi or the Mac.

This mirrors `SETUP_MacOS.md`. If you've done the Mac, this will feel familiar — the same
code runs on all three machines, it just picks different behaviour underneath.

---

## First, a Windows Annoyance Worth Knowing About

Windows has **two** command windows, and they don't speak quite the same language:

| | **PowerShell** (blue window) | **Command Prompt** (black window) |
|---|---|---|
| Change folder | `cd D:\Projects\OhbotPi2` | `cd /d D:\Projects\OhbotPi2` |
| Your home folder | `$HOME` | `%USERPROFILE%` |
| Run a file in this folder | `.\yobot.bat` | `yobot.bat` |

If you paste a Command Prompt command into PowerShell you get a wall of red text.
That's all it means — nothing is broken.

**You don't have to care about any of this.** There are two batch files in the project
folder that work identically in both windows:

```
.\yobot.bat            ← the robot: test, say, ports, full bot
.\yobot-launcher.bat   ← the Launcher web page
.\yobot-stop.bat       ← stop everything, when Ctrl-C won't
```

Every command in this guide uses those. If you ever want the long-hand version, it's at
the bottom under "The Long Way".

---

## What Got Built for Windows

| File | What it is |
|------|-----------|
| `yobot_win.py` | **New.** The Windows launcher — test mode, speech mode, port list, and the full conversation bot. The Windows twin of `yobot_mac.py`. |
| `yobot_core.py` | Updated: smarter COM port hunting (skips Bluetooth and modem ports instead of poking everything), and a `YOBOT_SERIAL_PORT` setting to skip the search entirely. |
| `launcher_server.py` | Updated: finds and stops programs on Windows, and opens the conversation bot in its own Command Prompt window so you can press Enter to wake Yobot. |
| `yobot_calibrate.py` | Updated: reads single keypresses using Windows' `msvcrt` instead of Unix's `termios`. It used to crash on Windows before printing anything. |

Everything else — the Sequence Builder, the Timeline, the Calibration web page, the brain
server — already had no platform-specific code and needs nothing new.

**One copy of the code, three machines.** Nothing here is a Windows-only fork.

---

## One-Time Windows Setup (do once)

### Step 1 — Install Python

Get Python 3 from **https://www.python.org/downloads/**.

⚠️ On the first screen of the installer, tick **"Add python.exe to PATH"** before clicking
Install. It's easy to miss and everything else depends on it.

To check it worked, open **PowerShell** (press the Windows key, type `powershell`, press
Enter) and type:

```
python --version
```

You should see something like `Python 3.12.4`. If instead the Microsoft Store opens, or you
get "not recognized", Python didn't get added to PATH — re-run the installer, choose
**Modify**, and tick the PATH box.

### Step 2 — Make Yobot's own Python environment (a "venv")

A venv is a private sandbox just for Yobot's packages, so nothing else on the PC gets
disturbed. Paste these two lines into **PowerShell**, one at a time:

```
python -m venv $HOME\yobot-venv
& "$HOME\yobot-venv\Scripts\pip.exe" install pyserial lxml httpx flask openai azure-cognitiveservices-speech psutil
```

The second one takes a few minutes — the Azure speech package is large.

(The `&` at the start of the second line is PowerShell's way of saying "run this program".
Without it PowerShell just prints the path back at you. In Command Prompt you'd leave the
`&` off and write `%USERPROFILE%` instead of `$HOME`.)

You never have to type that path again — `yobot.bat` finds the venv by itself from here on.
Nothing needs "activating".

`psutil` is optional but worth having: it makes the Launcher page's start/stop buttons quick.
Without it the Launcher falls back to a slower method that takes about a second per check.

### Step 3 — Get the project folder onto the PC

The project lives at **`D:\Projects\OhbotPi2`** on this PC. It needs two things that are not
optional:

- **`.env`** — the API keys (Azure speech + OpenAI)
- **`ohbotData\`** — Yobot's calibration, especially `MotorDefinitionsYobot.omd`

Both should already be there. If you ever rebuild the folder from GitHub, remember that
`.env` is deliberately **not** in git — copy it from the Pi or the Mac by hand.

⚠️ **Windows hides file extensions by default**, which bites here: a file that shows as
`.env` in File Explorer may really be `.env.txt`, and the code won't find it. Turn on
**View → Show → File name extensions** in File Explorer and check.

### Step 4 — Plug in Yobot and check Windows sees it

Plug Yobot's USB cable into the PC, turn Yobot's power supply on, then run:

```
cd D:\Projects\OhbotPi2
.\yobot.bat ports
```

This lists every serial port Windows can see. You're looking for one that mentions a USB
serial chip — commonly **CH340**, **CP210x**, **FTDI**, or plain **"USB Serial Device"**.

**If no ports are listed at all**, Windows is missing the driver for Ohbot's brain board.
Open **Device Manager** (Windows key, type `device manager`) and look for a yellow warning
triangle under **Other devices** or **Ports (COM & LPT)**. The name next to it tells you
which driver to install:

| What Device Manager shows | Driver to install |
|---------------------------|-------------------|
| USB-SERIAL CH340 / USB2.0-Serial | CH340 driver (WCH) |
| CP2102 / Silicon Labs | CP210x VCP driver (Silicon Labs) |
| FT232 / FTDI | FTDI VCP driver |
| Arduino / unknown | Try the CH340 driver first |

This is a one-time install. Windows 11 usually handles it automatically, but not always.

---

## Every Time: Handing Yobot to the PC

Only one computer can drive Yobot at a time — they'd fight over the one USB cable.

1. Stop the Pi's services. The easiest way is the Pi's own Launcher page at
   http://192.168.50.155:5000 — press its **Stop** button. Or from PowerShell:
   ```
   ssh michael@192.168.50.155 "systemctl --user stop ohbot-server ohbot-conversation"
   ```
   (Windows 10 and 11 have `ssh` built in.)
2. Unplug Yobot's **USB cable from the Pi** and plug it into the **PC**.
3. Run the hardware test — first time, or any time something seems off:
   ```
   cd D:\Projects\OhbotPi2
   .\yobot.bat test
   ```
   Head moves + eye colours change = success.

---

## The Four Ways to Run It

Do these in order on the first day — each one tests a little more than the last.
Always `cd D:\Projects\OhbotPi2` first.

```
.\yobot.bat ports
      ↳ just lists COM ports. Proves Windows can see the robot at all.

.\yobot.bat test
      ↳ moves only. No internet, no API keys. Proves the USB cable and motors.

.\yobot.bat say "Hello from my PC"
      ↳ voice + lip sync. Proves the speaker, the .env keys, and Azure.

.\yobot.bat
      ↳ the full conversation bot. Proves the microphone and the brain server.
```

In the full bot: talk to Yobot normally. When it falls asleep, **press Enter** to wake it
(on the Pi that's the GPIO button; there isn't one on a PC). **Ctrl-C** quits.

---

## The Web Pages on Windows

**The easy way — start the Launcher and let it do the rest:**

```
cd D:\Projects\OhbotPi2
.\yobot-launcher.bat
```

That starts the Launcher and opens http://localhost:5000 in your browser. From that one
page you can start and stop the Greeter, the Sequence Builder, the Timeline, and
Calibration. Leave the black window open — closing it stops the Launcher.

`localhost` just means "this computer" — it replaces the Pi's `192.168.50.155`.

**Or start a page directly**, if you'd rather skip the Launcher. Each one is its own
program; `Ctrl-C` in the window stops it.

| Page | Start it with | Then open |
|------|--------------|-----------|
| **Sequence Builder** | `& "$HOME\yobot-venv\Scripts\python.exe" gui_server.py` | http://localhost:5001/gui |
| **Timeline** | (same server as above) | http://localhost:5001/timeline |
| **Calibration** | `& "$HOME\yobot-venv\Scripts\python.exe" calibration_server.py` | http://localhost:5003/calibration |

Three things to know about the Launcher on Windows:

- **Shut Down / Restart buttons are hidden** (a web page shouldn't be able to switch off
  your PC). Same as on the Mac.
- Starting the **conversation bot** opens a **new Command Prompt window**, so it has a
  keyboard and you can press Enter to wake Yobot. Closing that window stops the bot.
- The first time a server starts, **Windows Firewall will ask for permission.** Click
  **Allow access**. Private networks is enough — you don't need public.

Ports: 5000 launcher, 5001 GUI/Timeline, 5002 brain server, 5003 calibration.

---

## Handing Yobot Back to the Pi

1. Quit whatever's running on the PC (Ctrl-C, or the Launcher's Stop button).
2. Plug the USB cable back into the Pi.
3. Restart the services:
   ```
   ssh michael@192.168.50.155 "systemctl --user start ohbot-server ohbot-conversation"
   ```

---

## Troubleshooting

**"Robot not found"** — the usual fix first: unplug the USB cable, wait 5 seconds, plug it
back in, run again. Then check the cable actually went into the PC and not the Pi. If it
still fails, run `.\yobot.bat ports` — that tells you whether the problem is Windows
not seeing the robot (a driver problem) or the code not recognising it.

**Auto-detection keeps picking the wrong port** — tell it directly. Add this line to the
`.env` file, using whichever COM number `.\yobot.bat ports` showed:

```
YOBOT_SERIAL_PORT=COM4
```

**No sound** — check the PC isn't muted, and that the right output is chosen in
**Settings → System → Sound**. Yobot plays through whatever Windows' default speaker is.
Bluetooth speakers work but add a delay, which puts lip sync slightly out of step; a wired
speaker, HDMI, or the PC's own is better.

**The first fraction of a second of speech is missing** — this is a real Windows behaviour,
and it's already compensated for. Windows powers the sound device down when nothing is
playing, and waking it up takes a moment; anything playing during that moment is never
heard. Azure's speech starts at sample zero with no run-up, so the wake-up eats real words.
The fix is a short piece of silence glued onto the front of every clip — **450 ms by
default**, measured against HDMI output on this PC (the device took about 300 ms to wake,
350 ms was borderline, 450 ms was clean). The lip sync waits the same amount, so the mouth
stays in step.

If a different PC or speaker still clips words, raise it in `.env`:

```
AUDIO_LEAD_IN_MS=550
```

Lower it if speech feels sluggish to start. `0` turns it off. It costs almost nothing in
real delay — the wake-up was happening either way; the silence just gives it somewhere
harmless to happen.

`win_audio_check.py` in the project folder re-runs the measurement if you ever need it:
`& "$HOME\yobot-venv\Scripts\python.exe" win_audio_check.py`

**Bot doesn't hear you** — check the input device in **Settings → System → Sound → Input**,
and speak a little; the level bar should move. Also check
**Settings → Privacy & security → Microphone** and make sure desktop apps are allowed.

**"AZURE_SPEECH_KEY not found"** — the `.env` file isn't being found. Check it's in
`D:\Projects\OhbotPi2` and is really called `.env` and not `.env.txt` (see Step 3).

**Brain server didn't start** — run it by hand to see the real error:
`& "$HOME\yobot-venv\Scripts\python.exe" ohbotchat_server.py`.
A firewall prompt hiding behind another window is a common cause.

**"No module named ..."** — the venv wasn't found, so plain `python` ran instead. `yobot.bat`
prints a warning when that happens. Redo Step 2.

**"'python' is not recognized"** — Python isn't on PATH. See Step 1.

**A wall of red text starting "Set-Location : A positional parameter..."** — you pasted a
Command Prompt command into PowerShell. Drop the `/d` from `cd`, and use `.\` in front of
batch files. See the table at the top.

**"...cannot be loaded because running scripts is disabled on this system"** — that's
PowerShell blocking `.ps1` script files. Nothing here uses those; the two `.bat` files are
deliberately not affected. If you hit it, you ran something else.

**Ctrl-C won't stop something, or you've lost the window it was in** — run this from the
project folder:

```
.\yobot-stop.bat
```

It stops anything on Yobot's four ports and any python still running one of Yobot's
programs. Safe to run when nothing is going. Use it before handing Yobot back to the Pi,
or when you get "address already in use".

**The Launcher's Stop button doesn't seem to stop the bot** — install psutil:
`& "$HOME\yobot-venv\Scripts\pip.exe" install psutil`. Without it, Windows process hunting
falls back to a PowerShell query that some locked-down PCs restrict.

---

## The Long Way

The batch files are only a convenience. If you'd rather type it all out, this is exactly
what `.\yobot.bat test` does:

```
cd D:\Projects\OhbotPi2
& "$HOME\yobot-venv\Scripts\python.exe" yobot_win.py test
```

And `.\yobot-launcher.bat`:

```
cd D:\Projects\OhbotPi2
& "$HOME\yobot-venv\Scripts\python.exe" launcher_server.py
```

In **Command Prompt** rather than PowerShell, the same two would be:

```
cd /d D:\Projects\OhbotPi2
%USERPROFILE%\yobot-venv\Scripts\python.exe yobot_win.py test
```

---

## Known Rough Edges on Windows

- **Playback stopping is blunt.** Windows' "stop the sound" call silences everything the
  program is playing, not one specific sound. This only affects interrupting the thinking
  chime, and you're unlikely to notice.
- **WAV only.** Windows playback uses `winsound`, which plays WAV files and nothing else.
  Everything in this project is WAV, so this is fine today — just something to remember if
  audio formats ever change.
- **Stopping the bot is less graceful than on the Pi.** Windows has no polite "please shut
  down" signal the way Mac and Linux do. The Launcher asks nicely first (Ctrl-Break) and
  waits a few seconds before forcing it, but a forced stop can leave the serial port stuck —
  the same "red dot" symptom as on the Pi, with the same fix (unplug/replug the USB cable).
- **`yobot_calibrate.py` (the terminal calibrator) is untested on Windows.** The keypress
  crash is fixed, but nobody has run a full calibration with it here. The **web calibration
  page is the recommended route** anyway — it does the same job and has no platform-specific
  code at all.
