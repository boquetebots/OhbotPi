#!/usr/bin/env python3
"""
*** DEPRECATED 2026-07-13 — NO LONGER USED ***
This file's routes were merged into gui_server.py so the Sequence Builder
and Timeline run as ONE program on port 5001 instead of two separate
programs fighting over the robot's USB cable. See
HANDOFF_timeline_merge_plan.md for why, and gui_server.py's "TIMELINE
PLAYBACK" section for where this logic now lives.

Do not run this file — start gui_server.py instead, then open both
http://<pi-ip>:5001/gui and http://<pi-ip>:5001/timeline.

Kept here only as a reference copy of how the Timeline worked before the
merge. Safe to delete once the merged gui_server.py has been confirmed
working on the real robot.
---

Ohbot Timeline Server — Phase 2b (adds live keyframe capture)
Runs on port 5003 (separate from the conversation bot on 5000, the
sequence-builder GUI on 5001, and the chat server on 5002).

What this does:
    Loads sequences already saved by the sequence-builder GUI (same
    `sequences/` folder gui_server.py uses), serves a page that draws
    them as a horizontal timeline of clips, connects directly to the
    Ohbot hardware so you can press spacebar and watch the robot
    actually run a sequence from wherever the playhead is sitting on
    the timeline (Phase 2a) — and now (Phase 2b) lets you pose the
    robot with sliders and capture that pose as a new keyframe that
    lands right at the playhead, then save the result back to the same
    `sequences/` folder the Sequence Builder GUI reads from.
    See /Users/michael/Projects/OhbotPi2/HANDOFF_gui_timeline.md for the
    full design plan and the phase breakdown.

IMPORTANT — serial cable rule: this server now owns the Ohbot's serial
connection directly, the same way gui_server.py does. Only ONE of these
three programs can be running at a time:
    - the conversation bot (ohbot_server.py / ohbot_conversation.py)
    - gui_server.py (the sequence builder)
    - this file (timeline_server.py)
Stop whichever one is running before starting this.

Playback here does NOT include speech yet — only motor moves and the
LED color from each keyframe. If a keyframe has a speech line, it's
skipped during timeline playback for now (Phase 1's read-only view
still shows a 🗣 badge on any clip that has speech, so you can see
which ones have it). Speech can be added to playback later if wanted.

Usage:
    python3 timeline_server.py

Then open in your browser:
    http://<pi-ip-address>:5003/timeline
"""

from flask import Flask, request, jsonify, send_from_directory
import json
import os
import threading
import time

# Import Ohbot hardware library — same module gui_server.py uses.
import ohbot_pi as ohbot

app = Flask(__name__)

# ── Paths ──────────────────────────────────────────────────────────────────
# Same folder gui_server.py already uses — the timeline reads sequences
# that were saved from the existing sequence-builder GUI. Nothing new to
# set up; if you can already see saved sequences in the GUI, this will see
# them too.
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
SEQUENCES_DIR = os.path.join(BASE_DIR, 'sequences')
GUI_DIR       = os.path.join(BASE_DIR, 'gui')

os.makedirs(SEQUENCES_DIR, exist_ok=True)

# ── Motor info ─────────────────────────────────────────────────────────────
# Copied from gui_server.py on purpose (see HANDOFF doc — this server
# doesn't import from gui_server.py, so this small bit of setup code is
# duplicated rather than shared).
MOTORS = {
    0: {'key': 'HEADNOD',   'label': 'Head Nod',    'default': 5},
    1: {'key': 'HEADTURN',  'label': 'Head Turn',   'default': 5},
    2: {'key': 'EYETURN',   'label': 'Eye Turn',    'default': 5},
    3: {'key': 'LIDBLINK',  'label': 'Lid / Blink', 'default': 10},
    4: {'key': 'TOPLIP',    'label': 'Top Lip',     'default': 5},
    5: {'key': 'BOTTOMLIP', 'label': 'Bottom Lip',  'default': 5},
    6: {'key': 'EYETILT',   'label': 'Eye Tilt',    'default': 5},
    7: {'key': 'HEADROLL',  'label': 'Head Roll',   'default': 5},
}
KEY_TO_ID = {v['key']: k for k, v in MOTORS.items()}

# Same speed lookup table as gui_server.py — converts the 1-10 dial value
# saved in a keyframe into the real speed sent to ohbot.move().
SPEED_CURVE = {
    1: 0.4, 2: 0.8, 3: 1.4, 4: 2.3, 5: 2.5,
    6: 3.0, 7: 4.0, 8: 5.4, 9: 6.5, 10: 8.0,
}

