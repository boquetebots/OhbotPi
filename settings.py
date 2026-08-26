#!/usr/bin/env python3
"""
settings.py — one safe place to read and write the .env file.

WHY THIS FILE EXISTS
--------------------
All the account keys the robot needs (Azure for the voice, OpenAI for the
brain) live in a plain text file called .env sitting next to this one.
Editing that file means SSH-ing into the Pi and using a text editor, which
is a lot to ask of somebody who has just unboxed a robot.

This file lets the Launcher web page do it instead. Everything that touches
.env goes through here so there is exactly ONE piece of code that knows how
to do it safely, rather than four that each do it slightly differently.

WHAT "SAFELY" MEANS HERE
------------------------
  * Your comments and any settings this page has never heard of are kept
    exactly as they were. Nothing gets thrown away.
  * The file is written to a temporary name and then renamed over the real
    one. Renaming is instant, so a power cut can never leave you with half
    a file and a robot that won't start.
  * The file is locked down to "only the owner can read it" (chmod 600).
  * Real key values are NEVER sent to the web page. It only ever sees
    something like sk-…4f2a, enough to recognise which key is in there.

IMPORTANT: nothing that is already running picks up a changed key. Every
program reads .env once, when it starts. The Launcher restarts things for
you after a save — see launcher_server.py.
"""

import hashlib
import json
import os
import secrets
import time
import urllib.error
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, '.env')


# ============================================================================
# WHICH SETTINGS THE PAGE IS ALLOWED TO TOUCH
# ============================================================================
# Anything not on this list is left alone completely — read from the file,
# written back unchanged, never shown. That is deliberate: it means somebody
# can hand-edit an unusual setting into .env without the web page eating it.
#
#   secret  = True  -> never shown in full, only as sk-…4f2a
#   secret  = False -> shown and edited as ordinary text
#
FIELDS = {
    # Voice
    'AZURE_SPEECH_KEY':    {'secret': True,  'group': 'voice'},
    'AZURE_SPEECH_REGION': {'secret': False, 'group': 'voice'},

    # Brain. WHICH company answers is LLM_PROVIDER; the rest of these are
    # one key per company, so several can be set up at once and you can flip
    # between them from the dropdown without re-pasting anything.
    # See llm.py for what each provider is and where its key comes from.
    'LLM_PROVIDER':        {'secret': False, 'group': 'brain'},
    'LLM_MODEL':           {'secret': False, 'group': 'brain'},
    'LLM_BASE_URL':        {'secret': False, 'group': 'brain'},
    'OPENAI_API_KEY':      {'secret': True,  'group': 'brain'},
    'ANTHROPIC_API_KEY':   {'secret': True,  'group': 'brain'},
    'GEMINI_API_KEY':      {'secret': True,  'group': 'brain'},
    'XAI_API_KEY':         {'secret': True,  'group': 'brain'},
    'OLLAMA_API_KEY':      {'secret': True,  'group': 'brain'},
    'LLM_API_KEY':         {'secret': True,  'group': 'brain'},

    # Other
    'AZURE_MIC_DEVICE':    {'secret': False, 'group': 'advanced'},
    'SETTINGS_PASSWORD':   {'secret': True,  'group': 'lock'},
}

# The voice keys the robot cannot work without. The brain is checked
# separately, by asking llm.py — "is the AI ready" depends on which provider
# is chosen, and a local Ollama server needs no key at all.
REQUIRED_VOICE = ['AZURE_SPEECH_KEY', 'AZURE_SPEECH_REGION']


def _is_placeholder(value):
    """True if this is the example text from .env.example, not a real key."""
    if not value:
        return True
    low = value.strip().lower()
    return low.startswith('your_') or low.endswith('_here') or low in (
        'changeme', 'xxx', 'none')


# ============================================================================
# READING
# ============================================================================

def _read_raw():
    """Every KEY=VALUE line in .env, as a plain dictionary. No masking."""
    values = {}
    if not os.path.exists(ENV_PATH):
        return values
    try:
        with open(ENV_PATH, 'r', encoding='utf-8') as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, value = line.split('=', 1)
                values[key.strip()] = value.strip().strip('"').strip("'")
    except Exception as e:                                   # noqa: BLE001
        print(f"⚠️  settings.py could not read .env: {e}")
    return values


def get_value(name):
    """The real, unmasked value of one setting. For server-side use ONLY."""
    return _read_raw().get(name, '')


def _mask(value):
    """Turn a real key into something safe to show: sk-proj…4f2a"""
    if not value:
        return ''
    if len(value) <= 8:
        return '•' * len(value)
    return value[:6] + '…' + value[-4:]


