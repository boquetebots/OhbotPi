#!/usr/bin/env python3
"""
Ohbot Azure Controller - Async-First with Azure Speech Services
Version: 1.1.0
Platforms: Raspberry Pi / Linux, macOS (Windows pending)
Features: Azure STT/TTS, Viseme-based lip sync, Async motor control

Microphone: on Mac/Windows the system default microphone is used.
On Linux/Pi the device comes from AZURE_MIC_DEVICE in the .env file
(default plughw:3,0 — this Pi's USB mic).
Speaker: playback goes through yobot_core's cross-platform player
(pw-play/aplay on Linux, afplay on Mac → default output device).
"""

import asyncio
import os
import re
import sys
import tempfile
import threading
import time
import wave
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, List, Tuple

# Global lock — all calls into the ohbot serial library (ohbot.move,
# ohbot.baseColour, ohbot.reset) must hold this lock.  The serial port is
# NOT thread-safe: two threads writing to it simultaneously corrupts
# commands/crashes.  Both gui_server.py and this module import this lock.
OHBOT_SERIAL_LOCK = threading.Lock()

# Add project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import azure.cognitiveservices.speech as speechsdk
except ImportError:
    print("❌ Azure Speech SDK not found. Install with:")
    print("   pip install azure-cognitiveservices-speech")
    sys.exit(1)

try:
    # Try package import first
    from ohbot import ohbot_pi as ohbot
except ImportError:
    try:
        # Fall back to direct import if ohbot_pi.py is in same directory
        import ohbot_pi as ohbot
    except ImportError:
        print("❌ ohbot_pi module not found")
        print("Make sure ohbot_pi.py is in the same directory")
        sys.exit(1)


# ============================================================================
# THREAD-SAFE OHBOT HELPERS
# ============================================================================

def _safe_move(motor, position, speed, avoid=True):
    """Call ohbot.move() while holding OHBOT_SERIAL_LOCK."""
    with OHBOT_SERIAL_LOCK:
        ohbot.move(motor, position, speed, avoid)


def _safe_base_colour(r, g, b):
    """Call ohbot.baseColour() while holding OHBOT_SERIAL_LOCK."""
    with OHBOT_SERIAL_LOCK:
        ohbot.baseColour(r, g, b)


def _safe_reset():
    """Call ohbot.reset() while holding OHBOT_SERIAL_LOCK."""
    with OHBOT_SERIAL_LOCK:
        ohbot.reset()


# ============================================================================
# AZURE VISEME TO OHBOT LIP MAPPING
# ============================================================================

