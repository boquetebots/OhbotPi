#!/usr/bin/env python3
"""
Ohbot Azure Controller - Async-First with Azure Speech Services
Version: 1.0.0
Platform: Raspberry Pi 5
Features: Azure STT/TTS, Viseme-based lip sync, Async motor control
"""

import asyncio
import os
import sys
import tempfile
import threading
import time
import wave
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, List, Tuple

# Global lock — all calls into the ohbot serial library (ohbot.move,
# ohbot.baseColour, ohbot.reset) must hold this lock.  The Ohbot C extension
# is NOT thread-safe: two threads calling it simultaneously causes a
# segmentation fault.  Both gui_server.py and this module import this lock.
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
    # Bottom lip servo range adjusted in MotorDefinitionsv21.omd so
    # position 5 produces the same physical closed position as top lip.
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

    @classmethod
    def get_lip_positions(cls, viseme_id: int) -> Tuple[float, float]:
        """
        Get (top_lip, bottom_lip) positions for a viseme.

        Returns:
            Tuple of (top_lip_pos, bottom_lip_pos) in 0-10 range
        """
        return cls.VISEME_MAP.get(viseme_id, (5, 5))


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

    # Words that need IPA correction in English synthesis
    # Add entries here if Azure mispronounces a word specific to your location or use case.
    # Example: "Ohbot": '<phoneme alphabet="ipa" ph="oʊbɒt">Ohbot</phoneme>'
    PHONEME_FIXES = {
    }

    def _make_ssml(self, text: str) -> str:
        """Wrap text in SSML with per-voice pitch and phoneme corrections."""
        voice = self.speech_config.speech_synthesis_voice_name
        pitch = self.VOICE_PITCH.get(voice, "+0%")

        ssml_text = text
        if voice.startswith("en-"):
            for word, replacement in self.PHONEME_FIXES.items():
                ssml_text = ssml_text.replace(word, replacement)

        return (
            '<speak version="1.0" '
            'xmlns="http://www.w3.org/2001/10/synthesis" '
            'xml:lang="en-US">\n'
            f'  <voice name="{voice}">\n'
            f'    <prosody pitch="{pitch}">{ssml_text}</prosody>\n'
            '  </voice>\n'
            '</speak>'
        )

    async def recognize_once(self, timeout: float = 10.0, language: str = None) -> str:
        """Recognize speech from microphone (single utterance)."""
        audio_config = speechsdk.audio.AudioConfig(device_name="plughw:3,0")

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

    def synthesize_to_file_with_visemes(self, text: str, output_file: str) -> List[Dict]:
        """Synthesize speech to file and capture viseme events."""
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

        ssml   = self._make_ssml(text)
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

    async def say(self, text: str, lip_sync: bool = True) -> None:
        """Speak text using Azure TTS with optional viseme-based lip sync."""
        if not text or text.isspace():
            return

        async with self.speech_lock:
            self.is_speaking = True

            try:
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                    temp_file = f.name

                print(f"🗣️ Speaking: {text}")

                visemes = await asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    self.azure.synthesize_to_file_with_visemes,
                    text,
                    temp_file
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

                os.unlink(temp_file)

            finally:
                self.is_speaking = False
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
        """Play audio file asynchronously using aplay"""
        process = await asyncio.create_subprocess_exec(
            'aplay', '-D', 'plug:default', audio_file,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await process.wait()

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
    await controller.say("Hello! I am Ohbot running on Azure Speech Services.")
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
