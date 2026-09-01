#!/usr/bin/env python3
"""
llm.py — the one place the robot talks to an AI.

WHY THIS FILE EXISTS
--------------------
Yobot used to call OpenAI from four different places, each with its own
copy of the setup code. Changing anything about the AI meant finding and
editing all four and hoping you didn't miss one.

Now all four call ask() below, and this file is the only thing that knows
which company is answering. That is what makes the provider dropdown on the
Launcher's Settings page possible.

THE USEFUL SURPRISE
-------------------
OpenAI, Anthropic, Google Gemini, Groq and Ollama all understand the
same request format — the one OpenAI published. So switching between them
is not five different pieces of code. It is one piece of code and a
different web address.

That also means anything else speaking that format works with no code
change at all: LM Studio, llama.cpp's server, vLLM, and the Clubhouse's DGX
Spark when it is ready. Pick "Custom" in the dropdown and type its address.

WHAT DECIDES WHICH ONE IS USED
------------------------------
Three settings in .env, all editable from the Launcher's Settings page:

    LLM_PROVIDER   openai | anthropic | gemini | groq | ollama | custom
    LLM_MODEL      which model to ask for. Blank = the provider's default.
    LLM_BASE_URL   the web address. Blank = the provider's usual one.
                   Only really needed for Ollama and Custom.

Plus one key per provider, so you can keep several set up and flip between
them without re-pasting anything:

    OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, GROQ_API_KEY,
    OLLAMA_API_KEY (rarely needed), LLM_API_KEY (for Custom)

Nothing is set? It behaves exactly as it always did: OpenAI, using
OPENAI_API_KEY. Upgrading an existing robot changes nothing.
"""

import os


# Load the .env file so the settings below are available. Anything already in
# the real environment wins, which is how systemd can override a value on the
# Pi. yobot_core does this for the whole project; the small copy underneath is
# a safety net so this file still works on its own, or in a cut-down install.
def _load_env():
    try:
        from yobot_core import load_env
        load_env()
        return
    except Exception:                                      # noqa: BLE001
        pass
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if not os.path.exists(path):
        return
    try:
        with open(path, encoding='utf-8') as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(),
                                      value.strip().strip('"').strip("'"))
    except Exception as e:                                 # noqa: BLE001
        print(f"⚠️  llm.py could not read .env: {e}")


_load_env()


# ============================================================================
# THE PROVIDERS
# ============================================================================
# base_url      where to send the request
# key_env       which .env setting holds that provider's key
# model         a sensible default if LLM_MODEL is blank
# models        a few known-good names for the dropdown. NOT a fixed list —
#               the Settings page also has a free-text box, because model
#               names change every few months and this file should not need
#               editing when they do. The Test button lists what is really
#               available if the name is wrong.
# needs_key     False for a local server that isn't guarding anything
# where         plain-English "go here to get a key", shown on the page
#
PROVIDERS = {
    'openai': {
        'label':    'OpenAI',
        'base_url': 'https://api.openai.com/v1',
        'key_env':  'OPENAI_API_KEY',
        'model':    'gpt-4o-mini',
        'models':   ['gpt-4o-mini', 'gpt-4o', 'gpt-4.1-mini', 'gpt-4.1'],
        'needs_key': True,
        'where':    'platform.openai.com/api-keys',
    },
    'anthropic': {
        'label':    'Anthropic (Claude)',
        'base_url': 'https://api.anthropic.com/v1/',
        'key_env':  'ANTHROPIC_API_KEY',
        'model':    'claude-haiku-4-5',
        'models':   ['claude-haiku-4-5', 'claude-sonnet-4-5'],
        'needs_key': True,
        'where':    'console.anthropic.com → API keys',
    },
    'gemini': {
        'label':    'Google Gemini',
        'base_url': 'https://generativelanguage.googleapis.com/v1beta/openai/',
        'key_env':  'GEMINI_API_KEY',
        'model':    'gemini-2.5-flash',
        'models':   ['gemini-2.5-flash', 'gemini-2.0-flash'],
        'needs_key': True,
        'where':    'aistudio.google.com/apikey',
    },
    'groq': {
        # Not a typo for Grok, and not the same company. Groq runs open
        # models (Llama and friends) on its own hardware, very fast and
        # very cheap, which suits a robot that answers a visitor.
        'label':    'Groq (fast open models)',
        'base_url': 'https://api.groq.com/openai/v1',
        'key_env':  'GROQ_API_KEY',
        'model':    'llama-3.1-8b-instant',
        'models':   ['llama-3.1-8b-instant', 'llama-3.3-70b-versatile',
                     'openai/gpt-oss-20b'],
        'needs_key': True,
        'where':    'console.groq.com → API keys',
    },
    'ollama': {
        'label':    'Ollama (this machine or your network)',
        'base_url': 'http://localhost:11434/v1',
        'key_env':  'OLLAMA_API_KEY',
        'model':    'llama3.2',
        'models':   ['llama3.2', 'qwen2.5', 'mistral', 'phi4'],
        'needs_key': False,
        'where':    'nothing to sign up for — install Ollama and pull a model',
    },
    'custom': {
        'label':    'Custom / anything else',
        'base_url': '',
        'key_env':  'LLM_API_KEY',
        'model':    '',
        'models':   [],
        'needs_key': False,
        'where':    'any server that speaks the OpenAI format — LM Studio, '
                    'vLLM, a DGX Spark, a company gateway',
    },
}

