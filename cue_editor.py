#!/usr/bin/env python3
"""
cue_editor.py — lets the Clubhouse director edit Yobot's cues from a web page
Version: 1.0.0  (2026-09-09)

WHAT THIS IS
------------
`show_server.py` plays a list of pre-recorded cues (see demo_cues.json). This
file adds the *other half*: a page where somebody who does not write code can
add a cue, change the words, reorder them, delete one, and then record the new
lines in Yobot's voice.

It follows the same shape as `ohbot_lang.py` — one function you call from a
server, and the routes appear:

    from cue_editor import register_editor_routes
    register_editor_routes(app, motion_names=list(MOTIONS))

RECORDING NEEDS THE INTERNET. Everything else here does not. The intended
workflow is: edit and record at the Clubhouse where there is wifi, then carry
the laptop to the comarca and play back with no network at all.

WHY THE SAVE IS SO CAREFUL
--------------------------
The person using this is not a programmer and the file being written is the
one thing the whole show depends on. So a save:

  1. is validated field by field BEFORE anything is written,
  2. copies the current file into cue_backups/ with a timestamp,
  3. writes to a temporary file and renames it into place (atomic — there is
     no instant where demo_cues.json is half written).

A rejected save changes nothing and says, in the user's own language, which
cue was wrong. There is no way to type raw JSON, so it cannot be broken by a
stray comma.
"""

import os
import re
import json
import shutil
import string
import subprocess
import sys
import threading
from datetime import datetime

from flask import jsonify, request, send_from_directory

HERE = os.path.dirname(os.path.abspath(__file__))
CUE_FILE = os.path.join(HERE, 'demo_cues.json')
BACKUP_DIR = os.path.join(HERE, 'cue_backups')
KEEP_BACKUPS = 30

# Fields a cue is allowed to have. Anything else in the incoming JSON is
# dropped rather than trusted — the page is the only intended client, but it
# is not the only *possible* one.
ALLOWED = ('id', 'group', 'label_en', 'label_es', 'motion',
           'lang_lock', 'text_en', 'text_es')

MAX_CUES = 200
MAX_TEXT = 4000
SAFE_ID = re.compile(r'^[a-z0-9_]{1,40}$')


# ─────────────────────────────────────────────────────────────────────────────
# READING AND WRITING THE CUE FILE
# ─────────────────────────────────────────────────────────────────────────────
def load_doc():
    with open(CUE_FILE, encoding='utf-8') as f:
        return json.load(f)


def _slug(text, taken):
    """Turn a label into a usable id, e.g. "¿Qué es esto?" -> 'que_es_esto'.

    The director never sees or types an id — this invents one so that saved
    recordings can be matched to a cue, and so two cues can never collide.
    """
    keep = string.ascii_lowercase + string.digits + ' _'
    # Strip accents the simple way: é -> e, ñ -> n. Enough for an internal id.
    table = str.maketrans('áéíóúüñàèìòùâêîôûç', 'aeiouunaeiouaeiouc')
    base = (text or '').lower().translate(table)
    base = ''.join(c for c in base if c in keep).strip()
    base = re.sub(r'\s+', '_', base)[:30] or 'cue'
    candidate = base
    n = 2
    while candidate in taken:
        candidate = f'{base}_{n}'
        n += 1
    return candidate


