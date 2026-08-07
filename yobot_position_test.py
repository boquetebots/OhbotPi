#!/usr/bin/env python3
"""
================================================================================
 YOBOT MANUAL POSITION TEST TOOL
================================================================================
Run this ON THE PI (over SSH), in the same folder as ohbot_pi.py.

WHAT THIS IS FOR
-----------------
This is a simpler cousin of yobot_calibrate.py. Instead of nudging a motor
with the keyboard, you type an exact position number (0-1000) and press
Enter, and the motor jumps straight there. Use it to try out specific
numbers and see how they look on the robot.

THIS SCRIPT NEVER SAVES ANYTHING. It does not touch
MotorDefinitionsv21.omd, MotorDefinitionsYobot.omd, or any other file you
care about. Whatever positions you find, you write down yourself — nothing
is recorded automatically.

BEFORE YOU RUN THIS
--------------------
1. Stop the two background services — they hold the same USB cable this
   script needs:

       sudo systemctl stop ohbot-server
       sudo systemctl stop ohbot-conversation

2. Make sure the Yobot's brain board is plugged into the Pi via USB.

3. cd to the project folder and run the script:

       cd ~/Projects/Ohbot
       python3 yobot_position_test.py

   When you're done, remember to start the services again:

       sudo systemctl start ohbot-server
       sudo systemctl start ohbot-conversation

WHAT THE SCRIPT DOES
----------------------
- Reads ohbotData/MotorDefinitionsv21.omd only to find out which motor
  number and wiring (Reverse) setting goes with each motor name. It does
  NOT use that file's Min/Max limits.
- Temporarily gives every motor a wide-open range (0-1000, its full
  mechanical swing) so any number you type is reachable. This uses a
  throwaway working file that is deleted when the script exits — your
  real files are never touched.
- Moves every motor to 500 (the middle) EXCEPT the two lip motors
  (TopLip, BottomLip), which start at 900 (mostly open) for safety.
- Turns OFF the built-in "lips can't crash into each other" safety rule
  for the whole session, so you have full independent control of each
  lip. The two lip motors come LAST in the motor order, with an on-screen
  warning, so you can go slowly and watch closely while they're
  unprotected.
- For each motor, lets you type as many position numbers as you like
  (0-1000). Each one moves the motor immediately. Press Enter with
  nothing typed to move on to the next motor. Type 'q' at any time to
  stop the whole script.

CONTROLS
---------
  <number> + Enter     move the current motor to that position (0-1000)
  Enter (nothing typed) move on to the next motor
  q + Enter             quit the whole script right now

A NOTE ON DIRECTION
---------------------
If a motor moves the "wrong way" for a given number, that's the "Reverse"
wiring setting in the .omd file, not something this script changes.
================================================================================
"""

import os
import sys
import time
from lxml import etree

import ohbot_pi as ohbot

# ------------------------------------------------------------------------
# File locations
# ------------------------------------------------------------------------
SOURCE_OMD = "ohbotData/MotorDefinitionsv21.omd"
WORKING_OMD = "ohbotData/_yobot_position_test_working.omd"   # temporary, deleted at the end

# Motor index constants (must match ohbot_pi.py)
HEADNOD = 0
HEADTURN = 1
EYETURN = 2
LIDBLINK = 3
TOPLIP = 4
BOTTOMLIP = 5
EYETILT = 6
HEADROLL = 7

# Order to go through motors in: everything except the lips first (safe,
# nothing to pinch), then TopLip, then BottomLip last, with a warning.
MOTOR_ORDER = [HEADTURN, HEADNOD, EYETURN, EYETILT, LIDBLINK, HEADROLL, TOPLIP, BOTTOMLIP]

MOVE_SPEED = 3   # gentle speed (0-10 scale) used for every move


# ============================================================================
# Reading the source .omd (for Motor#/Speed/Reverse/Acceleration/Avoid only)
# ============================================================================

def load_source_motors():
    if not os.path.exists(SOURCE_OMD):
        print(f"Could not find {SOURCE_OMD}. Nothing to read — stopping.")
        sys.exit(1)
    try:
        tree = etree.parse(SOURCE_OMD)
    except etree.XMLSyntaxError as e:
        print(f"\n{SOURCE_OMD} has a formatting error and can't be read:")
        print(f"  {e}")
        print("This usually means a quote mark (\") is missing somewhere in")
        print("that file. Fix it in a text editor and try again.")
        sys.exit(1)

    motors = []
    for child in tree.getroot():
        motors.append({
            "Name": child.get("Name"),
            "Motor": child.get("Motor"),
            "Speed": child.get("Speed"),
            "Reverse": child.get("Reverse"),
            "Acceleration": child.get("Acceleration"),
            "RestPosition": child.get("RestPosition"),
            "Avoid": child.get("Avoid", ""),
        })
    return motors


