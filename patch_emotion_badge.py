#!/usr/bin/env python3
"""
patch_emotion_badge.py
Adds a + badge to each emotion button so clicking + captures
that emotion as a keyframe in the sequence builder.

Run on the Pi (uses your home directory automatically):
  python3 ~/Projects/Ohbot/patch_emotion_badge.py

Or on the Mac (when SAMBA is mounted):
  python3 /Volumes/Projects/Ohbot/patch_emotion_badge.py
"""

import os, shutil
from pathlib import Path

# ── Locate the file ──────────────────────────────────────────────────────────
# Checks the current user's home directory on the Pi, then the SAMBA mount on Mac
CANDIDATES = [
    str(Path.home() / 'Projects/Ohbot/gui/index.html'),  # Pi: works for any username
    '/Volumes/Projects/Ohbot/gui/index.html',              # Mac via SAMBA
]
TARGET = next((p for p in CANDIDATES if os.path.exists(p)), None)
if not TARGET:
    raise SystemExit("❌  Could not find index.html — is SAMBA mounted / are you on the Pi?")

# Back up first
BACKUP = TARGET + '.bak'
shutil.copy2(TARGET, BACKUP)
print(f"✅  Backed up to {BACKUP}")

html = open(TARGET, encoding='utf-8').read()


# ── 1. CSS — make .btn-emotion use flex so the + sits right-aligned ──────────
OLD_BTN_EMOTION_CSS = """\
  .btn-emotion {"""

NEW_BTN_EMOTION_CSS = """\
  .btn-emotion {
    display: flex;
    align-items: center;
    justify-content: space-between;"""

# Only patch once
if 'justify-content: space-between' not in html:
    html = html.replace(OLD_BTN_EMOTION_CSS, NEW_BTN_EMOTION_CSS, 1)
    print("✅  CSS: btn-emotion updated to flex layout")
else:
    print("⏭️   CSS: flex already applied, skipping")


# ── 2. CSS — add .emotion-badge style after the last .btn-emotion rule ───────
BADGE_CSS = """\
  .emotion-badge {
    font-size: 0.9rem;
    font-weight: 900;
    line-height: 1;
    padding: 1px 5px;
    border-radius: 4px;
    opacity: 0.55;
    cursor: pointer;
    flex-shrink: 0;
    transition: opacity 0.15s, background 0.15s;
    pointer-events: all;
  }
  .emotion-badge:hover { opacity: 1; background: rgba(255,255,255,0.22); }
"""

BADGE_ANCHOR = "  .btn-emotion:last-child:nth-child(odd) { grid-column: span 2; }"

if '.emotion-badge' not in html:
    html = html.replace(BADGE_ANCHOR, BADGE_ANCHOR + '\n' + BADGE_CSS, 1)
    print("✅  CSS: .emotion-badge style added")
else:
    print("⏭️   CSS: .emotion-badge already present, skipping")


# ── 3. HTML — inject + badge span into each emotion button ───────────────────
BUTTON_MAP = {
    "onclick=\"setEmotion('happy')\">😊 Happy</button>":
        "onclick=\"setEmotion('happy')\">😊 Happy<span class=\"emotion-badge\" onclick=\"captureEmotion('happy',event)\" title=\"Add to sequence\">＋</span></button>",

    "onclick=\"setEmotion('sad')\">😢 Sad</button>":
        "onclick=\"setEmotion('sad')\">😢 Sad<span class=\"emotion-badge\" onclick=\"captureEmotion('sad',event)\" title=\"Add to sequence\">＋</span></button>",

    "onclick=\"setEmotion('surprised')\">😮 Surprised</button>":
        "onclick=\"setEmotion('surprised')\">😮 Surprised<span class=\"emotion-badge\" onclick=\"captureEmotion('surprised',event)\" title=\"Add to sequence\">＋</span></button>",

    "onclick=\"setEmotion('thinking')\">🤔 Thinking</button>":
        "onclick=\"setEmotion('thinking')\">🤔 Thinking<span class=\"emotion-badge\" onclick=\"captureEmotion('thinking',event)\" title=\"Add to sequence\">＋</span></button>",

    "onclick=\"setEmotion('sleeping')\">😴 Sleeping</button>":
        "onclick=\"setEmotion('sleeping')\">😴 Sleeping<span class=\"emotion-badge\" onclick=\"captureEmotion('sleeping',event)\" title=\"Add to sequence\">＋</span></button>",
}

for old, new in BUTTON_MAP.items():
    if old in html:
        html = html.replace(old, new, 1)
        emotion = old.split("'")[1]
        print(f"✅  HTML: {emotion} button updated")
    else:
        emotion = old.split("'")[1]
        print(f"⏭️   HTML: {emotion} button already patched or not found")


# ── 4. JS — update captureKeyframe() to accept an optional autoLabel ─────────
OLD_CAPTURE = "function captureKeyframe() {"
NEW_CAPTURE = "function captureKeyframe(autoLabel = '') {"

if OLD_CAPTURE in html:
    html = html.replace(OLD_CAPTURE, NEW_CAPTURE, 1)
    print("✅  JS: captureKeyframe() updated to accept autoLabel")
else:
    print("⏭️   JS: captureKeyframe() already updated or not found")

# Inject autoLabel into the kf object — find "label:  ''" or "label: ''" line
OLD_LABEL_LINE = "    label:  ''"
NEW_LABEL_LINE = "    label:  autoLabel"

if OLD_LABEL_LINE in html:
    html = html.replace(OLD_LABEL_LINE, NEW_LABEL_LINE, 1)
    print("✅  JS: kf.label wired to autoLabel")
else:
    # Try alternate spacing
    OLD_LABEL_LINE2 = "    label: ''"
    NEW_LABEL_LINE2 = "    label: autoLabel"
    if OLD_LABEL_LINE2 in html:
        html = html.replace(OLD_LABEL_LINE2, NEW_LABEL_LINE2, 1)
        print("✅  JS: kf.label wired to autoLabel (alt spacing)")
    else:
        print("⚠️   JS: Could not find label field in kf object — check manually")


# ── 5. JS — add captureEmotion() function after setEmotion() ─────────────────
CAPTURE_EMOTION_FN = """
// Capture an emotion directly as a keyframe in one click
async function captureEmotion(emotion, event) {
  event.stopPropagation();           // don't also fire the outer button's setEmotion
  await setEmotion(emotion);         // move robot + sync sliders
  await new Promise(r => setTimeout(r, 80));  // tiny wait for sliders to settle
  captureKeyframe(EMOTION_LABELS[emotion] || emotion);
}
"""

ANCHOR_AFTER = "// Emotion Presets"

if 'captureEmotion' not in html:
    html = html.replace(ANCHOR_AFTER, ANCHOR_AFTER + CAPTURE_EMOTION_FN, 1)
    print("✅  JS: captureEmotion() function added")
else:
    print("⏭️   JS: captureEmotion() already present, skipping")


# ── Write it out ─────────────────────────────────────────────────────────────
open(TARGET, 'w', encoding='utf-8').write(html)
print(f"\n🎉  Done! index.html updated at {TARGET}")
print("    Restart gui_server.py on the Pi and hard-refresh the browser.")
