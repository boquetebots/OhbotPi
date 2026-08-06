#!/usr/bin/env python3
"""
Ohbot/Yobot Motor Calibration Server
Runs on port 5003. A standalone tool for finding each motor's min, max,
and center travel positions and writing a fresh MotorDefinitionsv21.omd.
Works on the Raspberry Pi and on macOS (uses the shared yobot_core library).

WHY THIS IS ITS OWN PROGRAM, NOT PART OF gui_server.py:
Calibration needs to send RAW absolute servo positions straight to the
board, bypassing the normal Min/Max/Reverse math in ohbot_pi.py (since
the whole point is to go find out what those numbers should be). Keeping
that separate from the main GUI avoids any chance of the two control
paths getting tangled together.

IMPORTANT: This uses the same USB serial cable as the Greeter Bot and the
Sequence Builder GUI. Only one of the three can run at a time. Stop
whichever one is currently running before starting this
(the Launcher page's "Stop Current Service" button does this).

Usage:
    python3 calibration_server.py

Then open in your browser:
    http://localhost:5003/calibration        (on the computer running it)
    http://<pi-ip-address>:5003/calibration  (from another device)
"""

from flask import Flask, request, jsonify, send_from_directory
import os
import shutil
import subprocess
import threading
import time
from lxml import etree

# Import the Ohbot hardware library — we reuse its serial connection and
# low-level attach/write helpers, but NOT its move()/_move() functions
# (those apply Min/Max/Reverse, which is exactly what we're trying to find).
import ohbot_pi as ohbot

# Saving/loading calibrations under a robot's name (ohbotData/robots/).
import robot_profiles

app = Flask(__name__)

# ── English / Spanish ──────────────────────────────────────────────────────
# Adds two routes: /i18n.js (hands the web pages their wording) and /lang
# (remembers which language was picked). See ohbot_lang.py.
from ohbot_lang import register_language_routes
register_language_routes(app)

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
CALIB_DIR     = os.path.join(BASE_DIR, 'calibration')
OHBOT_DATA    = os.path.join(BASE_DIR, 'ohbotData')
MOTOR_DEF_FILE = os.path.join(OHBOT_DATA, 'MotorDefinitionsv21.omd')

# Port 5003 — kept separate from the conversation brain server (5002) so the
# two can never collide. Ports in use: 5000 launcher, 5001 GUI/Timeline,
# 5002 chat brain, 5003 calibration.
CALIBRATION_PORT = 5003

SERIAL_LOCK = threading.Lock()

# ── Motor info (same 8 motors, same order, as gui_server.py) ───────────────
MOTORS = {
    0: {'key': 'HEADNOD',   'label': 'Head Nod'},
    1: {'key': 'HEADTURN',  'label': 'Head Turn'},
    2: {'key': 'EYETURN',   'label': 'Eye Turn'},
    3: {'key': 'LIDBLINK',  'label': 'Lid / Blink'},
    4: {'key': 'TOPLIP',    'label': 'Top Lip'},
    5: {'key': 'BOTTOMLIP', 'label': 'Bottom Lip'},
    6: {'key': 'EYETILT',   'label': 'Eye Tilt'},
    7: {'key': 'HEADROLL',  'label': 'Head Roll'},
}
TOPLIP    = 4
BOTTOMLIP = 5
LIP_MOTORS = (TOPLIP, BOTTOMLIP)

