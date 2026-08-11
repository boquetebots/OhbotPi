#!/usr/bin/env python3
"""
ohbot_mic.py — find the microphone by NAME instead of by card number.

WHY THIS FILE EXISTS
--------------------
On 2026-08-10 at the Rincon Clubhouse, Yobot greeted people and then went
completely silent. The cause: the code asked ALSA for "plughw:3,0" — card
number 3 — but the real microphone was on card 2. Azure opened a device that
did not exist and waited forever. No error, no log, nothing.

Linux hands out card numbers at boot. Unplug the mic, plug in a USB speaker,
reboot in a different order, and yesterday's card 3 is today's card 2. Pinning
a number in a config file was always going to break eventually.

So: this module looks at what `arecord -l` actually reports and picks the
microphone by name. Card numbers stop mattering.

ORDER OF PREFERENCE
-------------------
  1. AZURE_MIC_DEVICE in .env — an exact device like "plughw:2,0".
     Still honoured, because sometimes you want to force a specific one.
     BUT it is now checked against reality first. If it points at a card that
     isn't there, we say so loudly and auto-detect instead of failing silently.
  2. AZURE_MIC_NAME in .env — part of the mic's name, e.g. "USB Audio".
     Case doesn't matter. Use this if you have two mics and want a specific one.
  3. Auto-detect — the first capture device whose name looks like a USB mic.
  4. Any capture device at all.

If there is genuinely no microphone attached, find_microphone() returns None
and the caller is expected to make a fuss about it out loud.

This module deliberately has NO dependencies beyond the Python standard
library, so it can be tested on the Mac without the Azure SDK installed.

Try it by hand on the Pi:

    python3 ohbot_mic.py
"""

import os
import re
import shutil
import subprocess

# Words that suggest "this is the USB microphone", best guess first.
# Matched case-insensitively against the card name, card id and device name.
USB_HINTS = ("usb audio", "usb-audio", "usb pnp", "usb mic", "webcam", "usb")

# Used only if detection finds nothing at all and the caller insists on a
# device string anyway. It is a guess, and a bad one — that is the point.
LAST_RESORT_DEVICE = "plughw:1,0"


# ─────────────────────────────────────────────────────────────────────────────
# Reading the list of microphones
# ─────────────────────────────────────────────────────────────────────────────

# `arecord -l` prints lines that look like this:
#
#   card 2: Audio [USB Audio], device 0: USB Audio [USB Audio]
#        │      │              │         │
#        │      │              │         └─ device name
#        │      │              └─ device number
#        │      └─ card name (the useful bit)
#        └─ card number (the bit that keeps changing)
_CARD_LINE = re.compile(
    r"^card\s+(\d+):\s+(\S+)\s+\[([^\]]*)\],\s+device\s+(\d+):\s+(.*?)\s*(?:\[([^\]]*)\])?\s*$",
    re.IGNORECASE,
)


