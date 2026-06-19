#!/usr/bin/env python3
"""
Ohbot Async Conversation Bot
Version: 2.0.0

A fully async conversation controller for the Ohbot robot head.
Listens for speech, classifies intent, and responds with voice + animation.

Features:
  - Continuous conversation loop — runs until Ctrl-C or power-off
  - Sleep / wake states — Ohbot sleeps after SILENCE_TIMEOUT seconds of
    no input, and wakes on a GPIO button press (or voice, if enabled)
  - GPIO wake button — GPIO pin 17 (BCM), falls back gracefully if unavailable
  - Idle animations — head turns, eye movement, random blinks
  - Language detection — detects English or Spanish from the visitor's speech
  - Bilingual voice — JennyMultilingualNeural handles both naturally
  - Conversation context reset between sessions

Architecture:
  - ohbotchat_server.py must be running (handles OpenAI calls)
  - AZURE_SPEECH_KEY, AZURE_SPEECH_REGION, OPENAI_API_KEY must be set in .env
"""

import asyncio
import json
import os
import random
import sys
import time
from typing import Optional

# ── path ─────────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── core imports ──────────────────────────────────────────────────────────────
try:
    from ohbot_azure import AsyncOhbotController, AzureSpeechManager
except ImportError:
    print("❌ Could not import from ohbot_azure.py")
    sys.exit(1)

try:
    import ohbot_pi as ohbot
except ImportError:
    print("❌ ohbot_pi module not found")
    sys.exit(1)

try:
    import httpx
except ImportError:
    print("❌ httpx not found — install with: pip install httpx")
    sys.exit(1)

# ── GPIO (optional — degrades gracefully on non-Pi hardware) ─────────────────
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    print("⚠️  RPi.GPIO not available — GPIO wake button disabled")

# ── audio constants ───────────────────────────────────────────────────────────
CHIME_FILE  = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "thinking_chime.wav")
PHRASES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "phrases")
AUDIO_DEVICE = "plug:default"   # same device as speech

# ── LED colour constants ──────────────────────────────────────────────────────
COLOR_GREEN   = (0, 10, 0)    # Ready / idle
COLOR_ORANGE  = (10, 5, 0)    # Listening
COLOR_BLUE    = (5, 5, 10)    # Thinking
COLOR_CYAN    = (0, 10, 5)    # Speaking
COLOR_RED     = (10, 0, 0)    # Error
COLOR_PURPLE  = (10, 0, 10)   # Goodbye / sleep
COLOR_DIM     = (1, 1, 1)     # Sleeping
COLOR_OFF     = (0, 0, 0)     # Off

# ── tuning constants ──────────────────────────────────────────────────────────
SILENCE_TIMEOUT    = 12.0   # seconds to wait before counting a missed turn
MISSED_TURNS_SLEEP = 2      # consecutive missed turns before sleep
SLEEP_LISTEN_SECS  = 5.0   # listen window while sleeping (longer = better pickup)
GPIO_WAKE_PIN      = 17    # BCM pin number for the wake button

# Set to False to use GPIO button only — eliminates all Azure STT cost while sleeping.
# Set to True to also allow voice wake words ("Ohbot", "wake up").
VOICE_WAKE_ENABLED = False

# Azure voice — Jenny Multilingual handles both English and Spanish
VOICE = "en-US-JennyMultilingualNeural"

# ─────────────────────────────────────────────────────────────────────────────
# ASYNC CONVERSATION CLASS
# ─────────────────────────────────────────────────────────────────────────────