class VisemeMapper:
    """
    Maps Azure viseme IDs to Ohbot lip positions.

    Azure provides 22 visemes (0-21) representing mouth shapes.
    We map these to Ohbot's TOPLIP and BOTTOMLIP motors (0-10 range).
    """

    # Viseme reference: https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-speech-synthesis-viseme
    # Lip position calibration: neutral/closed = 5 for both lips.
    #
    # Position 5 lands on each lip's measured Center in
    # MotorDefinitionsv21.omd, and for the lips that centre is calibrated as
    # "the two lips just touching" — so 5 is genuinely mouth-closed on both
    # motors by measurement. This replaced an older hack where BottomLip's
    # Min/Max were hand-adjusted to force position 5 to match the top lip.
    # If the lips are ever recalibrated, the Center OK step MUST be taken at
    # the just-touching point or everything below breaks.
    VISEME_MAP = {
        0: (5, 5),      # Silence / closed
        1: (6, 6),      # ae, ax, ah (as in "bat")
        2: (7, 7),      # aa (as in "father")
        3: (5.5, 5.5),  # ao (as in "ought")
        4: (6.5, 7),    # ey (as in "ate")
        5: (6, 6.5),    # eh (as in "bet")
        6: (5, 5.5),    # uh (as in "but")
        7: (7, 8),      # iy (as in "eat")
        8: (5.5, 6),    # ih (as in "it")
        9: (6, 7),      # uw (as in "boot")
        10: (5, 5.5),   # uh (as in "book")
        11: (6.5, 7.5), # er (as in "bird")
        12: (5, 5),     # ax (schwa, as in "about")
        13: (5.5, 5.5), # s, z
        14: (5, 5),     # sh, zh
        15: (5, 5),     # th (as in "think")
        16: (5.5, 6),   # f, v
        17: (5, 5),     # d, t, n
        18: (5, 5),     # k, g
        19: (5, 5),     # ch, j
        20: (5, 5),     # m, b, p
        21: (6, 6.5),   # w, r
    }

    # Neutral/closed position for both lips (see calibration note above).
    NEUTRAL = 5.0

    # How much bigger to make lip-sync movement than the base VISEME_MAP
    # values above. 1.0 = no change, 1.6 = 60% more exaggerated.
    # This scales each viseme's distance from NEUTRAL, so closed-mouth
    # sounds (silence, m/b/p, etc.) still land exactly on NEUTRAL — only
    # the open-mouth shapes get bigger. Raise/lower this one number to
    # tune how exaggerated lip-sync looks; results are capped to the
    # motors' 0-10 range so nothing can overshoot.
    #
    # History. Was 1.6 for a long time, but that was compensating for the
    # lips only getting half their opening travel — with centre stuck at the
    # midpoint, slider 5-10 covered just half the range, so the visemes had
    # to be stretched to look like anything. After the lips were three-point
    # calibrated on 2026-08-05 (centre = "just touching"), slider 5-10 covers
    # nearly the whole opening range, so this was dropped to 1.0.
    #
    # Then raised to 1.4 on 2026-08-05 after watching it on the robot: 1.0
    # was working but read as a little understated.
    #
    # Headroom: the widest viseme in VISEME_MAP is 8, and 5 + (8-5) * 1.4 =
    # 9.2, still under the 10 ceiling, so nothing clips. Pushing much past
    # 1.6 would start flattening the biggest mouth shapes against that
    # ceiling, which makes different sounds start to look the same.
    EXAGGERATION = 1.4

    @classmethod
    def get_lip_positions(cls, viseme_id: int) -> Tuple[float, float]:
        """
        Get (top_lip, bottom_lip) positions for a viseme, scaled by
        EXAGGERATION and clamped to the motors' 0-10 range.

        Returns:
            Tuple of (top_lip_pos, bottom_lip_pos) in 0-10 range
        """
        top, bottom = cls.VISEME_MAP.get(viseme_id, (5, 5))

        top = cls.NEUTRAL + (top - cls.NEUTRAL) * cls.EXAGGERATION
        bottom = cls.NEUTRAL + (bottom - cls.NEUTRAL) * cls.EXAGGERATION

        top = max(0.0, min(10.0, top))
        bottom = max(0.0, min(10.0, bottom))

        return (top, bottom)


# ============================================================================
# AZURE SPEECH MANAGER
# ============================================================================

