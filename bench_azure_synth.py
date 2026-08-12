#!/usr/bin/env python3
"""
bench_azure_synth.py  -  Is a new SpeechSynthesizer per sentence costing us?

WHY THIS EXISTS
  ohbot_azure.py builds a brand new speechsdk.SpeechSynthesizer inside
  synthesize_to_file_with_visemes(), so every sentence Yobot speaks opens a
  fresh connection to Azure. This measures whether that matters, using the
  same voice, same SSML and same viseme callback as the real code.

  NO ROBOT NEEDED. No motors move, no sound plays. Safe to run on Windows,
  Mac or the Pi while the Greeter is stopped.

WHAT IT COMPARES

  A  CURRENT        new synthesizer each sentence, render to file
                    (exactly what ohbot_azure.py does today)
  B  REUSED         one synthesizer, reused
  C  REUSED + WARM  one synthesizer, connection opened in advance
  D  STREAMING      reused + warm, but audio pulled as it is generated
                    instead of waiting for the whole file

  A, B and C report when synthesis FINISHED, because that is the earliest
  the current code could start playing. D reports when the FIRST AUDIO
  arrived, because streaming can start there.

  All four count viseme events, so you can confirm lip sync data still
  arrives in every mode - including while streaming.

  Each run uses a DIFFERENT sentence. Repeating one sentence lets Azure
  serve a cached result, which is how an earlier test of mine produced a
  number that was far too good.

SETUP
  Needs the Azure Speech SDK, which ohbot_azure.py already requires:
      pip install azure-cognitiveservices-speech

RUN
      python bench_azure_synth.py
"""

import os
import statistics
import sys
import tempfile
import time
from pathlib import Path

try:
    import azure.cognitiveservices.speech as speechsdk
except ImportError:
    print("Azure Speech SDK not found. Install with:")
    print("   pip install azure-cognitiveservices-speech")
    sys.exit(1)


# ---------------------------------------------------------------- config
# The key is read from the .env file next to this script, the same one
# ohbot_azure.py uses. Nothing to paste.

HERE = Path(__file__).resolve().parent


def load_env():
    """Minimal .env reader - no extra packages needed."""
    values = {}
    env_path = HERE / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            values[k.strip()] = v.strip().strip('"').strip("'")
    return values


ENV = load_env()
AZURE_KEY = os.environ.get("AZURE_SPEECH_KEY") or ENV.get("AZURE_SPEECH_KEY", "")
AZURE_REGION = (os.environ.get("AZURE_SPEECH_REGION")
                or ENV.get("AZURE_SPEECH_REGION", "eastus"))

# Mirrors AzureSpeechManager in ohbot_azure.py.
VOICE = "en-US-JennyMultilingualNeural"
LOCALE = "en-US"
PITCH = "+2%"

# Different every run, so nothing can be served from a cache.
SENTENCES = [
    "The garden club meets on the first Tuesday of every month.",
    "There is a farmers market by the river on Saturday mornings.",
    "The pool is open from seven in the morning until dusk.",
    "Yoga class has moved to the upstairs room this week.",
    "The library keeps a shelf of books in both English and Spanish.",
    "Trivia night starts at six thirty in the clubhouse.",
    "The walking group leaves from the front gate at eight.",
]

RUNS = 5


def make_ssml(text):
    """Same shape as AzureSpeechManager._make_ssml()."""
    return (
        '<speak version="1.0" '
        'xmlns="http://www.w3.org/2001/10/synthesis" '
        f'xml:lang="{LOCALE}">\n'
        f'  <voice name="{VOICE}">\n'
        f'    <lang xml:lang="{LOCALE}">\n'
        f'      <prosody pitch="{PITCH}">{text}</prosody>\n'
        '    </lang>\n'
        '  </voice>\n'
        '</speak>'
    )


