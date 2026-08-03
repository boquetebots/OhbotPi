#!/usr/bin/env python3
"""
center_servos.py — Set motors to their exact midpoint before assembly.

WHAT IT DOES
  Each time you press Enter it commands all motors (0-7) to their true
  center (90 degrees = "500" on the Ohbot 0-1000 scale). Plug in a fresh
  servo, press Enter, it snaps to center, attach the horn, swap the next
  servo, press Enter again. Type q to quit.

HOW TO RUN (on the Pi)
  1. Stop anything else using the serial cable first:
       sudo systemctl stop ohbot-server
       sudo systemctl stop ohbot-conversation
     (and make sure gui_server.py / timeline_server.py aren't running)
  2. Run:
       python3 center_servos.py
  3. When done, restart the services if you need the bot:
       sudo systemctl start ohbot-server
       sudo systemctl start ohbot-conversation
"""

import serial
import serial.tools.list_ports
import time

# ── Settings you might want to change ───────────────────────────────
MOTORS = [0, 1, 2, 3, 4, 5, 6, 7]   # which motors to center (all of them)
CENTER = 90                # 90 degrees = servo midpoint (= 500 on 0-1000 scale)
SPEED  = 250               # full speed
# ────────────────────────────────────────────────────────────────────


def find_ohbot():
    """Look through USB serial ports until we find the Ohbot brain board.
    Returns an open serial connection, or None if not found."""
    for p in serial.tools.list_ports.comports():
        name = p.device.lower()
        if "usb" in name or "acm" in name:
            try:
                test = serial.Serial(p.device, 19200, timeout=0.5)
                test.write(b"v\n")            # ask the board for its version
                line = test.readline()
                test.close()
                if b"v1" in line or b"v2" in line:
                    print(f"Ohbot found on {p.device}")
                    return serial.Serial(p.device, 19200)
            except Exception:
                pass
    return None


def center_motors(ser):
    """Attach each motor and send it to center."""
    for m in MOTORS:
        ser.write(f"a0{m}\n".encode())                     # attach (power on)
        ser.write(f"m0{m},{CENTER},{SPEED}\n".encode())    # move to center
        time.sleep(0.05)
    print(f"Motors {MOTORS} sent to center ({CENTER} degrees).")


def detach_motors(ser):
    """Power the motors off so they don't hold/buzz."""
    for m in MOTORS:
        ser.write(f"d0{m}\n".encode())
        time.sleep(0.02)


def main():
    ser = find_ohbot()
    if ser is None:
        print("Ohbot brain board not found.")
        print("Check the USB cable, and make sure no other server is running.")
        return

    print()
    print("Servo centering tool — motors", MOTORS)
    center_motors(ser)

    while True:
        answer = input("\nPress Enter to fire again, or q + Enter to quit: ").strip().lower()
        if answer == "q":
            break
        center_motors(ser)

    detach_motors(ser)
    ser.close()
    print("Motors released. Done.")


if __name__ == "__main__":
    main()