# ── How each motor gets saved ──────────────────────────────────────────────
# There are three different treatments, because the eight motors genuinely
# want different things. A motor listed in neither tuple below gets the old
# original behaviour.
#
# 1. THREE_POINT_MOTORS — "keep full travel AND use a measured centre"
#    The head and eye motors, where "centre" has an obvious physical meaning
#    (head straight ahead, eyes looking straight). Min, Center and Max are
#    all saved exactly as measured. Slider 5 lands on the real neutral and
#    no travel is discarded.
#
# 2. FULL_RANGE_MOTORS — "keep full travel, but NO centre"
#    Lid/Blink. Every blink in the codebase is move(LIDBLINK, 0) or
#    move(LIDBLINK, 10) — nothing ever uses a position in between, so a
#    measured centre would change precisely nothing about blinking. What
#    the lid DOES want is its full range, so the eye can properly close and
#    properly open instead of being trimmed. So: save the found Min and Max
#    untouched, and write no Center. With no Center, yobot_core falls back
#    to the midpoint, which keeps the mapping a single straight line exactly
#    as it has always been — just a longer one. No kink, nothing to re-tune.
#
# 3. Anything in neither tuple — the original behaviour: Min/Max trimmed so
#    centre sits exactly halfway, no Center written. Nothing uses this now,
#    but it is kept as the fallback for any motor added in future before
#    someone has decided which of the two modes above it belongs in.
#
# On the lips specifically (added to THREE_POINT_MOTORS 2026-08-05):
# their "centre" is the mouth-closed position where the two lips just touch,
# NOT a halfway point. This matters because lip sync only ever uses slider
# 5-10 — see VisemeMapper in ohbot_azure.py, where NEUTRAL is 5 (meaning
# closed) and every viseme sits between 5 and 8. With centre at the midpoint
# the old way, roughly half of each lip's opening travel sat in the 0-5
# range that lip sync never touches. Putting centre at "just touching" hands
# almost all of that travel to the 5-10 range lip sync actually uses.
THREE_POINT_MOTORS = (
    0,   # HeadNod
    1,   # HeadTurn
    2,   # EyeTurn
    4,   # TopLip     — centre = lips just touching (mouth closed)
    5,   # BottomLip  — centre = lips just touching (mouth closed)
    6,   # EyeTilt
    7,   # HeadRoll
)

FULL_RANGE_MOTORS = (
    3,   # LidBlink
)

# Display order on the calibration page — mechanical calibration order,
# not motor index order (chosen by Michael: head tilt/nod/turn, then lid,
# then eyes, then lips last since lips need the coordinated
# neutral/near-touching step at the end).
# NOTE: this has to be sent to the browser as an explicit list, not just
# relied on as Python dict order — JavaScript objects silently re-sort
# any integer-like keys ("0", "1", ...) into ascending numeric order
# regardless of the order they arrived in, so MOTORS' own key order
# can't be trusted to survive the trip through JSON.
MOTOR_ORDER = [7, 0, 1, 3, 6, 2, 4, 5]   # HeadRoll(tilt), HeadNod, HeadTurn, LidBlink, EyeTilt, EyeTurn, TopLip, BottomLip

# ── Raw position scale ──────────────────────────────────────────────────────
# Calibration slider: 1-100 on screen -> raw position 10-1000 sent to the
# board (multiply by 10). Raw 0-1000 maps linearly onto the servo's 0-180
# degree range (same ratio ohbot_pi.py already uses when it loads the old
# Min/Max out of the .omd file: raw / 1000 * 180 = degrees).
RAW_MAX   = 1000
DEG_MAX   = 180
CALIB_SPEED = 2   # fixed slow speed (0-10 scale) for every calibration move,
                   # so we never slam a motor into a hard stop while hunting
                   # for its limits.

# In-memory calibration results for the current session.
# Each motor: found_a / found_b are the two raw values clicked via the
# Min OK / Max OK buttons (order doesn't matter — we sort them at save
# time), center is the raw value clicked via Center OK (or, for the lips,
# via the Neutral/Near-Touching OK buttons), reverse is the checkbox state.
calib_state = {
    m: {'found_a': None, 'found_b': None, 'center': None, 'reverse': False}
    for m in MOTORS
}

# Last PHYSICAL raw position we actually sent to each motor (after any
# Reverse flip) — this is what gets recorded when a "___ OK" button is
# clicked, and what the on-screen readout shows.
last_raw = {m: 500 for m in MOTORS}

# Last LOGICAL raw value each motor was asked to go to — i.e. what the
# slider (or the default-pose button) requested, before any Reverse flip.
# Kept so that ticking the Reversed? checkbox can immediately re-issue
# the same logical position under the new flip, instead of doing nothing
# until the next slider drag.
last_logical = {m: 500 for m in MOTORS}