def read_for_page():
    """
    What the web page is allowed to know.

    For every setting: is it filled in, and what does it look like. Secrets
    come back masked, so even somebody who gets to this page cannot read
    your keys off the screen and use them somewhere else.
    """
    raw = _read_raw()
    out = {}
    for name, spec in FIELDS.items():
        value = raw.get(name, '')
        placeholder = _is_placeholder(value)
        out[name] = {
            'set':     bool(value) and not placeholder,
            'display': '' if (spec['secret'] or placeholder) else value,
            'masked':  _mask(value) if (spec['secret'] and not placeholder) else '',
            'group':   spec['group'],
        }
    return out


def needs_setup():
    """True on a brand-new install — nothing usable filled in yet."""
    raw = _read_raw()
    if any(_is_placeholder(raw.get(name, '')) for name in REQUIRED_VOICE):
        return True
    try:
        import llm
        return not llm.is_ready()[0]
    except Exception:                                        # noqa: BLE001
        # llm.py missing or broken — fall back to the old question.
        return _is_placeholder(raw.get('OPENAI_API_KEY', ''))


# ============================================================================
# WRITING
# ============================================================================

def write_values(changes):
    """
    Update .env with {NAME: value}, keeping everything else exactly as it is.

    An empty string means "leave whatever is already there alone" — that is
    how the page can show a masked key without ever having to send the real
    one back to us. To actually clear a setting, pass the word DELETE.

    Returns (True, list-of-names-changed) or (False, "why not").
    """
    for name in changes:
        if name not in FIELDS:
            return False, f"Unknown setting: {name}"

    raw = _read_raw()
    real = {}
    for name, value in changes.items():
        value = (value or '').strip()
        if value == '':
            continue                       # untouched field — keep old value
        if value == 'DELETE':
            real[name] = ''
        elif name == 'SETTINGS_PASSWORD':
            real[name] = hash_password(value)
        else:
            real[name] = value

    if not real:
        return True, []

    # Read the file as lines so comments and layout survive.
    lines = []
    if os.path.exists(ENV_PATH):
        try:
            with open(ENV_PATH, 'r', encoding='utf-8') as fh:
                lines = fh.read().splitlines()
        except Exception as e:                               # noqa: BLE001
            return False, f"Could not read .env: {e}"

    still_to_write = dict(real)
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('#') and '=' in stripped:
            key = stripped.split('=', 1)[0].strip()
            if key in still_to_write:
                value = still_to_write.pop(key)
                if value == '':
                    continue               # cleared — drop the line entirely
                new_lines.append(f"{key}={value}")
                continue
        new_lines.append(line)

    # Anything that was not already in the file gets added at the end.
    leftovers = [(k, v) for k, v in still_to_write.items() if v != '']
    if leftovers:
        if new_lines and new_lines[-1].strip():
            new_lines.append('')
        new_lines.append('# ── Added by the Launcher Settings page ──')
        for key, value in leftovers:
            new_lines.append(f"{key}={value}")

    text = '\n'.join(new_lines).rstrip('\n') + '\n'

    # Write to a temporary file, then rename it over the real one. The rename
    # is a single instant step, so the robot can never see a half-written file.
    tmp_path = ENV_PATH + '.tmp'
    try:
        with open(tmp_path, 'w', encoding='utf-8') as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, ENV_PATH)
        try:
            os.chmod(ENV_PATH, 0o600)      # only the owner may read it
        except Exception:                                    # noqa: BLE001
            pass                           # Windows does not do this — fine
    except Exception as e:                                   # noqa: BLE001
        return False, f"Could not write .env: {e}"

    # Make the new values live for THIS program too. Other programs still
    # need a restart, which the Launcher offers after a save.
    for key, value in real.items():
        if value:
            os.environ[key] = value
        else:
            os.environ.pop(key, None)

    changed = sorted(real.keys())
    print(f"⚙️  Settings saved: {', '.join(changed)}")
    return True, changed


# ============================================================================
# THE SETTINGS PASSWORD
# ============================================================================
# Anybody on the same WiFi can open the Launcher page. Without a password
# they could also read which keys are set and replace them with their own.
# One password, stored scrambled (not as plain text), stops that.
#
# Forgotten it? SSH into the Pi and delete the SETTINGS_PASSWORD line from
# .env — the page then goes back to asking you to make a new one.

_SALT = 'ohbot-settings-v1'
_TOKENS = {}                    # token -> the time it was handed out
_TOKEN_LIFE = 60 * 60           # an unlock lasts an hour


def hash_password(plain):
    """Scramble a password so the real one is never stored anywhere."""
    digest = hashlib.sha256((_SALT + plain).encode('utf-8')).hexdigest()
    return 'sha256:' + digest


def password_is_set():
    return bool(get_value('SETTINGS_PASSWORD'))


def check_password(plain):
    """True if this is the right password."""
    stored = get_value('SETTINGS_PASSWORD')
    if not stored:
        return True                        # no password set — nothing to check
    if stored.startswith('sha256:'):
        return secrets.compare_digest(stored, hash_password(plain or ''))
    # Somebody typed a plain password straight into .env by hand. Accept it.
    return secrets.compare_digest(stored, (plain or '').strip())


