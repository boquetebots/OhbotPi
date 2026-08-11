#!/usr/bin/env python3
"""
Ohbot/Yobot Launcher Server
Version: 2.0.0 — cross-platform (Raspberry Pi + macOS)

Runs on port 5000 and lets you choose what to do from a web page:
  - Start the Greeter/Conversation Bot (voice conversation mode)
  - Start the Sequence Builder GUI (port 5001)
  - Start Motor Calibration (port 5003)

Only one of these can run at a time — they all share the one USB serial
cable to the robot.

HOW IT WORKS ON EACH PLATFORM
-----------------------------
Raspberry Pi (systemd available and the services are installed):
    Starts and stops the systemd services, exactly as before. Also offers
    Shut Down / Restart buttons for the Pi itself.

Mac (or a Pi running this by hand, without the services installed):
    There is no systemd, so the launcher starts and stops the Python
    programs directly. The conversation bot is opened in its own Terminal
    window so you can see it talk and press Enter to wake it. The
    Shut Down / Restart buttons are hidden — a web page has no business
    turning off your Mac.

Which mode is in use is decided automatically at startup and shown in the
console when the launcher starts.
"""

from flask import Flask, jsonify, request, send_from_directory
import os
import platform
import shutil
import subprocess
import sys
import threading
import time
import urllib.request   # used by the Wake button to talk to the Greeter

# Save everything this program prints into logs/launcher-<date>.log
try:
    from ohbot_logging import setup_logging
    setup_logging("launcher")
except Exception as _log_err:                                # noqa: BLE001
    print(f"⚠️  Log file not started ({_log_err}) — carrying on without one")

# Saved per-robot calibrations (ohbotData/robots/). See robot_profiles.py.
import robot_profiles

app = Flask(__name__)

# ── English / Spanish ──────────────────────────────────────────────────────
# Adds two routes: /i18n.js (hands the web pages their wording) and /lang
# (remembers which language was picked). See ohbot_lang.py.
from ohbot_lang import register_language_routes
register_language_routes(app)

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
LAUNCHER_DIR = os.path.join(BASE_DIR, 'launcher')

IS_LINUX   = platform.system() == 'Linux'
IS_MAC     = platform.system() == 'Darwin'
IS_WINDOWS = platform.system() == 'Windows'

# Systemd service names (Pi only)
GREETER_SERVICES    = ['ohbot-server', 'ohbot-conversation']
GUI_SERVICE         = 'ohbot-gui'
CALIBRATION_SERVICE = 'ohbot-calibration'

# Python programs to run when not using systemd.
# Greeter = brain server (OpenAI, port 5002) + the conversation bot itself.
PROC_GREETER_BRAIN = 'ohbotchat_server.py'
PROC_GREETER_BOT   = 'ohbot_chat.py'
PROC_GUI           = 'gui_server.py'
PROC_CALIBRATION   = 'calibration_server.py'

PYTHON = sys.executable          # the same python running this launcher


# ── Helpers ────────────────────────────────────────────────────────────────

def _run(cmd):
    """Run a shell command. Returns (success, output)."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return result.returncode == 0, result.stdout.strip()
    except Exception as e:
        return False, str(e)


def _systemd_available():
    """True only if systemd is present AND our services are installed."""
    if not IS_LINUX or not shutil.which('systemctl'):
        return False
    ok, out = _run(['systemctl', '--user', 'list-unit-files', f'{GUI_SERVICE}.service'])
    return ok and GUI_SERVICE in out


USE_SYSTEMD = _systemd_available()


# ── Backend A: systemd (Raspberry Pi) ──────────────────────────────────────

def _service_active(name):
    _, out = _run(['systemctl', '--user', 'is-active', name])
    return out == 'active'


# ── Backend B: plain processes (Mac, or Pi without services) ───────────────
# Processes are found by searching for their script name, so the launcher
# can see and stop programs even if they were started from a Terminal
# window by hand (or if the launcher itself was restarted).

_tracked = {}      # script name → Popen object (Windows fallback only)

# Which port each web server listens on — checking the port is the most
# reliable "is it running?" test for those.
SCRIPT_PORTS = {
    PROC_GUI:         5001,
    PROC_GREETER_BRAIN: 5002,
    PROC_CALIBRATION: 5003,
}


def _port_in_use(port):
    """True if something is already listening on this port."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex(('127.0.0.1', port)) == 0


