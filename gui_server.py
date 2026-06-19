#!/usr/bin/env python3
"""
Ohbot GUI Server - Web interface for building and testing Ohbot sequences
Runs on port 5001 (separate from the main conversation server on port 5000)

Usage:
    python3 gui_server.py

Then open in your browser:
    http://<pi-ip-address>:5001/gui

IMPORTANT: Stop the main conversation bot before running this!
Both this server and ohbot_conversation.py use the same serial cable.
They cannot run at the same time.

To find the Pi's IP address:  hostname -I
"""

from flask import Flask, request, jsonify, send_from_directory
import asyncio
import json
import os
import time
import threading
from collections import deque
from openai import OpenAI

# Load .env file manually (no python-dotenv needed)
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _k, _v = _line.split('=', 1)
                os.environ.setdefault(_k.strip(), _v.strip())

# Import Ohbot hardware library
import ohbot_pi as ohbot

# Import Azure speech — also grab the shared serial lock so that sequence
# playback and lip-sync threads never call the serial port at the same time
# (simultaneous access causes a segmentation fault in the Ohbot C extension).
try:
    from ohbot_azure import (
        AzureSpeechManager,
        AsyncOhbotController as AzureController,
        OHBOT_SERIAL_LOCK,
    )
    _AZURE_AVAILABLE = True
except ImportError:
    _AZURE_AVAILABLE = False
    OHBOT_SERIAL_LOCK = threading.Lock()   # dummy lock when speech is disabled
    print("⚠️  ohbot_azure not found — speech disabled")

app = Flask(__name__)

# ── OpenAI (for GUI chat) ──────────────────────────────────────────────────
_openai_key    = os.environ.get("OPENAI_API_KEY")
_openai_client = OpenAI(api_key=_openai_key) if _openai_key else None
_chat_history  = deque(maxlen=20)   # last 10 exchanges

_PERSONALITIES = {
    'friendly': (
        "You are Ohbot, a friendly robot assistant. "
        "Keep responses brief — 1 to 3 sentences — since you speak them aloud. "
        "Be warm and conversational."
    ),
    'comedian': (
        "You are Ohbot, a robot comedian. "
        "Every response includes a pun, joke, or playful wordplay. "
        "Keep it short — 1 to 3 sentences — since you speak them aloud. "
        "You're funny but family-friendly."
    ),
    'pirate': (
        "You are Ohbot, a pirate robot. Arrr! "
        "Speak like a swashbuckling pirate — use pirate slang like 'arrr', 'matey', 'shiver me timbers'. "
        "Keep responses brief — 1 to 3 sentences — since you speak them aloud."
    ),
    'professor': (
        "You are Ohbot, a grumpy professor robot. "
        "You are brilliant but easily irritated by simple questions. "
        "If the user's message contains any grammatical errors, spelling mistakes, or poor sentence structure, "
        "you MUST point out and correct them first — with obvious irritation — before answering the actual question. "
        "Use phrases like 'It is WHOM, not WHO,' or 'One does not end a sentence with a preposition!' "
        "If the grammar is perfect, grudgingly acknowledge it before answering. "
        "Use academic language and exasperation throughout. "
        "Keep total response brief — 2 to 4 sentences — since you speak them aloud."
    ),
    'shy': (
        "You are Ohbot, a very shy and timid robot. "
        "You get flustered easily, speak softly, and often second-guess yourself. "
        "Use hesitant language like 'um', 'well', 'maybe'. "
        "Keep responses brief — 1 to 3 sentences — since you speak them aloud."
    ),
}

_current_personality = 'friendly'

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
SEQUENCES_DIR  = os.path.join(BASE_DIR, 'sequences')
GUI_DIR        = os.path.join(BASE_DIR, 'gui')

# Create sequences folder if it doesn't exist yet
os.makedirs(SEQUENCES_DIR, exist_ok=True)

# ── Motor info ─────────────────────────────────────────────────────────────
# Maps motor ID → display name, key name, and default (neutral) position
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

# Build a reverse lookup: key name → motor ID  (e.g. 'HEADTURN' → 1)
KEY_TO_ID = {v['key']: k for k, v in MOTORS.items()}

# Playback state (shared between endpoints and the background thread)
play_state  = {'playing': False, 'stop_requested': False}
speak_state = {'speaking': False, 'last_error': None}
demo_state  = {'running': False, 'stop_requested': False}

