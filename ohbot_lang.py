"""
ohbot_lang.py — the language plumbing shared by all four web pages.

WHAT THIS DOES (plain English)
------------------------------
Two small jobs:

1. Hands out `i18n.js` — the single file holding every English and Spanish
   phrase. All four pages ask for it at `/i18n.js`, and each of the four
   servers needs to know how to hand it over. Rather than writing that four
   times, they all call `register_language_routes(app)` from here.

2. Remembers which language you picked. When you use the 🌐 dropdown, the
   page quietly posts the choice here and it gets written to

       ohbotData/language.txt

   as a single word: `en` or `es`.

   Nothing reads that file yet. It exists so that when we later give Ohbot a
   Spanish speaking voice, the Python side can call `get_language()` and know
   which voice to use without any of this having to be redone.

HOW A SERVER USES IT
--------------------
Two lines near the top of the server file:

    from ohbot_lang import register_language_routes
    register_language_routes(app)

That's it. The routes appear and everything else keeps working exactly as it
did before.
"""

import os

from flask import jsonify, request, send_from_directory

# Everything lives next to this file.
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
OHBOT_DATA = os.path.join(BASE_DIR, 'ohbotData')
LANG_FILE  = os.path.join(OHBOT_DATA, 'language.txt')

# The languages the pages actually have wording for. Anything else is refused
# rather than written to disk, so a typo can't leave the robot in a state no
# page knows how to render.
SUPPORTED = ('en', 'es')
DEFAULT   = 'en'


def get_language():
    """
    Which language is currently chosen: 'en' or 'es'.

    Falls back to English if the file is missing, empty, unreadable, or has
    something unexpected in it. This never raises — a language preference is
    not worth crashing a robot over.
    """
    try:
        with open(LANG_FILE, 'r', encoding='utf-8') as f:
            value = f.read().strip().lower()
        if value in SUPPORTED:
            return value
    except (OSError, UnicodeDecodeError):
        pass
    return DEFAULT


def set_language(value):
    """
    Write the chosen language to disk. Returns True if it was saved.

    Refuses anything that isn't a language we actually have wording for.
    """
    value = (value or '').strip().lower()
    if value not in SUPPORTED:
        return False
    try:
        os.makedirs(OHBOT_DATA, exist_ok=True)
        with open(LANG_FILE, 'w', encoding='utf-8') as f:
            f.write(value + '\n')
        return True
    except OSError:
        return False


def register_language_routes(app):
    """
    Add `/i18n.js` and `/lang` to a Flask app.

    Safe to call on every server. If a server has somehow already registered
    these (e.g. this function got called twice), the duplicate is skipped
    rather than blowing up at startup.
    """
    existing = {rule.rule for rule in app.url_map.iter_rules()}

    if '/i18n.js' not in existing:
        @app.route('/i18n.js')
        def serve_i18n():
            # max-age=0 so editing i18n.js and refreshing the browser shows
            # the new wording immediately, instead of the browser serving a
            # stale cached copy and making it look like the edit didn't work.
            response = send_from_directory(
                BASE_DIR, 'i18n.js', mimetype='application/javascript')
            response.headers['Cache-Control'] = 'no-cache, max-age=0'
            return response

    if '/lang' not in existing:
        @app.route('/lang', methods=['GET', 'POST'])
        def language_pref():
            if request.method == 'POST':
                data = request.get_json(silent=True) or {}
                ok = set_language(data.get('lang'))
                return jsonify({'success': ok, 'lang': get_language()}), (200 if ok else 400)
            return jsonify({'success': True, 'lang': get_language()})
