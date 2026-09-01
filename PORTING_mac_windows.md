# Porting the Project to Mac and Windows

**Originally written:** August 3, 2026 (analysis)
**Updated:** August 3, 2026 — **Mac port is DONE and working. This is now the Windows plan.**
**Updated:** August 12, 2026 — **Windows code is now WRITTEN. See the status box below.**

---

## Windows Status — August 12, 2026 — ✅ WORKING

All four items under "What Still Needs Building" are done, plus one extra, and the whole
thing has been run on the real robot from a Windows PC. One real bug was found and fixed
during testing (audio clipping — see the log below).

| Item | State |
|------|-------|
| `yobot_win.py` | Written. Adds a fourth mode, `ports`, that lists COM ports for troubleshooting. |
| Launcher's Windows half | Written. Uses `psutil` when installed, PowerShell otherwise; opens the bot in its own Command Prompt window; stops it politely (Ctrl-Break) before forcing it. |
| `yobot_calibrate.py` keypresses | Fixed — uses `msvcrt` on Windows, `termios` elsewhere. |
| `SETUP_Windows.md` | Written, including the USB driver table and the hidden-file-extension trap. |
| **Extra:** COM port probing | The "we poke every COM port" risk below is now fixed — Bluetooth/modem ports are skipped, USB serial chips are tried first, and `YOBOT_SERIAL_PORT` in `.env` skips the search entirely. |

**Decision made:** `psutil` is used *if present*, not required. One `pip install`, but the
launcher still works without it.

### Testing log — the PC

| Step | Result |
|------|--------|
| 1. `.\yobot.bat ports` | ✅ Aug 12. Yobot appears as **COM4**, `USB VID:PID=2E8A:000A` — the Pico brain board. Windows describes it only as "USB Serial Device", so the vendor ID `2e8a` was added to `yobot_core.py` as the top-priority match. |
| 2. `.\yobot.bat test` | ✅ Aug 12. Motors, blink, lips, and eye LEDs all working. COM port auto-detection confirmed — no `YOBOT_SERIAL_PORT` override needed. |
| 3. `.\yobot.bat say "..."` | ✅ Aug 12. Voice and lip sync both working. This clears `winsound` playback, the `.env` key loading, and Azure speech synthesis in one go — the three biggest "drafted but never run" items. |
| 4. Full conversation bot | ✅ Aug 12. Microphone, brain server, and Enter-to-wake all working. |
| **Bug found & fixed** | ⚠️→✅ Aug 12. The first ~300 ms of every utterance was inaudible. Cause: Windows powers the sound device down when idle and the wake-up swallows the start — worst on HDMI, which is what this PC uses. Azure speech starts at sample zero, so real words were being lost. Fix: `AUDIO_LEAD_IN_MS` glues silence onto the front of every clip in `yobot_core.start_wav()`, and both lip-sync routines wait the same amount so the mouth stays in step. Measured: ~300 ms wake-up, 350 ms borderline, **450 ms clean — now the default**. Tunable in `.env`; zero on Pi and Mac. Diagnostic kept as `win_audio_check.py`. |
| 5. Launcher page (Windows process control) | ✅ Aug 12. Greeter and Sequence Builder both start from the page, and the Wake button works. The Builder getting the serial cable proves the bot was stopped properly first — i.e. the Windows `psutil`/Ctrl-Break stop path works, not just the start path. |
| 6. `yobot_calibrate.py` on Windows | not yet run — low priority, the web calibration page covers it |

**Second bug found & fixed — Aug 12.** Ctrl-C did nothing in the Launcher's window, and
the process could not be killed from a normal prompt. Two causes, both in the new Windows
code:

1. Background servers were started **sharing the Launcher's console**, so Ctrl-C went to
   them instead of the Launcher. They ignored it. Fixed with `CREATE_NO_WINDOW`.
2. Child processes carried `CREATE_NEW_PROCESS_GROUP`, which on Windows **disables Ctrl-C
   for that process**. It had been added so the Launcher could stop things politely with
   Ctrl-Break — but console signals only reach processes sharing the sender's console,
   which none of these do, so it never worked and only broke Ctrl-C. Removed.

Consequence, now stated honestly in the code: on Windows the Launcher stops programs with
`taskkill`, not a graceful shutdown. Windows closes the serial port handle when the process
dies, so the robot is released either way — the motors just stay where they were instead of
resetting. Added `yobot-stop.bat` as a break-glass "stop everything" for when a window is
lost.

**Third round — Launcher speed, Aug 12.** Starting and stopping a service took ~10 seconds
on Windows, and the calibration page 15–20 seconds. Not a Windows tax — three things in
`launcher_server.py`:

1. Stopping hunted for all four programs by scanning processes. Three of them answer on a
   port, which is instant; only the conversation bot needs the hunt. Up to 8 scans → 1.
2. Fixed `time.sleep(2)` after starting the brain server and the calibration server.
   Replaced with `_wait_for_port()`, which returns the moment the server answers.
3. The psutil scan read every process's full command line. On Windows that means opening
   each process. Now it only does that for python ones.

**Result: ~10s → ~1.5s.** Each start/stop now prints its own timing (the ⏱ lines) to the
console and log, so this can be measured next time instead of guessed at.

Worth remembering: psutil *was* installed the whole time. The cost was the *number* of
scans, not the fallback. The first theory was wrong and measuring settled it.

**This is not Windows-only.** `launcher_server.py` is shared, so the Mac and the Pi get the
same fix from the same file — Michael has seen similar slowness on the Mac. Which fix helps
which machine, how to measure it with the new ⏱ lines, and the one remaining Mac-specific
suspect (two slow `osascript` calls when opening the bot's Terminal window) are written up
in **`HANDOFF_launcher_speed.md`**.

**Verdict: the Windows port is working.** Everything that matters day to day — the robot,
the voice, the conversation, the Launcher, the Sequence Builder — is confirmed on the PC.
The only untested thing left is the terminal calibrator, which the web calibration page
makes redundant anyway.

**Convenience files added:** `yobot.bat` and `yobot-launcher.bat`. They find the venv python
themselves and behave identically in PowerShell and Command Prompt, which sidesteps the
`cd /d` / `%USERPROFILE%` / `.\` differences between the two shells.

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
- A copy of **`.env`** (API keys) and the **`ohbotData`** folder (Yobot's calibration) — either by mapping the Pi's shared folder as a network drive (`\\<your-pi-address>\Projects`) or copying the project folder to the PC
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