def _run_arecord():
    """Return the raw text of `arecord -l`, or None if it can't be run."""
    if not shutil.which("arecord"):
        return None
    try:
        result = subprocess.run(
            ["arecord", "-l"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:                                       # noqa: BLE001
        return None
    # arecord prints "no soundcards found" to stderr and exits non-zero.
    return (result.stdout or "") + "\n" + (result.stderr or "")


def list_microphones(raw=None):
    """
    Return a list of the capture devices ALSA can see.

    Each entry is a dict:
        {"card": 2, "device": 0, "id": "Audio",
         "name": "USB Audio", "device_name": "USB Audio",
         "alsa": "plughw:2,0"}

    Pass `raw` to parse text you already have (used by the tests).
    """
    if raw is None:
        raw = _run_arecord()
    if not raw:
        return []

    mics = []
    for line in raw.splitlines():
        match = _CARD_LINE.match(line.strip())
        if not match:
            continue
        card_no, card_id, card_name, dev_no, dev_name, _dev_extra = match.groups()
        mics.append({
            "card": int(card_no),
            "device": int(dev_no),
            "id": card_id,
            "name": card_name,
            "device_name": (dev_name or "").strip(),
            "alsa": f"plughw:{int(card_no)},{int(dev_no)}",
        })
    return mics


def _haystack(mic):
    """All the text we're willing to match a name against, lowercased."""
    return " ".join([
        str(mic.get("id", "")),
        str(mic.get("name", "")),
        str(mic.get("device_name", "")),
    ]).lower()


def _looks_like_usb(mic):
    text = _haystack(mic)
    return any(hint in text for hint in USB_HINTS)


def describe(mic):
    """One-line human description of a mic, for logs."""
    return f"card {mic['card']}: {mic['name']} [{mic['device_name']}] → {mic['alsa']}"


# ─────────────────────────────────────────────────────────────────────────────
# Choosing one
# ─────────────────────────────────────────────────────────────────────────────

def _card_number_of(device_string):
    """'plughw:2,0' → 2.  Returns None if it can't be read."""
    match = re.search(r":\s*(\d+)", str(device_string))
    return int(match.group(1)) if match else None


def find_microphone(env=None, mics=None, verbose=True):
    """
    Work out which ALSA device to record from.

    Returns (device_string, reason) — e.g. ("plughw:2,0", "auto-detected USB mic").
    Returns (None, reason) if there is no microphone attached at all.

    Never raises. If anything goes wrong it says so and returns None, because
    a silent robot with no explanation is the exact bug this file exists to
    prevent.
    """
    env = os.environ if env is None else env
    if mics is None:
        mics = list_microphones()

    def say(message):
        if verbose:
            print(message)

    if mics:
        say(f"🎤 Microphones found: {len(mics)}")
        for mic in mics:
            say(f"     {describe(mic)}")
    else:
        say("🎤 Microphones found: none — `arecord -l` reported no capture devices")

    # ── 1. An exact device pinned in .env ────────────────────────────────────
    pinned = (env.get("AZURE_MIC_DEVICE") or "").strip()
    if pinned:
        wanted_card = _card_number_of(pinned)
        available = {mic["card"] for mic in mics}

        if not mics:
            # Can't check — no list to check against. Trust it and hope.
            say(f"🎤 Using AZURE_MIC_DEVICE={pinned} (unverified — no mic list available)")
            return pinned, "pinned in .env, could not verify"

        if wanted_card in available:
            say(f"🎤 Using AZURE_MIC_DEVICE={pinned} from .env")
            return pinned, "pinned in .env"

        say(f"⚠️  AZURE_MIC_DEVICE={pinned} points at card {wanted_card}, "
            f"which does NOT exist. Cards present: {sorted(available)}")
        say("⚠️  Ignoring it and detecting the microphone by name instead.")
        say("⚠️  Fix .env when you get a chance, or delete the line to always auto-detect.")

    # ── 2. A name fragment pinned in .env ────────────────────────────────────
    wanted_name = (env.get("AZURE_MIC_NAME") or "").strip().lower()
    if wanted_name:
        for mic in mics:
            if wanted_name in _haystack(mic):
                say(f"🎤 Matched AZURE_MIC_NAME='{wanted_name}' → {describe(mic)}")
                return mic["alsa"], f"matched name '{wanted_name}'"
        say(f"⚠️  AZURE_MIC_NAME='{wanted_name}' matched nothing. Falling back to auto-detect.")

    # ── 3. Auto-detect: anything that smells like a USB mic ──────────────────
    for mic in mics:
        if _looks_like_usb(mic):
            say(f"🎤 Auto-detected USB microphone → {describe(mic)}")
            return mic["alsa"], "auto-detected USB mic"

    # ── 4. Anything at all ───────────────────────────────────────────────────
    if mics:
        mic = mics[0]
        say(f"🎤 No USB mic recognised — using the first capture device → {describe(mic)}")
        return mic["alsa"], "first available capture device"

    # ── 5. Nothing ───────────────────────────────────────────────────────────
    say("❌ NO MICROPHONE FOUND. Yobot will be able to speak but not to hear.")
    say("   Check the USB mic is plugged in, then run:  arecord -l")
    return None, "no capture device found"


def find_microphone_or_fallback(env=None, mics=None, verbose=True):
    """
    Same as find_microphone(), but always returns a device string.

    Used by the speech code so that a bug in detection can never stop Yobot
    from trying. The caller still gets `ok=False` so it can complain out loud.

    Returns (device_string, ok, reason).
    """
    device, reason = find_microphone(env=env, mics=mics, verbose=verbose)
    if device:
        return device, True, reason
    return LAST_RESORT_DEVICE, False, reason


# ─────────────────────────────────────────────────────────────────────────────
# Run this file directly to see what it finds
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 62)
    print("  Ohbot microphone check")
    print("=" * 62)

    for var in ("AZURE_MIC_DEVICE", "AZURE_MIC_NAME"):
        value = os.environ.get(var)
        print(f"  {var:18} = {value if value else '(not set)'}")
    print()

    chosen, why = find_microphone()
    print()
    print("-" * 62)
    if chosen:
        print(f"  RESULT: Yobot will listen on  {chosen}")
        print(f"  REASON: {why}")
        print()
        print("  Test it for real with:")
        print(f"    arecord -D {chosen} -d 3 -f cd /tmp/mictest.wav && aplay /tmp/mictest.wav")
    else:
        print("  RESULT: no microphone — Yobot would not be able to hear.")
        print(f"  REASON: {why}")
    print("-" * 62)