def make_config():
    cfg = speechsdk.SpeechConfig(subscription=AZURE_KEY, region=AZURE_REGION)
    cfg.speech_synthesis_voice_name = VOICE
    cfg.set_property(
        speechsdk.PropertyId.SpeechServiceResponse_RequestWordLevelTimestamps,
        "true")
    return cfg


def safe_unlink(path):
    """
    Windows keeps the wav locked until the synthesizer that wrote it is
    released, and sometimes for a moment after. Not worth crashing over -
    leftovers live in the temp folder and Windows clears them itself.
    """
    for _ in range(5):
        try:
            os.unlink(path)
            return
        except (PermissionError, OSError):
            time.sleep(0.1)


def attach_visemes(synth, box):
    """Record viseme events exactly as ohbot_azure.py does."""
    def cb(evt):
        box.append({"viseme_id": evt.viseme_id,
                    "audio_offset": evt.audio_offset,
                    "at": time.perf_counter()})
    synth.viseme_received.connect(cb)


def open_connection(synth):
    """Pre-open the websocket so the first sentence doesn't pay for it."""
    try:
        conn = speechsdk.Connection.from_speech_synthesizer(synth)
        conn.open(True)
        time.sleep(0.5)          # give the handshake a moment to land
        return conn
    except Exception as e:
        print(f"    (could not pre-open connection: {e})")
        return None


# ---------------------------------------------------------------- variants

def variant_a(sentences):
    """New synthesizer every sentence, to file. Today's behaviour."""
    times, viseme_counts = [], []
    cfg = make_config()
    for text in sentences:
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()
        audio_cfg = speechsdk.audio.AudioOutputConfig(filename=tmp.name)

        t0 = time.perf_counter()
        synth = speechsdk.SpeechSynthesizer(speech_config=cfg,
                                            audio_config=audio_cfg)
        visemes = []
        attach_visemes(synth, visemes)
        result = synth.speak_ssml(make_ssml(text))
        elapsed = time.perf_counter() - t0

        if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
            print(f"    synthesis failed: {result.reason}")
            return None, None
        times.append(elapsed)
        viseme_counts.append(len(visemes))

        # Release the synthesizer BEFORE deleting the file it wrote,
        # otherwise Windows refuses.
        result = None
        synth = None
        audio_cfg = None
        safe_unlink(tmp.name)
    return times, viseme_counts


def variant_reused(sentences, warm):
    """One synthesizer for all sentences. Optionally pre-open the connection."""
    cfg = make_config()
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    audio_cfg = speechsdk.audio.AudioOutputConfig(filename=tmp.name)
    synth = speechsdk.SpeechSynthesizer(speech_config=cfg,
                                        audio_config=audio_cfg)
    visemes = []
    attach_visemes(synth, visemes)

    conn = open_connection(synth) if warm else None

    times, viseme_counts = [], []
    for text in sentences:
        visemes.clear()
        t0 = time.perf_counter()
        result = synth.speak_ssml(make_ssml(text))
        elapsed = time.perf_counter() - t0

        if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
            print(f"    synthesis failed: {result.reason}")
            return None, None
        times.append(elapsed)
        viseme_counts.append(len(visemes))

    if conn:
        try:
            conn.close()
        except Exception:
            pass
    synth = None
    audio_cfg = None
    safe_unlink(tmp.name)
    return times, viseme_counts