class AsyncOhbotConversation:
    """
    Fully async conversation controller.

    Session lifecycle:
      SLEEPING → (button press or voice) → GREETING → ACTIVE → SLEEPING
                                                          ↑__________|
                                                     (new question)

    Language is detected from the visitor's first utterance and held for
    the entire session.
    """

    def __init__(self, controller: AsyncOhbotController,
                 azure_manager: AzureSpeechManager):
        self.controller = controller
        self.azure = azure_manager

        self.server_url = os.environ.get("OHBOT_SERVER_URL", "http://localhost:5002")
        self.http_client = httpx.AsyncClient(timeout=15.0)
        self.knowledge = self._load_knowledge()

        # Set voice once — Jenny Multilingual handles both languages
        self._init_voice()

        # Per-session state
        self.session_language = "en"   # detected from first visitor utterance
        self.missed_turns = 0          # consecutive empty listens
        self._last_topic  = None       # topic from last local knowledge lookup
        self.is_sleeping = False

    # ── knowledge base ────────────────────────────────────────────────────────

    def _load_knowledge(self) -> dict:
        kfile = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "knowledge.json")
        try:
            with open(kfile, "r", encoding="utf-8") as f:
                data = json.load(f)
            data.pop("_instructions", None)
            print(f"✅ Loaded {len(data)} knowledge topics")
            return data
        except FileNotFoundError:
            print("⚠️  knowledge.json not found — instant answers disabled")
            return {}
        except json.JSONDecodeError as e:
            print(f"⚠️  Error reading knowledge.json: {e}")
            return {}

    def lookup_knowledge(self, topic: str, language: str = "en") -> str:
        entry = self.knowledge.get(topic)
        if not entry:
            return ""
        if language == "es":
            return entry.get("answer_es", entry.get("answer_en", ""))
        return entry.get("answer_en", "")

    async def close(self):
        await self.http_client.aclose()

    # ── LED helpers ───────────────────────────────────────────────────────────

    async def set_color(self, color: tuple):
        await self.controller.set_eye_color(*color)

    # ── TTS voice ─────────────────────────────────────────────────────────────

    def _init_voice(self):
        """Set the TTS voice — Jenny Multilingual handles English and Spanish."""
        self.azure.set_voice(VOICE)

    # ── Flask server helpers ──────────────────────────────────────────────────

    async def check_server(self) -> bool:
        try:
            r = await self.http_client.get(f"{self.server_url}/health")
            if r.status_code == 200:
                print("✅ Flask server is running")
                return True
        except Exception:
            pass
        print("❌ Flask server not reachable")
        return False

    async def detect_intent(self, message: str) -> dict:
        try:
            r = await self.http_client.post(
                f"{self.server_url}/intent", json={"message": message})
            data = r.json()
            if data.get("success"):
                return {
                    "intent":   data.get("intent", "general_chat"),
                    "topic":    data.get("topic"),
                    "language": data.get("language", "en"),
                }
        except Exception as e:
            print(f"⚠️  Intent detection failed: {e}")
        return {"intent": "general_chat", "topic": None, "language": "en"}

    async def send_to_openai(self, message: str) -> tuple:
        try:
            r = await self.http_client.post(
                f"{self.server_url}/chat", json={"message": message})
            data = r.json()
            if data.get("success"):
                return data["response"], True
            return data.get("error", "Unknown error"), False
        except httpx.TimeoutException:
            return "Network issues", False
        except httpx.ConnectError:
            return "Network issues", False
        except Exception as e:
            print(f"❌ OpenAI error: {e}")
            return "OpenAI API failed", False

    async def reset_conversation(self):
        try:
            await self.http_client.post(f"{self.server_url}/reset")
            print("🔄 Conversation history reset")
        except Exception:
            pass

    # ── main intent handler ───────────────────────────────────────────────────

    async def handle_visitor_input(self, user_text: str) -> tuple:
        """Route visitor input to local knowledge base or GPT."""
        intent_result = await self.detect_intent(user_text)
        intent   = intent_result["intent"]
        topic    = intent_result["topic"]
        language = intent_result["language"]

        # Update session language from first real utterance
        if language and language != self.session_language:
            print(f"🌐 Language detected: {language}")
            self.session_language = language

        if intent == "local_knowledge" and topic:
            print(f"📖 Local knowledge: topic='{topic}', lang='{language}'")
            self._last_topic = topic
            answer = self.lookup_knowledge(topic, language)
            if answer:
                return answer, True
            # Topic not in knowledge.json — fall through to GPT
            self._last_topic = None
            return await self.send_to_openai(user_text)

        else:
            self._last_topic = None
            print("💬 General chat path")
            return await self.send_to_openai(user_text)

    # ── idle animation ────────────────────────────────────────────────────────

    async def idle_animation(self, cancel_event: asyncio.Event):
        """
        Lifelike idle movements while waiting for speech input.

        Pattern:
          1. Eyes dart to a random position
          2. Head catches up to match
          3. Eyes return to centre
          4. Random pause before next look
        Blinks run on a separate independent timer.

        Motor direction notes:
          HEADTURN / EYETURN : 3=right, 7=left, 5=centre
          HEADNOD  / EYETILT : 3=down,  7=up,   5=centre
        """
        MAX_BLINK_WAIT = 5.0

        try:
            next_blink = time.time() + random.uniform(1.0, MAX_BLINK_WAIT)

            while not cancel_event.is_set():

                eye_turn = random.uniform(3.0, 7.0)
                eye_tilt = random.uniform(3.0, 7.0)
                await self.controller.move(ohbot.EYETURN, eye_turn, 10)
                await self.controller.move(ohbot.EYETILT, eye_tilt, 10)

                for _ in range(5):
                    if cancel_event.is_set():
                        break
                    await asyncio.sleep(0.1)
                if cancel_event.is_set():
                    break

                await self.controller.move(ohbot.HEADTURN, eye_turn, 2)
                await self.controller.move(ohbot.HEADNOD,  eye_tilt, 2)
                await self.controller.move(ohbot.EYETURN, 5, 10)
                await self.controller.move(ohbot.EYETILT, 5, 10)

                now = time.time()
                if now >= next_blink:
                    await self.controller.move(ohbot.LIDBLINK, 0, 10)
                    await asyncio.sleep(0.3)
                    await self.controller.move(ohbot.LIDBLINK, 10, 10)
                    next_blink = time.time() + random.uniform(0.5, MAX_BLINK_WAIT)

                pause = random.uniform(0.0, 2.0)
                elapsed = 0.0
                while elapsed < pause and not cancel_event.is_set():
                    await asyncio.sleep(0.1)
                    elapsed += 0.1

        except asyncio.CancelledError:
            pass
        finally:
            await self.controller.move(ohbot.HEADTURN, 5, 2)
            await self.controller.move(ohbot.HEADNOD,  5, 2)
            await self.controller.move(ohbot.EYETURN,  5, 5)
            await self.controller.move(ohbot.EYETILT,  5, 5)

    # ── sleep animation ───────────────────────────────────────────────────────

    async def sleep_animation(self, cancel_event: asyncio.Event):
        """Sleeping pose — lids closed, head drooped, eyes dimmed."""
        try:
            await self.set_color(COLOR_DIM)
            await self.controller.move(ohbot.LIDBLINK, 0, 5)
            await self.controller.move(ohbot.HEADNOD,  2, 1)
            await self.controller.move(ohbot.HEADTURN, 5, 1)
            await self.controller.move(ohbot.EYETURN,  5, 5)
            await self.controller.move(ohbot.EYETILT,  5, 5)

            while not cancel_event.is_set():
                await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            pass
        finally:
            await self.controller.move(ohbot.HEADNOD, 5, 2)
            await self.controller.move(ohbot.HEADTURN, 5, 2)

    # ── thinking chime ────────────────────────────────────────────────────────

    async def play_thinking_chime(self, stop_event: asyncio.Event,
                                   delay: float = 2.0):
        """
        Loop the thinking chime until stop_event is set.
        Waits 'delay' seconds first — if the response arrives before then,
        no chime plays at all (avoids chimes on fast local-knowledge lookups).
        """
        if not os.path.exists(CHIME_FILE):
            await stop_event.wait()
            return

        try:
            elapsed = 0.0
            while elapsed < delay and not stop_event.is_set():
                await asyncio.sleep(0.1)
                elapsed += 0.1

            if stop_event.is_set():
                return

            while not stop_event.is_set():
                proc = await asyncio.create_subprocess_exec(
                    'aplay', '-D', AUDIO_DEVICE, CHIME_FILE,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL
                )
                done, _ = await asyncio.wait(
                    [
                        asyncio.create_task(proc.wait()),
                        asyncio.create_task(stop_event.wait()),
                    ],
                    return_when=asyncio.FIRST_COMPLETED
                )
                if stop_event.is_set():
                    try:
                        proc.terminate()
                        await proc.wait()
                    except Exception:
                        pass
                    break
        except asyncio.CancelledError:
            pass

    # ── pre-recorded phrase playback ──────────────────────────────────────────

    def _phrase_paths(self, key: str):
        """Return (wav_path, json_path) for a phrase key, or (None, None)."""
        wav = os.path.join(PHRASES_DIR, f"{key}.wav")
        jsn = os.path.join(PHRASES_DIR, f"{key}.json")
        if os.path.exists(wav) and os.path.exists(jsn):
            return wav, jsn
        return None, None

    async def play_phrase(self, key: str) -> bool:
        """
        Play a pre-recorded phrase WAV with lip sync from its JSON sidecar.
        Returns True if found and played, False if not found.
        """
        wav, jsn = self._phrase_paths(key)
        if not wav:
            return False

        with open(jsn, "r", encoding="utf-8") as f:
            visemes = json.load(f)

        print(f"🎵 Playing phrase: {key}")

        async with self.controller.speech_lock:
            self.controller.is_speaking = True
            try:
                lip_task = asyncio.create_task(
                    self.controller._animate_lips_with_visemes(wav, visemes)
                )
                await self.controller._play_audio_async(wav)
                await lip_task
            finally:
                self.controller.is_speaking = False
                await self.controller.move(ohbot.TOPLIP,    5, 10)
                await self.controller.move(ohbot.BOTTOMLIP, 5, 10)

        return True

    async def speak_phrase_or_synthesise(self, key: str, fallback_text: str):
        """
        Try to play a pre-recorded phrase. If not found, synthesise live.
        Speaking animations (blinks, head, eyes) run in both cases.
        """
        wav, _ = self._phrase_paths(key)

        stop = asyncio.Event()
        anim_tasks = [
            asyncio.create_task(self._speak_blink(stop)),
            asyncio.create_task(self._speak_headturn(stop)),
            asyncio.create_task(self._speak_headnod(stop)),
            asyncio.create_task(self._speak_eyes(stop)),
        ]

        if wav:
            await self.play_phrase(key)
        else:
            print(f"⚠️  Phrase '{key}' not found — synthesising live")
            await self.controller.say(fallback_text)

        stop.set()
        await asyncio.gather(*anim_tasks, return_exceptions=True)

    # ── speaking animations ───────────────────────────────────────────────────

    async def _speak_blink(self, stop: asyncio.Event):
        """Random blinks while speaking."""
        try:
            await asyncio.sleep(random.uniform(0.5, 1.5))
            while not stop.is_set():
                await self.controller.move(ohbot.LIDBLINK, 0, 10)
                await asyncio.sleep(0.15)
                await self.controller.move(ohbot.LIDBLINK, 10, 10)
                wait = random.uniform(2.0, 5.0)
                elapsed = 0.0
                while elapsed < wait and not stop.is_set():
                    await asyncio.sleep(0.1)
                    elapsed += 0.1
        except asyncio.CancelledError:
            pass

    async def _speak_headturn(self, stop: asyncio.Event):
        """Gentle side-to-side head turns while speaking."""
        try:
            await asyncio.sleep(random.uniform(0.3, 1.0))
            while not stop.is_set():
                target = random.uniform(4.0, 6.0)
                await self.controller.move(ohbot.HEADTURN, target, 2)
                wait = random.uniform(1.0, 2.5)
                elapsed = 0.0
                while elapsed < wait and not stop.is_set():
                    await asyncio.sleep(0.1)
                    elapsed += 0.1
        except asyncio.CancelledError:
            pass
        finally:
            await self.controller.move(ohbot.HEADTURN, 5, 2)

    async def _speak_headnod(self, stop: asyncio.Event):
        """Gentle nods while speaking."""
        try:
            while not stop.is_set():
                await self.controller.move(ohbot.HEADNOD, 5.5, 2)
                wait = random.uniform(0.4, 0.7)
                elapsed = 0.0
                while elapsed < wait and not stop.is_set():
                    await asyncio.sleep(0.1)
                    elapsed += 0.1
                if stop.is_set():
                    break
                await self.controller.move(ohbot.HEADNOD, 4.5, 2)
                wait = random.uniform(0.4, 0.7)
                elapsed = 0.0
                while elapsed < wait and not stop.is_set():
                    await asyncio.sleep(0.1)
                    elapsed += 0.1
        except asyncio.CancelledError:
            pass
        finally:
            await self.controller.move(ohbot.HEADNOD, 5, 2)

    async def _speak_eyes(self, stop: asyncio.Event):
        """Subtle eye movements while speaking."""
        try:
            await asyncio.sleep(random.uniform(0.8, 2.0))
            while not stop.is_set():
                eye_turn = random.uniform(4.0, 6.0)
                eye_tilt = random.uniform(4.5, 5.5)
                await self.controller.move(ohbot.EYETURN, eye_turn, 8)
                await self.controller.move(ohbot.EYETILT, eye_tilt, 8)
                wait = random.uniform(1.5, 3.5)
                elapsed = 0.0
                while elapsed < wait and not stop.is_set():
                    await asyncio.sleep(0.1)
                    elapsed += 0.1
        except asyncio.CancelledError:
            pass
        finally:
            await self.controller.move(ohbot.EYETURN, 5, 5)
            await self.controller.move(ohbot.EYETILT, 5, 5)

    async def speak_with_animation(self, text: str):
        """Speak with lip sync and concurrent lifelike animations."""
        stop = asyncio.Event()

        tasks = [
            asyncio.create_task(self._speak_blink(stop)),
            asyncio.create_task(self._speak_headturn(stop)),
            asyncio.create_task(self._speak_headnod(stop)),
            asyncio.create_task(self._speak_eyes(stop)),
            asyncio.create_task(self.controller.say(text)),
        ]

        await tasks[-1]  # wait for speech to finish
        stop.set()
        await asyncio.gather(*tasks[:-1], return_exceptions=True)

    # ── greeting ──────────────────────────────────────────────────────────────

    async def greet(self):
        """
        Greeting spoken at the start of each new session.
        Uses a pre-recorded WAV if available (phrases/en_greeting.wav),
        otherwise synthesises live via Azure TTS.

        To customize: edit the fallback text below, or record a WAV file
        as phrases/en_greeting.wav for instant zero-latency playback.
        """
        self.session_language = "en"
        await self.set_color(COLOR_GREEN)
        await asyncio.sleep(0.25)  # prevents first syllable clipping

        await self.speak_phrase_or_synthesise(
            "en_greeting",
            "Hi there! I'm Ohbot. How can I help you today?"
        )

    # ── session loop ──────────────────────────────────────────────────────────

    async def run_session(self, wake_text: str = None):
        """
        One conversation session: greet → listen/respond loop → sleep.

        Ends when MISSED_TURNS_SLEEP consecutive turns have no speech,
        or when the visitor says goodbye.
        """
        self.missed_turns = 0
        exchange = 0

        if wake_text:
            self.session_language = "en"
            await self.set_color(COLOR_GREEN)

            if self._is_pure_wake_command(wake_text):
                await self.speak_phrase_or_synthesise(
                    "en_wake", "I'm awake and ready to help!")
                first_input = None
            else:
                first_input = wake_text
        else:
            await self.greet()
            first_input = None

        while True:
            exchange += 1
            self._last_topic = None
            print(f"\n{'─'*50}")
            print(f"  Exchange {exchange}  (lang={self.session_language})")
            print(f"{'─'*50}")

            if first_input:
                user_text = first_input
                first_input = None
                print(f"✅ Processing wake text: {user_text}")
            else:
                await self.set_color(COLOR_ORANGE)
                idle_stop = asyncio.Event()
                idle_task = asyncio.create_task(self.idle_animation(idle_stop))
                user_text = await self.controller.listen(timeout=SILENCE_TIMEOUT)
                idle_stop.set()
                await idle_task

            if not user_text or not user_text.strip():
                self.missed_turns += 1
                print(f"  (no speech — missed turn {self.missed_turns}/{MISSED_TURNS_SLEEP})")

                if self.missed_turns >= MISSED_TURNS_SLEEP:
                    await self.set_color(COLOR_PURPLE)
                    if self.session_language == "es":
                        await self.speak_phrase_or_synthesise(
                            "es_farewell", "¡Hasta luego! Aquí estaré si necesitas ayuda.")
                    else:
                        await self.speak_phrase_or_synthesise(
                            "en_farewell", "See you soon! I'll be right here if you need me.")
                    await self.reset_conversation()
                    return

                await self.set_color(COLOR_RED)
                if self.session_language == "es":
                    await self.speak_phrase_or_synthesise(
                        "es_missed_turn", "¿Puedo ayudarte en algo?")
                else:
                    await self.speak_phrase_or_synthesise(
                        "en_missed_turn", "I didn't catch that — could you try again?")
                await self.set_color(COLOR_GREEN)
                continue

            self.missed_turns = 0
            await self.set_color(COLOR_BLUE)

            chime_stop = asyncio.Event()
            chime_task = asyncio.create_task(
                self.play_thinking_chime(chime_stop, delay=2.0))

            response_text, success = await self.handle_visitor_input(user_text)

            chime_stop.set()
            await chime_task

            await self.set_color(COLOR_CYAN)

            if success:
                topic = getattr(self, '_last_topic', None)
                lang  = self.session_language
                if topic:
                    phrase_key = f"{lang}_{topic}"
                    wav, _ = self._phrase_paths(phrase_key)
                    if wav:
                        await self.speak_phrase_or_synthesise(phrase_key, response_text)
                    else:
                        await self.speak_with_animation(response_text)
                else:
                    await self.speak_with_animation(response_text)
            else:
                if "Network issues" in response_text:
                    await self.speak_with_animation(
                        "I'm having trouble with my connection. Please try again.")
                else:
                    await self.speak_with_animation(
                        "Something went wrong on my end. Let's try again.")

            topic = getattr(self, '_last_topic', None)
            if topic == "goodbye" or self._looks_like_goodbye(user_text):
                await self.reset_conversation()
                await asyncio.sleep(1.0)
                return

            await self.set_color(COLOR_GREEN)

    # ── static helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _looks_like_goodbye(text: str) -> bool:
        t = text.lower().strip()
        words = t.split()

        strong = ["bye", "goodbye", "good bye", "adios", "adiós",
                  "hasta luego", "chao", "chau", "see you"]
        if any(phrase in t for phrase in strong):
            return True

        if len(words) <= 6:
            has_question = ("?" in t or any(q in t for q in [
                "where", "what", "how", "when", "who", "can", "do you",
                "is there", "tell me", "donde", "qué", "que", "cómo",
                "como", "cuando", "cuándo", "puedo", "tienen",
            ]))
            if not has_question:
                weak = ["thanks", "thank you", "gracias", "muchas gracias"]
                if any(phrase in t for phrase in weak):
                    return True

        return False

    @staticmethod
    def _is_pure_wake_command(text: str) -> bool:
        t = text.lower().strip().rstrip(".!,?")
        for w in ["ohbot", "oh bot", "wake up", "despierta",
                  "despiértate", "despiertate", "hey", "hi", "hola"]:
            t = t.replace(w, "").strip()
        return len(t) < 3

    @staticmethod
    def _is_wake_phrase(text: str) -> bool:
        t = text.lower().strip()
        wake_triggers = ["ohbot", "oh bot", "wake up",
                         "despierta", "despiértate", "despiertate"]
        return any(trigger in t for trigger in wake_triggers)

    @staticmethod
    def _is_only_goodbye(text: str) -> bool:
        t = text.lower().strip().rstrip(".!,")
        if len(t.split()) > 4:
            return False
        goodbye_only = [
            "bye", "goodbye", "good bye", "adios", "adiós",
            "hasta luego", "chao", "chau", "see you", "see you later",
            "thanks", "thank you", "gracias", "muchas gracias",
            "thanks bye", "thank you bye", "bye bye",
        ]
        return any(t == phrase or t == phrase.rstrip(".!,") for phrase in goodbye_only)


