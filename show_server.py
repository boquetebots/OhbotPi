#!/usr/bin/env python3
"""
show_server.py — Yobot's offline demo show
Version: 1.0.0  (2026-09-02)

WHAT THIS IS
------------
A cue stack for Yobot, like a lighting desk. You get a web page of big
buttons on your phone. You tap one, Yobot says that line out loud with
proper lip sync and a bit of movement.

Every line is PRE-RECORDED (see prerender_cues.py), so this needs NO
INTERNET. Not for the voice, not for the brain, not for anything. The
microphone is never opened — the audience talks to you, and you tap the
cue. That is the whole trick, and it is why it cannot fail on the day.

HOW TO RUN IT
-------------
    ~/yobot-venv/bin/python3 show_server.py

then open   http://localhost:5004   on this Mac, or from your phone use
the address the program prints when it starts.

ONLY ONE PROGRAM CAN HOLD THE ROBOT AT A TIME. Stop the Greeter, the
Sequence Builder and Calibration before starting this — same rule as
always, this is just one more name on that list.

WHAT IT TOUCHES
---------------
Nothing. This is a brand new file. It imports the existing robot code
read-only and does not modify any of it. Delete this file and the robot
is exactly as it was.
"""

import os
import sys
import json
import time
import socket
import asyncio
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from flask import Flask, jsonify, request, send_from_directory   # noqa: E402

import voice_cache                                               # noqa: E402
import yobot_core as ohbot                                       # noqa: E402
import robot_profiles                                            # noqa: E402
from ohbot_azure import AsyncOhbotController                     # noqa: E402

PORT = 5004                       # 5000 launcher, 5001 gui, 5002 chat,
                                  # 5003 calibration/timeline
CUE_FILE = os.path.join(HERE, 'demo_cues.json')

app = Flask(__name__, static_folder=None)


# ─────────────────────────────────────────────────────────────────────────────
# WHICH ROBOT'S CALIBRATION IS THIS?
#
# There is exactly one "live" motor file — ohbotData/MotorDefinitionsv21.omd —
# and EVERY program reads it, once, at startup. Loading a different robot in
# the Launcher just copies that robot's saved file over the live one.
#
# Two consequences that matter on demo day:
#
#   1. Switching robots while this server is running does NOTHING until it is
#      restarted. The Launcher normally refuses to switch mid-run, but it only
#      knows about the services IT started — this one is invisible to it. So
#      the safety net does not cover us, and we have to notice for ourselves.
#
#   2. active_robot.txt is a LABEL ONLY. No motor code reads it. It can be
#      wrong. The live .omd file is always the truth.
#
# So: record the file's timestamp when we start, and keep checking it. If it
# changes underneath us, the page says so in red rather than letting the robot
# move on the wrong robot's numbers.
# ─────────────────────────────────────────────────────────────────────────────
calib = {'name': None, 'mtime': 0.0, 'file': robot_profiles.MOTOR_DEF_FILE}


def _calib_mtime():
    try:
        return os.path.getmtime(robot_profiles.MOTOR_DEF_FILE)
    except OSError:
        return 0.0


def snapshot_calibration():
    calib['name'] = robot_profiles.get_active() or '(unnamed)'
    calib['mtime'] = _calib_mtime()


def calibration_state():
    """What the page shows. 'stale' means the live motor file has been
    replaced since we read it — the robot is moving on the OLD numbers."""
    now_m = _calib_mtime()
    now_n = robot_profiles.get_active() or '(unnamed)'
    return {
        'name': calib['name'],
        'now_name': now_n,
        'missing': now_m == 0.0,
        'stale': bool(calib['mtime']) and (now_m != calib['mtime']),
    }