def variant_streaming(sentences):
    """
    Reused + warm, but pull audio as it is produced.
    Measures time to the FIRST audio chunk, not the whole file.
    """
    cfg = make_config()
    cfg.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Riff16Khz16BitMonoPcm)

    # audio_config=None means "don't play it, hand us the data".
    synth = speechsdk.SpeechSynthesizer(speech_config=cfg, audio_config=None)
    visemes = []
    attach_visemes(synth, visemes)

    conn = open_connection(synth)

    times, viseme_counts, first_viseme_times = [], [], []
    for text in sentences:
        visemes.clear()
        t0 = time.perf_counter()

        # Returns as soon as synthesis STARTS, not when it finishes.
        result = synth.start_speaking_ssml_async(make_ssml(text)).get()
        stream = speechsdk.AudioDataStream(result)

        buf = bytes(3200)
        filled = stream.read_data(buf)        # blocks until first audio
        t_first = time.perf_counter() - t0

        total = filled
        while filled > 0:                     # drain the rest
            filled = stream.read_data(buf)
            total += filled

        times.append(t_first)
        viseme_counts.append(len(visemes))
        if visemes:
            first_viseme_times.append(visemes[0]["at"] - t0)

    if conn:
        try:
            conn.close()
        except Exception:
            pass
    return times, viseme_counts, first_viseme_times


# ---------------------------------------------------------------- main

def main():
    if not AZURE_KEY:
        print("No AZURE_SPEECH_KEY found in .env or the environment.")
        sys.exit(1)

    sentences = SENTENCES[:RUNS]
    print(f"Region: {AZURE_REGION}   Voice: {VOICE}")
    print(f"Key: ...{AZURE_KEY[-4:]}   Sentences: {len(sentences)} (all different)\n")

    results = {}

    print("A  CURRENT       new synthesizer each sentence ...", flush=True)
    t, v = variant_a(sentences)
    if t:
        results["A  current (new synth each time)"] = (t, v)
        print(f"   median {statistics.median(t):.2f}s   "
              f"visemes {min(v)}-{max(v)} per sentence\n")

    print("B  REUSED        one synthesizer ...", flush=True)
    t, v = variant_reused(sentences, warm=False)
    if t:
        results["B  reused synthesizer"] = (t, v)
        print(f"   median {statistics.median(t):.2f}s   "
              f"visemes {min(v)}-{max(v)} per sentence\n")

    print("C  REUSED+WARM   one synthesizer, connection pre-opened ...", flush=True)
    t, v = variant_reused(sentences, warm=True)
    if t:
        results["C  reused + warm connection"] = (t, v)
        print(f"   median {statistics.median(t):.2f}s   "
              f"visemes {min(v)}-{max(v)} per sentence\n")

    print("D  STREAMING     reused + warm, first audio chunk ...", flush=True)
    try:
        t, v, fv = variant_streaming(sentences)
        if t:
            results["D  streaming (to FIRST audio)"] = (t, v)
            print(f"   median {statistics.median(t):.2f}s   "
                  f"visemes {min(v)}-{max(v)} per sentence")
            if fv:
                print(f"   first viseme arrived at {statistics.median(fv):.2f}s")
            print()
    except Exception as e:
        print(f"   streaming test failed: {type(e).__name__}: {e}\n")

    if not results:
        print("Nothing succeeded.")
        return

    print("=" * 64)
    print("  TIME UNTIL AUDIO COULD START  (median, lower is better)")
    print("=" * 64)

    baseline = statistics.median(results["A  current (new synth each time)"][0])
    for name, (times, counts) in results.items():
        med = statistics.median(times)
        bar = "#" * max(1, int(med * 25))
        tag = "  <- today" if name.startswith("A") else f"  saves {baseline - med:.2f}s"
        print(f"  {name:<34} {med:.2f}s {bar}{tag}")

    best_name = min(results, key=lambda n: statistics.median(results[n][0]))
    best = statistics.median(results[best_name][0])
    print(f"\n  Best: {best_name.strip()}")
    print(f"  Saving vs today: {baseline - best:.2f}s per sentence")

    all_counts = [c for _, counts in results.values() for c in counts]
    if all_counts and min(all_counts) > 0:
        print(f"\n  Visemes arrived in every mode ({min(all_counts)}-{max(all_counts)} "
              f"per sentence) - lip sync data is not lost by any of these changes.")
    else:
        print("\n  WARNING: some mode produced no visemes. Check before adopting it.")

    print("\n  Run twice. Network jitter can be larger than the effect.\n")


if __name__ == "__main__":
    main()