def validate(cues, motion_names):
    """Return a list of problems. Empty list means the save is safe.

    Each problem is {'index': n, 'key': '<i18n key>', 'extra': '...'} so the
    page can show it in Spanish or English without this file knowing either.
    """
    problems = []
    if not isinstance(cues, list):
        return [{'index': -1, 'key': 'editor.err.shape'}]
    if not cues:
        return [{'index': -1, 'key': 'editor.err.empty'}]
    if len(cues) > MAX_CUES:
        return [{'index': -1, 'key': 'editor.err.toomany', 'extra': str(MAX_CUES)}]

    seen = set()
    for i, c in enumerate(cues):
        if not isinstance(c, dict):
            problems.append({'index': i, 'key': 'editor.err.shape'})
            continue

        cid = (c.get('id') or '').strip()
        if cid:
            if not SAFE_ID.match(cid):
                problems.append({'index': i, 'key': 'editor.err.badid'})
            elif cid in seen:
                problems.append({'index': i, 'key': 'editor.err.dupid'})
            seen.add(cid)

        # A cue with no words at all is almost certainly a half-finished row
        # the director forgot about. Better to stop than to ship a dead button.
        if not (c.get('text_es') or '').strip() and not (c.get('text_en') or '').strip():
            problems.append({'index': i, 'key': 'editor.err.notext'})

        for field in ('text_en', 'text_es'):
            if len(c.get(field) or '') > MAX_TEXT:
                problems.append({'index': i, 'key': 'editor.err.toolong'})
                break

        if not (c.get('label_es') or '').strip() and not (c.get('label_en') or '').strip():
            problems.append({'index': i, 'key': 'editor.err.nolabel'})

        if c.get('motion') and c['motion'] not in motion_names:
            problems.append({'index': i, 'key': 'editor.err.badmotion',
                             'extra': str(c.get('motion'))})

        lock = c.get('lang_lock')
        if lock not in (None, '', 'en', 'es'):
            problems.append({'index': i, 'key': 'editor.err.badlock'})

    return problems


def _backup():
    """Timestamped copy of the current cue file, oldest pruned."""
    if not os.path.exists(CUE_FILE):
        return None
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    dest = os.path.join(BACKUP_DIR, f'demo_cues.{stamp}.json')
    shutil.copy2(CUE_FILE, dest)

    kept = sorted(f for f in os.listdir(BACKUP_DIR) if f.endswith('.json'))
    for old in kept[:-KEEP_BACKUPS]:
        try:
            os.unlink(os.path.join(BACKUP_DIR, old))
        except OSError:
            pass
    return os.path.basename(dest)


def save_cues(cues, motion_names):
    """Validate, back up, then write. Returns (ok, result)."""
    problems = validate(cues, motion_names)
    if problems:
        return False, problems

    try:
        doc = load_doc()
    except Exception:                                        # noqa: BLE001
        doc = {}

    taken = {(c.get('id') or '').strip() for c in cues if (c.get('id') or '').strip()}
    clean = []
    for c in cues:
        row = {k: c[k] for k in ALLOWED if k in c and c[k] not in (None, '')}
        if not row.get('id'):
            row['id'] = _slug(row.get('label_es') or row.get('label_en'), taken)
            taken.add(row['id'])
        row.setdefault('motion', 'explain')
        clean.append(row)

    doc['cues'] = clean
    backup = _backup()

    tmp = CUE_FILE + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    os.replace(tmp, CUE_FILE)          # atomic — never a half-written file

    return True, {'count': len(clean), 'backup': backup}


# ─────────────────────────────────────────────────────────────────────────────
# RECORDING
#
# Shelled out to prerender_cues.py rather than reimplemented, so there is one
# recording code path and it is the one already proven on the Mac. It runs in
# a thread and streams its output into a buffer the page polls, because
# recording twenty lines takes longer than a browser will wait.
# ─────────────────────────────────────────────────────────────────────────────
class Recorder:
    def __init__(self):
        self.running = False
        self.lines = []
        self.done = False
        self.ok = None
        self._lock = threading.Lock()

    def start(self):
        with self._lock:
            if self.running:
                return False
            self.running = True
            self.done = False
            self.ok = None
            self.lines = []
        threading.Thread(target=self._run, daemon=True).start()
        return True

    def _run(self):
        try:
            proc = subprocess.Popen(
                [sys.executable, os.path.join(HERE, 'prerender_cues.py')],
                cwd=HERE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding='utf-8', errors='replace', bufsize=1)
            for line in proc.stdout:
                line = line.rstrip()
                if line:
                    with self._lock:
                        self.lines.append(line)
                        # Don't let a runaway process eat memory.
                        if len(self.lines) > 400:
                            self.lines = self.lines[-400:]
            proc.wait()
            self.ok = (proc.returncode == 0)
        except Exception as e:                               # noqa: BLE001
            with self._lock:
                self.lines.append(f'ERROR: {e}')
            self.ok = False
        finally:
            self.running = False
            self.done = True

    def state(self):
        with self._lock:
            return {'running': self.running, 'done': self.done,
                    'ok': self.ok, 'lines': list(self.lines)}


