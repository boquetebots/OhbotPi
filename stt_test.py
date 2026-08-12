#!/usr/bin/env python3
"""
stt_test.py  -  Can we get bilingual AND fast?

WHAT WE KNOW ALREADY (measured 2026-08-12)
  A  auto-detect, at-start   ~5.5s   works in both languages
  B  locked to one language  ~2.3-3.0s   but mis-hears the other one

  Locking made Yobot fast and a bit deaf. This asks whether Azure's
  CONTINUOUS language identification gives us both.

WHAT IT COMPARES
  A  AT-START LID     what the greeter does on exchange 1 - the 5s window
  B  LOCKED en-US     speed reference, English only
  D  CONTINUOUS LID   same recognize_once call, continuous detection mode
  E  CONTINUOUS LID   continuous recognition, stopped at the first result

  D is the small change - if it works, it's a one-line fix in ohbot_azure.py.
  E is the bigger one, needing a different recognition call, and is here in
  case D turns out not to be supported.

  Modes A, D and E ALTERNATE English and Spanish and report which language
  Azure decided on, because speed is worthless if it mishears the visitor.

  NO ROBOT NEEDED. Microphone only. Stop the Greeter first so they don't
  fight over it.

RUN
      cd D:\\Projects\\OhbotPi2
      python stt_test.py
"""

import os
import statistics
import sys
import threading
import time
from pathlib import Path

try:
    import azure.cognitiveservices.speech as speechsdk
except ImportError:
    print("Azure Speech SDK not found:  pip install azure-cognitiveservices-speech")
    sys.exit(1)


HERE = Path(__file__).resolve().parent
LANGUAGES = ["es-MX", "en-US"]
ROUNDS = 3
TICKS_PER_MS = 10_000


def load_env():
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
KEY = os.environ.get("AZURE_SPEECH_KEY") or ENV.get("AZURE_SPEECH_KEY", "")
REGION = (os.environ.get("AZURE_SPEECH_REGION")
          or ENV.get("AZURE_SPEECH_REGION", "eastus"))


def make_config(continuous_lid=False):
    cfg = speechsdk.SpeechConfig(subscription=KEY, region=REGION)
    cfg.set_property(speechsdk.PropertyId.Speech_SegmentationSilenceTimeoutMs,
                     "500")
    if continuous_lid:
        # 'AtStart' (the default) holds a fixed ~5 second window open.
        # 'Continuous' is meant to keep identifying as speech goes on.
        cfg.set_property(
            speechsdk.PropertyId.SpeechServiceConnection_LanguageIdMode,
            "Continuous")
    return cfg


def detected_language(result):
    try:
        return speechsdk.AutoDetectSourceLanguageResult(result).language or "?"
    except Exception:
        return "?"


# ---------------------------------------------------------------- modes

def listen_once(mode_key):
    """
    mode_key: 'atstart', 'locked-en', or 'continuous'.
    Returns (total_ms, text, language) - text empty if nothing recognised.
    """
    continuous = (mode_key == "continuous")
    cfg = make_config(continuous_lid=continuous)
    audio_cfg = speechsdk.audio.AudioConfig(use_default_microphone=True)

    if mode_key == "locked-en":
        rec = speechsdk.SpeechRecognizer(speech_config=cfg,
                                         audio_config=audio_cfg,
                                         language="en-US")
    else:
        auto = speechsdk.languageconfig.AutoDetectSourceLanguageConfig(
            languages=LANGUAGES)
        rec = speechsdk.SpeechRecognizer(
            speech_config=cfg, audio_config=audio_cfg,
            auto_detect_source_language_config=auto)

    t0 = time.perf_counter()
    result = rec.recognize_once()
    total_ms = (time.perf_counter() - t0) * 1000

    if result.reason == speechsdk.ResultReason.RecognizedSpeech and result.text:
        return total_ms, result.text, detected_language(result)
    return total_ms, "", "-"


def listen_continuous_stream(timeout=20.0):
    """
    Continuous recognition with continuous language ID, stopped as soon as
    the first final result arrives. Returns (total_ms, text, language).
    """
    cfg = make_config(continuous_lid=True)
    auto = speechsdk.languageconfig.AutoDetectSourceLanguageConfig(
        languages=LANGUAGES)
    audio_cfg = speechsdk.audio.AudioConfig(use_default_microphone=True)
    rec = speechsdk.SpeechRecognizer(
        speech_config=cfg, audio_config=audio_cfg,
        auto_detect_source_language_config=auto)

    done = threading.Event()
    got = {}
    t0 = time.perf_counter()

    def on_recognized(evt):
        if got:
            return
        r = evt.result
        if r.reason == speechsdk.ResultReason.RecognizedSpeech and r.text:
            got["ms"] = (time.perf_counter() - t0) * 1000
            got["text"] = r.text
            got["lang"] = detected_language(r)
            done.set()

    rec.recognized.connect(on_recognized)
    rec.start_continuous_recognition()
    done.wait(timeout)
    try:
        rec.stop_continuous_recognition()
    except Exception:
        pass

    if got:
        return got["ms"], got["text"], got["lang"]
    return (time.perf_counter() - t0) * 1000, "", "-"