# ─────────────────────────────────────────────────────────────────────────────
# MOVEMENT LIBRARY
#
# Each motion is a list of steps. A step can set motor positions, the eye
# colour, and how long to hold before the next step.
#
# Motors used here are deliberately HEAD and EYES only — never TOPLIP or
# BOTTOMLIP. The lips belong to the lip-sync while Yobot is talking, and
# two things fighting over the same motor looks terrible.
#
# 'loop': True means "keep doing this until he stops talking", so a long
# answer doesn't end with the robot frozen mid-sentence.
#
# Positions are the usual Ohbot 0–10 scale, 5 is centre.
# HOW LONG A MOVE ACTUALLY TAKES  (this is the bit that bites)
#
# ***  THE EYE MOTORS IGNORE SPEED. PROVED ON THE HARDWARE 2026-09-02.  ***
#
# eye_speed_test.py ran the SAME eye swing at speeds 10, 5, 2 and 1 and all
# four were indistinguishable. EyeTurn and EyeTilt always snap to their
# target flat out, whatever number you send. (Both carry Speed="0" in the
# calibration file, which fits.) So for the eyes there is only ONE lever:
# HOW FAR THEY GO. A short snap reads as a twitch; a long snap reads as a
# proper look, because that is what real eyes do — they flick, they do not
# glide. Michael tested the range and settled on 2.0 to 8.0.
#
# If a slow eye GLIDE is ever wanted, the only way is to send a string of
# small in-between positions by hand. That was tried for the Sequence
# Builder timeline and rejected as too choppy — see the project memory note
# on keyframe speed before going down that road again.
#
# The head motors DO obey speed. There, 'speed' is multiplied by 25 and
# sent as roughly DEGREES PER SECOND: speed 1.5 = 37 deg/sec, speed 9 =
# 225 deg/sec. Fractions are allowed and useful — speed 1 to 2 is where the
# lifelike head movement lives.
#
# But a slider point is worth a different number of degrees on every motor
# (from the calibration file), so the SAME speed looks completely different
# depending on which motor is moving:
#
#     Head nod   12.6 deg per point   <- most sensitive, keep swings small
#     Eye tilt    9.7
#     Head turn   9.3
#     Eye turn    8.3
#     Lid blink   5.8
#     Head roll   5.6                 <- least sensitive, needs big swings
#
#     head move time  =  (points travelled x degrees per point) / (speed x 25)
#
# The original version of this library moved only 0.7-1.5 points at a time.
# For the head that worked out at a tenth of a second of movement followed
# by two full seconds of standing perfectly still. For the eyes it was an
# instant flick of a few degrees. Both read as twitchy and over-caffeinated.
# The blink was the only thing that looked right, because it is the only
# move that travels its full range.
#
# The rules now:
#   EYES  — swing WIDE, 2.0 to 8.0. The speed number is decoration.
#   HEAD  — speed 1.5 (1.0 for head roll) with swings roughly doubled, which
#           puts head moves at about three quarters of a second.
#   BLINK — stays fast, speed 8-9. A real eyelid IS fast.
#
# Eyes therefore arrive before the head every time. That is correct: the
# eyes lead and the head follows, which is what people actually do.
#
# 'wait' is the whole length of the step, measured from when the move
# starts — not extra time on the end. So wait must always be comfortably
# longer than the move, or the next step interrupts this one.
# ─────────────────────────────────────────────────────────────────────────────
NEUTRAL = {'HEADNOD': 5, 'HEADTURN': 5, 'EYETURN': 5,
           'LIDBLINK': 10, 'EYETILT': 5, 'HEADROLL': 5}

