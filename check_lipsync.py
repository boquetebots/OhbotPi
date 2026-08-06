#!/usr/bin/env python3
"""
check_lipsync.py — why aren't the lips moving?

Answers three questions, in order, and tells you which one failed:

  1. Is the robot actually connected on this machine?
  2. Does Azure send back viseme (mouth shape) events for a test phrase?
  3. Do the lip motors physically move when told to?

No guessing — each step prints a clear PASS or FAIL.

Run it from the project folder with the venv's python:

    cd /Users/michael/Projects/OhbotPi2
    ~/yobot-venv/bin/python3 check_lipsync.py

Nothing here changes any settings or files. It is safe to run any time.
"""

import os
import sys
import tempfile
import time

print("=" * 62)
print("LIP SYNC CHECK")
print("=" * 62)

# ── 1. Robot connection ────────────────────────────────────────────────────
print("\n[1/3] Looking for the robot...")
try:
    import yobot_core as yobot
except Exception as e:
    print(f"  FAIL — could not import yobot_core: {e}")
    sys.exit(1)

if not yobot.init():
    print("  FAIL — no robot found on this machine.")
    print()
    print("  This is the most common cause of 'speech works but lips don't'.")
    print("  yobot_mac.py say prints a one-line warning about this and then")
    print("  speaks anyway, which is easy to miss.")
    print()
    print("  Usual reason: another program is holding the USB cable. Only one")
    print("  program can use it at a time. Stop the calibration server, the")
    print("  GUI server and the launcher, then try again.")
    print("  If that doesn't do it, unplug and replug the USB cable.")
    sys.exit(1)

print(f"  PASS — robot connected on port {yobot.port}")

# Show what the lips are calibrated to, since that is the thing under test.
tl, bl = yobot.TOPLIP, yobot.BOTTOMLIP
print(f"  Top lip    min {yobot.motorMins[tl]:3}  centre {yobot.motorCenters[tl]:6.1f}  "
      f"max {yobot.motorMaxs[tl]:3}  (degrees)")
print(f"  Bottom lip min {yobot.motorMins[bl]:3}  centre {yobot.motorCenters[bl]:6.1f}  "
      f"max {yobot.motorMaxs[bl]:3}  (degrees)")
for name, m in (("Top lip", tl), ("Bottom lip", bl)):
    midpoint = (yobot.motorMins[m] + yobot.motorMaxs[m]) / 2
    kind = "3-point" if abs(yobot.motorCenters[m] - midpoint) > 0.01 else "midpoint only"
    print(f"  {name} calibration: {kind}")

# ── 2. Do the lips physically move? ────────────────────────────────────────
print("\n[2/3] Moving the lips directly — watch the mouth...")
try:
    yobot.move(tl, 5, 5, avoid=False)
    yobot.move(bl, 5, 5, avoid=False)
    time.sleep(1)
    print("  ...closed (position 5 on both lips)")
    time.sleep(0.5)
    for _ in range(2):
        yobot.move(tl, 8, 8, avoid=False)
        yobot.move(bl, 8, 8, avoid=False)
        time.sleep(0.6)
        yobot.move(tl, 5, 8, avoid=False)
        yobot.move(bl, 5, 8, avoid=False)
        time.sleep(0.6)
    print("  ...opened and closed twice (positions 5 <-> 8)")
    print("  PASS if you saw the mouth open and shut. If it did NOT move,")
    print("       the problem is the motors or the cable, not Azure.")
except Exception as e:
    print(f"  FAIL — error moving the lips: {e}")
    yobot.close()
    sys.exit(1)

# ── 3. Does Azure send viseme events? ──────────────────────────────────────
print("\n[3/3] Asking Azure for viseme (mouth shape) events...")

if not os.environ.get("AZURE_SPEECH_KEY"):
    print("  SKIPPED — no AZURE_SPEECH_KEY found.")
    print("  The .env file needs to be in this folder. Steps 1 and 2 above")
    print("  still tell you whether the hardware side is healthy.")
    yobot.reset()
    yobot.close()
    sys.exit(0)

try:
    from ohbot_azure import AzureSpeechManager, VisemeMapper

    azure = AzureSpeechManager()
    phrase = "Hello. My name is Yobot. Peter picked a peck of peppers."
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp = f.name

    visemes = azure.synthesize_to_file_with_visemes(phrase, tmp)
    try:
        os.unlink(tmp)
    except OSError:
        pass

    if not visemes:
        print("  FAIL — Azure returned ZERO viseme events.")
        print()
        print("  Speech would still work, but ohbot_azure.py only starts the")
        print("  lip animation when it gets visemes, so the mouth stays still.")
        print("  Usually means the configured voice doesn't support visemes.")
    else:
        print(f"  PASS — Azure returned {len(visemes)} viseme events.")
        tops = [VisemeMapper.get_lip_positions(v['viseme_id'])[0] for v in visemes]
        bots = [VisemeMapper.get_lip_positions(v['viseme_id'])[1] for v in visemes]
        print(f"  EXAGGERATION is currently {VisemeMapper.EXAGGERATION}")
        print(f"  Top lip would move between    {min(tops):.2f} and {max(tops):.2f}")
        print(f"  Bottom lip would move between {min(bots):.2f} and {max(bots):.2f}")
        if max(tops) - min(tops) < 0.5 and max(bots) - min(bots) < 0.5:
            print("  WARNING — that is barely any movement. Raise EXAGGERATION")
            print("            in ohbot_azure.py.")

except Exception as e:
    print(f"  FAIL — {type(e).__name__}: {e}")

print("\nResetting to neutral...")
yobot.reset()
yobot.close()
print("Done.")