# ── Preload Reverse + other non-calibrated attributes from the old file ───
# (so the Reversed? checkboxes start out matching the current live robot,
# and so Save can carry over Speed/Acceleration/RestPosition/Avoid/Name
# unchanged.)
def _load_old_reverse_defaults():
    if not os.path.exists(MOTOR_DEF_FILE):
        return
    try:
        tree = etree.parse(MOTOR_DEF_FILE)
        for child in tree.getroot():
            idx = int(child.get('Motor'))
            if idx in calib_state:
                calib_state[idx]['reverse'] = (child.get('Reverse') == 'True')
    except Exception as e:
        print(f"⚠️  Could not read old motor file for Reverse defaults: {e}")


# ── Raw serial move, bypassing ohbot_pi.py's Min/Max/Reverse logic ────────
def _apply_reverse(motor_id, raw_val):
    """
    Flip a 0-1000 raw value end-for-end if this motor's Reversed? box is
    ticked. Self-inverse (flipping twice returns the original value), so
    this same function converts logical->physical and physical->logical.
    """
    if calib_state[motor_id]['reverse']:
        return RAW_MAX - raw_val
    return raw_val


def raw_move(motor_id, raw_pos, speed=CALIB_SPEED):
    """
    raw_pos is the LOGICAL 0-1000 position — what the slider shows, or
    what the default-pose button asks for. If Reversed? is ticked for
    this motor, we flip it end-for-end before sending it to the servo,
    so a physically backwards-mounted motor still moves the direction
    the slider suggests. last_raw always stores the PHYSICAL position
    actually sent — that's what Min OK / Max OK / Center OK record, and
    what ends up (after trimming) as Min/Max in the saved file.
    """
    raw_pos = max(0, min(RAW_MAX, int(raw_pos)))
    physical_raw = _apply_reverse(motor_id, raw_pos)

    deg = int(physical_raw / RAW_MAX * DEG_MAX)
    wire_speed = int((250 / 10) * speed)

    with SERIAL_LOCK:
        if not ohbot.isAttached[motor_id]:
            ohbot._attach(motor_id)
        ohbot._serwrite(f"m0{motor_id},{deg},{wire_speed}\n")

    last_logical[motor_id] = raw_pos
    last_raw[motor_id] = physical_raw
    return physical_raw


def _next_backup_name():
    n = 1
    while os.path.exists(os.path.join(OHBOT_DATA, f'MD_old_{n}.omd')):
        n += 1
    return f'MD_old_{n}.omd'


# ============================================================================
# ROUTES
# ============================================================================

@app.route('/calibration')
@app.route('/calibration/')
def serve_page():
    return send_from_directory(CALIB_DIR, 'index.html')


@app.route('/calibration/status')
def status():
    return jsonify({
        'success': True,
        'ohbot_connected': ohbot.connected,
        'motors': MOTORS,
        'order': MOTOR_ORDER,
        'state': calib_state,
        'last_raw': last_raw,
    })


@app.route('/calibration/move', methods=['POST'])
def move():
    try:
        data = request.get_json()
        motor_id = int(data['motor'])
        raw_pos  = int(data['raw'])
        if motor_id not in MOTORS:
            return jsonify({'success': False, 'error': 'Unknown motor'}), 400
        physical = raw_move(motor_id, raw_pos)
        return jsonify({'success': True, 'raw': physical})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/calibration/pose_default', methods=['POST'])
def pose_default():
    """All motors except lips -> logical 500. Bottom lip -> 900. Top lip -> 800.
    Always at the fixed slow calibration speed. These are LOGICAL targets,
    so a motor with Reversed? ticked still ends up physically in the
    equivalent mirrored spot rather than fighting the checkbox."""
    try:
        targets = {}
        for m in MOTORS:
            if m == TOPLIP:
                targets[m] = 800
            elif m == BOTTOMLIP:
                targets[m] = 900
            else:
                targets[m] = 500
        for m, logical in targets.items():
            raw_move(m, logical)
        return jsonify({'success': True, 'targets': targets, 'last_raw': last_raw})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/calibration/mark', methods=['POST'])