MOTIONS = {
    'none':  {'loop': False, 'steps': []},

    # Coming to life and finding the audience.
    # Eyes open slowly, then a proper look left and right.
    'wake': {'loop': False, 'led': (10, 7, 2), 'steps': [
        {'m': {'LIDBLINK': 0}, 'speed': 8, 'wait': 0.35},
        {'m': {'LIDBLINK': 10}, 'speed': 3, 'wait': 0.90},          # 0.77s dreamy open
        {'m': {'HEADNOD': 6.2, 'EYETILT': 7.2}, 'speed': 1.5, 'wait': 0.90},   # chin and eyes up
        {'m': {'HEADTURN': 3.2, 'EYETURN': 2.2}, 'speed': 1.5, 'wait': 1.4},   # head 0.45s
        {'m': {'HEADTURN': 6.8, 'EYETURN': 7.8}, 'speed': 1.5, 'wait': 1.7},   # head 0.90s
        {'m': {'HEADTURN': 5, 'EYETURN': 5, 'EYETILT': 5, 'HEADNOD': 5.5},
         'speed': 1.5, 'wait': 0.9},
    ]},

    # Chin up, pleased with himself. Head roll gets its own slower steps
    # because roll is the least sensitive motor on the robot.
    'proud': {'loop': True, 'led': (10, 8, 0), 'steps': [
        {'m': {'HEADNOD': 6.4, 'EYETILT': 7.6}, 'speed': 1.5, 'wait': 1.3},    # looking up, pleased
        {'m': {'HEADROLL': 3.8, 'EYETURN': 2.6}, 'speed': 1.0, 'wait': 1.5},   # glance away
        {'m': {'LIDBLINK': 0}, 'speed': 9, 'wait': 0.12},
        {'m': {'LIDBLINK': 10}, 'speed': 9, 'wait': 1.3},
        {'m': {'HEADROLL': 6.0, 'EYETURN': 7.4}, 'speed': 1.0, 'wait': 1.7},   # and back across
        {'m': {'HEADNOD': 5.4, 'HEADROLL': 5, 'EYETURN': 5, 'EYETILT': 5},
         'speed': 1.5, 'wait': 1.8},
    ]},

    # Thinking about it. Eyes up and away, slow, with a lid droop.
    'ponder': {'loop': True, 'led': (2, 4, 10), 'steps': [
        {'m': {'HEADROLL': 3.4, 'EYETILT': 8.0, 'EYETURN': 2.2},
         'speed': 1.5, 'wait': 2.7},                     # eyes up and hard away
        {'m': {'LIDBLINK': 2}, 'speed': 5, 'wait': 0.45},           # 0.37s droop
        {'m': {'LIDBLINK': 10}, 'speed': 6, 'wait': 0.55},          # 0.31s back up
        {'m': {'EYETURN': 7.8, 'HEADNOD': 5.6}, 'speed': 1.5, 'wait': 2.8},    # eyes swing right
        {'m': {'HEADROLL': 5, 'EYETILT': 5, 'EYETURN': 5}, 'speed': 1.5, 'wait': 2.4},
    ]},

    # The everyday talking-to-you motion. This is the one that runs under
    # almost every cue, so it is the one that has to look unhurried.
    'explain': {'loop': True, 'led': (3, 9, 5), 'steps': [
        {'m': {'HEADTURN': 3.6, 'EYETURN': 2.0, 'EYETILT': 6.8, 'HEADNOD': 5.5},
         'speed': 1.5, 'wait': 2.6},                     # up and left; head 0.35s behind
        {'m': {'LIDBLINK': 0}, 'speed': 9, 'wait': 0.12},
        {'m': {'LIDBLINK': 10}, 'speed': 9, 'wait': 1.5},
        {'m': {'HEADTURN': 6.4, 'EYETURN': 8.0, 'EYETILT': 3.2, 'HEADNOD': 4.5},
         'speed': 1.5, 'wait': 3.0},                     # down and right; head 0.70s behind
        {'m': {'HEADROLL': 3.2}, 'speed': 1.0, 'wait': 1.9},        # 0.40s
        {'m': {'HEADTURN': 5, 'EYETURN': 5, 'EYETILT': 5, 'HEADROLL': 5.8},
         'speed': 1.5, 'wait': 2.4},
    ]},

    # Showing off. Left fast on purpose — a dance SHOULD be snappy.
    'dance': {'loop': True, 'steps': [
        {'m': {'HEADROLL': 2.5, 'HEADTURN': 3}, 'speed': 6, 'led': (10, 0, 4), 'wait': 0.45},
        {'m': {'HEADROLL': 7.5, 'HEADTURN': 7}, 'speed': 6, 'led': (0, 8, 10), 'wait': 0.45},
        {'m': {'HEADNOD': 7, 'HEADROLL': 5}, 'speed': 7, 'led': (10, 8, 0), 'wait': 0.35},
        {'m': {'HEADNOD': 3.5}, 'speed': 7, 'led': (6, 0, 10), 'wait': 0.35},
        {'m': {'HEADNOD': 5.5, 'HEADTURN': 5, 'LIDBLINK': 0}, 'speed': 8, 'wait': 0.15},
        {'m': {'LIDBLINK': 10}, 'speed': 8, 'wait': 0.30},
    ]},

    # A nod goodbye, then the lights go down. The nod stays a little brisker
    # than the ambient motions — a nod that slow reads as falling asleep.
    'farewell': {'loop': False, 'led': (8, 4, 1), 'steps': [
        {'m': {'HEADNOD': 3.4}, 'speed': 2.5, 'wait': 0.75},        # 0.32s
        {'m': {'HEADNOD': 6.2}, 'speed': 2.5, 'wait': 0.85},        # 0.56s
        {'m': {'HEADNOD': 5, 'HEADTURN': 5}, 'speed': 1.5, 'wait': 1.4},
        {'m': {'LIDBLINK': 1}, 'speed': 2, 'wait': 1.2},            # 1.04s slow close
        {'m': {'LIDBLINK': 10}, 'speed': 3, 'wait': 0.8},
    ]},
}