# ── Azure speech — persistent event loop in a background thread ────────────
_speech_loop       = None
_azure_controller  = None

def _run_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

def _init_azure():
    global _speech_loop, _azure_controller
    if not _AZURE_AVAILABLE:
        return
    try:
        azure_mgr        = AzureSpeechManager()
        _azure_controller = AzureController(azure_mgr)
        _speech_loop      = asyncio.new_event_loop()
        t = threading.Thread(target=_run_loop, args=(_speech_loop,), daemon=True)
        t.start()
        # Start the controller's motor queues inside that loop
        future = asyncio.run_coroutine_threadsafe(_azure_controller.start(), _speech_loop)
        future.result(timeout=5)
        print("✅ Azure speech ready")
    except Exception as e:
        print(f"⚠️  Azure speech init failed: {e}")
        _azure_controller = None


# ============================================================================
# SERVE THE GUI PAGE
# ============================================================================

@app.route('/')
def root_redirect():
    """Redirect root to /gui"""
    from flask import redirect
    return redirect('/gui')

@app.route('/gui')
@app.route('/gui/')
def serve_gui():
    return send_from_directory(GUI_DIR, 'index.html')


# ============================================================================
# STATUS
# ============================================================================

@app.route('/gui/status')
def gui_status():
    """Returns connection status and whether a sequence is playing"""
    return jsonify({
        'success':         True,
        'ohbot_connected': ohbot.connected,
        'playing':         play_state['playing'],
        'speaking':        speak_state['speaking'],
        'speak_error':     speak_state['last_error'],
        'demo_running':    demo_state['running'],
    })

@app.route('/gui/motors/info')
def motor_info():
    """Returns motor names and defaults so the page can build itself"""
    return jsonify({'success': True, 'motors': MOTORS})


# ============================================================================
# ROBOT CONTROL
# ============================================================================