recorder = Recorder()


# ─────────────────────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────────────────────
def register_editor_routes(app, motion_names=None, is_busy=None):
    """Add the editor page and its API to an existing Flask app.

    motion_names — the movements the director may choose from.
    is_busy      — optional callable; if it returns True the save is refused,
                   because rewriting the cue list while Yobot is mid-sentence
                   is a good way to confuse both of them.
    """
    motions = list(motion_names or ['explain'])

    @app.route('/editor')
    def editor_page():
        return send_from_directory(os.path.join(HERE, 'gui'), 'editor.html')

    @app.route('/api/editor/load')
    def editor_load():
        try:
            doc = load_doc()
        except Exception as e:                               # noqa: BLE001
            return jsonify({'ok': False, 'error': str(e)}), 500

        import voice_cache
        out = []
        for c in doc.get('cues', []):
            lock = c.get('lang_lock') or ''
            def ready(lang):
                L = lock or lang
                return voice_cache.is_cached(c.get(f'text_{L}', ''), L)
            row = {k: c.get(k, '') for k in ALLOWED}
            row['ready_en'] = ready('en')
            row['ready_es'] = ready('es')
            out.append(row)

        groups = []
        for c in out:
            if c['group'] and c['group'] not in groups:
                groups.append(c['group'])

        return jsonify({'ok': True, 'cues': out, 'motions': motions,
                        'groups': groups})

    @app.route('/api/editor/save', methods=['POST'])
    def editor_save():
        if is_busy and is_busy():
            return jsonify({'ok': False, 'busy': True}), 409
        body = request.get_json(force=True, silent=True) or {}
        ok, result = save_cues(body.get('cues'), motions)
        if not ok:
            return jsonify({'ok': False, 'problems': result}), 400
        return jsonify({'ok': True, **result})

    @app.route('/api/editor/record', methods=['POST'])
    def editor_record():
        if not recorder.start():
            return jsonify({'ok': False, 'error': 'already running'}), 409
        return jsonify({'ok': True})

    @app.route('/api/editor/record/status')
    def editor_record_status():
        return jsonify(recorder.state())

    @app.route('/api/editor/backups')
    def editor_backups():
        if not os.path.isdir(BACKUP_DIR):
            return jsonify({'backups': []})
        names = sorted((f for f in os.listdir(BACKUP_DIR) if f.endswith('.json')),
                       reverse=True)
        return jsonify({'backups': names[:KEEP_BACKUPS]})

    @app.route('/api/editor/restore', methods=['POST'])
    def editor_restore():
        """Put a backup back. The current file is itself backed up first, so
        an accidental restore is also undoable."""
        if is_busy and is_busy():
            return jsonify({'ok': False, 'busy': True}), 409
        name = (request.get_json(force=True, silent=True) or {}).get('name', '')
        if not re.match(r'^demo_cues\.\d{8}-\d{6}\.json$', name or ''):
            return jsonify({'ok': False, 'error': 'bad name'}), 400
        src = os.path.join(BACKUP_DIR, name)
        if not os.path.exists(src):
            return jsonify({'ok': False, 'error': 'not found'}), 404
        _backup()
        shutil.copy2(src, CUE_FILE)
        return jsonify({'ok': True})
