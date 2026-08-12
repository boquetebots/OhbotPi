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

# ── logging ──────────────────────────────────────────────────────────────────
# Copies everything printed below into logs/greeter-<date>.log, so that when
# something goes wrong at a venue there is a record of it. Set up first, before
# anything else can print. See ohbot_logging.py.
try:
    from ohbot_logging import setup_logging
    setup_logging("greeter")
except Exception as _log_err:                                # noqa: BLE001
    print(f"⚠️  Log file not started ({_log_err}) — carrying on without one")

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
# Playback goes through yobot_core's cross-platform player (via the ohbot
# module) — pw-play/aplay on the Pi, afplay on Mac, winsound on Windows.

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
# Set to True to also allow voice wake words ("Yobot", "wake up").
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

        # Per-session state.
        # Starts from the 🌐 dropdown, then follows whichever language the
        # visitor actually speaks.
        self.session_language = self._starting_language()
        self.missed_turns = 0          # consecutive empty listens
        self._last_topic  = None       # topic from last local knowledge lookup
        self.is_sleeping = False

    # ── knowledge base ────────────────────────────────────────────────────────

    def _load_knowledge(self) -> dict:
        """Load every answer Yobot knows.

        This used to read knowledge.json on its own. It now goes through
        knowledge_base.py, which reads three files and merges them:

            knowledge.json             who Yobot is
            library_knowledge.json     the library and the park
            clubhouse_knowledge.json   the Rincón Clubhouse

        Edit those JSON files to change what Yobot says. Restart the Greeter
        afterwards so it picks up the change.
        """
        try:
            import knowledge_base as kb
            self._kb = kb
            print(f"✅ Loaded {len(kb.KNOWLEDGE)} knowledge topics from "
                  f"{len(kb.ALL_FILES)} files")
            return kb.KNOWLEDGE
        except Exception as e:                            # noqa: BLE001
            self._kb = None
            print(f"⚠️  knowledge_base.py not loaded ({e}) — "
                  "instant answers disabled")
            return {}

    def lookup_knowledge(self, topic: str, language: str = "en") -> str:
        if self._kb:
            return self._kb.answer(topic, language)
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

    def _starting_language(self) -> str:
        """
        Which language a new conversation should OPEN in.

        This is the 🌐 dropdown on the web pages, which saves your choice to
        ohbotData/language.txt. It is only a starting point — if a visitor
        speaks the other language, Yobot follows them (see the auto-switch in
        handle_visitor_input below).

        Read fresh every session rather than once at startup, so changing the
        dropdown takes effect on the next visitor instead of needing the
        Greeter restarted.

        The import is done here rather than at the top of the file on purpose:
        ohbot_lang pulls in Flask, and the Greeter has no web page of its own.
        If Flask were ever missing, this must not stop the robot talking.
        """
        try:
            from ohbot_lang import get_language
            return get_language()
        except Exception as e:
            # A language preference is never worth crashing a robot over.
            print(f"⚠️  Could not read the language setting ({e}) — using English")
            return "en"

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
                    "language": data.get("language"),
                }
        except Exception as e:
            print(f"⚠️  Intent detection failed: {e}")
        # language=None means "we don't know" — see handle_visitor_input,
        # which then leaves the session's language alone. Guessing "en" here
        # would drop a Spanish conversation into English every time the
        # server hiccuped.
        return {"intent": "general_chat", "topic": None, "language": None}

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

        # The visitor's own choice decides the language — the 🌐 dropdown or
        # the kiosk buttons — so nothing here is allowed to override it.
        #
        # This used to reassign session_language whenever the intent server
        # thought it saw the other language. That made sense when Azure was
        # auto-detecting speech. Now that we listen in one fixed language,
        # the other one arrives mis-transcribed, and the detector would be
        # reading noise: on 2026-08-12 a single stray "Gracias" in an English
        # sentence flipped Yobot into Spanish and gave the wrong answer.
        #
        # We still log what it thought, because a run of these is a good hint
        # that a visitor picked the wrong language button.
        if language and language != self.session_language:
            print(f"🌐 (heard something that looked like '{language}' — "
                  f"staying in '{self.session_language}')")

        if intent == "local_knowledge" and topic:
            print(f"📖 Local knowledge: topic='{topic}', lang='{language}'")
            self._last_topic = topic
            # session_language, not `language` — the line above may have just
            # updated it, and `language` can be None when the server had no
            # opinion. This way the answer always comes back in whatever
            # language the conversation is actually in.
            answer = self.lookup_knowledge(topic, self.session_language)
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
                proc = await ohbot.start_wav(CHIME_FILE)
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

    async def speak_phrase_or_synthesise(self, key: str, fallback_text: str,
                                         language: str = None):
        """
        Try to play a pre-recorded phrase. If not found, synthesise live.
        Speaking animations (blinks, head, eyes) run in both cases.

        `language` is 'en' or 'es'. It only matters for the live-synthesis
        path — a pre-recorded WAV is already in whatever language it was
        recorded in. Left out, it follows the current session's language.
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
            await self.controller.say(
                fallback_text,
                language=language or self.session_language)

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

    async def speak_with_animation(self, text: str, language: str = None):
        """Speak with lip sync and concurrent lifelike animations.

        `language` is 'en' or 'es' and decides how Azure PRONOUNCES the words.
        The voice itself doesn't change — Jenny Multilingual speaks both, so
        Yobot sounds like the same robot either way. Left out, it follows the
        current session's language.
        """
        stop = asyncio.Event()

        tasks = [
            asyncio.create_task(self._speak_blink(stop)),
            asyncio.create_task(self._speak_headturn(stop)),
            asyncio.create_task(self._speak_headnod(stop)),
            asyncio.create_task(self._speak_eyes(stop)),
            asyncio.create_task(self.controller.say(
                text, language=language or self.session_language)),
        ]

        await tasks[-1]  # wait for speech to finish
        stop.set()
        await asyncio.gather(*tasks[:-1], return_exceptions=True)

    # ── greeting ──────────────────────────────────────────────────────────────

    async def greet(self):
        """
        Greeting spoken at the start of each new session.
        Uses a pre-recorded WAV if available (phrases/en_greeting.wav or
        phrases/es_greeting.wav), otherwise synthesises live via Azure TTS.

        Which language he opens in comes from the 🌐 dropdown. If the visitor
        then speaks the other language, he follows them from the next reply on.

        To customize: edit the fallback text below, or record a WAV file
        as phrases/en_greeting.wav for instant zero-latency playback.
        """
        self.session_language = self._starting_language()
        await self.set_color(COLOR_GREEN)
        await asyncio.sleep(0.25)  # prevents first syllable clipping

        if self.session_language == "es":
            await self.speak_phrase_or_synthesise(
                "es_greeting",
                "¡Hola! Soy Yobot. ¿En qué te puedo ayudar?"
            )
        else:
            await self.speak_phrase_or_synthesise(
                "en_greeting",
                "Hi there! I'm Yobot. How can I help you today?"
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
            self.session_language = self._starting_language()
            await self.set_color(COLOR_GREEN)

            if self._is_pure_wake_command(wake_text):
                if self.session_language == "es":
                    await self.speak_phrase_or_synthesise(
                        "es_wake", "¡Estoy despierto y listo para ayudar!")
                else:
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

                # Listen in the language the visitor chose — the 🌐 dropdown
                # or the kiosk buttons. Automatic detection was removed on
                # 2026-08-12: it cost a fixed ~3 extra seconds on every
                # single turn. See the note in ohbot_azure.recognize_once().
                user_text = await self.controller.listen(
                    timeout=SILENCE_TIMEOUT, language=self.session_language)

                idle_stop.set()
                await idle_task

            if not user_text or not user_text.strip():
                self.missed_turns += 1
                print(f"  (no speech — missed turn {self.missed_turns}/{MISSED_TURNS_SLEEP})")

                # Silence because nobody spoke is normal. Silence because the
                # microphone died is not — and the two look identical from
                # here. If the speech code flagged a mic fault, say it out
                # loud, once, so the problem is audible in the room.
                if not getattr(self.azure, "_mic_ok", True) \
                        and not getattr(self.azure, "mic_warning_spoken", False):
                    self.azure.mic_warning_spoken = True
                    print("  ⚠️  Microphone fault flagged — announcing it out loud")
                    await self.set_color(COLOR_RED)
                    await self.speak_with_animation(
                        "Tengo un problema con mi micrófono y no puedo oír."
                        if self.session_language == "es" else
                        "I'm having a problem with my microphone and I can't hear anything."
                    )

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
                spanish = (self.session_language == "es")
                if "Network issues" in response_text:
                    await self.speak_with_animation(
                        "Tengo problemas con mi conexión. Inténtalo de nuevo, por favor."
                        if spanish else
                        "I'm having trouble with my connection. Please try again.")
                else:
                    await self.speak_with_animation(
                        "Algo salió mal por mi parte. Vamos a intentarlo otra vez."
                        if spanish else
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
        for w in ["yobot", "yo bot", "ohbot", "oh bot", "wake up", "despierta",
                  "despiértate", "despiertate", "hey", "hi", "hola"]:
            t = t.replace(w, "").strip()
        return len(t) < 3

    @staticmethod
    def _is_wake_phrase(text: str) -> bool:
        t = text.lower().strip()
        wake_triggers = ["yobot", "yo bot", "ohbot", "oh bot", "wake up",
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
# KEYBOARD WAKE (Mac / Windows / any computer without GPIO)
# ─────────────────────────────────────────────────────────────────────────────

class KeyboardWake:
    """
    Wake the bot by pressing Enter in the terminal.

    Used on Mac/Windows where there is no GPIO wake button. Without this,
    the bot would fall asleep after the first session with no way to wake
    it (voice wake is normally disabled to save Azure costs).

    One background thread reads the keyboard for the whole life of the
    program; pressing Enter only wakes the bot while it's actually
    sleeping ("armed"), and is ignored the rest of the time.
    """

    def __init__(self):
        self._armed_event: Optional[asyncio.Event] = None
        self._loop = None
        self._started = False
        self.available = True

    def arm(self, wake_event: asyncio.Event, loop: asyncio.AbstractEventLoop):
        self._armed_event = wake_event
        self._loop = loop
        if not self._started:
            import threading
            thread = threading.Thread(target=self._reader, daemon=True)
            thread.start()
            self._started = True

    def _reader(self):
        while True:
            try:
                input()   # blocks until Enter is pressed
            except (EOFError, OSError):
                # No usable keyboard (e.g. running as a background service)
                self.available = False
                return
            ev, lp = self._armed_event, self._loop
            if ev and lp:
                print("  [keyboard] Enter pressed — waking up")
                lp.call_soon_threadsafe(ev.set)

    def disarm(self):
        self._armed_event = None


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

    # ── Can he actually hear? ────────────────────────────────────────────────
    # Checked up front, out loud. On 2026-08-10 the mic was on a different
    # ALSA card than the config expected, so Yobot greeted visitors and then
    # stood there in silence for hours with nothing in any log. Never again:
    # if the mic is missing he now SAYS so, in the room, where you'll hear it.
    print("\nChecking the microphone...")
    mic_device, mic_ok, mic_reason = azure.resolve_microphone()
    if not mic_ok:
        print("=" * 60)
        print("  ❌ NO MICROPHONE FOUND")
        print(f"     {mic_reason}")
        print("     Yobot will start anyway, but he will not hear anyone.")
        print("     Plug the USB mic in, then: systemctl --user restart ohbot-conversation")
        print("     To see what the Pi can find:  python3 ohbot_mic.py")
        print("=" * 60)
        try:
            await conversation.set_color(COLOR_RED)
            await controller.say(
                "Warning. I cannot find my microphone, so I will not be able "
                "to hear anyone. Please check the U S B microphone is plugged in."
            )
        except Exception as e:                               # noqa: BLE001
            print(f"  (couldn't announce the mic problem out loud: {e})")
    else:
        print(f"✅ Microphone ready: {mic_device}  ({mic_reason})")

    print("\nChecking Flask server...")
    if not await conversation.check_server():
        print("\n⚠️  Flask server not running!")
        print("Start it with: python3 ohbotchat_server.py")
        await controller.stop()
        return

    wake_button = GPIOWakeButton(pin=GPIO_WAKE_PIN)

    # On computers without GPIO (Mac/Windows), wake with the Enter key instead
    keyboard_wake = None
    if not wake_button.available:
        keyboard_wake = KeyboardWake()

    print("\n" + "=" * 60)
    print("  Starting — press Ctrl-C to exit")
    if wake_button.available:
        print("  Wake from sleep: GPIO button (pin 17), or the Wake button")
        print("  on the Launcher page — http://<this-pi>:5000")
    else:
        print("  Wake from sleep: press Enter, or the Wake button on the")
        print("  Launcher page — http://localhost:5000")
    print("=" * 60 + "\n")

    loop = asyncio.get_event_loop()
    pending_wake_text = None

    try:
        while True:
            await conversation.run_session(wake_text=pending_wake_text)
            pending_wake_text = None

            print("\n  [sleep] Yobot is sleeping — press Wake on the Launcher page")
            await conversation.set_color(COLOR_DIM)
            conversation.is_sleeping = True

            wake_event = asyncio.Event()
            wake_button.arm(wake_event, loop)
            if keyboard_wake:
                print("  [sleep] Press Enter to wake")
                keyboard_wake.arm(wake_event, loop)

            sleep_stop = asyncio.Event()
            sleep_task = asyncio.create_task(
                conversation.sleep_animation(sleep_stop))

            # ── Wake button on the Launcher web page ──────────────────────
            # Checks in with the Flask server once a second to ask whether
            # anyone pressed Wake. This is a local request to the same Pi, so
            # it costs nothing — unlike voice wake, which pays Azure to listen
            # the whole time he's asleep.
            #
            # A press made while he was still saying goodbye counts too — the
            # server remembers presses for a minute, so nothing is lost in the
            # few seconds between "the button was pressed" and "he is asleep
            # and watching for it".
            async def web_wake_listener():
                async def check():
                    r = await conversation.http_client.get(
                        f"{conversation.server_url}/wake/pending", timeout=5.0)
                    return r.status_code == 200 and r.json().get('wake')

                checks   = 0
                failures = 0
                last_err = None

                while not wake_event.is_set():
                    await asyncio.sleep(1.0)
                    try:
                        checks += 1
                        if await check():
                            print("  [wake] Wake button pressed on the Launcher page")
                            wake_event.set()
                            return
                    except Exception as e:
                        # Don't swallow this silently — if the check is broken,
                        # the Wake button stops working with no clue why.
                        failures += 1
                        err = f"{type(e).__name__}: {e}"
                        if err != last_err:
                            print(f"  [wake] check failing — {err}")
                            last_err = err

                    # Heartbeat, so the log shows whether we're still watching.
                    if checks % 30 == 0:
                        print(f"  [wake] still watching "
                              f"({checks} checks, {failures} failed)")

            web_task = asyncio.create_task(web_wake_listener())

            if VOICE_WAKE_ENABLED:
                async def voice_wake_listener():
                    nonlocal pending_wake_text
                    while not wake_event.is_set():
                        speech = await conversation.controller.listen(
                            timeout=SLEEP_LISTEN_SECS,
                            language=conversation.session_language)
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

            web_task.cancel()
            try:
                await web_task
            except asyncio.CancelledError:
                pass

            if VOICE_WAKE_ENABLED:
                voice_task.cancel()
                try:
                    await voice_task
                except asyncio.CancelledError:
                    pass

            sleep_stop.set()
            await sleep_task
            wake_button.disarm()
            if keyboard_wake:
                keyboard_wake.disarm()
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
