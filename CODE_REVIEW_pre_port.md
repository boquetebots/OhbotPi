# Pre-Port Code Review

**Date:** August 3, 2026
**Scope:** ohbot_pi.py, ohbot_azure.py, ohbot_chat.py (the future ohbot_core), plus housekeeping and git
**Verdict:** The code is in good shape overall — clean structure, well-commented, no serious bugs found. But the review caught **four issues that would have bitten us during the port** and weren't in the original porting doc. Worth doing this review.

---

## Findings That Change the Port Plan

These are new — none were in PORTING_mac_windows.md.

### 1. The microphone is hardcoded to a Pi-only device ⚠️ Biggest catch

`ohbot_azure.py` line 219:

```python
audio_config = speechsdk.audio.AudioConfig(device_name="plughw:3,0")
```

`plughw:3,0` means "USB sound card number 3" in Linux-speak. On Mac or Windows this name is gibberish — listening would fail every time. It's also fragile **on the Pi itself**: if the USB mic ever enumerates as card 2 instead of 3 (different boot order, different USB port), listening silently breaks.

**Fix:** on Mac/Windows use the system default microphone; on the Pi keep the device name but move it to the `.env` file so it's a setting, not buried in code.

### 2. The `.env` file is never loaded by most of the code

The Azure and OpenAI keys live in `.env`, but here's the thing: **only systemd reads that file** (the services have an `EnvironmentFile=` line), plus gui_server.py which has its own small loader (line 38). ohbot_chat.py, ohbot_azure.py, and ohbotchat_server.py just assume the keys are already in the environment.

On Mac/Windows there is no systemd — run any of these directly and they'd crash with "Azure Speech subscription key not provided."

**Fix:** put gui_server's little `.env` loader into ohbot_core so every program loads keys itself, on every platform. (Also makes things easier on the Pi — scripts run by hand would get keys too.)

### 3. On a desktop, the bot would fall asleep forever

ohbot_chat.py's sleep/wake cycle: after 2 missed turns the bot sleeps, then waits for either the GPIO button (doesn't exist on desktop) or a voice wake word (`VOICE_WAKE_ENABLED = False`, line 87 — turned off to save Azure costs). On a Mac or PC, **nothing can ever set the wake event** — the first time the bot dozes off, it's asleep until you kill the program.

**Fix:** add a keyboard wake (press Enter to wake) on desktop platforms.

### 4. Windows would crash the moment it imports the library

`ohbot_pi.py` line 92 runs the Linux/Mac command `which piper` — and it runs **at import time** (line 156 creates a PiperTTS the moment the file loads). On Windows there is no `which`, and Python throws a `FileNotFoundError` before any of our code even starts.

**Fix:** replace with Python's built-in `shutil.which("piper")` — one line, works on all three platforms. (Windows venvs also keep programs in `Scripts\` not `bin\` — same function fixes that search too.)

---

## Smaller Code Findings (not urgent, worth fixing during the port)

1. **Silent error swallowing** — ohbot_pi.py has three bare `except:` blocks (lines 387, 399, 644) that hide *all* errors. The worst is `_serwrite` (line 644): if the serial port dies mid-session, every motor command is silently thrown away — the robot just freezes with no message. This is very likely why the "robot not found / red dot" problem is confusing to debug. Fix: print the error once instead of hiding it.
2. **Ignored timeout** — `recognize_once(timeout=10.0)` in ohbot_azure.py accepts a timeout that is never used; Azure's own internal timeout applies instead. Misleading, should be removed or wired up.
3. **Temp file leak** — in both `say()` functions, the temporary WAV is only deleted if playback succeeds. Errors slowly accumulate stray files in /tmp. Fix: delete in the `finally` block.
4. **Outdated comment** — ohbot_azure.py line 21 says the "Ohbot C extension" isn't thread-safe; there's no C extension anymore (ohbot_pi is pure Python). The lock is still correct and needed — only the comment is stale.

Nothing else of concern: motor math, lip avoidance, viseme mapping, threading locks, and the async structure all look solid.

---

## Housekeeping Findings

### Junk files in the Pi project folder

| What | Count | Verdict |
|------|-------|---------|
| `.smbdeleteAAA...` files | 14 (~250 KB) | SAMBA leftovers from deleting open files — safe to delete |
| `._filename` files + `.DS_Store` | ~12 | Mac metadata sprayed over SAMBA — safe to delete (already gitignored) |
| `gui_server_BACKUP_2026-07-13.py` | 1 | Superseded — git has the full history; safe to delete |
| `patch_emotion_badge.py` | 1 | One-off patch script, already applied — safe to delete or archive |
| Old calibration files in ohbotData (`MD_old_1..6`, `MotorDefinitionsYobot_v3`, `...v21 copy`) | 8 | From calibration week — archive into `ohbotData/archive/`, keep the live `MotorDefinitionsv21.omd` |

Also: add `.smbdelete*` to `.gitignore` so those never show up as untracked files again.

### Git status — the important one

> **RESOLVED — August 12, 2026.** The work described below was committed and pushed.
> Checked from the Windows PC: local `main` is level with `origin/main`, nothing ahead
> or behind. **Ignore the warning below** — it's kept only as a record of what happened.
>
> One thing to know if `git status` on Windows ever looks alarming again: an NTFS drive
> flips every file's permission bits, so git reports dozens of files as "modified" when
> only the mode changed and the content is identical. `core.fileMode=false` was set on
> the Windows clone to silence it. If you see 50+ modified files, check
> `git diff --numstat` before believing it.

Good news: the July 23 "reconciled" commit **did get pushed** — the Pi and GitHub currently match.

Not-so-good news: **~5 weeks of work since July 23 is uncommitted** — 67 changed/new files, including:

- The final Yobot calibration values (`MotorDefinitionsv21.omd`) — irreplaceable without redoing calibration
- The lip-sync exaggeration tuning in ohbot_azure.py (Aug 1)
- calibration_server.py + its web page, the yobot_* scripts, launcher updates, saved sequences

If the Pi's SD card died today, all of that would be gone. **Commit and push before touching anything for the port** — it also gives us a clean "known good" snapshot to return to if a port change ever breaks the Pi.

(Reminder from past sessions: pushing has to happen on the Pi itself via SSH — this sandbox has no GitHub credentials, and git writes over SAMBA are flaky.)

---

## Recommended Order

1. Clean up junk files, archive old calibration files
2. Commit everything + push to GitHub (on the Pi, via SSH)
3. Then start the port with a clean, backed-up baseline — folding the four fixes above into ohbot_core as we build it
