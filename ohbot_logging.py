#!/usr/bin/env python3
"""
ohbot_logging.py — save everything the Ohbot programs print into log files.

WHY THIS FILE EXISTS
--------------------
On 2026-08-10 the greeter stopped working at the Clubhouse and there was no
record of it at all — `journalctl` said "No journal files were found". The
fault had to be guessed at instead of looked up. This fixes that.

WHAT IT DOES
------------
Every Ohbot program already prints useful things as it runs ("🎤 Listening...",
"✅ Recognized...", "❌ Recognition failed"). Normally that text vanishes.
This module quietly copies all of it into a dated text file, with a timestamp
on every line, while STILL printing to the screen exactly as before.

Nothing else in the code has to change. No print() statements need rewriting.

WHERE THE LOGS GO
-----------------
    /home/yobot/Projects/Ohbot/logs/greeter-2026-08-10.log
    /home/yobot/Projects/Ohbot/logs/gui-2026-08-10.log
    ... and so on, one file per program per day.

Read the newest greeter log on the Pi with:

    tail -n 60 ~/Projects/Ohbot/logs/greeter-$(date +%F).log

HOUSEKEEPING (so the SD card can never fill up)
----------------------------------------------
  - Logs older than KEEP_DAYS are deleted automatically at startup.
  - If a single day's log passes MAX_BYTES it is rolled over to .part2, .part3
    and so on, so one runaway loop can't eat the card.

HOW A PROGRAM USES IT
---------------------
One line, as early in the program as possible:

    from ohbot_logging import setup_logging
    setup_logging("greeter")

Safe to call twice — the second call does nothing.
"""

import atexit
import os
import sys
import time
from datetime import datetime

# ── settings ─────────────────────────────────────────────────────────────────
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
KEEP_DAYS = 14                     # delete logs older than this
MAX_BYTES = 5 * 1024 * 1024        # 5 MB per file before it rolls over

_installed = False                 # guards against setting up twice


# ─────────────────────────────────────────────────────────────────────────────
# The log file itself
# ─────────────────────────────────────────────────────────────────────────────

class _LogFile:
    """
    One open log file, shared by both the normal output and the error output
    so that the two stay in the right order.
    """

    def __init__(self, program):
        self.program = program
        self.handle = None
        self.path = None
        self.bytes_written = 0
        self.part = 1
        self._open()

    def _filename(self):
        today = datetime.now().strftime("%Y-%m-%d")
        if self.part == 1:
            return os.path.join(LOG_DIR, f"{self.program}-{today}.log")
        return os.path.join(LOG_DIR, f"{self.program}-{today}.part{self.part}.log")

    def _open(self):
        try:
            os.makedirs(LOG_DIR, exist_ok=True)
            self.path = self._filename()
            # If today's file already exists and is huge, skip ahead a part.
            while (os.path.exists(self.path)
                   and os.path.getsize(self.path) >= MAX_BYTES):
                self.part += 1
                self.path = self._filename()
            self.handle = open(self.path, "a", encoding="utf-8", errors="replace")
            self.bytes_written = (os.path.getsize(self.path)
                                  if os.path.exists(self.path) else 0)
        except Exception:                                   # noqa: BLE001
            # Logging must never take the robot down. If the file can't be
            # opened (read-only card, no space) we simply don't log.
            self.handle = None

    def _roll_if_needed(self):
        if self.handle and self.bytes_written >= MAX_BYTES:
            try:
                self.handle.write(f"\n--- this log reached {MAX_BYTES} bytes, "
                                  f"continuing in part {self.part + 1} ---\n")
                self.handle.close()
            except Exception:                               # noqa: BLE001
                pass
            self.part += 1
            self._open()

    def write(self, text):
        if not self.handle:
            return
        try:
            self.handle.write(text)
            self.handle.flush()
            self.bytes_written += len(text)
            self._roll_if_needed()
        except Exception:                                   # noqa: BLE001
            self.handle = None

    def close(self):
        if self.handle:
            try:
                self.handle.close()
            except Exception:                               # noqa: BLE001
                pass
            self.handle = None


# ─────────────────────────────────────────────────────────────────────────────
# The tee — writes to the screen AND the file
# ─────────────────────────────────────────────────────────────────────────────

