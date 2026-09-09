#!/usr/bin/env python3
"""
prerender_cues.py — the shopping trip. RUN THIS WHILE THE INTERNET IS GOOD.
Version: 1.0.0  (2026-09-02)

Reads demo_cues.json and asks Azure to record every line, in English and
Spanish, into the voice_cache folder. After this has run once, the show
needs no internet at all.

    python3 prerender_cues.py            render anything not already done
    python3 prerender_cues.py --force    re-record everything from scratch
    python3 prerender_cues.py --check    render nothing, just report

Safe to run over and over. A line already in the cache is skipped, so
re-running after editing one cue only costs you that one line.

This touches no other program. It only adds files to voice_cache/.
"""

import os
import sys
import json
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import voice_cache                                            # noqa: E402

CUE_FILE = os.path.join(HERE, 'demo_cues.json')


def load_cues():
    if not os.path.exists(CUE_FILE):
        print("❌ demo_cues.json not found next to this script.")
        sys.exit(1)
    with open(CUE_FILE, encoding='utf-8') as f:
        return json.load(f).get('cues', [])


def lines_from(cues):
    """Flatten the cue list into (cue_id, language, text) jobs.

    A cue with 'lang_lock' is only ever spoken in that one language (the
    Spanish greeting, for instance), so we record it once instead of
    twice — and never in the wrong accent.
    """
    out = []
    for cue in cues:
        lock = cue.get('lang_lock')
        for lang in ((lock,) if lock else ('en', 'es')):
            text = (cue.get(f'text_{lang}') or '').strip()
            if text:
                out.append((cue.get('id', '?'), lang, text))
    return out


def main():
    force = '--force' in sys.argv
    check_only = '--check' in sys.argv

    jobs = lines_from(load_cues())
    todo = [j for j in jobs if force or not voice_cache.is_cached(j[2], j[1])]

    print(f"\n{len(jobs)} lines in demo_cues.json")
    print(f"{len(jobs) - len(todo)} already recorded, {len(todo)} to do\n")

    if check_only:
        for cid, lang, text in jobs:
            mark = "✅" if voice_cache.is_cached(text, lang) else "❌"
            print(f"  {mark} {cid:<11} [{lang}]  {text[:56]}...")
        s = voice_cache.stats()
        print(f"\nCache: {s['entries']} files, {s['bytes']/1_000_000:.1f} MB")
        print("Nothing rendered (--check).")
        return

    if not todo:
        print("✅ Everything is already recorded. You are ready to go offline.")
        return

    # Imported late and inside a try, so that --check still works on a
    # machine with no keys and no Azure library installed.
    try:
        from ohbot_azure import AzureSpeechManager
    except BaseException as e:                               # noqa: BLE001
        print(f"❌ Could not load the Azure speech code: {e}")
        print("   Are you using Yobot's Python?  ~/yobot-venv/bin/python3")
        sys.exit(1)

    try:
        azure = AzureSpeechManager()
    except BaseException as e:                               # noqa: BLE001
        print(f"❌ Could not start Azure: {e}")
        print("   Check your key in the Launcher's Settings page, and that")
        print("   this computer is online. THIS STEP NEEDS THE INTERNET.")
        sys.exit(1)

    os.makedirs(voice_cache.CACHE_DIR, exist_ok=True)
    done = failed = 0

    for i, (cid, lang, text) in enumerate(todo, 1):
        wav, _ = voice_cache.paths(text, lang)
        print(f"[{i}/{len(todo)}] {cid} [{lang}] … ", end='', flush=True)
        try:
            visemes = azure.synthesize_to_file_with_visemes(text, wav, lang)
            voice_cache.save(text, lang, visemes)
            size = os.path.getsize(wav) / 1000
            print(f"ok  ({size:.0f} kB, {len(visemes)} mouth shapes)")
            done += 1
        except Exception as e:                               # noqa: BLE001
            print(f"FAILED — {e}")
            failed += 1
            # Don't leave a half-written wav that would look cached later.
            try:
                if os.path.exists(wav) and os.path.getsize(wav) == 0:
                    os.unlink(wav)
            except OSError:
                pass
        time.sleep(0.15)          # be gentle with the Azure endpoint

    s = voice_cache.stats()
    print(f"\n{'─'*58}")
    print(f"Recorded {done} line(s), {failed} failed.")
    print(f"Cache now holds {s['entries']} files, {s['bytes']/1_000_000:.1f} MB")
    if failed:
        print("\n⚠️  Some lines failed. Run this again — it only retries those.")
    else:
        print("\n✅ Done. You can switch the WiFi off and the show still works.")


if __name__ == '__main__':
    main()