DEFAULT_PROVIDER = 'openai'
DEFAULT_TIMEOUT = 20.0


# ============================================================================
# WHAT IS SWITCHED ON RIGHT NOW
# ============================================================================

def current(provider=None, model=None, base_url=None, key=None):
    """
    Work out the settings to use, filling in every blank with a sensible
    default. Pass arguments in to try a different setup without saving it —
    that is how the Settings page tests a key before you commit to it.
    """
    name = (provider or os.environ.get('LLM_PROVIDER') or DEFAULT_PROVIDER).strip().lower()
    spec = PROVIDERS.get(name)
    if spec is None:
        name, spec = DEFAULT_PROVIDER, PROVIDERS[DEFAULT_PROVIDER]

    return {
        'provider':  name,
        'label':     spec['label'],
        'model':     (model or os.environ.get('LLM_MODEL') or spec['model']).strip(),
        'base_url':  (base_url or os.environ.get('LLM_BASE_URL') or spec['base_url']).strip(),
        'key':       (key or os.environ.get(spec['key_env']) or '').strip(),
        'key_env':   spec['key_env'],
        'needs_key': spec['needs_key'],
    }


def is_ready(**kw):
    """
    (True, '') if a question could be asked right now, else (False, why not).

    The "why not" is written to be read out to a person, not a programmer.
    """
    cfg = current(**kw)
    if cfg['needs_key'] and not cfg['key']:
        return False, (f"No {cfg['label']} key yet. Add one on the Launcher "
                       f"page under Settings.")
    if not cfg['base_url']:
        return False, (f"{cfg['label']} needs a server address. Add one on "
                       f"the Launcher page under Settings.")
    if not cfg['model']:
        return False, (f"{cfg['label']} needs a model name. Add one on the "
                       f"Launcher page under Settings.")
    return True, ''


def describe():
    """One short line for logs and status displays."""
    cfg = current()
    return f"{cfg['label']} / {cfg['model']}"


# ============================================================================
# ASKING IT SOMETHING
# ============================================================================
# The connection is built once and kept. The cache key includes every setting
# that matters, so changing a key or a provider quietly builds a new one
# instead of carrying on with the old.

_clients = {}


def _client(cfg, timeout):
    signature = (cfg['base_url'], cfg['key'], timeout)
    if signature not in _clients:
        from openai import OpenAI
        _clients[signature] = OpenAI(
            api_key=cfg['key'] or 'not-needed',   # local servers ignore this
            base_url=cfg['base_url'],
            timeout=timeout,
        )
    return _clients[signature]