# ─────────────────────────────────────────────────────────────────────────────
# THE ROBOT, ON ITS OWN THREAD
#
# The existing robot code is async (it runs all 8 motors at once). Flask is
# not. So we run one asyncio loop forever on a background thread and hand
# work to it from the web routes. This is the same arrangement ohbot_chat.py
# uses, just driven by buttons instead of a microphone.
# ─────────────────────────────────────────────────────────────────────────────
class Show:
    def __init__(self):
        self.loop = None
        self.controller = None
        self.robot_ok = False
        self.busy = False
        self.now_playing = None
        self.stop_flag = False
        self.ready = threading.Event()
        self.error = None

    # ---- background loop -------------------------------------------------
    def start(self, robot=None):
        self._robot = robot
        threading.Thread(target=self._run, daemon=True).start()
        self.ready.wait(timeout=30)

    def _run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._boot(getattr(self, '_robot', None)))
        self.ready.set()
        self.loop.run_forever()

    async def _boot(self, robot=None):
        # Optional: switch to a named robot's calibration BEFORE connecting,
        # so `--robot Goldie` is the whole job — no Launcher dance at the
        # venue. The live file is backed up automatically by load_profile().
        if robot:
            ok, res = robot_profiles.load_profile(robot)
            if ok:
                print(f"✅ Calibration loaded: {res['name']}")
            else:
                self.error = f"Could not load robot '{robot}': {res}"
                print(f"❌ {self.error}")
                print("   Available:  python3 show_server.py --list-robots")
        snapshot_calibration()
        print(f"   Calibration in use: {calib['name']}")

        try:
            if ohbot.init():
                ohbot.reset()
                self.robot_ok = True
                print("✅ Robot connected")
            else:
                self.error = ("Robot not found. Check the USB cable, and that "
                              "the Greeter / Sequence Builder are stopped.")
                print(f"⚠️  {self.error}")
        except Exception as e:                               # noqa: BLE001
            self.error = f"Robot connection failed: {e}"
            print(f"⚠️  {self.error}")

        # No Azure manager is created — we never synthesise here, we only
        # play back what prerender_cues.py already recorded. Passing None
        # is safe: the controller only stores it, and the two methods we
        # call (lip sync + audio playback) never look at it.
        self.controller = AsyncOhbotController(None)
        await self.controller.start()

    def submit(self, coro):
        """Hand a job to the robot thread from a Flask route."""
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    # ---- movement --------------------------------------------------------
    async def _apply(self, step, default_speed=4):
        speed = step.get('speed', default_speed)
        for name, pos in (step.get('m') or {}).items():
            await self.controller.move(getattr(ohbot, name), pos, speed,
                                       avoid=(name not in ('LIDBLINK',)))
        led = step.get('led')
        if led:
            await self.controller.set_eye_color(*led)

    async def _motion_task(self, motion_name, stop_when):
        """Run a motion, looping if it is a looping one, until the speech
        finishes. Never raises into the caller — a movement glitch must not
        take the voice down with it."""
        motion = MOTIONS.get(motion_name) or MOTIONS['none']
        try:
            if motion.get('led'):
                await self.controller.set_eye_color(*motion['led'])
            steps = motion.get('steps') or []
            if not steps:
                return
            while True:
                for step in steps:
                    if stop_when.is_set() or self.stop_flag:
                        return
                    await self._apply(step)
                    await asyncio.sleep(step.get('wait', 0.5))
                if not motion.get('loop'):
                    return
        except asyncio.CancelledError:
            raise
        except Exception as e:                               # noqa: BLE001
            print(f"⚠️  motion '{motion_name}' stopped: {e}")

    async def to_neutral(self):
        try:
            await self._apply({'m': NEUTRAL, 'speed': 1.5})
            await self.controller.move(ohbot.TOPLIP, 5, 6, avoid=False)
            await self.controller.move(ohbot.BOTTOMLIP, 5, 6, avoid=False)
            await self.controller.set_eye_color(4, 6, 8)
        except Exception as e:                               # noqa: BLE001
            print(f"⚠️  neutral failed: {e}")

    # ---- the actual cue --------------------------------------------------
    async def play(self, cue, lang):
        # A cue can pin itself to one language — the Spanish greeting stays
        # Spanish even when the page is toggled to English.
        lang = cue.get('lang_lock') or lang
        text = (cue.get(f'text_{lang}') or '').strip()
        hit = voice_cache.load(text, lang)
        if not hit:
            # Should never happen if prerender_cues.py ran — but if it does,
            # say so loudly on the page rather than standing there silently.
            raise RuntimeError(
                f"'{cue.get('id')}' [{lang}] has not been recorded yet. "
                f"Run:  python3 prerender_cues.py")

        wav, visemes = hit
        self.busy = True
        self.now_playing = cue.get('id')
        self.stop_flag = False
        done = asyncio.Event()

        motion = asyncio.create_task(
            self._motion_task(cue.get('motion', 'explain'), done))
        lips = None
        try:
            if visemes:
                lips = asyncio.create_task(
                    self.controller._animate_lips_with_visemes(wav, visemes))
            await self.controller._play_audio_async(wav)
            if lips:
                await lips
        finally:
            # Whatever happened — finished, failed, or the audio player fell
            # over — the movement and the mouth both stop, and Yobot goes
            # back to a tidy rest position ready for the next cue.
            done.set()
            for task in (motion, lips):
                if task is None:
                    continue
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):  # noqa: BLE001
                    pass
            await self.to_neutral()
            self.busy = False
            self.now_playing = None