# ─────────────────────────────────────────────────────────────────────────────
# GPIO WAKE BUTTON
# ─────────────────────────────────────────────────────────────────────────────

class GPIOWakeButton:
    """
    Monitors a physical push-button on GPIO pin 17 (BCM).
    Sets an asyncio.Event when pressed.

    Wiring:
      - One leg of button to GPIO 17
      - Other leg to GND
      - Internal pull-up enabled (no external resistor needed)
    """

    def __init__(self, pin: int = GPIO_WAKE_PIN):
        self.pin = pin
        self.available = GPIO_AVAILABLE
        self._wake_event: Optional[asyncio.Event] = None
        self._loop = None
        self._running = False

        if self.available:
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                print(f"✅ GPIO wake button on pin {self.pin}")
            except Exception as e:
                print(f"⚠️  GPIO setup failed: {e}")
                self.available = False

    def arm(self, wake_event: asyncio.Event, loop: asyncio.AbstractEventLoop):
        self._wake_event = wake_event
        self._loop = loop
        self._running = True
        if not self.available:
            return
        import threading
        self._thread = threading.Thread(target=self._poll, daemon=True)
        self._thread.start()

    def _poll(self):
        import time
        was_pressed = False
        try:
            while self._running:
                val = GPIO.input(self.pin)
                if val == 0 and not was_pressed:
                    was_pressed = True
                    print(f"  [GPIO] Wake button pressed on pin {self.pin}")
                    if self._wake_event and self._loop:
                        self._loop.call_soon_threadsafe(self._wake_event.set)
                    break
                elif val == 1:
                    was_pressed = False
                time.sleep(0.05)
        except Exception as e:
            print(f"⚠️  GPIO polling error: {e}")

    def disarm(self):
        self._running = False

    def cleanup(self):
        if self.available:
            try:
                GPIO.cleanup(self.pin)
            except Exception:
                pass


