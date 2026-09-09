#!/usr/bin/env python3
"""
eye_speed_test.py — find out what is actually making Yobot's eyes twitch

WHY THIS EXISTS
---------------
Slowing the eye movements down in the show did not work, which means one
of two things is true and we do not yet know which:

  A) The speed number does nothing to the eye motors, so they always slam
     to their target as fast as the servo can physically go.
  B) The speed number works fine, but the eyes were simply not moving FAR
     enough for anyone to read it as a move.

This tests both, one at a time, so you can just watch and tell me what you
saw. It does not touch any other file.

BEFORE YOU RUN IT
-----------------
Stop the show server (and the Greeter, and the Sequence Builder). Only one
program can hold the robot's USB cable at a time.

HOW TO RUN IT
-------------
    ~/yobot-venv/bin/python3 eye_speed_test.py

It prints what it is about to do, then does it, then waits for you to
press Return before the next one. Nothing is saved, nothing is changed.
Press Ctrl-C at any time to stop.

WHAT TO TELL ME
---------------
  Part 1 — did the four moves look DIFFERENT from each other, or did all
           four look identical?
  Part 2 — which number was the first one that looked like a real LOOK
           rather than a twitch?
"""

import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import ohbot_pi as ohbot


def pause(msg="   ...press Return for the next one "):
    try:
        input(msg)
    except (EOFError, KeyboardInterrupt):
        print("\nStopped.")
        raise SystemExit(0)


def swing(motor, low, high, speed, times=3, settle=1.4):
    """Rock a motor back and forth so it is easy to watch."""
    ohbot.move(motor, 5, 4)
    time.sleep(0.8)
    for _ in range(times):
        t0 = time.time()
        ohbot.move(motor, low, speed)
        time.sleep(settle)
        ohbot.move(motor, high, speed)
        time.sleep(settle)
    ohbot.move(motor, 5, speed)
    time.sleep(settle)


def main():
    print("\nConnecting to the robot...")
    if not ohbot.init():
        print("\n❌ Robot not found.")
        print("   Is the show server or the Greeter still running?")
        print("   Stop it, then unplug and replug the USB cable and try again.\n")
        return
    ohbot.reset()
    time.sleep(1.5)
    print("✅ Connected.\n")

    print("=" * 66)
    print("PART 1 — DOES THE SPEED NUMBER DO ANYTHING AT ALL?")
    print("=" * 66)
    print("Same big eye swing (3.5 to 6.5) four times, at four very")
    print("different speeds. If speed works, these should look obviously")
    print("different from each other. If they all look the same, the eye")
    print("motors are ignoring speed and always moving flat out.\n")
    pause("   ...press Return to start Part 1 ")

    for n, spd in enumerate([10, 5, 2, 1], 1):
        print(f"\n  1.{n}  speed {spd}   <- watch how FAST the eyes move")
        swing(ohbot.EYETURN, 3.5, 6.5, spd)
        pause()

    print("\n" + "=" * 66)
    print("PART 2 — HOW FAR DO THE EYES NEED TO MOVE?")
    print("=" * 66)
    print("All at the same slow speed (1.5). Only the DISTANCE changes,")
    print("getting bigger each time. Tell me the first number that looks")
    print("like a real look instead of a twitch.\n")
    pause("   ...press Return to start Part 2 ")

    for n, (lo, hi, label) in enumerate([
        (3.9, 6.1, "small  - this is what the show does now"),
        (3.0, 7.0, "medium"),
        (2.0, 8.0, "large"),
        (0.5, 9.5, "nearly the whole eye range"),
    ], 1):
        print(f"\n  2.{n}  eyes {lo} to {hi}   ({label})")
        swing(ohbot.EYETURN, lo, hi, 1.5)
        pause()

    print("\n" + "=" * 66)
    print("PART 3 — THE SAME TWO QUESTIONS FOR EYE TILT (up and down)")
    print("=" * 66)
    pause("   ...press Return to start Part 3 ")

    print("\n  3.1  eye tilt, small swing, speed 1.5")
    swing(ohbot.EYETILT, 3.9, 6.1, 1.5)
    pause()
    print("\n  3.2  eye tilt, large swing, speed 1.5")
    swing(ohbot.EYETILT, 2.0, 8.0, 1.5)
    pause()

    print("\nTidying up...")
    ohbot.reset()
    time.sleep(1.0)
    print("\nDone. Tell me:")
    print("  Part 1 — did 1.1 / 1.2 / 1.3 / 1.4 look different, or all the same?")
    print("  Part 2 — which number first looked like a real look?")
    print("  Part 3 — same question for the up-and-down.\n")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
        try:
            ohbot.reset()
        except Exception:
            pass
