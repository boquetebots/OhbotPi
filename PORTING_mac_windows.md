# Porting the Project to Mac and Windows

**Originally written:** August 3, 2026 (analysis)
**Updated:** August 3, 2026 — **Mac port is DONE and working. This is now the Windows plan.**

---

## Where Things Stand

**Mac: complete.** Conversation bot, Sequence Builder, Timeline, Launcher, and Calibration all confirmed working on the MacBook. See `SETUP_MacOS.md` for how to run it.

The way it was built matters for Windows: instead of separate copies per platform, there's **one shared library, `yobot_core.py`**, that checks which operating system it's on and picks the right behavior. The Pi's `ohbot_pi.py` is now a 3-line forwarder to it. That means Windows support isn't a new port — it's filling in the Windows branches of code that already exists.

**Much of Windows is already written.** While building the Mac version I put the Windows paths in at the same time. None of it has ever run on a real PC, so treat it as "drafted, unverified."

---

## Already Written for Windows (untested)

| Thing | How it's handled | Confidence |
|-------|-----------------|-----------|
| **Audio playback** | Python's built-in `winsound` (no install needed) | Medium — the logic is simple, but never run |
| **Finding the robot** | Windows COM ports (COM3, COM4…) are each probed with the version handshake | Medium — see risk note below |
| **Finding Piper** (optional offline voice) | `shutil.which`, plus Windows' `Scripts\piper.exe` layout | High |
| **API keys** | `.env` loaded by the core library itself, no systemd needed | High |
| **Microphone & speaker** | System default devices, same as the Mac | High |
| **Wake from sleep** | Press Enter — the `KeyboardWake` class is plain Python, works anywhere | High |
| **Calibration page** | Now exits its own process rather than calling systemd | High |
| **Sequence Builder / Timeline / calibration web pages** | No platform-specific code at all | High |

---

## What Still Needs Building

### 1. `yobot_win.py` — the Windows launcher

The Mac has `yobot_mac.py` with three modes (`test`, `say "..."`, and the full bot). Windows needs the same file with Windows-flavored help text and install instructions. Small job — mostly a copy with the paths changed.

### 2. The Launcher page's Windows half ⚠️ New since the original analysis

This is the one real gap, and it didn't exist when the first draft of this document was written — because the cross-platform Launcher was built after it.

`launcher_server.py` now runs in two modes: systemd on the Pi, direct process control everywhere else. The direct mode currently uses two Unix-only commands:

- **`pgrep`** — to notice whether the conversation bot is already running
- **`pkill`** — to stop it

Windows has neither. There's a fallback that remembers programs the launcher itself started, but it's blind to anything started from a separate window, and it can't survive a launcher restart. Windows equivalents exist (`tasklist` / `taskkill`, or the `psutil` package) and would need wiring in.

Also, on the Mac the Launcher opens the conversation bot **in its own Terminal window** so you can press Enter to wake it. Windows needs the same trick with `start cmd` — otherwise a bot launched from the web page has no keyboard and can never be woken.

Note that web servers (GUI, calibration, brain) are detected by checking whether their port answers, which already works identically on Windows. Only the conversation bot needs the process hunt.

### 3. `yobot_calibrate.py` — the terminal calibrator

Still the only file that would crash outright on Windows: it uses `tty` and `termios` (Unix-only) to read single keypresses. Windows' equivalent is the built-in `msvcrt`.

**Lower priority than it used to be** — the web calibration page does the same job, works on any platform, and is what you actually used to fix HeadNod. This script is a fallback at this point.

### 4. A `SETUP_Windows.md` guide

Plain-English install steps, mirroring `SETUP_MacOS.md`.

---

## Windows-Specific Risks Worth Knowing

**Probing every COM port could poke other devices.** On Mac and Linux the code only looks at ports whose names contain "usb" or "acm". Windows port names (COM3, COM4) say nothing about what's attached, so the code opens each one and asks "are you a robot?" On a PC with Bluetooth serial ports, a USB modem, or similar, that means briefly opening devices that aren't Yobot. Usually harmless, occasionally not. If it causes trouble, the fix is to filter on the port's *description* (the USB chip name) instead of trying them all.

**A USB driver may be needed.** Ohbot's brain board talks through a USB-to-serial chip. Recent Windows versions usually install the right driver automatically, but not always — if no COM port appears in Device Manager when Yobot is plugged in, that's a one-time driver install (which chip it is determines which driver).

**`winsound` only plays WAV files.** Everything in this project is WAV, so this should be fine — worth remembering if audio formats ever change.

**Stopping playback is blunt.** The Windows "stop the sound" call silences *all* sounds from the program, not just one. Only matters for the thinking-chime interruption, and the effect is likely invisible in practice.

---

## What the PC Will Need

- **Python 3** from python.org — tick **"Add Python to PATH"** during install
- A virtual environment (same idea as the Mac's, but the Windows path is `Scripts\python.exe` instead of `bin/python3`)
- These packages: flask, pyserial, lxml, openai, httpx, azure-cognitiveservices-speech
- A copy of **`.env`** (API keys) and the **`ohbotData`** folder (Yobot's calibration) — either by mapping the Pi's shared folder as a network drive (`\\192.168.50.155\Projects`) or copying the project folder to the PC
- The Ohbot USB cable plugged into the PC — and remember the standing rule: only one computer can drive the robot at a time

---

## Suggested Order of Work

1. `yobot_win.py` + basic hardware test — proves COM port detection and motor control
2. Speech test — proves `winsound` playback, the microphone, and the API keys
3. Full conversation bot — proves Enter-to-wake and the brain server
4. Launcher page's Windows half (`tasklist`/`taskkill` + `start cmd`)
5. `yobot_calibrate.py` keypress fix (optional — the web page already covers this)
6. `SETUP_Windows.md`

**Effort estimate:** roughly a day, most of it testing rather than writing. Steps 1–3 are mostly verification of code that already exists; step 4 is the only real new construction.

**One thing to decide when we start:** whether to add the `psutil` package (one extra install, makes process management clean and identical on all three platforms) or stick to built-in Windows commands (no new dependency, slightly messier code). I'd lean toward `psutil` — it would also let me simplify the Mac and Pi paths.