class AzureSpeechManager:
    """Manages Azure Speech Services for STT and TTS"""

    def __init__(self, subscription_key: Optional[str] = None, region: Optional[str] = None):
        self.subscription_key = subscription_key or os.environ.get("AZURE_SPEECH_KEY")
        self.region = region or os.environ.get("AZURE_SPEECH_REGION", "eastus")

        if not self.subscription_key:
            raise ValueError(
                "Azure Speech subscription key not provided. "
                "Set AZURE_SPEECH_KEY environment variable or pass subscription_key parameter."
            )

        self.speech_config = speechsdk.SpeechConfig(
            subscription=self.subscription_key,
            region=self.region
        )

        # Default voice — Jenny Multilingual handles English and Spanish
        self.speech_config.speech_synthesis_voice_name = "en-US-JennyMultilingualNeural"

        self.speech_config.set_property(
            speechsdk.PropertyId.SpeechServiceResponse_RequestWordLevelTimestamps,
            "true"
        )

        # Reduce end-of-speech silence timeout (500 ms feels snappier than default 1000+ ms)
        self.speech_config.set_property(
            speechsdk.PropertyId.Speech_SegmentationSilenceTimeoutMs, "500"
        )

        print(f"✅ Azure Speech initialized (region: {self.region}, silence timeout: 500 ms)")

    def set_voice(self, voice_name: str):
        """Change the TTS voice."""
        self.speech_config.speech_synthesis_voice_name = voice_name
        print(f"🎤 Voice set to: {voice_name}")

    # Pitch adjustments per voice
    VOICE_PITCH = {
        "en-US-JennyMultilingualNeural": "+2%",
    }

    # Which Azure locale each of our two languages maps to.
    #
    # The voice itself does NOT change between English and Spanish — Jenny
    # Multilingual is one voice that speaks both, so Ohbot sounds like the
    # same robot either way. What changes is the xml:lang tag we hand Azure,
    # which tells it which set of pronunciation rules to use. Without it,
    # Spanish text gets read with an English accent ("Hola" → "HOH-lah" with
    # an American L), and the visemes (lip shapes) come out wrong to match.
    #
    # 'es-MX' is Mexican Spanish, matching what the conversation bot already
    # listens for. Change it to 'es-ES' here if you ever want Castilian.
    LANG_LOCALE = {
        'en': 'en-US',
        'es': 'es-MX',
    }
    DEFAULT_LANG = 'en'

    @classmethod
    def locale_for(cls, language):
        """Turn 'en' or 'es' (or a full locale, or None) into an Azure locale.

        Deliberately forgiving: anything unrecognised falls back to English
        rather than raising, because a bad language string should never stop
        the robot from talking.
        """
        if not language:
            return cls.LANG_LOCALE[cls.DEFAULT_LANG]
        language = str(language).strip()
        if language.lower() in cls.LANG_LOCALE:
            return cls.LANG_LOCALE[language.lower()]
        if '-' in language:            # already a full locale, e.g. 'es-MX'
            return language            # kept as typed — Azure wants es-MX, not es-mx
        return cls.LANG_LOCALE[cls.DEFAULT_LANG]

    # ------------------------------------------------------------------
    # Pronunciation fixes for the ENGLISH voice
    # ------------------------------------------------------------------
    # Azure's English voice reads Spanish place names with English spelling
    # rules, so "Boquete" comes out as "bo-KEET" and "Rincon" as "RIN-kun".
    # This table tells Azure exactly which sounds to make instead.
    #
    # Format is simply:   "the word as it is spelled": "the IPA sounds"
    #
    # The IPA must come from Azure's ENGLISH (en-US) sound list. If you use a
    # symbol that isn't on that list, Azure quietly ignores the whole fix and
    # you hear no change. The full list, plus how to add a new word, is in
    # HANDOFF_pronunciation_guide.md in this folder.
    #
    # Matching is whole-word and ignores capitals, so "Rincon" does NOT
    # break "Rincones" — Azure already says that one correctly.
    PHONEME_FIXES = {
        # bo-KEH-tay  (the way it's said in English around town)
        "Boquete": "boʊˈkɛteɪ",
        # reen-KOHN
        "Rincón":  "ɹɪnˈkoʊn",
        "Rincon":  "ɹɪnˈkoʊn",
    }

    # Built once, on first use: one regex that finds any of the words above.
    # Longest words first so a longer entry always wins over a shorter one.
    _phoneme_pattern = None

    @classmethod
    def _get_phoneme_pattern(cls):
        if cls._phoneme_pattern is None and cls.PHONEME_FIXES:
            words = sorted(cls.PHONEME_FIXES, key=len, reverse=True)
            cls._phoneme_pattern = re.compile(
                r'\b(' + '|'.join(re.escape(w) for w in words) + r')\b',
                re.IGNORECASE,
            )
        return cls._phoneme_pattern

    @classmethod
    def apply_phoneme_fixes(cls, text: str) -> str:
        """Wrap any word in PHONEME_FIXES with an SSML <phoneme> tag.

        Done in a single pass, so a word we've already tagged can never be
        matched again by a later entry in the table.
        """
        pattern = cls._get_phoneme_pattern()
        if not pattern:
            return text

        # Look the word up ignoring capitals, but keep the original spelling
        # inside the tag so the text still reads correctly.
        lookup = {w.lower(): ipa for w, ipa in cls.PHONEME_FIXES.items()}

        def _tag(match):
            word = match.group(0)
            ipa  = lookup[word.lower()]
            return f'<phoneme alphabet="ipa" ph="{ipa}">{word}</phoneme>'

        return pattern.sub(_tag, text)

    def _make_ssml(self, text: str, language: str = None) -> str:
        """Wrap text in SSML with per-voice pitch and phoneme corrections.

        `language` is 'en' or 'es' (or None for English). It sets the xml:lang
        tag, which is what makes Jenny Multilingual switch her accent from
        English to Spanish. See LANG_LOCALE above.
        """
        voice  = self.speech_config.speech_synthesis_voice_name
        pitch  = self.VOICE_PITCH.get(voice, "+0%")
        locale = self.locale_for(language)

        # The phoneme fixes are English spellings, so they only apply when
        # we're actually speaking English. Applying them to Spanish text would
        # mangle it.
        ssml_text = text
        if locale.startswith("en-"):
            ssml_text = self.apply_phoneme_fixes(ssml_text)

        return (
            '<speak version="1.0" '
            'xmlns="http://www.w3.org/2001/10/synthesis" '
            f'xml:lang="{locale}">\n'
            f'  <voice name="{voice}">\n'
            f'    <lang xml:lang="{locale}">\n'
            f'      <prosody pitch="{pitch}">{ssml_text}</prosody>\n'
            '    </lang>\n'
            '  </voice>\n'
            '</speak>'
        )

    async def recognize_once(self, timeout: float = 10.0, language: str = None) -> str:
        """Recognize speech from microphone (single utterance).

        Microphone selection is platform-aware:
          - Mac/Windows: the system default microphone (whatever is selected
            in Sound settings).
          - Linux/Pi: the ALSA device named in AZURE_MIC_DEVICE in .env
            (defaults to plughw:3,0, this Pi's USB mic). If the mic ever
            stops being found, check `arecord -l` for the card number and
            update AZURE_MIC_DEVICE.
        """
        if ohbot.IS_LINUX:
            mic_device = os.environ.get("AZURE_MIC_DEVICE", "plughw:3,0")
            audio_config = speechsdk.audio.AudioConfig(device_name=mic_device)
        else:
            audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)

        # Accept either a short code ('es') or a full Azure locale ('es-MX').
        # Passing nothing still means "auto-detect between the two".
        if language:
            language = self.locale_for(language)

        if language:
            recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config,
                audio_config=audio_config,
                language=language
            )
            print(f"🎤 Listening (locked: {language})...")
        else:
            auto_detect_config = speechsdk.languageconfig.AutoDetectSourceLanguageConfig(
                languages=["es-MX", "en-US"]
            )
            recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config,
                audio_config=audio_config,
                auto_detect_source_language_config=auto_detect_config
            )
            print("🎤 Listening (auto-detect)...")

        t_start = time.perf_counter()
        t_first_audio = None

        def on_recognizing(evt):
            nonlocal t_first_audio
            if t_first_audio is None:
                t_first_audio = time.perf_counter()

        recognizer.recognizing.connect(on_recognizing)

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, recognizer.recognize_once)

        t_end = time.perf_counter()
        total_ms = (t_end - t_start) * 1000
        if t_first_audio is not None:
            waiting_ms    = (t_first_audio - t_start) * 1000
            processing_ms = (t_end - t_first_audio) * 1000
            print(
                f"⏱️  STT: {total_ms:.0f}ms total  |  "
                f"{waiting_ms:.0f}ms waiting for speech  |  "
                f"{processing_ms:.0f}ms processing (silence timeout + network)"
            )
        else:
            print(f"⏱️  STT: {total_ms:.0f}ms total (no speech detected)")

        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            if language:
                print(f"✅ Recognized ({language}): {result.text}")
            else:
                lang_result = speechsdk.AutoDetectSourceLanguageResult(result)
                detected_lang = lang_result.language
                print(f"✅ Recognized ({detected_lang}): {result.text}")
            return result.text
        elif result.reason == speechsdk.ResultReason.NoMatch:
            print("🤔 No speech recognized")
            return ""
        else:
            print(f"❌ Recognition failed: {result.reason}")
            return ""

    def synthesize_to_file_with_visemes(self, text: str, output_file: str,
                                        language: str = None) -> List[Dict]:
        """Synthesize speech to file and capture viseme events.

        `language` is 'en' or 'es' (None means English). It only affects
        pronunciation and the resulting lip shapes — the voice stays the same.
        """
        visemes = []

        audio_config = speechsdk.audio.AudioOutputConfig(filename=output_file)
        synthesizer  = speechsdk.SpeechSynthesizer(
            speech_config=self.speech_config,
            audio_config=audio_config
        )

        def viseme_callback(evt):
            visemes.append({
                'viseme_id': evt.viseme_id,
                'audio_offset': evt.audio_offset
            })

        synthesizer.viseme_received.connect(viseme_callback)

        ssml   = self._make_ssml(text, language)
        result = synthesizer.speak_ssml(ssml)

        if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
            raise RuntimeError(f"Speech synthesis failed: {result.reason}")

        return visemes