def ask(messages, max_tokens=150, temperature=0.7, timeout=DEFAULT_TIMEOUT,
        **kw):
    """
    Ask the AI something and get the words back.

    messages is the usual list of {"role": ..., "content": ...} dictionaries.
    Raises on failure — every caller already has a try/except, and each one
    wants to say something different when the AI is unreachable.
    """
    cfg = current(**kw)
    ok, why = is_ready(**kw)
    if not ok:
        raise RuntimeError(why)

    response = _client(cfg, timeout).chat.completions.create(
        model=cfg['model'],
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return (response.choices[0].message.content or '').strip()


# ============================================================================
# TESTING A SETUP BEFORE TRUSTING IT
# ============================================================================

def list_models(timeout=8.0, **kw):
    """The model names this provider will accept. Empty list if it won't say."""
    cfg = current(**kw)
    try:
        page = _client(cfg, timeout).models.list()
        return sorted(m.id for m in page.data)
    except Exception:                                      # noqa: BLE001
        return []


def test(**kw):
    """
    Ask for one word, and report back in plain English.

    A tiny real question is used rather than just checking the key, because
    it is the only thing that proves all three parts at once: the key is
    accepted, the address answers, AND the model name exists. Checking the
    key alone happily passes with a model name that will fail every time
    the robot actually speaks.

    It costs a fraction of a cent, and nothing at all on a local server.
    """
    cfg = current(**kw)
    ok, why = is_ready(**kw)
    if not ok:
        return False, why

    try:
        reply = ask([{"role": "user", "content": "Reply with the single word: ready"}],
                    max_tokens=8, temperature=0, timeout=20.0, **kw)
        reply = (reply or '').strip() or '(an empty answer)'
        return True, f'{cfg["label"]} answered using {cfg["model"]} — "{reply}"'
    except Exception as e:                                 # noqa: BLE001
        return False, _explain(e, cfg, **kw)


def _explain(error, cfg, **kw):
    """Turn a library error into something worth reading."""
    text = str(error)
    low = text.lower()

    # A wrong model name is the most likely mistake, and the most fixable —
    # so when it looks like that, go and find out what IS available.
    if 'model' in low and ('not found' in low or 'does not exist' in low
                           or 'invalid' in low or '404' in low):
        names = list_models(**kw)
        if names:
            shown = ', '.join(names[:8])
            more = f' (and {len(names) - 8} more)' if len(names) > 8 else ''
            return (f'{cfg["label"]} does not have a model called '
                    f'"{cfg["model"]}". It does have: {shown}{more}.')
        return (f'{cfg["label"]} does not have a model called '
                f'"{cfg["model"]}". Check the spelling on their website.')

    if '401' in low or 'unauthor' in low or 'invalid_api_key' in low or 'api key' in low:
        return (f'{cfg["label"]} rejected that key. Check you copied all of '
                f'it, with no spaces at the ends.')
    if '403' in low or 'permission' in low:
        return (f'{cfg["label"]} accepted the key but will not allow this. '
                f'The account may not have access to "{cfg["model"]}".')
    if '429' in low or 'quota' in low or 'rate limit' in low:
        return (f'The key works, but the {cfg["label"]} account is out of '
                f'credit or being rate-limited.')
    if 'connect' in low or 'timeout' in low or 'timed out' in low or 'name or service' in low:
        if cfg['provider'] in ('ollama', 'custom'):
            return (f'Nothing answered at {cfg["base_url"]}. Is that machine '
                    f'switched on, is the address right, and is the server '
                    f'set to accept connections from other machines?')
        return (f'Could not reach {cfg["label"]}. Is this machine online?')

    return f'{cfg["label"]} said: {text[:300]}'


# ============================================================================
# Run this file directly to see what is switched on:
#     python3 llm.py
# ============================================================================
if __name__ == '__main__':
    cfg = current()
    print(f"Provider : {cfg['label']}  ({cfg['provider']})")
    print(f"Model    : {cfg['model'] or '— not set —'}")
    print(f"Address  : {cfg['base_url'] or '— not set —'}")
    print(f"Key      : {'set (' + cfg['key_env'] + ')' if cfg['key'] else '— not set —'}")
    print()
    ok, message = test()
    print(('OK   ' if ok else 'FAIL ') + message)