show = Show()


def load_cues():
    with open(CUE_FILE, encoding='utf-8') as f:
        return json.load(f).get('cues', [])


def lan_ip():
    """Best guess at the address to type on a phone. No internet needed —
    this only asks the operating system which address it would use."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('192.168.1.1', 1))      # no packet is actually sent
        return s.getsockname()[0]
    except Exception:                                        # noqa: BLE001
        return '127.0.0.1'
    finally:
        s.close()


# ─────────────────────────────────────────────────────────────────────────────
# WEB ROUTES
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/')
def page():
    return send_from_directory(os.path.join(HERE, 'gui'), 'show.html')


@app.route('/api/cues')
def api_cues():
    out = []
    for cue in load_cues():
        lock = cue.get('lang_lock')
        def ready(lang):
            L = lock or lang
            return voice_cache.is_cached(cue.get(f'text_{L}', ''), L)
        out.append({
            'id': cue.get('id'),
            'group': cue.get('group', ''),
            'lang_lock': lock or '',
            'label_en': cue.get('label_en'),
            'label_es': cue.get('label_es'),
            'motion': cue.get('motion'),
            'text_en': cue.get('text_en', ''),
            'text_es': cue.get('text_es', ''),
            'ready_en': ready('en'),
            'ready_es': ready('es'),
        })
    return jsonify({'cues': out, 'robot': show.robot_ok, 'error': show.error,
                    'calib': calibration_state()})


@app.route('/api/status')
def api_status():
    return jsonify({'busy': show.busy, 'playing': show.now_playing,
                    'robot': show.robot_ok, 'error': show.error,
                    'calib': calibration_state()})


@app.route('/api/play', methods=['POST'])
def api_play():
    if show.busy:
        return jsonify({'ok': False, 'error': 'Yobot is already speaking.'}), 409
    body = request.get_json(force=True, silent=True) or {}
    lang = 'es' if body.get('lang') == 'es' else 'en'
    cue = next((c for c in load_cues() if c.get('id') == body.get('id')), None)
    if not cue:
        return jsonify({'ok': False, 'error': 'No such cue.'}), 404
    try:
        show.submit(show.play(cue, lang)).result(timeout=120)
        return jsonify({'ok': True})
    except Exception as e:                                   # noqa: BLE001
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/neutral', methods=['POST'])
def api_neutral():
    try:
        show.submit(show.to_neutral()).result(timeout=15)
        return jsonify({'ok': True})
    except Exception as e:                                   # noqa: BLE001
        return jsonify({'ok': False, 'error': str(e)}), 500


def parse_args():
    """--robot NAME to load a calibration first, --list-robots to see them."""
    argv = sys.argv[1:]
    if '--list-robots' in argv:
        print("\nSaved robot calibrations:")
        for r in robot_profiles.list_robots():
            print(f"   {r.get('name')}")
        print(f"\nCurrently live: {robot_profiles.get_active() or '(unnamed)'}")
        print("\nUse:  python3 show_server.py --robot NAME\n")
        sys.exit(0)
    if '--robot' in argv:
        i = argv.index('--robot')
        if i + 1 >= len(argv):
            print("❌ --robot needs a name, e.g.  --robot Goldie")
            sys.exit(1)
        return argv[i + 1]
    return None


# ─────────────────────────────────────────────────────────────────────────────
# ENGLISH / SPANISH, AND THE EDITOR
#
# register_language_routes() is the same one-liner every other server in this
# project uses — it adds /i18n.js (the shared wording) and /lang (remembers
# which language was picked). See ohbot_lang.py.
#
# register_editor_routes() adds the page where the Clubhouse director edits
# the cues. It is handed the movement names so its dropdown can never offer a
# motion this server does not have, and a way to ask whether Yobot is
# currently speaking so a save cannot land mid-sentence.
# ─────────────────────────────────────────────────────────────────────────────
from ohbot_lang import register_language_routes                  # noqa: E402
register_language_routes(app)

from cue_editor import register_editor_routes                    # noqa: E402
register_editor_routes(app, motion_names=list(MOTIONS),
                       is_busy=lambda: show.busy)


if __name__ == '__main__':
    which_robot = parse_args()
    print("\n" + "─" * 58)
    print("  YOBOT SHOW — offline cue stack")
    print("─" * 58)
    s = voice_cache.stats()
    print(f"  Voice cache : {s['entries']} recorded lines "
          f"({s['bytes']/1_000_000:.1f} MB)")
    if s['entries'] == 0:
        print("  ⚠️  NOTHING IS RECORDED YET. While you still have internet:")
        print("      python3 prerender_cues.py")
    print("  Starting the robot…")
    show.start(which_robot)
    ip = lan_ip()
    print("─" * 58)
    print(f"  Show page   : http://localhost:{PORT}")
    print(f"  Edit the cues: http://localhost:{PORT}/editor")
    print(f"  From a phone : http://{ip}:{PORT}")
    print("  (same wifi — no internet needed to run the show)")
    print("─" * 58 + "\n")
    app.run(host='0.0.0.0', port=PORT, debug=False, threaded=True)