def new_token():
    """Hand out a pass that proves this browser already gave the password."""
    _expire_old_tokens()
    token = secrets.token_urlsafe(24)
    _TOKENS[token] = time.time()
    return token


def token_is_good(token):
    if not password_is_set():
        return True                        # no password set — everyone is in
    _expire_old_tokens()
    return bool(token) and token in _TOKENS


def _expire_old_tokens():
    cutoff = time.time() - _TOKEN_LIFE
    for token, issued in list(_TOKENS.items()):
        if issued < cutoff:
            _TOKENS.pop(token, None)


# ============================================================================
# TESTING KEYS — "is this thing actually going to work?"
# ============================================================================
# Both tests are deliberately tiny and free. Neither one speaks out loud or
# touches the robot, so they are safe to press at any time, even with the
# Greeter running.

def _http(url, headers, data=None, timeout=12):
    """A small wrapper so both tests report failures the same way."""
    req = urllib.request.Request(url, data=data, headers=headers,
                                 method='POST' if data is not None else 'GET')
    return urllib.request.urlopen(req, timeout=timeout)


def test_brain(provider=None, model=None, base_url=None, key=None):
    """
    Ask whichever AI is chosen for one word, and report back in plain English.

    All the work is in llm.py — this is just the doorway from the web page.
    Anything passed in here is tried WITHOUT saving it, so the Test button
    checks what is typed on screen rather than what is on disk.
    """
    try:
        import llm
    except Exception as e:                                   # noqa: BLE001
        return False, f'llm.py could not be loaded ({e}).'
    return llm.test(provider=provider, model=model, base_url=base_url, key=key)


def brain_providers():
    """
    The AI companies for the dropdown, straight from llm.py.

    A LIST, not a dictionary, so the order llm.py lists them in is the order
    they appear on the page — the familiar one first, "Custom" last. Sent as
    a dictionary they would come back alphabetised, which reads as random.
    """
    try:
        import llm
    except Exception:                                        # noqa: BLE001
        return []
    return [{
        'name':      name,
        'label':     spec['label'],
        'models':    spec['models'],
        'model':     spec['model'],           # used if the box is left blank
        'base_url':  spec['base_url'],
        'key_env':   spec['key_env'],
        'needs_key': spec['needs_key'],
        'where':     spec['where'],
    } for name, spec in llm.PROVIDERS.items()]


def brain_active():
    """Which provider/model is actually in force right now."""
    try:
        import llm
    except Exception:                                        # noqa: BLE001
        return {}
    cfg = llm.current()
    ok, why = llm.is_ready()
    return {'provider': cfg['provider'], 'model': cfg['model'],
            'base_url': cfg['base_url'], 'ready': ok, 'problem': why}


def test_voice(key=None, region=None):
    """
    Ask Azure for a short-lived ticket using the key.

    This is the same handshake the robot does before it speaks, minus the
    speaking. It proves the key AND the region are both right — a wrong
    region is the most common reason a correct key still fails.
    """
    key = (key or '').strip() or get_value('AZURE_SPEECH_KEY')
    region = (region or '').strip() or get_value('AZURE_SPEECH_REGION') or 'eastus'
    if not key or _is_placeholder(key):
        return False, 'No Azure Speech key saved yet.'
    url = f'https://{region}.api.cognitive.microsoft.com/sts/v1.0/issueToken'
    try:
        with _http(url, {'Ocp-Apim-Subscription-Key': key,
                         'Content-Length': '0'}, data=b'') as resp:
            resp.read()
        return True, f'Key works in region "{region}".'
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            return False, ('Azure rejected that key. Either the key is wrong, '
                           f'or it does not belong to region "{region}".')
        if e.code == 404:
            return False, f'No Azure Speech service in region "{region}".'
        return False, f'Azure answered with error {e.code}.'
    except Exception as e:                                   # noqa: BLE001
        return False, (f'Could not reach Azure — check the region spelling '
                       f'("{region}") and that the Pi is online. ({e})')


# ============================================================================
# Run this file directly to check the current settings from the command line:
#     python3 settings.py
# ============================================================================
if __name__ == '__main__':
    print(f"Reading: {ENV_PATH}")
    print(f"Needs first-time setup: {needs_setup()}")
    print(f"Settings password set:  {password_is_set()}")
    for name, info in read_for_page().items():
        state = info['masked'] or info['display'] or ('set' if info['set'] else '— not set —')
        print(f"  {name:22} {state}")
    print()
    print(f"Brain       : {brain_active()}")
    print()
    ok, msg = test_voice()
    print(f"Azure voice : {'OK  ' if ok else 'FAIL'} — {msg}")
    ok, msg = test_brain()
    print(f"AI brain    : {'OK  ' if ok else 'FAIL'} — {msg}")