def curve_speed(dial_value):
    d = int(round(float(dial_value)))
    d = max(1, min(10, d))
    return SPEED_CURVE[d]

# ── Playback state ─────────────────────────────────────────────────────────
OHBOT_SERIAL_LOCK = threading.Lock()
play_state = {'playing': False, 'stop_requested': False}


@app.route('/timeline')
@app.route('/timeline/')
def timeline_page():
    """Serve the timeline page itself."""
    return send_from_directory(GUI_DIR, 'timeline.html')


@app.route('/timeline/api/sequences')
def list_sequences():
    """Return the list of saved sequences (name/description/count only —
    not the full keyframe data, so the left-side picker loads fast)."""
    try:
        sequences = []
        for filename in sorted(os.listdir(SEQUENCES_DIR)):
            if not filename.endswith('.json'):
                continue
            filepath = os.path.join(SEQUENCES_DIR, filename)
            try:
                with open(filepath) as f:
                    seq = json.load(f)
                sequences.append({
                    'filename':       filename,
                    'name':           seq.get('name', filename),
                    'description':    seq.get('description', ''),
                    'created':        seq.get('created', ''),
                    'keyframe_count': len(seq.get('keyframes', [])),
                })
            except Exception:
                pass  # Skip anything malformed rather than failing the whole list

        return jsonify({'success': True, 'sequences': sequences})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def _safe_filename(name):
    """Turn a sequence name into a safe filename — same rule gui_server.py
    uses, so names line up the same way in both tools."""
    safe = "".join(c for c in name if c.isalnum() or c in ('_', '-', ' ')).strip()
    return safe.replace(' ', '_')