# ---------------------------------------------------------------- runner

def run_mode(label, runner, bilingual):
    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"{'=' * 60}")

    totals, langs, misses = [], [], 0

    for i in range(ROUNDS):
        if not bilingual:
            # A locked recognizer doesn't report a detected language, so
            # there is nothing to check. Round 3 still tests the pause.
            want, expect = "ENGLISH", None
            hint = ("say something short in English" if i < 2 else
                    "say a LONG sentence WITH A PAUSE in the middle")
        elif i == 2:
            # The pause test. Continuous recognition segments on silence, so
            # this is where mode E would show its weakness: if it stops at
            # the first final result, we get only the half before the pause.
            want, expect = "ENGLISH", "en-US"
            hint = ("say a LONG sentence WITH A PAUSE in the middle, e.g.\n"
                    "         'can you tell me ... (pause) ... where the "
                    "bathrooms are'")
        else:
            want = "ENGLISH" if i == 0 else "SPANISH"
            hint = ("say something short in English, e.g. 'where is the park'"
                    if i == 0 else
                    "say something short in Spanish, e.g. 'donde esta el parque'")
            expect = "en-US" if i == 0 else "es-MX"

        input(f"\n  Round {i + 1}/{ROUNDS} [{want}] - press Enter, then {hint}: ")
        print("  listening...", flush=True)

        try:
            total, text, lang = runner()
        except Exception as e:
            print(f"  NOT SUPPORTED: {type(e).__name__}: {e}")
            return {"label": label, "supported": False}

        if not text:
            misses += 1
            print(f"  nothing recognised  ({total:.0f}ms)")
            continue

        if expect is None:
            ok = "n/a"          # locked mode - no language to get wrong
        else:
            ok = "OK " if lang.lower().startswith(expect[:2].lower()) else "WRONG"
        totals.append(total)
        langs.append((expect, lang, ok))
        print(f"  \"{text}\"")
        if i == 2:
            print(f"  {total:.0f}ms   heard as {lang}   [{ok}]"
                  f"   <-- did it get the WHOLE sentence?")
        else:
            print(f"  {total:.0f}ms   heard as {lang}   [{ok}]")

    return {"label": label,
            "supported": True,
            "totals": totals,
            "langs": langs,
            "misses": misses,
            "median": statistics.median(totals) if totals else None}


def main():
    if not KEY:
        print("No AZURE_SPEECH_KEY found in .env or the environment.")
        sys.exit(1)

    print(f"Region: {REGION}   Key: ...{KEY[-4:]}   Rounds per mode: {ROUNDS}")
    print("\nKeep each phrase SHORT. Short answers are where the waste shows.")
    print("Stop the Greeter first so it isn't holding the microphone.")

    results = []
    results.append(run_mode("A  AT-START LID (greeter's exchange 1)",
                            lambda: listen_once("atstart"), bilingual=True))
    results.append(run_mode("B  LOCKED en-US (speed reference)",
                            lambda: listen_once("locked-en"), bilingual=False))
    results.append(run_mode("D  CONTINUOUS LID, recognize_once",
                            lambda: listen_once("continuous"), bilingual=True))
    results.append(run_mode("E  CONTINUOUS LID, continuous recognition",
                            listen_continuous_stream, bilingual=True))

    print(f"\n\n{'=' * 60}")
    print("  RESULTS")
    print(f"{'=' * 60}")

    for r in results:
        if not r.get("supported"):
            print(f"  {r['label'][:40]:<42} not supported")
            continue
        if r["median"] is None:
            print(f"  {r['label'][:40]:<42} nothing recognised")
            continue
        wrong = sum(1 for _, _, ok in r["langs"] if ok == "WRONG")
        note = ""
        if r["misses"]:
            note += f"  {r['misses']} missed"
        if wrong:
            note += f"  {wrong} wrong language"
        bar = "#" * max(1, int(r["median"] / 200))
        print(f"  {r['label'][:40]:<42} {r['median']:>6.0f}ms {bar}{note}")

    print("\n  What to look for:")
    print("   * A mode that is FAST and gets the language right both times")
    print("     is the answer - we can be quick without going deaf.")
    print("   * If D and E are as slow as A, continuous LID doesn't help and")
    print("     the choice really is speed versus bilingual reliability.")
    print("   * If D says 'not supported', that setting needs continuous")
    print("     recognition, and E is the only route.\n")


if __name__ == "__main__":
    main()
