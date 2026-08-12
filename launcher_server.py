#!/usr/bin/env python3
"""
Ohbot/Yobot Launcher Server
Version: 2.2.0 — cross-platform (Raspberry Pi + macOS + Windows)

Changes in 2.2.0 (2026-08-12, from testing on the PC):
  - Starting and stopping went from ~10s to ~1.5s on Windows. Three causes:
    the process hunt ran for all four programs (now only the conversation
    bot, since the other three answer on a port); fixed 2-second sleeps
    after starting a server (now waits for the port and returns as soon as
    it answers); and the process scan read every process's command line
    (now only python ones).
  - The Stop button used to report success even when the program refused
    to die. It now checks, and says what to do about it.
  - Background servers no longer share the Launcher's console window, so
    Ctrl-C in that window stops the Launcher instead of being swallowed.
  - Each start/stop prints how long it took (the ⏱ lines), so slowness can
    be measured rather than guessed at. Harmless to leave on; they go to
    the console and the log file.

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

Mac and Windows (or a Pi running this by hand, without the services
installed):
    There is no systemd, so the launcher starts and stops the Python
    programs directly. The conversation bot is opened in its own window
    (Terminal on the Mac, Command Prompt on Windows) so you can see it
    talk and press Enter to wake it. The Shut Down / Restart buttons are
    hidden — a web page has no business turning off your computer.

Which mode is in use is decided automatically at startup and shown in the
console when the launcher starts.

OPTIONAL: install psutil (`pip install psutil`). It isn't required, but it
makes finding and stopping programs faster and identical on all three
operating systems. On Windows without it the launcher falls back to
PowerShell, which works but takes about a second per check.
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

def _run(cmd, want_stderr=False):
    """Run a shell command. Returns (success, output).

    `want_stderr` folds the error output in with the normal output. Off by
    default because callers like `systemctl is-active` compare the output
    exactly. Needed for taskkill, which reports "Access is denied" on
    stderr — so without this its failures looked like silence (2026-08-12).
    """
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        out = result.stdout.strip()
        if want_stderr:
            err = result.stderr.strip()
            out = f"{out}\n{err}".strip() if err else out
        return result.returncode == 0, out
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


# ── Backend B: plain processes (Mac, Windows, or Pi without services) ──────
# Processes are found by searching for their script name, so the launcher
# can see and stop programs even if they were started from a Terminal or
# Command Prompt window by hand (or if the launcher itself was restarted).
#
# Three ways to look for a running program, best first:
#   1. psutil        — one clean way that works identically on all three OSes.
#                      Install with:  pip install psutil
#   2. pgrep/pkill   — built into Mac and Linux.
#   3. PowerShell    — the Windows stand-in when psutil isn't installed.
#                      Slower (PowerShell takes about a second to start), so
#                      the answer is cached for a couple of seconds.

try:
    import psutil
    HAVE_PSUTIL = True
except ImportError:
    HAVE_PSUTIL = False

_tracked = {}      # script name → Popen object, for things we started ourselves

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


def _wait_for_port(port, seconds=8.0):
    """Wait until a server answers on this port, up to `seconds`.

    Better than a fixed sleep: it returns the moment the server is ready
    instead of always waiting for the worst case. The old flat 2-second
    sleeps were a large part of why starting things felt slow on Windows.
    """
    deadline = time.time() + seconds
    while time.time() < deadline:
        if _port_in_use(port):
            return True
        time.sleep(0.15)
    return False


_pid_cache = {}          # script name → (timestamp, [pids])
_PID_CACHE_SECONDS = 2.0


def _own_pids():
    """Our own process and the shell that started us — never count these."""
    try:
        return {os.getpid(), os.getppid()}
    except (AttributeError, OSError):        # getppid is Unix-ish
        return {os.getpid()}


def _find_pids(script):
    """Every python process currently running this script, by PID.

    Requiring "python" in the command avoids matching an editor or a
    command prompt that merely has the filename on screen.
    """
    now = time.time()
    cached = _pid_cache.get(script)
    if cached and (now - cached[0]) < _PID_CACHE_SECONDS:
        return cached[1]

    pids = []

    if HAVE_PSUTIL:
        # Ask for the name only, then read the command line for the handful
        # of python processes. Reading a command line means opening the
        # process, which is slow on Windows — doing it for every process on
        # the PC made the Launcher page feel sluggish (fixed 2026-08-12).
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                name = (proc.info.get('name') or '').lower()
                if 'python' not in name:
                    continue
                if script in ' '.join(proc.cmdline() or []):
                    pids.append(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    elif IS_WINDOWS:
        # No psutil — ask PowerShell for the same information.
        query = (
            "Get-CimInstance Win32_Process | Where-Object "
            f"{{ $_.Name -like 'python*' -and $_.CommandLine -like '*{script}*' }}"
            " | ForEach-Object { $_.ProcessId }"
        )
        ok, out = _run(['powershell', '-NoProfile', '-NonInteractive',
                        '-Command', query])
        if ok:
            pids = [int(line) for line in out.split() if line.strip().isdigit()]

    else:
        import re
        pattern = rf'python.*{re.escape(script)}'
        ok, out = _run(['pgrep', '-f', pattern])
        if ok:
            pids = [int(p) for p in out.split() if p.strip().isdigit()]

    pids = [p for p in pids if p not in _own_pids()]

    # Anything we started ourselves counts too, even if the search missed it
    # (a locked-down PC can refuse to list other processes).
    proc = _tracked.get(script)
    if proc is not None and proc.poll() is None and proc.pid not in pids:
        pids.append(proc.pid)

    _pid_cache[script] = (now, pids)
    return pids


def _proc_running(script):
    """Is a python program with this script name currently running?"""
    # Web servers: just ask whether their port is answering — fastest and
    # most reliable test, and it works the same on every platform.
    port = SCRIPT_PORTS.get(script)
    if port and _port_in_use(port):
        return True

    return bool(_find_pids(script))


def _proc_start(script, new_terminal=False):
    """Start a python program from the project folder.

    `new_terminal` means "give this program its own window with a working
    keyboard" — the conversation bot needs it so you can press Enter to
    wake Yobot from sleep.
    """
    path = os.path.join(BASE_DIR, script)
    _pid_cache.pop(script, None)

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

    kwargs = dict(cwd=BASE_DIR,
                  stdout=subprocess.DEVNULL,
                  stderr=subprocess.DEVNULL)

    if IS_WINDOWS:
        if new_terminal:
            # Its own Command Prompt window, so it has a keyboard and you
            # can watch it talk. Output goes to the window, not DEVNULL.
            #
            # Deliberately NOT CREATE_NEW_PROCESS_GROUP: that flag disables
            # Ctrl-C for the new process, so the bot's own window would
            # ignore Ctrl-C. It buys nothing either — a process with its own
            # console can't be sent console signals from here anyway.
            kwargs['creationflags'] = subprocess.CREATE_NEW_CONSOLE
            kwargs.pop('stdout')
            kwargs.pop('stderr')
        else:
            # Background web servers: no window at all. Without CREATE_NO_WINDOW
            # they inherit the Launcher's console, and then Ctrl-C in the
            # Launcher's window goes to them instead of stopping the Launcher —
            # which looked exactly like "Ctrl-C does nothing" (Aug 12 2026).
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW

    proc = subprocess.Popen([PYTHON, path], **kwargs)
    _tracked[script] = proc


def _proc_stop(script):
    """Stop a python program by script name.

    Mac and Linux get a polite SIGTERM, which lets the program run its
    cleanup and put the robot back to rest.

    Windows has no equivalent polite signal that reaches these programs:
    console control events only travel to processes sharing our console,
    and neither the windowed bot nor the no-window servers do. So it's
    taskkill. That's less tidy, but Windows still closes the serial port
    handle when the process dies, so the next program can pick the robot
    up — the motors simply stay where they were instead of resetting.

    Returns (stopped_ok, message). The message is only meaningful when
    something went wrong — it gets shown to the user, so it says what to
    do rather than just what failed.
    """
    # Fast path for the web servers: if nothing is listening on their port
    # and we aren't holding a live process for them, there is nothing to
    # stop — so skip the process hunt entirely. That hunt is the expensive
    # part on Windows (a PowerShell call when psutil isn't installed), and
    # stopping ran it for all four programs, which is why Stop took ~10
    # seconds. Checking a port is instant. (2026-08-12)
    port = SCRIPT_PORTS.get(script)
    if port and not _port_in_use(port):
        held = _tracked.get(script)
        if held is None or held.poll() is not None:
            _tracked.pop(script, None)
            return True, ''

    pids = _find_pids(script)
    _pid_cache.pop(script, None)

    if not pids:
        _tracked.pop(script, None)
        return True, ''

    denied = False
    if IS_WINDOWS:
        for pid in pids:
            # /T also takes any child processes with it. taskkill reports
            # its failures on stderr, hence want_stderr.
            ok, out = _run(['taskkill', '/PID', str(pid), '/T', '/F'],
                           want_stderr=True)
            if not ok:
                print(f"⚠️  taskkill {pid}: {out}")
                if 'denied' in (out or '').lower():
                    denied = True
    else:
        _run(['pkill', '-f', script])

    # Did it actually die? Ports can take a moment to be released, so give
    # it a beat before believing the answer.
    time.sleep(0.5)
    _pid_cache.pop(script, None)
    _tracked.pop(script, None)

    survivors = _find_pids(script)
    if not survivors:
        return True, ''

    pid = survivors[0]
    hint = ("Open Task Manager (Ctrl-Shift-Esc), go to the Details tab, "
            f"find process {pid} and End task. Or run yobot-stop.bat as "
            "administrator.")

    if denied:
        return False, (f"Windows refused to stop {script} — access denied "
                       f"(process {pid}). {hint}")
    return False, (f"{script} is still running (process {pid}) after being "
                   f"asked to stop. {hint}")


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


def _timed(label):
    """Time a block and print it to the Launcher's console.

    Used on the start/stop routes so slowness can be measured instead of
    guessed at. Prints a line like:
        ⏱  stop: 0.8s   (find 0.3s, kill 0.5s)
    """
    class _T:
        def __enter__(self):
            self.t0 = time.time()
            return self

        def __exit__(self, *exc):
            print(f"⏱  {label}: {time.time() - self.t0:.1f}s")
            return False
    return _T()


def _stop_everything():
    """Stop whatever is running, on either platform.

    Returns a list of things that refused to stop — empty means all clear.
    Before 2026-08-12 this reported success no matter what happened, so a
    program that ignored the Stop button looked like it had stopped.
    """
    problems = []

    if USE_SYSTEMD:
        for s in GREETER_SERVICES:
            _run(['systemctl', '--user', 'stop', s])
        _run(['systemctl', '--user', 'stop', GUI_SERVICE])
        _run(['systemctl', '--user', 'stop', CALIBRATION_SERVICE])
    else:
        for script in (PROC_GREETER_BOT, PROC_GREETER_BRAIN,
                       PROC_GUI, PROC_CALIBRATION):
            ok, msg = _proc_stop(script)
            if not ok:
                problems.append(msg)

    return problems


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
        with _timed('greeter: stop others'):
            _proc_stop(PROC_GUI)
            _proc_stop(PROC_CALIBRATION)
        time.sleep(1)
        # Brain server first (the bot needs it), then the bot in its own
        # window. Wait for the brain to actually answer rather than sleeping
        # a fixed 2 seconds — usually much quicker, and more reliable on a
        # slow start.
        if not _proc_running(PROC_GREETER_BRAIN):
            _proc_start(PROC_GREETER_BRAIN)
            if not _wait_for_port(SCRIPT_PORTS[PROC_GREETER_BRAIN], 10):
                print("⚠️  Brain server didn't answer on port "
                      f"{SCRIPT_PORTS[PROC_GREETER_BRAIN]} — starting the bot anyway")
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
        with _timed('gui: stop others'):
            _proc_stop(PROC_GREETER_BOT)
            _proc_stop(PROC_GREETER_BRAIN)
            _proc_stop(PROC_CALIBRATION)
        time.sleep(1)
        with _timed('gui: start'):
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
        with _timed('calibration: start + wait for page'):
            _proc_start(PROC_CALIBRATION)
            # Return as soon as the page is actually serving, instead of
            # always sleeping 2s. The browser tab is already waiting.
            _wait_for_port(SCRIPT_PORTS[PROC_CALIBRATION], 15)

    return jsonify({'success': True, 'status': 'calibration'})


@app.route('/launcher/stop', methods=['POST'])
def stop_all():
    """Stop whichever service is currently running."""
    with _timed('stop all'):
        problems = _stop_everything()
    if problems:
        for p in problems:
            print(f"⚠️  Stop failed: {p}")
        return jsonify({'success': False,
                        'error': ' '.join(problems),
                        'status': _get_status()}), 500
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
        if HAVE_PSUTIL:
            print("      Finding programs: psutil")
        elif IS_WINDOWS:
            print("      Finding programs: PowerShell (slower)")
            print("      Tip: 'pip install psutil' makes this quicker.")
        else:
            print("      Finding programs: pgrep / pkill")
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