@app.route('/timeline/api/sequence/save', methods=['POST'])
def save_sequence():
    """
    Save the sequence currently being built on the timeline — same file
    format and same `sequences/` folder gui_server.py's Save button uses,
    so anything saved here shows up in the Sequence Builder GUI too (and
    vice versa).
    Body: { "name": "greeting_wave", "description": "...", "keyframes": [...] }
    """
    try:
        data = request.get_json()
        name = data.get('name', '').strip()

        if not name:
            return jsonify({'success': False, 'error': 'Sequence name is required'}), 400

        sequence = {
            'name':        name,
            'description': data.get('description', ''),
            'created':     time.strftime('%Y-%m-%d %H:%M'),
            'keyframes':   data.get('keyframes', []),
        }

        filename = _safe_filename(name) + '.json'
        filepath = os.path.join(SEQUENCES_DIR, filename)

        with open(filepath, 'w') as f:
            json.dump(sequence, f, indent=2)

        print(f"💾 Timeline saved: {filename} ({len(sequence['keyframes'])} keyframes)")
        return jsonify({'success': True, 'filename': filename})

    except Exception as e:
        print(f"❌ Timeline save error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/timeline/api/sequence/<filename>')
def load_sequence(filename):
    """Load one saved sequence's full keyframe data by filename."""
    try:
        if not filename.endswith('.json'):
            filename += '.json'

        filepath = os.path.join(SEQUENCES_DIR, filename)
        if not os.path.exists(filepath):
            return jsonify({'success': False, 'error': 'Sequence not found'}), 404

        with open(filepath) as f:
            sequence = json.load(f)

        return jsonify({'success': True, 'sequence': sequence})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/timeline/api/status')
def status():
    """Connection + playback status, polled by the page to update the
    connection dot and the PLAYING badge."""
    return jsonify({
        'success':         True,
        'ohbot_connected': ohbot.connected,
        'playing':         play_state['playing'],
    })


# ── Live capture — hardware posing (Phase 2b) ──────────────────────────────
# These four routes are copied from gui_server.py on purpose, same as the
# MOTORS/KEY_TO_ID/SPEED_CURVE setup above — this server doesn't import from
# gui_server.py, it owns the Ohbot connection directly. They let the new
# "Pose & Capture" panel move real motors/LEDs while you're posing a
# keyframe, the same way the Sequence Builder's sliders do.

@app.route('/timeline/api/motors/info')
def motors_info():
    """Motor names/defaults so the page can build its slider panel."""
    return jsonify({'success': True, 'motors': MOTORS})


@app.route('/timeline/api/motor', methods=['POST'])
def move_motor():
    """
    Move a single motor (used while dragging a slider to pose the robot).
    Body: { "motor": 1, "position": 7, "speed": 5 }
    """
    try:
        data     = request.get_json()
        motor_id = int(data['motor'])
        position = float(data['position'])
        speed    = curve_speed(data.get('speed', 5))

        with OHBOT_SERIAL_LOCK:
            ohbot.move(motor_id, position, speed)
        return jsonify({'success': True})

    except Exception as e:
        print(f"❌ Timeline motor move error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/timeline/api/led', methods=['POST'])
def set_led():
    """
    Set LED eye colour while posing.
    Body: { "r": 0, "g": 5, "b": 10 }   (each 0–10)
    """
    try:
        data = request.get_json()
        r = float(data.get('r', 0))
        g = float(data.get('g', 0))
        b = float(data.get('b', 0))

        with OHBOT_SERIAL_LOCK:
            ohbot.baseColour(r, g, b)
        return jsonify({'success': True})

    except Exception as e:
        print(f"❌ Timeline LED error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/timeline/api/reset', methods=['POST'])
def reset_robot():
    """Reset all motors to neutral and turn off LEDs — handy before posing
    a fresh keyframe from a known starting point."""
    try:
        with OHBOT_SERIAL_LOCK:
            ohbot.reset()
        return jsonify({'success': True})
    except Exception as e:
        print(f"❌ Timeline reset error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/timeline/api/play', methods=['POST'])
def play():
    """
    Play a run of keyframes on the robot, starting wherever the timeline's
    playhead was when spacebar was pressed.

    Body: { "keyframes": [ {...}, {...}, ... ] }

    The page sends just the slice of keyframes starting at the playhead —
    this always plays them in the order given, same as gui_server.py's own
    sequence playback. Motors + LED only; speech is not played back yet
    (see the note at the top of this file).
    """
    try:
        data      = request.get_json()
        keyframes = data.get('keyframes', [])

        if not keyframes:
            return jsonify({'success': False, 'error': 'No keyframes to play'}), 400

        if play_state['playing']:
            return jsonify({'success': False, 'error': 'Already playing'}), 409

        def _sleep_interruptible(seconds):
            end = time.time() + seconds
            while time.time() < end:
                if play_state['stop_requested']:
                    return
                time.sleep(min(0.05, end - time.time()))

        def run_playback():
            play_state['playing']        = True
            play_state['stop_requested'] = False
            try:
                for i, frame in enumerate(keyframes):
                    if play_state['stop_requested']:
                        break

                    frame_speed = curve_speed(frame.get('speed', 5))
                    motors      = frame.get('motors', {})
                    for key, position in motors.items():
                        motor_id = KEY_TO_ID.get(key)
                        if motor_id is not None:
                            with OHBOT_SERIAL_LOCK:
                                ohbot.move(motor_id, float(position), frame_speed)

                    if 'led' in frame:
                        led = frame['led']
                        with OHBOT_SERIAL_LOCK:
                            ohbot.baseColour(
                                float(led.get('r', 0)),
                                float(led.get('g', 0)),
                                float(led.get('b', 0)),
                            )

                    print(f"▶ Timeline keyframe {i + 1}/{len(keyframes)} — "
                          f"speed {frame_speed} — {list(motors.keys())}")

                    if i < len(keyframes) - 1:
                        pre_wait = max(0.0, float(frame.get('preWait', 0)))
                        if pre_wait > 0:
                            _sleep_interruptible(pre_wait)
            finally:
                play_state['playing'] = False
                print("✅ Timeline playback finished")

        threading.Thread(target=run_playback, daemon=True).start()
        return jsonify({'success': True, 'message': 'Playback started'})

    except Exception as e:
        print(f"❌ Timeline playback error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/timeline/api/stop', methods=['POST'])
def stop():
    """Stop whatever's currently playing."""
    play_state['stop_requested'] = True
    return jsonify({'success': True})


if __name__ == '__main__':
    print("=" * 70)
    print("🎬  Ohbot Timeline Server — Phase 2b (live capture added)")
    print("=" * 70)
    print("⚠️  IMPORTANT: Make sure the conversation bot and gui_server.py")
    print("   are NOT running. All three share the same USB serial cable")
    print("   and will conflict with each other.")
    print()
    print(f"📁  Reading sequences from: {SEQUENCES_DIR}")

    print("🔌 Connecting to Ohbot hardware...")
    if ohbot.init():
        print(f"✅ Ohbot connected on {ohbot.port}")
    else:
        print("⚠️  Ohbot hardware not found.")
        print("   The timeline will still open — you can preview sequences,")
        print("   just nothing will move until the robot is found.")

    print()
    print("🌐  Open in a browser:  http://<pi-ip-address>:5003/timeline")
    print("=" * 70)
    app.run(host='0.0.0.0', port=5003, debug=False)