# ============================================================================
# ASYNC OHBOT CONTROLLER
# ============================================================================

class AsyncOhbotController:
    """
    Async Ohbot controller with Azure Speech and viseme-based lip sync.

    All 8 servos can move simultaneously via async queue processing.
    """

    def __init__(self, azure_manager: AzureSpeechManager):
        self.azure = azure_manager

        # Motor queues - one per motor for true parallel control
        self.motor_queues = [asyncio.Queue(maxsize=10) for _ in range(8)]

        # Speech state
        self.is_speaking = False
        self.speech_lock = asyncio.Lock()

        # Executor for blocking operations
        self.executor = ThreadPoolExecutor(max_workers=4)

        # Background tasks
        self.motor_tasks = []
        self.is_running = False

        print("🤖 AsyncOhbotController initialized")

    async def start(self):
        """Start the async controller"""
        if self.is_running:
            return

        self.is_running = True

        self.motor_tasks = [
            asyncio.create_task(self._motor_processor(motor_id), name=f"motor_{motor_id}")
            for motor_id in range(8)
        ]

        await asyncio.sleep(0.1)
        print("✅ AsyncOhbotController started")

    async def stop(self):
        """Stop the async controller"""
        print("🛑 Stopping AsyncOhbotController...")
        self.is_running = False

        for task in self.motor_tasks:
            task.cancel()

        if self.motor_tasks:
            await asyncio.gather(*self.motor_tasks, return_exceptions=True)

        self.executor.shutdown(wait=False)

        try:
            _safe_reset()  # lock-safe wrapper
        except:
            pass

        print("✅ AsyncOhbotController stopped")

    async def _motor_processor(self, motor_id: int):
        """Process motor commands for a specific motor"""
        queue = self.motor_queues[motor_id]

        while self.is_running:
            try:
                cmd = await asyncio.wait_for(queue.get(), timeout=0.1)

                # _safe_move acquires OHBOT_SERIAL_LOCK before touching the
                # serial port, preventing a collision with the sequence-playback
                # thread that causes a segmentation fault.
                await asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    _safe_move,
                    cmd['motor'],
                    cmd['position'],
                    cmd['speed'],
                    cmd.get('avoid', True)
                )

                await asyncio.sleep(0.01)

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ Motor {motor_id} error: {e}")

    async def move(self, motor: int, position: float, speed: int = 5, avoid: bool = True):
        """Move a motor asynchronously."""
        if not 0 <= motor <= 7:
            raise ValueError(f"Invalid motor ID: {motor}")

        cmd = {
            'motor': motor,
            'position': max(0, min(10, position)),
            'speed': max(0, min(10, speed)),
            'avoid': avoid
        }

        await self.motor_queues[motor].put(cmd)

    async def say(self, text: str, lip_sync: bool = True,
                  language: str = None) -> None:
        """Speak text using Azure TTS with optional viseme-based lip sync.

        `language` is 'en' or 'es'. Leaving it out keeps the old behaviour
        (English), so every existing caller carries on working unchanged.
        """
        if not text or text.isspace():
            return

        async with self.speech_lock:
            self.is_speaking = True
            temp_file = None

            try:
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                    temp_file = f.name

                print(f"🗣️ Speaking [{self.azure.locale_for(language)}]: {text}")

                visemes = await asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    self.azure.synthesize_to_file_with_visemes,
                    text,
                    temp_file,
                    language
                )

                if lip_sync and visemes:
                    lip_task = asyncio.create_task(
                        self._animate_lips_with_visemes(temp_file, visemes)
                    )
                else:
                    lip_task = None

                await self._play_audio_async(temp_file)

                if lip_task:
                    await lip_task

            finally:
                self.is_speaking = False
                # Always clean up the temp file, even if synthesis/playback failed
                if temp_file:
                    try:
                        os.unlink(temp_file)
                    except OSError:
                        pass
                if lip_sync:
                    await self.move(ohbot.TOPLIP, 5, 10, avoid=False)
                    await self.move(ohbot.BOTTOMLIP, 5, 10, avoid=False)

    async def _animate_lips_with_visemes(self, audio_file: str, visemes: List[Dict]):
        """Animate lips based on Azure viseme events."""
        if not visemes:
            return

        TICKS_PER_SECOND = 10_000_000

        viseme_timeline = [
            {
                'viseme_id': v['viseme_id'],
                'time': v['audio_offset'] / TICKS_PER_SECOND
            }
            for v in visemes
        ]

        viseme_timeline.sort(key=lambda x: x['time'])

        start_time  = asyncio.get_event_loop().time()
        current_idx = 0
        last_top    = None
        last_bottom = None

        while current_idx < len(viseme_timeline):
            elapsed = asyncio.get_event_loop().time() - start_time

            while current_idx < len(viseme_timeline) and viseme_timeline[current_idx]['time'] <= elapsed:
                viseme_id = viseme_timeline[current_idx]['viseme_id']
                top_pos, bottom_pos = VisemeMapper.get_lip_positions(viseme_id)

                if top_pos != last_top:
                    await self.move(ohbot.TOPLIP, top_pos, 10, avoid=False)
                    last_top = top_pos
                if bottom_pos != last_bottom:
                    await self.move(ohbot.BOTTOMLIP, bottom_pos, 10, avoid=False)
                    last_bottom = bottom_pos

                current_idx += 1

            await asyncio.sleep(0.03)

        await self.move(ohbot.TOPLIP, 5, 10, avoid=False)
        await self.move(ohbot.BOTTOMLIP, 5, 10, avoid=False)

    async def _play_audio_async(self, audio_file: str):
        """Play audio file asynchronously via yobot_core's cross-platform
        player: pw-play/aplay on Linux (pw-play preferred — on this Pi,
        aplay's direct ALSA open fails with error 524), afplay on Mac
        (default output device), winsound on Windows.
        """
        await ohbot.play_wav(audio_file)

    async def listen(self, timeout: float = 10.0, language: str = None) -> str:
        """Listen for speech input using Azure STT."""
        return await self.azure.recognize_once(timeout, language)

    async def set_eye_color(self, r: int, g: int, b: int):
        """Set eye LED color (0-10 range for each channel)"""
        await asyncio.get_event_loop().run_in_executor(
            self.executor,
            _safe_base_colour,
            r, g, b
        )


