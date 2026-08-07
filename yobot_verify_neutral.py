#!/usr/bin/env python3
"""
================================================================================
 YOBOT NEUTRAL POSITION CHECK
================================================================================
Run this ON THE PI (over SSH), in the same folder as ohbot_pi.py.

WHAT THIS IS FOR
-----------------
gui_server.py moves ALL 8 motors at once on startup (its automatic
"reset to neutral" step). This script checks the same thing -- whether
ohbotData/MotorDefinitionsv21.omd loads correctly and whether each
motor's neutral (RestPosition) spot is sensible -- but ONE MOTOR AT A
TIME, with a pause before each move, so you can watch closely and stop
instantly if anything looks wrong.

THIS SCRIPT NEVER SAVES ANYTHING and never touches any .omd file. It only
reads MotorDefinitionsv21.omd.

BEFORE YOU RUN THIS
--------------------
1. Make sure nothing else is using the USB cable:

       sudo systemctl status ohbot-server
       sudo systemctl status ohbot-conversation
       systemctl --user status ohbot-gui.service

   All should show inactive/not found before you continue.

2. cd to the project folder and run the script:

       cd ~/Projects/Ohbot
       python3 yobot_verify_neutral.py

WHAT THE SCRIPT DOES
----------------------
- Loads ohbotData/MotorDefinitionsv21.omd -- the real file, not a
  temporary copy -- and immediately prints out what it actually loaded
  for every motor (its min/max in degrees, its neutral setting, whether
  it's wired "reversed"). If the file failed to load the way it did
  before, this print-out will show every motor at 0/0, which is the
  same broken pattern we saw earlier. That alone tells you if the file
  read correctly, before anything even moves.
- Then goes through the 8 motors ONE AT A TIME -- everything except the
  lips first, then TopLip, then BottomLip last -- and for each one:
    - Shows you its neutral position.
    - Waits for you to press Enter before moving.
    - Moves ONLY that motor. Nothing else moves at the same time.
- Type 'q' instead of Enter at any point to stop immediately.

Once every motor has settled into its neutral spot cleanly, one at a
time, gui_server.py's all-at-once reset should be safe to try again.
================================================================================
"""

import os
import sys
import time
from lxml import etree

import ohbot_pi as ohbot

SOURCE_OMD = "ohbotData/MotorDefinitionsv21.omd"

HEADNOD = 0
HEADTURN = 1
EYETURN = 2
LIDBLINK = 3
TOPLIP = 4
BOTTOMLIP = 5
EYETILT = 6
HEADROLL = 7

# Non-lip motors first (nothing to pinch), lips last, with a warning.
MOTOR_ORDER = [HEADTURN, HEADNOD, EYETURN, EYETILT, LIDBLINK, HEADROLL, TOPLIP, BOTTOMLIP]

MOVE_SPEED = 3   # gentle speed (0-10 scale)


def run():
    print("Connecting to Yobot over USB, loading", SOURCE_OMD, "as-is...")
    ohbot.motorDefFile = SOURCE_OMD
    connected = ohbot.init()
    if not connected:
        print("\nCould not connect to the Yobot.")
        print("Check the USB cable and that no other program is using it.")
        sys.exit(1)

    print("Connected. Here is what actually got loaded from the file:\n")

    # Figure out motor index -> name from the file itself.
    tree = etree.parse(SOURCE_OMD)
    name_by_idx = {}
    for child in tree.getroot():
        name_by_idx[int(child.get("Motor"))] = child.get("Name")

    # "Center (deg)" is where slider position 5 actually lands. A motor that
    # has been three-point calibrated shows a centre that is NOT the halfway
    # point between Min and Max — that is the whole point, and is flagged
    # with "3pt" in the last column. Motors with no Center in the .omd file
    # fall back to the midpoint and behave exactly as they always have.
    print(f"{'Motor':<12}{'Min (deg)':<12}{'Center (deg)':<14}{'Max (deg)':<12}"
          f"{'RestPosition':<14}{'Reversed':<11}{'Calibration'}")
    for idx in range(8):
        name = name_by_idx.get(idx, f"motor {idx}")
        centre = ohbot.motorCenters[idx]
        midpoint = (ohbot.motorMins[idx] + ohbot.motorMaxs[idx]) / 2
        kind = "3pt" if abs(centre - midpoint) > 0.01 else "midpoint"
        print(f"{name:<12}{ohbot.motorMins[idx]:<12}{centre:<14.1f}"
              f"{ohbot.motorMaxs[idx]:<12}{ohbot.restPos[idx]:<14}"
              f"{str(ohbot.motorRev[idx]):<11}{kind}")

    if all(ohbot.motorMins[i] == 0 and ohbot.motorMaxs[i] == 0 for i in range(8)):
        print("\n⚠  Every motor shows Min=0 and Max=0 -- this is the broken")
        print("   'file did not load' pattern from before. Stopping here so")
        print("   nothing moves. Check the file path and try again.")
        ohbot.close()
        sys.exit(1)

    print("\nLooks like the file loaded. Now let's move each motor to its")
    print("neutral position, one at a time. Press Enter before each move,")
    print("or 'q' + Enter at any point to stop.\n")

    try:
        for idx in MOTOR_ORDER:
            name = name_by_idx.get(idx, f"motor {idx}")

            if idx in (TOPLIP, BOTTOMLIP):
                print("\n" + "=" * 60)
                print(f"  ⚠  {name}: watch closely, lip safety is off here too.")
                print("=" * 60)

            rest = ohbot.restPos[idx]
            answer = input(f"\nPress Enter to move {name} to its neutral position (RestPosition {rest}), or 'q' to stop: ").strip().lower()
            if answer == "q":
                print("Stopping.")
                break

            if idx in (TOPLIP, BOTTOMLIP):
                ohbot._move(idx, rest, MOVE_SPEED, avoid=False)
            else:
                ohbot.move(idx, rest, MOVE_SPEED)

            time.sleep(0.5)
            print(f"  {name} moved. Take a look before continuing.")

    except KeyboardInterrupt:
        print("\n\nInterrupted -- stopping now.")

    finally:
        print("\nDetaching motors and closing connection...")
        ohbot.close()

    print("\nDone. Nothing was saved -- this script only reads the file.")


if __name__ == "__main__":
    run()
