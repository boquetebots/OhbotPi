#!/usr/bin/env python3
"""
test_pronunciation.py — Hear the pronunciation fixes before you deploy them.

This makes a set of WAV files: each tricky word said the WRONG way (no fix)
and then the RIGHT way (with the fix from PHONEME_FIXES in ohbot_azure.py),
so you can play them back to back and compare.

Nothing here touches the robot's motors, so it's safe to run at any time —
you don't need to stop the Greeter or the GUI first.

HOW TO RUN IT (on the Pi):

    cd ~/Projects/Ohbot
    source venv/bin/activate
    python3 test_pronunciation.py

The files land in  ~/Projects/Ohbot/pronunciation_tests/  and the script
prints the exact play commands at the end. Or just double-click
deploy_pronunciation_fix.command on the Mac, which does the whole lot.

IF A WORD STILL SOUNDS WRONG:
Don't edit this file. Edit the PHONEME_FIXES table near the top of
ohbot_azure.py, then run this again. See HANDOFF_pronunciation_guide.md.
"""

import os
import sys
from pathlib import Path

try:
    import azure.cognitiveservices.speech as speechsdk
except ImportError:
    print("❌ Azure Speech SDK not found.")
    print("   Did you forget:  source venv/bin/activate")
    sys.exit(1)

# Load the .env file sitting next to this script, so the API keys are found
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

# Pull the real fix table straight out of ohbot_azure.py, so what you hear
# here is exactly what the robot will say. No second copy to keep in sync.
sys.path.insert(0, str(Path(__file__).parent))
from ohbot_azure import AzureSpeechManager  # noqa: E402

SPEECH_KEY    = os.environ.get("AZURE_SPEECH_KEY")
SPEECH_REGION = os.environ.get("AZURE_SPEECH_REGION", "eastus")
VOICE         = "en-US-JennyMultilingualNeural"
PITCH         = "+2%"

OUTPUT_DIR = Path(__file__).parent / "pronunciation_tests"

# Sentences to test. Use real sentences the robot actually says, so you hear
# each word in context — a word on its own can sound fine and still be wrong
# in the middle of a sentence.
SENTENCES = [
    ("boquete",
     "Welcome to the Biblioteca de Boquete, here in Boquete, Panama."),

    ("rincon",
     "This is the Rincon Clubhouse, the newest Rincon Clubhouse in Panama."),

    ("rincones",
     "There are Rincones all over Panama, and the Rincones Clubhouse are "
     "free for every young person."),

    ("all_together",
     "A Rincon Clubhouse is a free after-school space. "
     "There are Rincones all over Panama, and the newest one is right here "
     "at the Biblioteca de Boquete."),
]


def build_ssml(text, use_fix):
    """Wrap text in SSML, with or without the pronunciation fixes applied."""
    if use_fix:
        text = AzureSpeechManager.apply_phoneme_fixes(text)
    return (
        '<speak version="1.0" '
        'xmlns="http://www.w3.org/2001/10/synthesis" '
        'xml:lang="en-US">'
        f'<voice name="{VOICE}">'
        '<lang xml:lang="en-US">'
        f'<prosody pitch="{PITCH}">{text}</prosody>'
        '</lang></voice></speak>'
    )


def synthesize(filename, ssml):
    filepath = OUTPUT_DIR / f"{filename}.wav"
    if filepath.exists():
        filepath.unlink()

    speech_config = speechsdk.SpeechConfig(
        subscription=SPEECH_KEY, region=SPEECH_REGION
    )
    audio_config = speechsdk.audio.AudioOutputConfig(filename=str(filepath))
    synthesizer  = speechsdk.SpeechSynthesizer(
        speech_config=speech_config, audio_config=audio_config
    )

    result = synthesizer.speak_ssml_async(ssml).get()
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return filepath
    print(f"    ❌ Azure said no: {result.reason}")
    if result.reason == speechsdk.ResultReason.Canceled:
        print(f"       {speechsdk.CancellationDetails(result).error_details}")
    return None


def main():
    if not SPEECH_KEY:
        print("❌ AZURE_SPEECH_KEY not found.")
        print("   It should be in the .env file in this folder.")
        sys.exit(1)

    OUTPUT_DIR.mkdir(exist_ok=True)

    print("=" * 64)
    print("  Pronunciation test")
    print("=" * 64)
    print()
    print("  Words currently being corrected:")
    if AzureSpeechManager.PHONEME_FIXES:
        for word, ipa in AzureSpeechManager.PHONEME_FIXES.items():
            print(f"    {word:<12} → {ipa}")
    else:
        print("    (none — PHONEME_FIXES in ohbot_azure.py is empty)")
    print()

    made = []
    for name, sentence in SENTENCES:
        print(f"  {name}:")
        print(f"    \"{sentence[:60]}...\"")
        for label, use_fix in (("before", False), ("after", True)):
            path = synthesize(f"{name}_{label}", build_ssml(sentence, use_fix))
            if path:
                print(f"    ✅ {label:<6} {path.name}")
                made.append(path)
        print()

    if not made:
        print("Nothing was generated — see the errors above.")
        sys.exit(1)

    # Pibot runs PiOS Lite, which has no sound server, so plain ALSA aplay
    # works. (The OLD Pi needed pw-play — PipeWire was holding the device and
    # aplay failed with error 524. Not an issue on this build.)
    player = "aplay" if sys.platform.startswith("linux") else "afplay"

    print("=" * 64)
    print("  Listen to them — 'before' then 'after' for each pair:")
    print()
    for name, _ in SENTENCES:
        print(f"  # {name}")
        print(f"  {player} {OUTPUT_DIR}/{name}_before.wav")
        print(f"  {player} {OUTPUT_DIR}/{name}_after.wav")
        print()
    print("=" * 64)
    print("  'rincones' should sound the SAME before and after —")
    print("  if it changed, something is wrong. Tell Claude.")
    print("=" * 64)


if __name__ == "__main__":
    main()
