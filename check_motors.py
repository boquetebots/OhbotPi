"""
check_motors.py — is every motor actually able to move?

Reads a motor settings file and prints the travel each motor has been given.
A motor whose Min and Max are the same number cannot move at all: every
slider position converts to the same servo angle, so the motor is always
told to go where it already is.

That failure is very quiet. The GUI slider moves on screen, the program
reports no error in the browser, and the motor just sits there. This is what
happened to Yobot's bottom lip in August 2026 — see the notes at the bottom.

    python check_motors.py              this machine's live settings
    python check_motors.py Goldie       a saved robot, before you load it
    python check_motors.py --all        the live file and every saved robot

On the Pi and the Mac it is python3 rather than python.

No robot needed. It only reads files.
"""

import os
import sys
import glob
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
OHBOT_DATA = os.path.join(HERE, 'ohbotData')
LIVE_FILE = os.path.join(OHBOT_DATA, 'MotorDefinitionsv21.omd')
ROBOTS_DIR = os.path.join(OHBOT_DATA, 'robots')
ACTIVE_FILE = os.path.join(OHBOT_DATA, 'active_robot.txt')

# Raw servo units, on a 0-1000 scale — so these are a percentage of
# everything the servo could possibly do.
DEAD = 1       # Min and Max the same, near enough. The motor is frozen.
CRAMPED = 100  # Under a tenth of full scale. Probably a mis-click.


def active_robot():
    if os.path.exists(ACTIVE_FILE):
        with open(ACTIVE_FILE) as f:
            return f.read().strip() or '(none recorded)'
    return '(none recorded)'


def check_file(path, title):
    """Print one table. Returns a list of frozen motor names."""
    print(f"  {title}")
    print(f"  {path}")
    print()

    if not os.path.exists(path):
        print("  This file does not exist.")
        print()
        return ['(file missing)']

    try:
        root = ET.parse(path).getroot()
    except Exception as e:
        print(f"  This file cannot be read as XML: {e}")
        print()
        return ['(file unreadable)']

    frozen, cramped, no_centre = [], [], []

    print(f"  {'Motor':<12}{'Min':>6}{'Centre':>8}{'Max':>6}{'Travel':>8}   Verdict")
    print("  " + "-" * 60)

    for motor in root:
        name = motor.get('Name', '?')
        lo = int(motor.get('Min', 0))
        hi = int(motor.get('Max', 0))
        travel = hi - lo

        # No Centre attribute means the halfway point gets used instead,
        # so that is what we show, marked with a star.
        centre_attr = motor.get('Center')
        if centre_attr is None:
            centre = f"{(lo + hi) // 2}*"
            no_centre.append(name)
        else:
            centre = str(int(centre_attr))

        if travel <= DEAD:
            verdict = "FROZEN - cannot move"
            frozen.append(name)
        elif travel < CRAMPED:
            verdict = "very little travel"
            cramped.append(name)
        else:
            verdict = "ok"

        print(f"  {name:<12}{lo:>6}{centre:>8}{hi:>6}{travel:>8}   {verdict}")

    print()

    if frozen:
        print("  PROBLEM — these motors cannot move at all:")
        for name in frozen:
            print(f"      {name}")
        print("  Their Min and Max are the same number. Re-calibrate each one,")
        print("  and make sure the centre you mark sits BETWEEN the two ends.")
        print()
    if cramped:
        print("  WORTH A LOOK — unusually little travel:")
        for name in cramped:
            print(f"      {name}")
        print()

    # The lips are the ones where a missing centre genuinely matters, because
    # for them centre means "lips just touching", not "halfway".
    lip_no_centre = [n for n in no_centre if 'Lip' in n]
    if lip_no_centre:
        print("  NOTE — no centre recorded for: " + ", ".join(lip_no_centre))
        print("  For a lip, centre is the mouth-closed position where the two")
        print("  lips just touch, and lip sync only ever uses centre upwards.")
        print("  Falling back to halfway wastes most of the mouth's movement.")
        print()

    return frozen


def main():
    args = [a for a in sys.argv[1:]]

    print()
    if not args:
        targets = [(LIVE_FILE, f"LIVE SETTINGS — the robot plugged in here "
                               f"(last loaded: {active_robot()})")]
    elif args[0] in ('--all', '-a'):
        targets = [(LIVE_FILE, f"LIVE SETTINGS (last loaded: {active_robot()})")]
        for path in sorted(glob.glob(os.path.join(ROBOTS_DIR, '*.omd'))):
            name = os.path.splitext(os.path.basename(path))[0]
            targets.append((path, f"SAVED ROBOT — {name}"))
    else:
        name = args[0]
        targets = [(os.path.join(ROBOTS_DIR, f"{name}.omd"),
                    f"SAVED ROBOT — {name}")]

    all_frozen = {}
    for path, title in targets:
        print("=" * 70)
        frozen = check_file(path, title)
        if frozen:
            all_frozen[title] = frozen

    print("=" * 70)
    print()
    print("  * next to a centre means the file has none of its own, so the")
    print("    halfway point is being used instead.")
    print()

    if all_frozen:
        print("  Something needs re-calibrating. Listed above.")
        print()
        return 1

    print("  No problems. Every motor checked has room to move.")
    print()
    return 0


# ── Why this file exists ───────────────────────────────────────────────────
# August 2026: Yobot's mouth only half worked. The top lip moved during lip
# sync, the bottom lip did not. The bottom lip DID move on the calibration
# page, which made it look like a bug in the lip-crossing avoidance code.
#
# It was neither. The calibration page sends servo angles straight down the
# cable and never reads the settings file, which is why it worked there.
# Everything else goes through yobot_core.py, which does read it — and the
# file said:
#
#     <Motor Name="BottomLip" Min="470" Max="470" ... />
#
# Zero travel. Frozen.
#
# It was saved that way because the centre marked for the bottom lip landed
# outside the Min and Max marked for it. calibration_server.py has a fallback
# for that case which pulls Min and Max inward until the centre sits halfway
# between them — and when the centre is outside the range, that pulls them
# all the way in to nothing. It saved the result without complaint.
#
# yobot_core.py does print a warning about a zero-travel motor when it loads
# the file. But that goes to the terminal the server is running in, and if
# you are looking at a web page in a browser you will never see it. Hence
# this file: something you can run on purpose and read.
#
# It happened twice in one afternoon — the bottom lip first, then EyeTurn on
# the very next calibration pass. Run this after every calibration.

if __name__ == '__main__':
    sys.exit(main())
