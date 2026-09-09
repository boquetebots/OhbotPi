#!/usr/bin/env python3
"""
voice_cache.py — Yobot's offline voice pantry
Version: 1.0.0  (2026-09-02)

WHAT THIS IS, IN PLAIN ENGLISH
------------------------------
Normally when Yobot speaks, he asks Microsoft Azure over the internet to
turn the words into sound. No internet, no voice.

This file lets us do that shopping trip *early*. While the internet is
good, we render each line Yobot will say into a .wav file and save it,
along with the "viseme" data (the list of mouth shapes and their exact
timings) that Azure sends back at the same time.

Later — with the WiFi switched off entirely — we just play the .wav and
read the mouth shapes back off disk. Same voice, same lip sync, no
network at all.

Think of it as pre-recording the announcements instead of relying on a
live announcer with a phone line.

WHAT IT DOES NOT DO
-------------------
Nothing here talks to Azure. This file only reads and writes files on
disk. `prerender_cues.py` is the one that does the Azure shopping trip.
This file has no effect on any existing program unless that program
imports it — and none of them do.

THE FILES IT MAKES
------------------
    voice_cache/en_3f9a1c....wav    the audio
    voice_cache/en_3f9a1c....json   the mouth shapes + the original text

The long name is a fingerprint (a hash) of the exact text and language.
Change so much as a comma in the line and it becomes a different
fingerprint, so you get a fresh render rather than yesterday's audio.
"""

import os
import json
import hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(HERE, 'voice_cache')

# Bumped only if the stored format ever changes, so old files are ignored
# rather than misread.
FORMAT_VERSION = 1


def _normalise(text: str) -> str:
    """Collapse whitespace so a stray newline or double space in the cue
    file doesn't force a pointless re-render of identical-sounding text."""
    return ' '.join((text or '').split())


def fingerprint(text: str, language: str = 'en') -> str:
    """The short name used for this line's two files."""
    lang = (language or 'en').lower()
    blob = f"v{FORMAT_VERSION}|{lang}|{_normalise(text)}"
    digest = hashlib.sha1(blob.encode('utf-8')).hexdigest()[:16]
    return f"{lang}_{digest}"


def paths(text: str, language: str = 'en'):
    """Where this line's audio and mouth-shape files live (they may not
    exist yet — this just works out the names)."""
    stem = os.path.join(CACHE_DIR, fingerprint(text, language))
    return stem + '.wav', stem + '.json'


def is_cached(text: str, language: str = 'en') -> bool:
    """True only if BOTH files are present and neither is empty. A
    half-written pair from an interrupted render counts as not cached."""
    wav, meta = paths(text, language)
    try:
        return (os.path.getsize(wav) > 0) and (os.path.getsize(meta) > 0)
    except OSError:
        return False


def load(text: str, language: str = 'en'):
    """Fetch a pre-rendered line.

    Returns (wav_path, visemes) — or None if it isn't in the pantry.
    Never raises: a corrupt or unreadable entry is reported as a miss so
    the caller can fall back gracefully instead of crashing mid-demo.
    """
    wav, meta = paths(text, language)
    if not is_cached(text, language):
        return None
    try:
        with open(meta, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if data.get('format_version') != FORMAT_VERSION:
            return None
        return wav, data.get('visemes', [])
    except Exception:                                        # noqa: BLE001
        return None


def save(text: str, language: str, visemes) -> str:
    """Write the mouth-shape sidecar for a line whose .wav has just been
    rendered. Returns the .wav path the caller should have written to.

    Call `paths()` first, hand that .wav path to Azure, then call this.
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    wav, meta = paths(text, language)
    payload = {
        'format_version': FORMAT_VERSION,
        'language': (language or 'en').lower(),
        'text': text,                      # kept so a human can read the
                                           # folder and see what each file is
        'visemes': list(visemes or []),
    }
    tmp = meta + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    os.replace(tmp, meta)                  # atomic: never leaves a half file
    return wav


def stats():
    """A quick count for the status line on the show page."""
    if not os.path.isdir(CACHE_DIR):
        return {'entries': 0, 'bytes': 0, 'dir': CACHE_DIR}
    n = total = 0
    for name in os.listdir(CACHE_DIR):
        if name.endswith('.wav'):
            n += 1
            try:
                total += os.path.getsize(os.path.join(CACHE_DIR, name))
            except OSError:
                pass
    return {'entries': n, 'bytes': total, 'dir': CACHE_DIR}


if __name__ == '__main__':
    s = stats()
    print(f"Voice cache: {s['entries']} lines, "
          f"{s['bytes']/1_000_000:.1f} MB")
    print(f"Folder: {s['dir']}")