def _proc_running(script):
    """Is a python program with this script name currently running?"""
    # Web servers: just ask whether their port is answering
    port = SCRIPT_PORTS.get(script)
    if port and _port_in_use(port):
        return True

    if IS_WINDOWS:
        proc = _tracked.get(script)
        return proc is not None and proc.poll() is None

    # No port (the conversation bot): look for a python process running it.
    # Requiring "python" in the command line avoids matching editors or
    # shell commands that merely mention the filename, and we ignore our
    # own process and the shell that started us.
    import re
    pattern = rf'python.*{re.escape(script)}'
    ok, out = _run(['pgrep', '-f', pattern])
    if not ok or not out.strip():
        return False

    mine = {os.getpid(), os.getppid()}
    pids = {int(p) for p in out.split() if p.strip().isdigit()}
    return bool(pids - mine)


def _proc_start(script, new_terminal=False):
    """Start a python program from the project folder."""
    path = os.path.join(BASE_DIR, script)

    if new_terminal and IS_MAC:
        # Open in its own Terminal window so the conversation bot has a
        # keyboard (needed to press Enter to wake it) and visible output.
        cmd = f'cd {BASE_DIR!r} && {PYTHON!r} {path!r}'
        script_osa = f'tell application "Terminal" to do script "{cmd}"'
        subprocess.run(['osascript', '-e', script_osa],
                       capture_output=True, timeout=15)
        subprocess.run(['osascript', '-e',
                        'tell application "Terminal" to activate'],
                       capture_output=True, timeout=10)
        return

    proc = subprocess.Popen(
        [PYTHON, path],
        cwd=BASE_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    _tracked[script] = proc


def _proc_stop(script):
    """Stop a python program by script name."""
    if IS_WINDOWS:
        proc = _tracked.pop(script, None)
        if proc and proc.poll() is None:
            proc.terminate()
        return

    _run(['pkill', '-f', script])
    _tracked.pop(script, None)


# ── Unified status / control ───────────────────────────────────────────────

def _get_status():
    """
    Returns the current state:
      'greeter'     — conversation bot is running
      'gui'         — sequence builder GUI is running
      'calibration' — motor calibration page is running
      'idle'        — nothing is running
    """
    if USE_SYSTEMD:
        if any(_service_active(s) for s in GREETER_SERVICES):
            return 'greeter'
        if _service_active(GUI_SERVICE):
            return 'gui'
        if _service_active(CALIBRATION_SERVICE):
            return 'calibration'
        return 'idle'

    if _proc_running(PROC_GREETER_BOT):
        return 'greeter'
    if _proc_running(PROC_GUI):
        return 'gui'
    if _proc_running(PROC_CALIBRATION):
        return 'calibration'
    return 'idle'


def _stop_everything():
    """Stop whatever is running, on either platform."""
    if USE_SYSTEMD:
        for s in GREETER_SERVICES:
            _run(['systemctl', '--user', 'stop', s])
        _run(['systemctl', '--user', 'stop', GUI_SERVICE])
        _run(['systemctl', '--user', 'stop', CALIBRATION_SERVICE])
    else:
        for script in (PROC_GREETER_BOT, PROC_GREETER_BRAIN,
                       PROC_GUI, PROC_CALIBRATION):
            _proc_stop(script)


# ── Routes ─────────────────────────────────────────────────────────────────

@app.route('/')
def serve_launcher():
    return send_from_directory(LAUNCHER_DIR, 'index.html')


@app.route('/launcher/status')
def get_status():
    """The page polls this every 2 seconds to know what's running."""
    return jsonify({'status': _get_status()})


@app.route('/launcher/robots')
def list_robots():
    """
    The saved robots, which one is loaded, and whether it's safe to switch
    right now.

    Switching is only offered when nothing is running. Every program reads
    the motor file once at startup, so swapping it underneath a running
    greeter or GUI would change nothing until a restart — and would leave
    the page claiming a robot is loaded when the running program is still
    driving the previous one.
    """
    try:
        data = robot_profiles.summary()
        data['can_switch'] = (_get_status() == 'idle')
        data['running'] = _get_status()
        return jsonify({'success': True, **data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/launcher/robots/save', methods=['POST'])
def save_robot():
    """
    File the CURRENT live motor file into the robot library under a name,
    without re-measuring anything.

    This exists because the calibration page — correctly — refuses to save
    when you haven't measured any motors in that session. So there was no
    way to say "the calibration already in the file belongs to this robot,
    remember it". That's exactly what you need when you already have a
    calibrated head and are about to introduce a second one.

    Allowed while a service is running: this only reads the live file and
    copies it, so it can't disturb anything.
    """
    try:
        data = request.get_json(silent=True) or {}
        overwrite = bool(data.get('overwrite', False))
        ok, result = robot_profiles.save_profile(data.get('name'),
                                                 overwrite=overwrite)
        if not ok:
            # 409 specifically means "that name is taken" — the page uses
            # this to ask before replacing, rather than clobbering silently.
            code = 409 if 'already exists' in str(result) else 400
            return jsonify({'success': False, 'error': result}), code
        return jsonify({'success': True, **result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/launcher/robots/load', methods=['POST'])
def load_robot():
    """
    Copy a saved robot's calibration over the live motor file, so everything
    started from now on drives that robot.

    The current live file is backed up to ohbotData/MD_old_N.omd first, so
    an accidental switch is always recoverable.
    """
    try:
        running = _get_status()
        if running != 'idle':
            return jsonify({
                'success': False,
                'error': f'Stop the {running} first — it is already running and '
                         f'has the current robot\'s numbers loaded in memory. '
                         f'Switching robots now would have no effect until it '
                         f'restarts. Press "Stop Current Service", then try '
                         f'again.'
            }), 409

        data = request.get_json(silent=True) or {}
        ok, result = robot_profiles.load_profile(data.get('name'))
        if not ok:
            return jsonify({'success': False, 'error': result}), 400
        return jsonify({'success': True, **result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/launcher/platform')
def get_platform():
    """Lets the page hide Pi-only buttons (Shut Down / Restart) on a Mac."""
    return jsonify({
        'platform':    platform.system(),
        'is_pi':       USE_SYSTEMD,
        'can_power':   USE_SYSTEMD,
    })


@app.route('/launcher/wake', methods=['POST'])
def wake_greeter():
    """Wake Yobot from sleep.

    The page can't call the Greeter's server (port 5002) directly — a browser
    blocks a page served from one port talking to another. So the request
    comes here, to port 5000, and this passes it along from the Pi itself
    where that rule doesn't apply.
    """
    try:
        req = urllib.request.Request(
            'http://127.0.0.1:5002/wake', data=b'', method='POST')
        with urllib.request.urlopen(req, timeout=5) as resp:
            resp.read()
        return jsonify({'success': True})
    except Exception as e:
        # Almost always means the Greeter isn't running.
        return jsonify({'success': False, 'error': str(e)}), 502


@app.route('/launcher/start/greeter', methods=['POST'])
def start_greeter():
    """Stop everything else, then start the conversation bot."""
    if USE_SYSTEMD:
        if _service_active(GUI_SERVICE):
            _run(['systemctl', '--user', 'stop', GUI_SERVICE])
            time.sleep(1)
        for s in GREETER_SERVICES:
            _run(['systemctl', '--user', 'start', s])
    else:
        _proc_stop(PROC_GUI)
        _proc_stop(PROC_CALIBRATION)
        time.sleep(1)
        # Brain server first (the bot needs it), then the bot in its own window
        if not _proc_running(PROC_GREETER_BRAIN):
            _proc_start(PROC_GREETER_BRAIN)
            time.sleep(2)
        _proc_start(PROC_GREETER_BOT, new_terminal=True)

    return jsonify({'success': True, 'status': 'greeter'})


@app.route('/launcher/start/gui', methods=['POST'])
def start_gui():
    """Stop the conversation bot if running, then start the GUI."""
    if USE_SYSTEMD:
        for s in GREETER_SERVICES:
            if _service_active(s):
                _run(['systemctl', '--user', 'stop', s])
        time.sleep(1)
        _run(['systemctl', '--user', 'start', GUI_SERVICE])
    else:
        _proc_stop(PROC_GREETER_BOT)
        _proc_stop(PROC_GREETER_BRAIN)
        _proc_stop(PROC_CALIBRATION)
        time.sleep(1)
        _proc_start(PROC_GUI)

    return jsonify({'success': True, 'status': 'gui'})


@app.route('/launcher/start/calibration', methods=['POST'])
def start_calibration():
    """
    Start the motor calibration server.

    Unlike Greeter/GUI, this does NOT auto-stop whatever else is running.
    Calibration is a deliberate, careful step (finding servo limits), so
    the user is expected to stop the current service first via the Stop
    button — this route just refuses to start if anything else is active.
    """
    current = _get_status()
    if current not in ('idle', 'calibration'):
        return jsonify({
            'success': False,
            'error': f'Stop the current service first (currently running: {current}).'
        }), 400

    if USE_SYSTEMD:
        _run(['systemctl', '--user', 'start', CALIBRATION_SERVICE])
    elif not _proc_running(PROC_CALIBRATION):
        _proc_start(PROC_CALIBRATION)
        time.sleep(2)

    return jsonify({'success': True, 'status': 'calibration'})


@app.route('/launcher/stop', methods=['POST'])
def stop_all():
    """Stop whichever service is currently running."""
    _stop_everything()
    return jsonify({'success': True, 'status': 'idle'})


@app.route('/launcher/shutdown', methods=['POST'])
def shutdown_pi():
    """Shut the Pi down cleanly after a short delay. Pi only."""
    if not USE_SYSTEMD:
        return jsonify({
            'success': False,
            'error': 'Shut Down is only available on the Raspberry Pi.'
        }), 400

    def do_shutdown():
        time.sleep(3)
        subprocess.run(['sudo', 'shutdown', '-h', 'now'])
    threading.Thread(target=do_shutdown, daemon=True).start()
    return jsonify({'success': True})


@app.route('/launcher/restart', methods=['POST'])
def restart_pi():
    """Restart the Pi after a short delay. Pi only."""
    if not USE_SYSTEMD:
        return jsonify({
            'success': False,
            'error': 'Restart is only available on the Raspberry Pi.'
        }), 400

    def do_restart():
        time.sleep(3)
        subprocess.run(['sudo', 'reboot'])
    threading.Thread(target=do_restart, daemon=True).start()
    return jsonify({'success': True})


# ── Startup ────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=" * 50)
    print("🚀  Ohbot / Yobot Launcher")
    print("=" * 50)
    print()
    if USE_SYSTEMD:
        print("Mode: Raspberry Pi (systemd services)")
    else:
        print(f"Mode: direct process control ({platform.system()})")
        print("      Shut Down / Restart buttons are disabled.")
    print()
    print("Open in your browser:")
    print("   http://localhost:5000       (on this computer)")

    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        print(f"   http://{ip}:5000      (from another device)")
    except Exception:
        pass

    print()
    print("Press Ctrl-C to stop.")
    print("=" * 50)
    print()

    app.run(host='0.0.0.0', port=5000, debug=False)