def mark():
    """
    Record the motor's current (last-commanded) raw position as one of:
      'min'    -> stored in found_a/found_b slot (sorted out at save time)
      'max'    -> stored in found_a/found_b slot (sorted out at save time)
      'center' -> the Center OK button for normal motors, or the
                  Neutral OK / Near-Touching OK button for the lips
    Body: { "motor": 4, "kind": "center" }
    """
    try:
        data = request.get_json()
        motor_id = int(data['motor'])
        kind = data['kind']
        if motor_id not in MOTORS:
            return jsonify({'success': False, 'error': 'Unknown motor'}), 400

        raw = last_raw[motor_id]
        state = calib_state[motor_id]

        if kind == 'center':
            state['center'] = raw
        elif kind in ('min', 'max'):
            if state['found_a'] is None:
                state['found_a'] = raw
            else:
                state['found_b'] = raw
        else:
            return jsonify({'success': False, 'error': 'Unknown kind'}), 400

        return jsonify({'success': True, 'state': state})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/calibration/clear', methods=['POST'])
def clear_motor():
    """Clear a single motor's recorded min/max/center so it can be redone."""
    try:
        data = request.get_json()
        motor_id = int(data['motor'])
        if motor_id not in MOTORS:
            return jsonify({'success': False, 'error': 'Unknown motor'}), 400
        calib_state[motor_id]['found_a'] = None
        calib_state[motor_id]['found_b'] = None
        calib_state[motor_id]['center']  = None
        return jsonify({'success': True, 'state': calib_state[motor_id]})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/calibration/reverse', methods=['POST'])
def set_reverse():
    """
    Flip this motor's Reversed? checkbox, then immediately re-send its
    last requested (logical) position under the new setting — so ticking
    the box visibly swings the motor to the mirrored spot right away,
    rather than only changing what gets written to the file at Save time.
    """
    try:
        data = request.get_json()
        motor_id = int(data['motor'])
        reversed_ = bool(data['reverse'])
        if motor_id not in MOTORS:
            return jsonify({'success': False, 'error': 'Unknown motor'}), 400
        calib_state[motor_id]['reverse'] = reversed_
        physical = raw_move(motor_id, last_logical[motor_id])
        return jsonify({'success': True, 'raw': physical})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/calibration/save', methods=['POST'])