@app.route('/gui/motor', methods=['POST'])
def move_motor():
    """
    Move a single motor.
    Body: { "motor": 1, "position": 7, "speed": 5 }
    """
    try:
        data     = request.get_json()
        motor_id = int(data['motor'])
        position = float(data['position'])
        speed    = int(data.get('speed', 5))

        with OHBOT_SERIAL_LOCK:
            ohbot.move(motor_id, position, speed)
        return jsonify({'success': True})

    except Exception as e:
        print(f"❌ Motor move error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/gui/led', methods=['POST'])
def set_led():
    """
    Set LED eye colour.
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
        print(f"❌ LED error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/gui/reset', methods=['POST'])
def reset_robot():
    """Reset all motors to neutral and turn off LEDs"""
    try:
        with OHBOT_SERIAL_LOCK:
            ohbot.reset()
        return jsonify({'success': True})
    except Exception as e:
        print(f"❌ Reset error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/gui/frame', methods=['POST'])
def go_to_frame():
    """
    Jump directly to a saved keyframe pose (preview without playing the
    whole sequence).
    Body: { "motors": {"HEADTURN": 7, ...}, "led": {"r":0,"g":5,"b":10} }
    """
    try:
        data   = request.get_json()
        motors = data.get('motors', {})
        led    = data.get('led', None)

        for key, position in motors.items():
            motor_id = KEY_TO_ID.get(key)
            if motor_id is not None:
                with OHBOT_SERIAL_LOCK:
                    ohbot.move(motor_id, float(position), 5)

        if led:
            with OHBOT_SERIAL_LOCK:
                ohbot.baseColour(
                    float(led.get('r', 0)),
                    float(led.get('g', 0)),
                    float(led.get('b', 0)),
                )

        return jsonify({'success': True})

    except Exception as e:
        print(f"❌ Frame preview error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# SPEECH
# ============================================================================

@app.route('/gui/speak', methods=['POST'])
def speak_now():
    """
    Make Ohbot say something with lip sync.
    Body: { "text": "Hello there!" }
    Runs in a background thread so the call returns immediately.
    """
    try:
        data = request.get_json()
        text = data.get('text', '').strip()

        if not text:
            return jsonify({'success': False, 'error': 'No text provided'}), 400

        if speak_state['speaking']:
            return jsonify({'success': False, 'error': 'Already speaking'}), 409

        if _azure_controller is None or _speech_loop is None:
            return jsonify({'success': False, 'error': 'Azure speech not available'}), 503

        def run_speech():
            speak_state['speaking']   = True
            speak_state['last_error'] = None
            try:
                future = asyncio.run_coroutine_threadsafe(
                    _azure_controller.say(text), _speech_loop
                )
                future.result(timeout=30)
            except Exception as e:
                err = str(e)
                print(f"❌ Speech error: {err}")
                speak_state['last_error'] = err
            finally:
                speak_state['speaking'] = False

        threading.Thread(target=run_speech, daemon=True).start()
        return jsonify({'success': True})

    except Exception as e:
        print(f"❌ Speak endpoint error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# LLM CHAT
# ============================================================================

@app.route('/gui/chat', methods=['POST'])
def gui_chat():
    """
    Send a message to OpenAI and get Ohbot's response.
    Body:    { "message": "hello there" }
    Returns: { "success": true, "response": "Hi! How can I help?" }
    """
    if not _openai_client:
        return jsonify({'success': False,
                        'error': 'No OpenAI API key — check your .env file'}), 503
    try:
        data    = request.get_json()
        message = data.get('message', '').strip()

        if not message:
            return jsonify({'success': False, 'error': 'No message provided'}), 400

        messages = [{"role": "system", "content": _PERSONALITIES[_current_personality]}]
        messages.extend(_chat_history)
        messages.append({"role": "user", "content": message})

        response = _openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=150,
            temperature=0.7
        )

        reply = response.choices[0].message.content.strip()

        _chat_history.append({"role": "user",     "content": message})
        _chat_history.append({"role": "assistant", "content": reply})

        print(f"💬 Chat: {message!r} → {reply!r}")
        return jsonify({'success': True, 'response': reply})

    except Exception as e:
        print(f"❌ GUI chat error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/gui/chat/reset', methods=['POST'])
def gui_chat_reset():
    """Clear the GUI chat conversation history."""
    _chat_history.clear()
    print("🔄 GUI chat history cleared")
    return jsonify({'success': True})


# ============================================================================
# MIC INPUT — server-side speech recognition via Azure
# ============================================================================

@app.route('/gui/mic/listen', methods=['POST'])
def mic_listen():
    """Listen on the Pi's USB mic for one utterance and return the transcript."""
    if _azure_controller is None or _speech_loop is None:
        return jsonify({'success': False, 'error': 'Azure speech not available'}), 503

    result = {}

    def run_recognition():
        try:
            future = asyncio.run_coroutine_threadsafe(
                _azure_controller.listen(timeout=10.0),
                _speech_loop
            )
            text = future.result(timeout=15)
            result['text'] = text or ''
            result['success'] = bool(text)
        except Exception as e:
            result['success'] = False
            result['error'] = str(e)

    t = threading.Thread(target=run_recognition, daemon=True)
    t.start()
    t.join(timeout=16)

    if 'success' not in result:
        return jsonify({'success': False, 'error': 'Recognition timed out'}), 504

    return jsonify(result)


# ============================================================================
# EMOTION PRESETS
# ============================================================================

# Motor positions and LED colour for each emotion.
# Both lips always move in the same direction to avoid physical jamming.
_EMOTIONS = {
    'happy': {
        'motors': {
            'HEADNOD': 6, 'HEADTURN': 5, 'EYETURN': 5,
            'LIDBLINK': 10, 'TOPLIP': 6, 'BOTTOMLIP': 7,
            'EYETILT': 6, 'HEADROLL': 5,
        },
        'led': {'r': 10, 'g': 7, 'b': 0},   # warm yellow-orange
    },
    'sad': {
        'motors': {
            'HEADNOD': 3, 'HEADTURN': 5, 'EYETURN': 5,
            'LIDBLINK': 4, 'TOPLIP': 4, 'BOTTOMLIP': 4,
            'EYETILT': 3, 'HEADROLL': 4,
        },
        'led': {'r': 0, 'g': 0, 'b': 10},   # blue
    },
    'surprised': {
        'motors': {
            'HEADNOD': 8, 'HEADTURN': 5, 'EYETURN': 5,
            'LIDBLINK': 10, 'TOPLIP': 7, 'BOTTOMLIP': 8,
            'EYETILT': 7, 'HEADROLL': 5,
        },
        'led': {'r': 10, 'g': 10, 'b': 10}, # bright white
    },
    'thinking': {
        'motors': {
            'HEADNOD': 6, 'HEADTURN': 4, 'EYETURN': 3,
            'LIDBLINK': 8, 'TOPLIP': 5, 'BOTTOMLIP': 5,
            'EYETILT': 7, 'HEADROLL': 3,
        },
        'led': {'r': 0, 'g': 6, 'b': 10},   # cyan
    },
    'sleeping': {
        'motors': {
            'HEADNOD': 2, 'HEADTURN': 5, 'EYETURN': 5,
            'LIDBLINK': 0, 'TOPLIP': 6, 'BOTTOMLIP': 6,
            'EYETILT': 5, 'HEADROLL': 4,
        },
        'led': {'r': 0, 'g': 0, 'b': 2},    # nearly off, dim blue
    },
}


@app.route('/gui/emotion', methods=['POST'])
def set_emotion():
    """
    Move Ohbot to an emotion preset pose.
    Body: { "emotion": "happy" }
    Valid values: happy, sad, surprised, thinking, sleeping
    """
    try:
        data    = request.get_json()
        emotion = data.get('emotion', '').lower()

        if emotion not in _EMOTIONS:
            return jsonify({'success': False,
                            'error': f'Unknown emotion: {emotion}'}), 400

        preset = _EMOTIONS[emotion]

        for key, position in preset['motors'].items():
            motor_id = KEY_TO_ID.get(key)
            if motor_id is not None:
                with OHBOT_SERIAL_LOCK:
                    ohbot.move(motor_id, float(position), 5)

        led = preset['led']
        with OHBOT_SERIAL_LOCK:
            ohbot.baseColour(float(led['r']), float(led['g']), float(led['b']))

        print(f"🎭 Emotion: {emotion}")
        return jsonify({'success': True, 'emotion': emotion})

    except Exception as e:
        print(f"❌ Emotion error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/gui/chat/personality', methods=['POST'])
def set_personality():
    """
    Swap Ohbot's chat personality.
    Body: { "personality": "pirate" }
    Valid values: friendly, comedian, pirate, professor, shy
    Also clears chat history so the new personality starts fresh.
    """
    global _current_personality
    data        = request.get_json()
    personality = data.get('personality', 'friendly')
    if personality not in _PERSONALITIES:
        return jsonify({'success': False, 'error': f'Unknown personality: {personality}'}), 400
    _current_personality = personality
    _chat_history.clear()
    print(f"🎭 Personality set to: {personality}")
    return jsonify({'success': True, 'personality': personality})


# ============================================================================
# DEMO MODE
# ============================================================================

@app.route('/gui/demo', methods=['POST'])
def start_demo():
    if demo_state['running']:
        return jsonify({'success': False, 'error': 'Demo already running'}), 409
    if play_state['playing']:
        return jsonify({'success': False, 'error': 'A sequence is playing'}), 409

    def _say(text):
        if demo_state['stop_requested']: return
        if _azure_controller and _speech_loop:
            speak_state['speaking'] = True
            try:
                future = asyncio.run_coroutine_threadsafe(_azure_controller.say(text), _speech_loop)
                future.result(timeout=30)
            except Exception as e:
                print(f"Demo speech error: {e}")
            finally:
                speak_state['speaking'] = False

    def _wait(seconds):
        end = time.time() + seconds
        while time.time() < end:
            if demo_state['stop_requested']: return
            time.sleep(0.05)

    def run_demo():
        demo_state['running'] = True
        demo_state['stop_requested'] = False
        def stopped(): return demo_state['stop_requested']
        try:
            with OHBOT_SERIAL_LOCK: ohbot.reset()
            with OHBOT_SERIAL_LOCK: ohbot.baseColour(0,0,10)
            _wait(0.6)
            if stopped(): return
            _say("Hi there! I am Ohbot, a friendly robot. Let me show you what I can do!")
            _wait(0.3)
            if stopped(): return
            _say("First, I can nod my head.")
            with OHBOT_SERIAL_LOCK: ohbot.move(0,8,3)
            _wait(0.5)
            with OHBOT_SERIAL_LOCK: ohbot.move(0,2,3)
            _wait(0.5)
            with OHBOT_SERIAL_LOCK: ohbot.move(0,5,5)
            if stopped(): return
            _say("I can also turn from side to side!")
            with OHBOT_SERIAL_LOCK: ohbot.move(1,2,3)
            _wait(0.5)
            with OHBOT_SERIAL_LOCK: ohbot.move(1,8,3)
            _wait(0.5)
            with OHBOT_SERIAL_LOCK: ohbot.move(1,5,5)
            if stopped(): return
            with OHBOT_SERIAL_LOCK: ohbot.baseColour(0,10,0)
            _say("My eyes can look around independently!")
            with OHBOT_SERIAL_LOCK: ohbot.move(2,2,5)
            _wait(0.4)
            with OHBOT_SERIAL_LOCK: ohbot.move(2,8,5)
            _wait(0.4)
            with OHBOT_SERIAL_LOCK: ohbot.move(2,5,5)
            if stopped(): return
            with OHBOT_SERIAL_LOCK: ohbot.baseColour(0,6,10)
            _say("And I can blink!")
            with OHBOT_SERIAL_LOCK: ohbot.move(3,0,8)
            _wait(0.25)
            with OHBOT_SERIAL_LOCK: ohbot.move(3,10,8)
            _wait(0.2)
            with OHBOT_SERIAL_LOCK: ohbot.move(3,0,8)
            _wait(0.25)
            with OHBOT_SERIAL_LOCK: ohbot.move(3,10,8)
            if stopped(): return
            _say("Check out my eye colors!")
            for r,g,b in [(10,0,0),(10,5,0),(10,10,0),(0,10,0),(0,0,10),(10,0,10),(0,10,10),(10,10,10)]:
                if stopped(): return
                with OHBOT_SERIAL_LOCK: ohbot.baseColour(r,g,b)
                _wait(0.35)
            if stopped(): return
            with OHBOT_SERIAL_LOCK: ohbot.baseColour(10,5,0)
            with OHBOT_SERIAL_LOCK: ohbot.move(0,7,5)
            _say("Want to hear a joke?")
            _wait(0.4)
            with OHBOT_SERIAL_LOCK: ohbot.move(0,5,5)
            _say("Why don't scientists trust atoms?")
            _wait(0.5)
            _say("Because they make up everything!")
            _wait(0.3)
            if stopped(): return
            with OHBOT_SERIAL_LOCK: ohbot.baseColour(0,0,10)
            with OHBOT_SERIAL_LOCK: ohbot.move(0,8,4)
            _wait(0.3)
            with OHBOT_SERIAL_LOCK: ohbot.move(0,5,5)
            _say("Thanks for watching! Feel free to explore the controls, or chat with me below!")
        finally:
            _wait(0.5)
            with OHBOT_SERIAL_LOCK: ohbot.reset()
            with OHBOT_SERIAL_LOCK: ohbot.baseColour(0,0,0)
            demo_state['running'] = False
            print("Demo finished")

    threading.Thread(target=run_demo, daemon=True).start()
    return jsonify({'success': True, 'message': 'Demo started'})


@app.route('/gui/demo/stop', methods=['POST'])
def stop_demo():
    demo_state['stop_requested'] = True
    return jsonify({'success': True})

# ============================================================================
# SEQUENCE PLAYBACK
# ============================================================================

@app.route('/gui/sequence/play', methods=['POST'])
def play_sequence():
    """
    Play a sequence on the robot.
    Body: { "keyframes": [ { "time": 0, "motors": {...}, "led": {...} }, ... ] }
    Playback runs in a background thread so this call returns immediately.
    """
    try:
        data      = request.get_json()
        keyframes = data.get('keyframes', [])

        if not keyframes:
            return jsonify({'success': False, 'error': 'No keyframes to play'}), 400

        if play_state['playing']:
            return jsonify({'success': False, 'error': 'Already playing'}), 409

        def run_playback():
            play_state['playing']        = True
            play_state['stop_requested'] = False

            try:
                sorted_frames = sorted(keyframes, key=lambda k: float(k.get('time', 0)))
                start_time    = time.time()

                for frame in sorted_frames:
                    if play_state['stop_requested']:
                        break

                    target_time = float(frame.get('time', 0))

                    # Wait until the right moment in the timeline
                    while True:
                        if play_state['stop_requested']:
                            break
                        elapsed = time.time() - start_time
                        if elapsed >= target_time:
                            break
                        time.sleep(0.01)

                    if play_state['stop_requested']:
                        break

                    # Move motors — skip lips if speech is active so lip sync isn't overridden.
                    # OHBOT_SERIAL_LOCK prevents a race with the lip-sync thread that runs
                    # inside the Azure controller — simultaneous serial access = segfault.
                    for key, position in frame.get('motors', {}).items():
                        if speak_state['speaking'] and key in ('TOPLIP', 'BOTTOMLIP'):
                            continue
                        motor_id = KEY_TO_ID.get(key)
                        if motor_id is not None:
                            with OHBOT_SERIAL_LOCK:
                                ohbot.move(motor_id, float(position), 5)

                    # Set LED
                    if 'led' in frame:
                        led = frame['led']
                        with OHBOT_SERIAL_LOCK:
                            ohbot.baseColour(
                                float(led.get('r', 0)),
                                float(led.get('g', 0)),
                                float(led.get('b', 0)),
                            )

                    # Trigger speech if this keyframe has text
                    speech_text = frame.get('text', '').strip()
                    if speech_text and _azure_controller and _speech_loop:
                        speak_state['speaking'] = True   # set before thread starts to protect lips immediately
                        def say_it(t):
                            try:
                                future = asyncio.run_coroutine_threadsafe(
                                    _azure_controller.say(t), _speech_loop
                                )
                                future.result(timeout=30)
                            except Exception as se:
                                print(f"❌ Keyframe speech error: {se}")
                            finally:
                                speak_state['speaking'] = False
                        threading.Thread(target=say_it, args=(speech_text,), daemon=True).start()

                    print(f"▶ Frame at {target_time:.1f}s — "
                          f"{list(frame.get('motors', {}).keys())}")

            finally:
                play_state['playing'] = False
                print("✅ Playback finished")

        threading.Thread(target=run_playback, daemon=True).start()
        return jsonify({'success': True, 'message': 'Playback started'})

    except Exception as e:
        print(f"❌ Playback error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/gui/sequence/stop', methods=['POST'])
def stop_sequence():
    """Stop the currently playing sequence"""
    play_state['stop_requested'] = True
    return jsonify({'success': True})


# ============================================================================
# SEQUENCE SAVE / LOAD / DELETE
# ============================================================================

def _safe_filename(name):
    """Turn a sequence name into a safe filename"""
    safe = "".join(c for c in name if c.isalnum() or c in ('_', '-', ' ')).strip()
    return safe.replace(' ', '_')


@app.route('/gui/sequence/save', methods=['POST'])
def save_sequence():
    """
    Save a sequence to disk.
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

        print(f"💾 Saved: {filename} ({len(sequence['keyframes'])} keyframes)")
        return jsonify({'success': True, 'filename': filename})

    except Exception as e:
        print(f"❌ Save error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/gui/sequence/list')
def list_sequences():
    """Return a list of all saved sequences"""
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
                pass  # Skip malformed files

        return jsonify({'success': True, 'sequences': sequences})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/gui/sequence/<filename>')
def load_sequence(filename):
    """Load a single sequence by filename"""
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


@app.route('/gui/sequence/<filename>', methods=['DELETE'])
def delete_sequence(filename):
    """Delete a sequence file"""
    try:
        if not filename.endswith('.json'):
            filename += '.json'

        filepath = os.path.join(SEQUENCES_DIR, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            print(f"🗑️  Deleted: {filename}")

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# STARTUP
# ============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("🎛️   Ohbot Sequence Builder — GUI Server")
    print("=" * 60)
    print()
    print("⚠️  IMPORTANT: Make sure the conversation bot is NOT running.")
    print("   Both use the same USB serial cable and will conflict.")
    print("   Stop it with:  sudo systemctl stop ohbot-conversation")
    print("   (or Ctrl-C in the tmux window where it's running)")
    print()

    # Connect to Azure speech
    print("🔊 Initializing Azure speech...")
    _init_azure()

    # Connect to Ohbot hardware
    print("🔌 Connecting to Ohbot hardware...")
    if ohbot.init():
        print(f"✅ Ohbot connected on {ohbot.port}")
        with OHBOT_SERIAL_LOCK:
            ohbot.reset()
        print("✅ Motors reset to neutral")
    else:
        print("⚠️  Ohbot hardware not found.")
        print("   The GUI will still open but sliders won't move the robot.")
        print("   This is fine if you just want to design sequences.")

    print()
    print("🌐 Open the GUI in your browser:")
    print("   http://localhost:5001/gui        (from the Pi)")

    # Try to show the Pi's IP address
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        print(f"   http://{ip}:5001/gui          (from your laptop / Mac)")
    except Exception:
        print("   http://<pi-ip>:5001/gui        (from your laptop / Mac)")

    print()
    print("Press Ctrl-C to stop.")
    print("=" * 60)
    print()

    app.run(host='0.0.0.0', port=5001, debug=False)