# ─────────────────────────────────────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────────────────────────────────────

async def main():
    print("=" * 60)
    print("  Ohbot Chat Bot v2.0")
    print("=" * 60)

    print("\nConnecting to Ohbot...")
    if not ohbot.init():
        print("❌ Ohbot not found — check USB connection")
        return
    print("✅ Ohbot connected")

    print("  Centering all motors...")
    ohbot.reset()
    print("  ✅ Motors centred")

    print("\nSetting up Azure Speech...")
    try:
        azure = AzureSpeechManager()
    except Exception as e:
        print(f"❌ Azure setup failed: {e}")
        return

    controller = AsyncOhbotController(azure)
    await controller.start()

    conversation = AsyncOhbotConversation(controller, azure)

    print("\nChecking Flask server...")
    if not await conversation.check_server():
        print("\n⚠️  Flask server not running!")
        print("Start it with: python3 ohbotchat_server.py")
        await controller.stop()
        return

    wake_button = GPIOWakeButton(pin=GPIO_WAKE_PIN)

    print("\n" + "=" * 60)
    print("  Starting — press Ctrl-C to exit")
    print("  Press GPIO button (pin 17) to wake Ohbot from sleep")
    print("=" * 60 + "\n")

    loop = asyncio.get_event_loop()
    pending_wake_text = None

    try:
        while True:
            await conversation.run_session(wake_text=pending_wake_text)
            pending_wake_text = None

            print("\n  [sleep] Ohbot is sleeping")
            await conversation.set_color(COLOR_DIM)
            conversation.is_sleeping = True

            wake_event = asyncio.Event()
            wake_button.arm(wake_event, loop)

            sleep_stop = asyncio.Event()
            sleep_task = asyncio.create_task(
                conversation.sleep_animation(sleep_stop))

            if VOICE_WAKE_ENABLED:
                async def voice_wake_listener():
                    nonlocal pending_wake_text
                    while not wake_event.is_set():
                        speech = await conversation.controller.listen(
                            timeout=SLEEP_LISTEN_SECS)
                        if speech and speech.strip():
                            if AsyncOhbotConversation._is_wake_phrase(speech):
                                print(f"  [wake] Voice wake: '{speech}'")
                                pending_wake_text = speech
                                wake_event.set()
                                return
                            else:
                                print(f"  [sleep] Ignored: '{speech}'")

                voice_task = asyncio.create_task(voice_wake_listener())

            await wake_event.wait()

            if VOICE_WAKE_ENABLED:
                voice_task.cancel()
                try:
                    await voice_task
                except asyncio.CancelledError:
                    pass

            sleep_stop.set()
            await sleep_task
            wake_button.disarm()
            conversation.is_sleeping = False

            await conversation.set_color(COLOR_GREEN)
            await asyncio.sleep(0.3)
            await controller.move(ohbot.LIDBLINK, 0, 8)
            await asyncio.sleep(0.1)
            await controller.move(ohbot.LIDBLINK, 10, 6)
            await asyncio.sleep(0.3)
            print("  [wake] Starting new session\n")

    except KeyboardInterrupt:
        print("\n\n  Interrupted — shutting down")
        try:
            await conversation.set_color(COLOR_OFF)
            await controller.say("Goodbye!")
        except Exception:
            pass

    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("\nCleaning up...")
        wake_button.cleanup()
        await conversation.close()
        await conversation.set_color(COLOR_OFF)
        await controller.stop()
        print("Done.")


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    asyncio.run(main())