def save():
    """
    Write a new MotorDefinitionsv21.omd from the calibration results.
    - Backs up the current file to ohbotData/MD_old_N.omd first.
    - If the page sent a robot_name, ALSO files a copy of the finished
      calibration under that name in ohbotData/robots/ so it can be loaded
      back later from the launcher page. The live file is still written
      either way — the named copy is an archive, not a replacement.
    - Only overwrites Min, Center, Max and Reverse on each <Motor> element —
      Name, Motor (index), Speed, Acceleration, RestPosition and Avoid are
      all carried over from the existing file untouched.
    - For the THREE_POINT_MOTORS (head and eyes): saves the measured Min,
      Center and Max as three independent numbers. Nothing is trimmed, so
      the motor keeps all the travel it actually has, and slider position 5
      lands on the real measured neutral.
    - For the FULL_RANGE_MOTORS (Lid/Blink): saves the measured Min and Max
      untrimmed but writes no Center, so the lid gets its full travel while
      the mapping stays the straight line it has always been.
    - Any motor in neither tuple falls back to the old behaviour: min/max
      trimmed so centre sits exactly halfway between them, and no Center
      written. See the notes above the two tuples for why each motor is
      where it is.
    """
    try:
        # Optional: the name the page asked for. Cleaned and checked BEFORE
        # anything is written, so a bad name can't leave the live file
        # rewritten but the named copy missing.
        payload = request.get_json(silent=True) or {}
        raw_robot_name = payload.get('robot_name')
        robot_name = None
        if raw_robot_name is not None and str(raw_robot_name).strip():
            robot_name = robot_profiles.clean_name(raw_robot_name)
            if not robot_name:
                return jsonify({
                    'success': False,
                    'error': 'That robot name has no usable characters in it. '
                             'Use letters, numbers, spaces, dashes or '
                             'underscores. Nothing was saved.'
                }), 400

        if not os.path.exists(MOTOR_DEF_FILE):
            return jsonify({
                'success': False,
                'error': f'{MOTOR_DEF_FILE} does not exist — nothing to '
                         f'base the new file on. Cannot safely guess Name/'
                         f'Speed/Acceleration/Avoid for each motor.'
            }), 400

        # ── Partial saves ─────────────────────────────────────────────────
        # A motor is only rewritten if it has ALL THREE values (Min, Center,
        # Max) recorded in this session. Any motor you didn't touch is left
        # completely alone in the file — its Min/Center/Max/Reverse stay
        # exactly as they were. That's what lets you re-calibrate one or two
        # servos without having to redo all eight.
        #
        # A motor with only one or two of the three recorded is treated as
        # half-finished: it is NOT saved, and it's reported back so you know
        # it didn't take. Saving a motor with a missing Min or Max would
        # produce a nonsense range.
        ready = []
        half_done = []
        untouched = []
        for m in MOTORS:
            st = calib_state[m]
            got = sum(1 for k in ('center', 'found_a', 'found_b')
                      if st[k] is not None)
            if got == 3:
                ready.append(m)
            elif got == 0:
                untouched.append(m)
            else:
                half_done.append(m)

        if not ready:
            return jsonify({
                'success': False,
                'error': 'No motor has all three of Min, Center and Max '
                         'recorded yet, so there is nothing to save. Use the '
                         'Min OK / Center OK / Max OK buttons on at least one '
                         'motor first.'
            }), 400

        tree = etree.parse(MOTOR_DEF_FILE)
        root = tree.getroot()

        motors_in_file = {int(child.get('Motor')) for child in root}
        if motors_in_file != set(MOTORS.keys()):
            return jsonify({
                'success': False,
                'error': 'The existing motor file does not have the same 8 '
                         'motors this page expects — stopping without '
                         'changing anything.'
            }), 400

        # Back up the current file BEFORE modifying it.
        backup_name = _next_backup_name()
        shutil.copy2(MOTOR_DEF_FILE, os.path.join(OHBOT_DATA, backup_name))

        three_point_saved = []
        full_range_saved = []
        trimmed_saved = []

        for child in root:
            idx = int(child.get('Motor'))
            st = calib_state[idx]
            label = MOTORS[idx]['label']

            # Skip anything not fully measured this session — leave that
            # motor's existing settings in the file completely untouched.
            if idx not in ready:
                continue

            found_min = min(st['found_a'], st['found_b'])
            found_max = max(st['found_a'], st['found_b'])
            center    = st['center']

            if idx in THREE_POINT_MOTORS and found_min <= center <= found_max:
                # Three-point: keep all three measurements exactly as found.
                # No trimming, so no travel is thrown away.
                new_min    = int(round(found_min))
                new_max    = int(round(found_max))
                new_center = int(round(center))
                three_point_saved.append(label)
            elif idx in FULL_RANGE_MOTORS:
                # Full range, no centre: keep the measured Min and Max, but
                # write no Center so the mapping stays the single straight
                # line it has always been. The Center OK value you recorded
                # is used only as a sanity check (below) — it is deliberately
                # not saved, because for Lid/Blink it would have no effect
                # and would only be misleading in the file.
                new_min    = int(round(found_min))
                new_max    = int(round(found_max))
                new_center = None
                full_range_saved.append(label)
            else:
                # Old two-point behaviour: pull min/max in until centre sits
                # exactly halfway. Used for the lips and Lid/Blink, and as a
                # safe fallback for any motor whose recorded centre somehow
                # landed outside its own found range.
                below = center - found_min
                above = found_max - center
                half  = min(below, above)
                if half < 0:
                    half = 0  # center was outside the found range — clamp to 0 width rather than invert

                new_min    = int(round(center - half))
                new_max    = int(round(center + half))
                new_center = None
                trimmed_saved.append(label)

            child.set('Min', str(new_min))
            child.set('Max', str(new_max))
            child.set('Reverse', 'True' if st['reverse'] else 'False')

            # A Center attribute is written ONLY for three-point motors.
            # Leaving it off for the trimmed motors is deliberate: yobot_core
            # then falls back to the exact halfway point it has always used,
            # so those motors are guaranteed byte-for-byte unchanged rather
            # than "changed by a rounding hair". Presence of Center is also a
            # clear signal of which motors have been three-point calibrated.
            if new_center is not None:
                child.set('Center', str(new_center))
            elif child.get('Center') is not None:
                del child.attrib['Center']

        tree.write(MOTOR_DEF_FILE, pretty_print=True, xml_declaration=False)

        # ── File a named copy for this robot ──────────────────────────────
        # Done AFTER the live file is written, so the copy captures the
        # finished calibration. If this step fails the live file is still
        # correct and the robot works — we just report that the named copy
        # didn't happen, rather than pretending the whole save failed.
        saved_as = None
        robot_error = None
        if robot_name:
            ok, result = robot_profiles.save_profile(robot_name)
            if ok:
                saved_as = result
            else:
                robot_error = result

        return jsonify({
            'success': True,
            'backup': backup_name,
            'three_point': three_point_saved,
            'full_range': full_range_saved,
            'trimmed': trimmed_saved,
            'untouched': [MOTORS[m]['label'] for m in untouched],
            'half_done': [MOTORS[m]['label'] for m in half_done],
            'saved_as': saved_as,
            'robot_error': robot_error,
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/calibration/robots')
def robots():
    """The list of saved robots and which one is currently loaded. The page
    uses this to pre-fill the name box and to warn before overwriting."""
    try:
        return jsonify({'success': True, **robot_profiles.summary()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/calibration/stop_service', methods=['POST'])
def stop_service():
    """
    Shut down this calibration server — what "Stop & Exit" on the page calls.

    On the Pi it's normally run as the ohbot-calibration systemd service, so
    ask systemd to stop it (otherwise systemd would just restart it). Anywhere
    else — Mac, Windows, or run by hand on the Pi — simply exit this process.

    Runs after a short delay on a background thread so the success response
    makes it back to the browser before the process gets torn down.
    """
    def do_stop():
        time.sleep(1)

        if ohbot.IS_LINUX:
            try:
                result = subprocess.run(
                    ['systemctl', '--user', 'is-active', 'ohbot-calibration'],
                    capture_output=True, text=True, timeout=5)
                if result.stdout.strip() == 'active':
                    subprocess.run(['systemctl', '--user', 'stop',
                                    'ohbot-calibration'], timeout=10)
                    return
            except Exception:
                pass   # systemd not managing us — fall through to plain exit

        # Not under systemd: release the robot and exit this process
        try:
            ohbot.reset()
            ohbot.close()
        except Exception:
            pass
        os._exit(0)

    threading.Thread(target=do_stop, daemon=True).start()
    return jsonify({'success': True})


# ============================================================================
# STARTUP
# ============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("🔧  Ohbot Motor Calibration Server")
    print("=" * 60)
    print()
    print("⚠️  IMPORTANT: Make sure the Greeter Bot and Sequence Builder")
    print("   GUI are both stopped first — all three share the same USB")
    print("   serial cable and cannot run at the same time.")
    print()

    os.makedirs(OHBOT_DATA, exist_ok=True)
    _load_old_reverse_defaults()

    print("🔌 Connecting to Ohbot hardware...")
    if ohbot.init():
        print(f"✅ Ohbot connected on {ohbot.port}")
    else:
        print("⚠️  Ohbot hardware not found.")
        print("   The page will still open but sliders won't move the robot.")

    print()
    print("🌐 Open in your browser:")
    print(f"   http://localhost:{CALIBRATION_PORT}/calibration   (on this computer)")

    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        print(f"   http://{ip}:{CALIBRATION_PORT}/calibration    (from another device)")
    except Exception:
        pass

    print()
    print("Press Ctrl-C to stop.")
    print("=" * 60)
    print()

    app.run(host='0.0.0.0', port=CALIBRATION_PORT, debug=False)