def write_working_omd(source_motors):
    """Throwaway file with every motor's Min/Max thrown wide open (0-1000)
    so any typed number is reachable. Deleted when the script exits."""
    root = etree.Element("Motors")
    for m in source_motors:
        etree.SubElement(root, "Motor", {
            "Name": m["Name"],
            "Min": "0",
            "Max": "1000",
            "Motor": m["Motor"],
            "Speed": m["Speed"],
            "Reverse": m["Reverse"],
            "Acceleration": m["Acceleration"],
            "RestPosition": m["RestPosition"],
            "Avoid": m["Avoid"],
        })
    etree.ElementTree(root).write(WORKING_OMD, pretty_print=True, xml_declaration=False)


def cleanup_working_file():
    try:
        if os.path.exists(WORKING_OMD):
            os.remove(WORKING_OMD)
    except OSError:
        pass


# ============================================================================
# Motor movement
# ============================================================================

def move_raw(idx, raw):
    """Move a motor to a raw 0-1000 position (matches the wide-open Min=0/
    Max=1000 working file, so raw/100 is exactly the 0-10 API position)."""
    raw = max(0, min(1000, raw))
    ohbot.move(idx, raw / 100.0, MOVE_SPEED, avoid=False)
    return raw


# ============================================================================
# Main loop
# ============================================================================

def run():
    print("Reading motor wiring info from", SOURCE_OMD)
    source_motors = load_source_motors()
    write_working_omd(source_motors)

    ohbot.motorDefFile = WORKING_OMD
    print("Connecting to Yobot over USB...")
    connected = ohbot.init()
    if not connected:
        print("\nCould not connect to the Yobot.")
        print("Check that:")
        print("  - The two background services are stopped:")
        print("      sudo systemctl stop ohbot-server")
        print("      sudo systemctl stop ohbot-conversation")
        print("  - The USB cable is plugged in.")
        cleanup_working_file()
        sys.exit(1)

    print("Connected. Moving all motors to their starting positions...")
    current_raw = {}
    for idx in range(8):
        start = 900 if idx in (TOPLIP, BOTTOMLIP) else 500
        current_raw[idx] = move_raw(idx, start)
        time.sleep(0.15)
    print("Lips are mostly open, everything else is centered.\n")
    time.sleep(0.5)

    name_by_idx = {int(m["Motor"]): m["Name"] for m in source_motors}
    quit_now = False

    try:
        for idx in MOTOR_ORDER:
            if quit_now:
                break
            name = name_by_idx[idx]

            if idx in (TOPLIP, BOTTOMLIP):
                print("\n" + "=" * 60)
                print(f"  ⚠  {name}: lip safety is OFF. Type numbers carefully and")
                print("     watch closely so the lips don't pinch on each other.")
                print("=" * 60)

            print(f"\n--- {name} (motor {idx}) ---")
            print(f"Currently at: {current_raw[idx]}")
            print("Type a number 0-1000 and press Enter to move there.")
            print("Press Enter with nothing typed to go to the next motor.")
            print("Type 'q' and press Enter to quit.\n")

            while True:
                raw_input_str = input(f"{name} position (now {current_raw[idx]}): ").strip()

                if raw_input_str == "":
                    break  # next motor

                if raw_input_str.lower() == "q":
                    quit_now = True
                    break

                try:
                    value = int(raw_input_str)
                except ValueError:
                    print("  Please type a whole number between 0 and 1000, or just press Enter.")
                    continue

                if value < 0 or value > 1000:
                    print("  That's outside 0-1000 — clamping to the nearest valid value.")

                current_raw[idx] = move_raw(idx, value)
                print(f"  Moved to {current_raw[idx]}")

    except KeyboardInterrupt:
        print("\n\nInterrupted — stopping now.")

    finally:
        print("\nDetaching motors and closing connection...")
        ohbot.close()
        cleanup_working_file()

    print("\nDone. Nothing was saved to any file — write down any positions")
    print("you want to keep.")
    print("\nDon't forget to restart the services:")
    print("  sudo systemctl start ohbot-server")
    print("  sudo systemctl start ohbot-conversation")


if __name__ == "__main__":
    run()
