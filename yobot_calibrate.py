#!/usr/bin/env python3
"""
================================================================================
 YOBOT SERVO CALIBRATION TOOL
================================================================================
Run this ON THE PI (over SSH), in the same folder as ohbot_pi.py.

WHAT THIS IS FOR
-----------------
The Yobot is a larger, custom 3D-printed rebuild of the Ohbot. Its 8 servo
motors physically move over a different range than the original small Ohbot,
so the Min/Max/RestPosition numbers in MotorDefinitionsv21.omd are only
"close" — not correct. This script lets you find the real safe minimum,
maximum, and resting position for each motor by nudging it with the keyboard
while you watch the robot, and saves the results into a brand new file:

    ohbotData/MotorDefinitionsYobot.omd

Your original ohbotData/MotorDefinitionsv21.omd is never modified.

BEFORE YOU RUN THIS
--------------------
1. Stop the two background services — they hold the same USB cable this
   script needs, so they must not be running at the same time:

       sudo systemctl stop ohbot-server
       sudo systemctl stop ohbot-conversation

2. Make sure the Yobot's brain board is plugged into the Pi via USB.

3. cd to the project folder and run the script:

       cd /home/michael/Projects/Ohbot
       python3 yobot_calibrate.py

   When you're done, remember to start the services again:

       sudo systemctl start ohbot-server
       sudo systemctl start ohbot-conversation

WHAT THE SCRIPT DOES
----------------------
- Temporarily gives every motor a wide-open range (0-1000, its full
  mechanical swing) so you can explore the complete range of motion. This
  does NOT touch your original .omd file — it's a throwaway working copy.
- Moves every motor to the middle position (500) EXCEPT the two lip motors
  (TopLip, BottomLip), which start fully OPEN (1000) so the mouth can't
  pinch shut on anything while you calibrate the other motors first.
- Turns OFF the built-in "lips can't crash into each other" safety rule for
  the whole session, so you have full independent control of each lip.
  The two lip motors are calibrated LAST, with an on-screen warning, so
  you can go slowly and watch closely while they're unprotected.
- Walks you through each motor, one at a time, in three steps:
    1) Jog it to find the safe MINIMUM and lock it in.
    2) Jog it to find the safe MAXIMUM and lock it in.
    3) Jog it to where it should sit normally (NEUTRAL / resting position)
       and lock it in.
- Saves everything to ohbotData/MotorDefinitionsYobot.omd — either when you
  finish all 8 motors, or if you quit early with 'q' (whatever you already
  locked in is kept; anything you never got to keeps its original number
  from MotorDefinitionsv21.omd).

CONTROLS
---------
  w        nudge the motor UP (increase position)
  s        nudge the motor DOWN (decrease position)
  ,        make the nudge step SMALLER (finer control)
  .        make the nudge step BIGGER (faster movement)
  ENTER    lock in the current value, move to the next step
  b        go BACK one step (e.g. redo the minimum)
  x        skip this motor entirely (keep its old numbers, move on)
  q        quit now — saves everything locked in so far

A NOTE ON DIRECTION
---------------------
If a motor moves the "wrong way" when you press w/s (e.g. the head turns
right when you expect left), that's a wiring/orientation setting called
"Reverse" in the .omd file, not something this script changes. Make a note
of which motor(s) do this and mention it afterwards — it's a one-line fix.
================================================================================
"""

import os
import sys
import time
import tty
import termios
from lxml import etree

import ohbot_pi as ohbot

# ------------------------------------------------------------------------
# File locations
# ------------------------------------------------------------------------
SOURCE_OMD = "ohbotData/MotorDefinitionsv21.omd"
WORKING_OMD = "ohbotData/_yobot_calibration_working.omd"   # temporary, deleted at the end
OUTPUT_OMD = "ohbotData/MotorDefinitionsYobot.omd"

# Motor index constants (must match ohbot_pi.py)
HEADNOD = 0
HEADTURN = 1
EYETURN = 2
LIDBLINK = 3
TOPLIP = 4
BOTTOMLIP = 5
EYETILT = 6
HEADROLL = 7

# Order to calibrate in: everything except the lips first (safe, nothing to
# pinch), then TopLip, then BottomLip last, with extra warnings.
CALIBRATION_ORDER = [HEADTURN, HEADNOD, EYETURN, EYETILT, LIDBLINK, HEADROLL, TOPLIP, BOTTOMLIP]

