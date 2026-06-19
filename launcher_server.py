#!/usr/bin/env python3
"""
Ohbot Launcher Server
Runs on port 5000 at boot and lets the user choose what to do:
  - Start the Greeter Bot (voice conversation mode)
  - Start the Sequence Builder GUI (web interface, port 5001)

Also provides Shut Down and Restart buttons for the Pi.

Started automatically by systemd (ohbot-launcher.service).
Runs as root so it can control other systemd services.
"""

from flask import Flask, jsonify, send_from_directory
import subprocess
import os
import threading
import time

app = Flask(__name__)

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
LAUNCHER_DIR = os.path.join(BASE_DIR, 'launcher')

# Systemd service names
GREETER_SERVICES = ['ohbot-server', 'ohbot-conversation']
GUI_SERVICE      = 'ohbot-gui'


# ── Helpers ────────────────────────────────────────────────────────────────

def _run(cmd):
    """Run a shell command. Returns (success, output)."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return result.returncode == 0, result.stdout.strip()
    except Exception as e:
        return False, str(e)

def _service_active(name):
    """Returns True if the named user systemd service is currently running."""
    _, out = _run(['systemctl', '--user', 'is-active', name])
    return out == 'active'

def _get_status():
    """
    Returns the current state:
      'greeter' — greeter bot is running
      'gui'     — sequence builder GUI is running
      'idle'    — nothing is running
    """
    if any(_service_active(s) for s in GREETER_SERVICES):
        return 'greeter'
    if _service_active(GUI_SERVICE):
        return 'gui'
    return 'idle'


# ── Routes ─────────────────────────────────────────────────────────────────

@app.route('/')
def serve_launcher():
    return send_from_directory(LAUNCHER_DIR, 'index.html')


@app.route('/launcher/status')
def get_status():
    """The page polls this every 2 seconds to know what's running."""
    return jsonify({'status': _get_status()})


@app.route('/launcher/start/greeter', methods=['POST'])
def start_greeter():
    """Stop GUI if running, then start the greeter bot services."""
    if _service_active(GUI_SERVICE):
        _run(['systemctl', '--user', 'stop', GUI_SERVICE])
        time.sleep(1)

    for s in GREETER_SERVICES:
        _run(['systemctl', '--user', 'start', s])

    return jsonify({'success': True, 'status': 'greeter'})


@app.route('/launcher/start/gui', methods=['POST'])
def start_gui():
    """Stop greeter if running, then start the GUI service."""
    for s in GREETER_SERVICES:
        if _service_active(s):
            _run(['systemctl', '--user', 'stop', s])
    time.sleep(1)

    _run(['systemctl', '--user', 'start', GUI_SERVICE])

    return jsonify({'success': True, 'status': 'gui'})


@app.route('/launcher/stop', methods=['POST'])
def stop_all():
    """Stop whichever service is currently running."""
    for s in GREETER_SERVICES:
        _run(['systemctl', '--user', 'stop', s])
    _run(['systemctl', '--user', 'stop', GUI_SERVICE])
    return jsonify({'success': True, 'status': 'idle'})


@app.route('/launcher/shutdown', methods=['POST'])
def shutdown_pi():
    """Shut the Pi down cleanly after a short delay."""
    def do_shutdown():
        time.sleep(3)
        subprocess.run(['sudo', 'shutdown', '-h', 'now'])
    threading.Thread(target=do_shutdown, daemon=True).start()
    return jsonify({'success': True})


@app.route('/launcher/restart', methods=['POST'])
def restart_pi():
    """Restart the Pi after a short delay."""
    def do_restart():
        time.sleep(3)
        subprocess.run(['sudo', 'reboot'])
    threading.Thread(target=do_restart, daemon=True).start()
    return jsonify({'success': True})


# ── Startup ────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=" * 50)
    print("🚀  Ohbot Launcher")
    print("=" * 50)
    print()
    print("Open in your browser:")
    print("   http://localhost:5000       (from the Pi)")

    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        print(f"   http://{ip}:5000      (from your laptop / Mac)")
    except Exception:
        print("   http://<pi-ip>:5000     (from your laptop / Mac)")

    print()
    print("Press Ctrl-C to stop.")
    print("=" * 50)
    print()

    app.run(host='0.0.0.0', port=5000, debug=False)