# ============================================================================
# DEMO PROGRAMS
# ============================================================================

async def demo_basic(controller: AsyncOhbotController):
    """Basic movement and speech demo"""
    print("\n🎯 Running basic demo...")

    await controller.set_eye_color(5, 0, 10)
    await controller.say("Hello! I am Yobot running on Azure Speech Services.")
    await asyncio.sleep(0.5)

    speech_task = asyncio.create_task(
        controller.say("Watch as I move multiple servos at the same time!")
    )

    await asyncio.sleep(0.5)

    for _ in range(3):
        await controller.move(ohbot.HEADTURN, 7, 3)
        await asyncio.sleep(0.5)
        await controller.move(ohbot.HEADTURN, 3, 3)
        await asyncio.sleep(0.5)

    await controller.move(ohbot.HEADTURN, 5, 3)
    await speech_task

    await controller.set_eye_color(0, 10, 0)
    await controller.say("Demo complete!")


async def demo_conversation(controller: AsyncOhbotController):
    """Interactive conversation demo"""
    print("\n🎯 Running conversation demo...")

    await controller.set_eye_color(0, 5, 10)
    await controller.say("Let's have a conversation! I'm listening...")

    for i in range(3):
        await controller.set_eye_color(10, 5, 0)
        text = await controller.listen(timeout=10.0)

        if text.strip():
            await controller.set_eye_color(0, 10, 5)
            await controller.say(f"You said: {text}")
            await asyncio.sleep(0.5)
        else:
            await controller.say("I didn't hear anything.")

        if i < 2:
            await controller.say("What else would you like to say?")

    await controller.set_eye_color(5, 0, 10)
    await controller.say("Thanks for talking with me!")


