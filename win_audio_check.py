#!/usr/bin/env python3
"""
win_audio_check.py — why is the start of Yobot's speech getting clipped?

Run it with:   .\\yobot.bat  ...no. Run it directly:

    cd D:\\Projects\\OhbotPi2
    & "$HOME\\yobot-venv\\Scripts\\python.exe" win_audio_check.py

No robot needed — this is purely about sound. Nothing moves.

WHAT IT'S SORTING OUT
---------------------
"The first fraction of a second gets cut off" has three possible causes,
and they need completely different fixes:

  A. The WAV file Azure made is genuinely missing its start.
     -> The problem is upstream, in synthesis. Test 1 catches this.

  B. Windows powers its speaker down when idle, and the first sound after
     a quiet spell wakes it up too slowly — so the beginning is eaten by
     hardware that isn't listening yet.
     -> Test 2 catches this: only the FIRST play is clipped.

  C. Something clips every single playback, every time.
     -> Test 2 catches this too: all three plays are clipped equally.

Test 3 then tries the likely fix for B, so you can hear whether it works
before we change any real code.

Read the numbers, then trust your ears on tests 2 and 3.
"""

import array
import os
import sys
import time
import wave

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

PHRASE = "One two three four five. Testing the start of my speech."
RAW_WAV = os.path.join(SCRIPT_DIR, "_audio_check_raw.wav")
PADDED_WAV = os.path.join(SCRIPT_DIR, "_audio_check_padded.wav")
PAD_MS = 300


# ─────────────────────────────────────────────────────────────────────────────
# WAV inspection — plain stdlib, no extra packages
# ─────────────────────────────────────────────────────────────────────────────

def describe_wav(path):
    """Print the file's shape and measure how much silence is at the front."""
    with wave.open(path, 'rb') as w:
        channels = w.getnchannels()
        width = w.getsampwidth()
        rate = w.getframerate()
        frames = w.getnframes()
        raw = w.readframes(frames)

    duration = frames / float(rate)
    print(f"    format   : {rate} Hz, {channels} channel(s), {width*8}-bit")
    print(f"    length   : {duration:.2f} seconds")

    if width != 2:
        print("    (can only measure silence on 16-bit audio — skipping)")
        return duration, None

    samples = array.array('h')
    samples.frombytes(raw)

    # Walk forward until the audio gets meaningfully loud. 1% of full scale
    # is well above dither/noise and well below speech.
    threshold = int(32767 * 0.01)
    first_loud = None
    for i, s in enumerate(samples):
        if abs(s) > threshold:
            first_loud = i
            break

    if first_loud is None:
        print("    ** the file is silent all the way through **")
        return duration, None

    lead_ms = (first_loud / channels) / rate * 1000
    print(f"    silence at the start: {lead_ms:.0f} ms")
    return duration, lead_ms


def pad_with_silence(src, dst, pad_ms):
    """Copy a WAV, adding silence to the front."""
    with wave.open(src, 'rb') as w:
        params = w.getparams()
        raw = w.readframes(w.getnframes())

    silent_frames = int(params.framerate * pad_ms / 1000)
    silence = b'\x00' * (silent_frames * params.nchannels * params.sampwidth)

    with wave.open(dst, 'wb') as out:
        out.setparams(params)
        out.writeframes(silence + raw)


def play(path):
    import winsound
    winsound.PlaySound(path, winsound.SND_FILENAME)


# ─────────────────────────────────────────────────────────────────────────────

def main():
    import platform
    if platform.system() != 'Windows':
        print("This check is about Windows audio — run it on the PC.")
        sys.exit(1)

    print("=" * 68)
    print("  Yobot audio start-clipping check")
    print("=" * 68)

    # ── Make the file ────────────────────────────────────────────────────
    print("\nAsking Azure for a test phrase...")
    print(f'  "{PHRASE}"')

    import yobot_core  # noqa: F401 — loads the .env keys
    if not os.environ.get("AZURE_SPEECH_KEY"):
        print("\n[X] AZURE_SPEECH_KEY not found — is .env in this folder?")
        sys.exit(1)

    from ohbot_azure import AzureSpeechManager
    azure = AzureSpeechManager()
    azure.synthesize_to_file_with_visemes(PHRASE, RAW_WAV)

    # ── TEST 1: is the file itself intact? ───────────────────────────────
    print("\n" + "-" * 68)
    print("TEST 1 — the file Azure produced")
    print("-" * 68)
    duration, lead_ms = describe_wav(RAW_WAV)

    print()
    if lead_ms is None:
        print("  Couldn't measure the lead-in.")
    elif lead_ms < 20:
        print("  >> The speech starts IMMEDIATELY — there's no run-up at all.")
        print("     That's normal for Azure, but it means any delay in waking")
        print("     the speaker eats real words instead of silence.")
    else:
        print(f"  >> There's already {lead_ms:.0f} ms of silence before the speech.")
        print("     If you're still losing words, more than that is being")
        print("     swallowed — which points at the sound device, not the file.")

    # ── TEST 2: first play vs. later plays ───────────────────────────────
    print("\n" + "-" * 68)
    print("TEST 2 — the same file, three times, with a pause between")
    print("-" * 68)
    print("\n  LISTEN CAREFULLY. The question is only:")
    print("  does the FIRST one sound different from the other two?\n")
    input("  Press Enter when you're ready to listen... ")

    for n in (1, 2, 3):
        print(f"\n    play {n} of 3...")
        play(RAW_WAV)
        if n < 3:
            time.sleep(1.5)

    print("\n  What did you hear?")
    print("    - Only #1 clipped, #2 and #3 clean")
    print("        -> Windows is powering the speaker down between sounds.")
    print("           Test 3 should fix it.")
    print("    - All three clipped the same amount")
    print("        -> Something clips every playback. Test 3 will still")
    print("           tell us whether padding is enough.")
    print("    - None clipped")
    print("        -> The clipping only happens in the middle of a")
    print("           conversation. Tell me and we'll look at that instead.")

    # ── TEST 3: does a run-up of silence fix it? ─────────────────────────
    print("\n" + "-" * 68)
    print(f"TEST 3 — the same audio with {PAD_MS} ms of silence glued on the front")
    print("-" * 68)
    pad_with_silence(RAW_WAV, PADDED_WAV, PAD_MS)
    print(f"\n  This gives the speaker {PAD_MS} ms to wake up before the first word.")
    print("  If this sounds complete, that's our fix.\n")
    input("  Press Enter to listen... ")

    print("\n    playing padded version...")
    play(PADDED_WAV)
    time.sleep(1.5)
    print("    playing padded version again...")
    play(PADDED_WAV)

    # ── Wrap up ──────────────────────────────────────────────────────────
    print("\n" + "=" * 68)
    print("  Done. Tell me:")
    print("    1. the 'silence at the start' number above")
    print("    2. whether only the FIRST play in test 2 was clipped")
    print("    3. whether test 3 sounded complete")
    print("=" * 68)
    print(f"\n  The two test files were left in the project folder so you can")
    print(f"  also open them in a media player if you want:")
    print(f"    {os.path.basename(RAW_WAV)}")
    print(f"    {os.path.basename(PADDED_WAV)}")
    print("  They're safe to delete.\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