class _Tee:
    """
    Stands in for sys.stdout (or sys.stderr). Passes everything straight
    through to the real one, and also writes a timestamped copy to the log.
    """

    def __init__(self, real_stream, log_file, tag=""):
        self._real = real_stream
        self._log = log_file
        self._tag = tag
        self._at_line_start = True

    # -- the bit that adds "[14:22:07] " to the front of each line -----------
    def _stamped(self, text):
        stamp = datetime.now().strftime("%H:%M:%S")
        prefix = f"[{stamp}]{self._tag} "
        out = []
        pieces = text.split("\n")
        for index, piece in enumerate(pieces):
            is_last = (index == len(pieces) - 1)
            if piece:
                if self._at_line_start:
                    out.append(prefix)
                out.append(piece)
                self._at_line_start = False
            if not is_last:
                out.append("\n")
                self._at_line_start = True
        return "".join(out)

    def write(self, text):
        if not isinstance(text, str):
            text = str(text)
        try:
            self._real.write(text)
        except Exception:                                   # noqa: BLE001
            pass
        if text:
            try:
                self._log.write(self._stamped(text))
            except Exception:                               # noqa: BLE001
                pass
        return len(text)

    def flush(self):
        try:
            self._real.flush()
        except Exception:                                   # noqa: BLE001
            pass

    # Some libraries poke at these. Pass them through to the real stream.
    def isatty(self):
        try:
            return self._real.isatty()
        except Exception:                                   # noqa: BLE001
            return False

    def fileno(self):
        return self._real.fileno()

    @property
    def encoding(self):
        return getattr(self._real, "encoding", "utf-8")

    def writelines(self, lines):
        for line in lines:
            self.write(line)


# ─────────────────────────────────────────────────────────────────────────────
# Housekeeping
# ─────────────────────────────────────────────────────────────────────────────

def prune_old_logs(keep_days=KEEP_DAYS):
    """Delete log files last modified more than `keep_days` ago."""
    removed = []
    try:
        if not os.path.isdir(LOG_DIR):
            return removed
        cutoff = time.time() - (keep_days * 24 * 60 * 60)
        for name in os.listdir(LOG_DIR):
            if not name.endswith(".log"):
                continue
            full = os.path.join(LOG_DIR, name)
            try:
                if os.path.getmtime(full) < cutoff:
                    os.remove(full)
                    removed.append(name)
            except Exception:                               # noqa: BLE001
                pass
    except Exception:                                       # noqa: BLE001
        pass
    return removed


# ─────────────────────────────────────────────────────────────────────────────
# The one function programs actually call
# ─────────────────────────────────────────────────────────────────────────────

def setup_logging(program="ohbot", keep_days=KEEP_DAYS):
    """
    Start copying everything this program prints into logs/<program>-<date>.log

    Returns the path to the log file, or None if logging could not be started
    (which is never fatal — the program carries on printing to the screen).
    """
    global _installed
    if _installed:
        return None
    _installed = True

    log_file = _LogFile(program)
    if not log_file.handle:
        print("⚠️  Could not open a log file — carrying on without one.")
        return None

    real_stdout = sys.stdout
    real_stderr = sys.stderr
    sys.stdout = _Tee(real_stdout, log_file)
    sys.stderr = _Tee(real_stderr, log_file, tag=" ERR")

    # ── header, so each run is easy to find in the file ──────────────────────
    started = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("")
    print("=" * 62)
    print(f"  {program} starting — {started}")
    print(f"  log file: {log_file.path}")
    print(f"  pid {os.getpid()}  |  python {sys.version.split()[0]}")
    print("=" * 62)

    removed = prune_old_logs(keep_days)
    if removed:
        print(f"  (tidied up {len(removed)} log file(s) older than {keep_days} days)")

    # ── make sure crashes end up in the file too ─────────────────────────────
    previous_hook = sys.excepthook

    def log_crash(exc_type, exc_value, exc_tb):
        # We only add the banner. The traceback itself goes to stderr, which
        # is already being copied into the log — printing it here as well just
        # gets you two copies of the same thing.
        try:
            print("\n" + "!" * 62)
            print("  CRASHED — full details below")
            print("!" * 62)
            sys.stdout.flush()
        except Exception:                                   # noqa: BLE001
            pass
        previous_hook(exc_type, exc_value, exc_tb)

    sys.excepthook = log_crash

    # ── footer on the way out ────────────────────────────────────────────────
    def on_exit():
        try:
            ended = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n=== {program} stopped — {ended} ===\n")
            sys.stdout.flush()
        except Exception:                                   # noqa: BLE001
            pass
        log_file.close()

    atexit.register(on_exit)

    return log_file.path


def current_log_path(program="ohbot"):
    """Where today's log for this program would be, without opening it."""
    today = datetime.now().strftime("%Y-%m-%d")
    return os.path.join(LOG_DIR, f"{program}-{today}.log")


if __name__ == "__main__":
    path = setup_logging("logging-selftest")
    print("This line should appear on screen AND in the log file.")
    print("Multi", "part", "line", "with", "spaces")
    sys.stderr.write("This one is an error line.\n")
    print(f"\nWrote: {path}")