JOG_SPEED = 3          # gentle speed (0-10 scale) used for every jog move
STEP_CHOICES = [1, 5, 10, 25, 50, 100]
DEFAULT_STEP_INDEX = 1  # starts at step = 5


# ============================================================================
# Keyboard input (single keypress, no Enter needed for jogging)
# ============================================================================

def getch():
    """Read one keypress from the terminal without needing Enter."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    if ch == "\x03":   # Ctrl+C while in raw mode doesn't raise KeyboardInterrupt
        raise KeyboardInterrupt
    return ch


# ============================================================================
# Reading / writing the .omd file
# ============================================================================

def load_source_motors():
    """Read the original .omd file into a list of dicts, in file order."""
    tree = etree.parse(SOURCE_OMD)
    motors = []
    for child in tree.getroot():
        motors.append({
            "Name": child.get("Name"),
            "Min": child.get("Min"),
            "Max": child.get("Max"),
            "Motor": child.get("Motor"),
            "Speed": child.get("Speed"),
            "Reverse": child.get("Reverse"),
            "Acceleration": child.get("Acceleration"),
            "RestPosition": child.get("RestPosition"),
            "Avoid": child.get("Avoid", ""),
        })
    return motors


def write_working_omd(source_motors):
    """Write a temporary .omd with every motor's Min/Max thrown wide open
    (0-1000), so the full mechanical range is reachable during calibration.
    Reverse/Speed/Acceleration/Avoid are carried over unchanged."""
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
    tree = etree.ElementTree(root)
    tree.write(WORKING_OMD, pretty_print=True, xml_declaration=False)


def write_output_omd(source_motors, results):
    """Write the final MotorDefinitionsYobot.omd. `results` maps motor index
    -> {"min": raw 0-1000, "max": raw 0-1000, "neutral": raw 0-1000} for
    every motor that was calibrated. Motors not in `results` (skipped, or
    never reached because of an early quit) keep their original numbers."""
    root = etree.Element("Motors")
    for m in source_motors:
        idx = int(m["Motor"])
        r = results.get(idx)
        if r is None:
            min_val = m["Min"]
            max_val = m["Max"]
            rest_val = m["RestPosition"]
        else:
            min_val = str(int(round(r["min"])))
            max_val = str(int(round(r["max"])))
            # RestPosition in the .omd is on a 0-10 scale, not the 0-1000
            # raw scale used everywhere else in this script.
            rest_val = str(int(round(r["neutral"] / 100.0)))
        etree.SubElement(root, "Motor", {
            "Name": m["Name"],
            "Min": min_val,
            "Max": max_val,
            "Motor": m["Motor"],
            "Speed": m["Speed"],
            "Reverse": m["Reverse"],
            "Acceleration": m["Acceleration"],
            "RestPosition": rest_val,
            "Avoid": m["Avoid"],
        })
    tree = etree.ElementTree(root)
    tree.write(OUTPUT_OMD, pretty_print=True, xml_declaration=False)


# ============================================================================
# Calibration UI
# ============================================================================

def move_raw(idx, raw):
    """Move a motor to a raw 0-1000 position (matches the wide-open Min=0/
    Max=1000 working file, so raw/100 is exactly the 0-10 API position)."""
    raw = max(0, min(1000, raw))
    ohbot.move(idx, raw / 100.0, JOG_SPEED, avoid=False)
    return raw


def jog_stage(name, idx, stage_label, start_raw, instructions):
    """Interactive jog loop for one stage (min / max / neutral) of one
    motor. Returns ('locked', raw_value), ('back', None), ('skip', None),
    or ('quit', raw_value)."""
    raw = move_raw(idx, start_raw)
    step_i = DEFAULT_STEP_INDEX

    print(f"\n--- {name} : {stage_label} ---")
    print(instructions)
    print("w = up   s = down   , = smaller step   . = bigger step")
    print("ENTER = lock in    b = back    x = skip motor    q = quit & save\n")

    while True:
        step = STEP_CHOICES[step_i]
        print(f"\r  position: {raw:4d} / 1000     step: {step:3d}     ", end="", flush=True)
        ch = getch()

        if ch == "w":
            raw = move_raw(idx, raw + step)
        elif ch == "s":
            raw = move_raw(idx, raw - step)
        elif ch == ".":
            step_i = min(step_i + 1, len(STEP_CHOICES) - 1)
        elif ch == ",":
            step_i = max(step_i - 1, 0)
        elif ch in ("\r", "\n"):
            print(f"\r  locked in: {raw}                              ")
            return ("locked", raw)
        elif ch == "b":
            print()
            return ("back", None)
        elif ch == "x":
            print()
            return ("skip", None)
        elif ch == "q":
            print()
            return ("quit", raw)
        # any other key is ignored


def calibrate_motor(name, idx, start_raw):
    """Run the 3-stage (min, max, neutral) calibration for one motor.
    Returns ("done", {...}), ("skip", None), or ("quit", partial_dict_or_None)."""
    stages = ["min", "max", "neutral"]
    values = {}
    stage_i = 0
    current_raw = start_raw

    while stage_i < len(stages):
        stage = stages[stage_i]
        if stage == "min":
            instr = "Jog DOWN until it's about to hit a hard stop or strain, then back off\na touch. That's the safe minimum."
        elif stage == "max":
            instr = "Jog UP until it's about to hit a hard stop or strain, then back off\na touch. That's the safe maximum."
        else:
            instr = "Jog to wherever this motor should normally rest (its neutral pose)."

        result, value = jog_stage(name, idx, stage.upper(), current_raw, instr)

        if result == "locked":
            values[stage] = value
            current_raw = value
            stage_i += 1
        elif result == "back":
            if stage_i == 0:
                print("  (already at the first step for this motor)")
                continue
            stage_i -= 1
            current_raw = values.get(stages[stage_i], current_raw)
        elif result == "skip":
            return ("skip", None)
        elif result == "quit":
            values["_last_raw"] = value
            return ("quit", values if values else None)

    return ("done", values)


def run():
    print("Loading original motor definitions from", SOURCE_OMD)
    source_motors = load_source_motors()
    write_working_omd(source_motors)

    # Point ohbot_pi at our wide-open working file, then connect.
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

    print("Connected. Moving all motors to their safe starting positions...")
    for idx in range(8):
        start = 1000 if idx in (TOPLIP, BOTTOMLIP) else 500
        move_raw(idx, start)
        time.sleep(0.15)
    print("Mouth is fully open and all other motors are centered.\n")
    time.sleep(0.5)

    name_by_idx = {int(m["Motor"]): m["Name"] for m in source_motors}
    results = {}
    quit_now = False

    try:
        for idx in CALIBRATION_ORDER:
            name = name_by_idx[idx]

            if idx in (TOPLIP, BOTTOMLIP):
                print("\n" + "=" * 60)
                print(f"  ⚠  {name}: lip safety is OFF. Jog slowly and watch")
                print("     closely so the lips don't pinch on each other.")
                print("=" * 60)

            start_raw = 1000 if idx in (TOPLIP, BOTTOMLIP) else 500
            outcome, values = calibrate_motor(name, idx, start_raw)

            if outcome == "done":
                results[idx] = {
                    "min": values["min"],
                    "max": values["max"],
                    "neutral": values["neutral"],
                }
                print(f"{name}: saved  min={values['min']}  max={values['max']}  neutral={values['neutral']}")
            elif outcome == "skip":
                print(f"{name}: skipped, keeping original numbers.")
            elif outcome == "quit":
                print(f"\n{name}: quitting now.")
                if values and "min" in values and "max" in values:
                    results[idx] = {
                        "min": values["min"],
                        "max": values["max"],
                        "neutral": values.get("neutral", values.get("_last_raw", (values["min"] + values["max"]) // 2)),
                    }
                quit_now = True
                break

    except KeyboardInterrupt:
        print("\n\nInterrupted — saving whatever was already locked in.")

    finally:
        print("\nDetaching motors and closing connection...")
        ohbot.close()
        cleanup_working_file()

    write_output_omd(source_motors, results)
    print(f"\nSaved: {OUTPUT_OMD}")
    print(f"Calibrated {len(results)} of 8 motors this run.")
    if len(results) < 8:
        print("Any motor you skipped or didn't reach kept its original")
        print("MotorDefinitionsv21.omd numbers in the new file.")
    print("\nDon't forget to restart the services:")
    print("  sudo systemctl start ohbot-server")
    print("  sudo systemctl start ohbot-conversation")


def cleanup_working_file():
    try:
        if os.path.exists(WORKING_OMD):
            os.remove(WORKING_OMD)
    except OSError:
        pass


if __name__ == "__main__":
    run()
