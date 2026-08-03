#!/usr/bin/env python3
"""
Quick single-motor jog for TopLip only.

yobot_position_test.py moves forward through all 8 motors and can't go
back once you've moved on -- this script skips that entirely. It does
NOT move anything on startup (not even TopLip), so if BottomLip is
already sitting where you left it (660), this won't disturb it. Only
TopLip moves, and only when you type a number for it.

Run it the same way as the others:
    cd /home/michael/Projects/Ohbot
    python3 yobot_jog_toplip.py

Type a number 0-1000 + Enter to move TopLip there. Blank Enter or 'q'
quits (detaches motors, nothing saved).
"""

import os
import sys
import time
from lxml import etree

import ohbot_pi as ohbot

SOURCE_OMD = "ohbotData/MotorDefinitionsv21.omd"
WORKING_OMD = "ohbotData/_yobot_jog_toplip_working.omd"
TOPLIP = 4

tree = etree.parse(SOURCE_OMD)
source_motors = []
for child in tree.getroot():
    source_motors.append({
        "Name": child.get("Name"), "Motor": child.get("Motor"),
        "Speed": child.get("Speed"), "Reverse": child.get("Reverse"),
        "Acceleration": child.get("Acceleration"),
        "RestPosition": child.get("RestPosition"),
        "Avoid": child.get("Avoid", ""),
    })

root = etree.Element("Motors")
for m in source_motors:
    etree.SubElement(root, "Motor", {**m, "Min": "0", "Max": "1000"})
etree.ElementTree(root).write(WORKING_OMD, pretty_print=True, xml_declaration=False)

ohbot.motorDefFile = WORKING_OMD
print("Connecting... (nothing will move until you type a number)")
if not ohbot.init():
    print("Could not connect. Check the USB cable / that nothing else is using it.")
    sys.exit(1)

print("Connected. TopLip only -- BottomLip is left untouched wherever it is.")
try:
    while True:
        s = input("TopLip position (0-1000), or q to quit: ").strip()
        if s == "" or s.lower() == "q":
            break
        try:
            raw = max(0, min(1000, int(s)))
        except ValueError:
            print("  Please type a whole number 0-1000, or q.")
            continue
        ohbot.move(TOPLIP, raw / 100.0, 3, avoid=False)
        print(f"  Moved TopLip to {raw}")
finally:
    ohbot.close()
    try:
        os.remove(WORKING_OMD)
    except OSError:
        pass
print("Done. Nothing saved.")