async def demo_parallel_motors(controller: AsyncOhbotController):
    """Demonstrate parallel motor control"""
    print("\n🎯 Running parallel motor demo...")

    await controller.say("I'll now move all my motors at once!")
    await asyncio.sleep(0.5)

    tasks = [
        controller.move(ohbot.HEADNOD, 7, 2),
        controller.move(ohbot.HEADTURN, 7, 2),
        controller.move(ohbot.EYETURN, 7, 2),
        controller.move(ohbot.LIDBLINK, 7, 2),
        controller.move(ohbot.TOPLIP, 7, 2),
        controller.move(ohbot.BOTTOMLIP, 7, 2),
        controller.move(ohbot.EYETILT, 7, 2),
    ]

    await asyncio.gather(*tasks)
    await asyncio.sleep(1)

    tasks = [controller.move(i, 5, 2) for i in range(8)]
    await asyncio.gather(*tasks)
    await controller.say("All motors moved together!")


# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Main entry point"""
    print("="*60)
    print("🤖 Ohbot Azure Controller")
    print("="*60)

    if not os.environ.get("AZURE_SPEECH_KEY"):
        print("\n⚠️  Azure Speech Key not found!")
        print("Set environment variable: export AZURE_SPEECH_KEY='your-key-here'")
        print("And optionally: export AZURE_SPEECH_REGION='eastus'")
        return

    print("\n📡 Initializing Ohbot hardware...")
    if not ohbot.init():
        print("❌ Ohbot hardware not found")
        return

    try:
        azure = AzureSpeechManager()
    except Exception as e:
        print(f"❌ Azure initialization failed: {e}")
        return

    controller = AsyncOhbotController(azure)

    try:
        await controller.start()

        print("\n🎯 Select demo:")
        print("1. Basic demo (speech + movement)")
        print("2. Conversation demo (STT + TTS)")
        print("3. Parallel motor demo")
        print("4. All demos")

        choice = input("\nEnter choice (1-4): ").strip()

        if choice == "1":
            await demo_basic(controller)
        elif choice == "2":
            await demo_conversation(controller)
        elif choice == "3":
            await demo_parallel_motors(controller)
        elif choice == "4":
            await demo_basic(controller)
            await asyncio.sleep(1)
            await demo_parallel_motors(controller)
            await asyncio.sleep(1)
            await demo_conversation(controller)
        else:
            print("Invalid choice")

    finally:
        await controller.stop()
        print("\n✅ All done!")


if __name__ == "__main__":
    asyncio.run(main())
