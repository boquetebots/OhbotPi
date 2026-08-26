#!/usr/bin/env python3
"""
Yobot Flask Server — OpenAI Integration
Receives visitor input, classifies intent, and returns a response.

Two intents:
  local_knowledge  → answer from knowledge.json (instant, no API cost)
  general_chat     → send to OpenAI GPT for a conversational response

Runs on port 5002. ohbot_chat.py connects to this server.
"""

from flask import Flask, request, jsonify
import json
import os
import sys
import time
from collections import deque

# Load API keys from the .env file next to this script (works on any
# platform, with or without systemd)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Save everything this program prints into logs/greeter-api-<date>.log
try:
    from ohbot_logging import setup_logging
    setup_logging("greeter-api")
except Exception as _log_err:                                # noqa: BLE001
    print(f"⚠️  Log file not started ({_log_err}) — carrying on without one")
try:
    from yobot_core import load_env
    load_env()
except ImportError:
    pass

app = Flask(__name__)

# ── The AI ─────────────────────────────────────────────────────────────────
# WHICH company answers — OpenAI, Anthropic, Gemini, Grok, an Ollama server on
# your own network, or anything else that speaks the same format — is decided
# in llm.py from the .env settings, and is changed from the Launcher's
# Settings page. Nothing in this file needs to know which one it is.
import llm

AI_READY, AI_PROBLEM = llm.is_ready()

# NO AI? START ANYWAY.
# --------------------
# This used to quit on the spot. That was wrong for anybody installing the
# robot for the first time: the Launcher page reports "Greeter" as running,
# it dies a second later, and there is nothing on screen explaining why.
#
# Now it starts regardless. The keyword answers in knowledge.json still work
# with no AI at all, so the robot is not mute — and anything it cannot
# answer gets the polite line below, which tells whoever is standing there
# exactly what to do about it.
if AI_READY:
    print(f"\U0001f9e0 AI: {llm.describe()}")
else:
    print(f"\u26a0\ufe0f  {AI_PROBLEM}")
    print("    Keyword answers still work. Open the Launcher page in a")
    print("    browser and use \u2699\ufe0f Settings & Keys to switch the AI on.")

# What Yobot says out loud when it has no AI and the question was not one of
# the keyword answers.
NO_BRAIN_REPLY = {
    "en": ("I don\u2019t have my thinking key yet, so I can only answer a few set "
           "questions. Whoever set me up can add one on my Launcher page, "
           "under Settings."),
    "es": ("Todav\u00eda no tengo mi clave para pensar, as\u00ed que solo puedo "
           "responder algunas preguntas fijas. Quien me configur\u00f3 puede "
           "a\u00f1adirla en mi p\u00e1gina de Lanzador, en Ajustes."),
}

# Conversation memory — stores last 10 exchanges (20 messages)
conversation_history = deque(maxlen=20)


# ============================================================================
# CUSTOMIZE THIS SECTION
# ============================================================================
#
# SYSTEM_PROMPT tells Yobot who it is and how to behave — its character.
#
# WHERE the robot lives is deliberately NOT in here. That text lives in
# venue.py and gets added on automatically just below. Keeping the two apart
# means you can change the robot's personality without retyping the venue
# description, and move the robot to a new building without rewriting its
# personality. Both files feed the GUI chat panel too.
#
# Tips for editing the character text:
#   - Keep responses brief — they are spoken aloud
#   - Describe the personality you want (friendly, funny, formal, etc.)
#   - Leave facts about the building to venue.py
#
SYSTEM_PROMPT = """You are Yobot, a friendly and curious robot assistant.

Keep your responses brief — 1 to 3 sentences — since they are spoken aloud.
Be warm, conversational, and a little playful.
You are talking face-to-face with someone standing right in front of you.
"""

# ── The venue description, loaded from venue.py ─────────────────────────────
# The try/except is a safety net: if venue.py ever goes missing, the robot
# still starts and talks — it just won't know where it is.
try:
    from venue import VENUE_INFO
except ImportError:
    VENUE_INFO = ""
    print("⚠️  venue.py not found — Yobot won't know where it lives.")

# ── The safety rules, loaded from guardrails.py ─────────────────────────────
# These come last on purpose — see the note at the top of guardrails.py.
try:
    from guardrails import SAFETY_RULES
except ImportError:
    SAFETY_RULES = ""
    print("⚠️  guardrails.py not found — Yobot is running WITHOUT safety rules.")

# ── The facts about the library and the Clubhouse ───────────────────────────
# knowledge_base.py reads the three JSON files (knowledge.json,
# library_knowledge.json, clubhouse_knowledge.json) and does two jobs here:
#
#   1. Matches common questions to an instant answer — free, no AI call.
#   2. Builds a "fact sheet" of everything about the building, which we hand
#      to the AI below. That's what stops Yobot inventing library hours when
#      a visitor phrases a question in a way the keywords didn't expect.
#
# The try/except is a safety net: if the file goes missing the robot still
# starts and talks, it just falls back to the AI for everything.
try:
    import knowledge_base as kb
    _kb_ok = True
except Exception as e:                                   # noqa: BLE001
    kb = None
    _kb_ok = False
    print(f"⚠️  knowledge_base.py could not load ({e}) — instant answers off.")


def full_system_prompt(language: str = "en") -> str:
    """What actually gets sent to the AI.

    Order: character, then where it lives, then the local facts, then the
    safety rules. The rules come last so they win any disagreement.
    """
    parts = [SYSTEM_PROMPT, VENUE_INFO]
    if _kb_ok:
        parts.append(kb.fact_sheet(language))
    parts.append(SAFETY_RULES)
    return "\n".join(parts)


# ── Language detection ─────────────────────────────────────────────────────────

def _detect_language(text: str) -> str:
    """Quick heuristic: if common Spanish words appear, call it Spanish."""
    if _kb_ok:
        return kb.detect_language(text)
    spanish_markers = [
        "qué", "que", "dónde", "donde", "está", "estan", "están",
        "hola", "gracias", "puedo", "cómo", "como", "cuando", "cuándo",
        "puedes", "tienen", "algo", "sobre", "eres", "tienes", "llamas",
    ]
    t = text.lower()
    return "es" if any(w in t for w in spanish_markers) else "en"


# ============================================================================
# LOCAL INTENT CLASSIFIER
# Handles common questions instantly — no LLM call, no tokens, no delay.
# Returns a dict, or None if the question should go to GPT.
# ============================================================================

def local_intent_detect(text: str):
    """
    Classify visitor input using keyword matching — zero LLM cost.

    THERE ARE NO KEYWORD LISTS IN THIS FILE ANY MORE. They used to live here,
    which meant adding a topic took two edits in two languages in two files.
    Now every keyword sits in the JSON file right next to the answer it
    triggers, and knowledge_base.py does the matching. To teach Yobot a new
    instant answer, edit the JSON — that's the whole job.

    Returns a dict, or None if the question should go to GPT instead.
    """
    if not _kb_ok:
        return None

    lang = kb.detect_language(text)
    topic = kb.find_topic(text)
    if topic:
        return {"intent": "local_knowledge", "topic": topic, "language": lang}
    return None


# ============================================================================
# INTENT CLASSIFICATION PROMPT (LLM fallback for ambiguous input)
# ============================================================================
#
# When the keywords don't match, we ask the AI to pick a topic. The list of
# topics it's allowed to choose from is built from the JSON files below, so
# new topics you add are automatically offered to the classifier too.

_TOPIC_LIST = ", ".join(kb.topic_names()) if _kb_ok else "greeting, goodbye"

INTENT_PROMPT = """You are a classifier for a robot assistant. Given a visitor's statement,
determine what they want. Respond with ONLY a JSON object, nothing else.

The JSON must have these fields:
{{
    "intent": "local_knowledge" or "general_chat",
    "topic": "knowledge topic key" or null,
    "language": "en" or "es"
}}

RULES:

1. "local_knowledge" = a common question that has a pre-written answer.
   Use ONLY these topic keys:
   {topics}

2. "general_chat" = anything else — set topic to null. If you are not
   confident the visitor is asking about one of the topics above, choose
   general_chat.

Set language to "en" or "es" based on the visitor's language.
""".format(topics=_TOPIC_LIST)


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.route('/intent', methods=['POST'])
def detect_intent():
    """
    Detect what the visitor wants.

    Expects JSON:  {"message": "visitor's words"}

    Returns JSON:
        {
            "success": true,
            "intent": "local_knowledge" or "general_chat",
            "topic": "who_are_you" or null,
            "language": "en" or "es"
        }
    """
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'success': False, 'error': 'No message provided'}), 400

        user_message = data['message'].strip()
        if not user_message:
            return jsonify({'success': False, 'error': 'Empty message'}), 400

        print(f"🔍 Detecting intent: {user_message}")

        # ── LOCAL CLASSIFIER (free — no LLM tokens) ───────────────────────────
        local = local_intent_detect(user_message)
        if local:
            print(f"⚡ Local: intent={local['intent']}, topic={local.get('topic')}, lang={local['language']}")
            return jsonify({
                'success':      True,
                'intent':       local['intent'],
                'search_terms': None,
                'topic':        local.get('topic'),
                'language':     local['language'],
            })

        # No AI key: everything the keyword matcher missed is just chat.
        # /chat below answers those with the "no key yet" line.
        if not AI_READY:
            return jsonify({
                'success':      True,
                'intent':       'general_chat',
                'search_terms': None,
                'topic':        None,
                'language':     _detect_language(user_message),
            })

        # ── LLM FALLBACK (for ambiguous questions) ────────────────────────────
        print("🤖 Ambiguous — asking LLM to classify")
        raw = llm.ask(
            [{"role": "system", "content": INTENT_PROMPT},
             {"role": "user",   "content": user_message}],
            max_tokens=100,
            temperature=0.1,
        )
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        result = json.loads(raw)
        print(f"✅ Intent: {result['intent']}, topic={result.get('topic')}, lang={result.get('language', 'en')}")

        return jsonify({
            'success':      True,
            'intent':       result.get('intent', 'general_chat'),
            'search_terms': None,
            'topic':        result.get('topic'),
            'language':     result.get('language'),
        })

    # On the two failure paths below, language is deliberately null rather
    # than 'en'. Saying "en" here is a guess, and the Greeter would take it
    # as a real answer and switch a Spanish conversation into English purely
    # because something went wrong. Null means "no opinion — carry on in
    # whatever language you were already speaking."
    except json.JSONDecodeError:
        print("⚠️  Could not parse intent JSON — defaulting to general_chat")
        return jsonify({'success': True, 'intent': 'general_chat',
                        'search_terms': None, 'topic': None, 'language': None})
    except Exception as e:
        print(f"❌ Intent detection error: {e}")
        return jsonify({'success': True, 'intent': 'general_chat',
                        'search_terms': None, 'topic': None, 'language': None})


@app.route('/chat', methods=['POST'])
def chat():
    """
    Main chat endpoint — sends visitor message to GPT and returns a response.

    Expects JSON:  {"message": "visitor's question"}
    Returns JSON:  {"response": "GPT response", "success": true/false}
    """
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'success': False, 'error': 'No message provided'}), 400

        user_message = data['message'].strip()
        if not user_message:
            return jsonify({'success': False, 'error': 'Empty message'}), 400

        print(f"📥 Received: {user_message}")

        # Facts are handed over in whichever language the visitor is speaking,
        # so the AI is quoting Spanish answers to Spanish questions rather than
        # translating English ones on the fly.
        lang = _detect_language(user_message)

        messages = [{"role": "system", "content": full_system_prompt(lang)}]
        messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_message})

        if not AI_READY:
            reply = NO_BRAIN_REPLY.get(lang, NO_BRAIN_REPLY["en"])
            print(f"⚠️  No AI key — answering: {reply}")
            return jsonify({'success': True, 'response': reply})

        print(f"🤖 Asking {llm.describe()}...")
        assistant_message = llm.ask(messages, max_tokens=150, temperature=0.7)
        print(f"📤 Response: {assistant_message}")

        conversation_history.append({"role": "user",      "content": user_message})
        conversation_history.append({"role": "assistant", "content": assistant_message})

        return jsonify({'success': True, 'response': assistant_message})

    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error: {error_msg}")
        if "connection" in error_msg.lower() or "network" in error_msg.lower():
            return jsonify({'success': False, 'error': 'Network issues'}), 503
        return jsonify({'success': False, 'error': 'OpenAI API failed'}), 500


@app.route('/reset', methods=['POST'])
def reset():
    """Reset conversation history — called between sessions."""
    conversation_history.clear()
    print("🔄 Conversation history reset")
    return jsonify({'success': True, 'message': 'Conversation reset'})


# ============================================================================
# WAKE FROM SLEEP
# ============================================================================
#
# After a couple of quiet turns Yobot goes to sleep to stop paying Azure to
# listen to an empty room. Something then has to wake him back up.
#
# On the Pi that used to mean a physical button wired to GPIO pin 17 — and if
# no button is wired, he sleeps forever with no way back. These two routes are
# the way out: the Launcher web page can now ask for a wake, so any phone or
# laptop on the network can do the job of that button.
#
# It's deliberately just a flag, not a live connection. The conversation loop
# (ohbot_chat.py) is a separate program, so while it's sleeping it checks in
# here once a second and asks "has anyone pressed wake?" That check is a local
# request to this same Pi — it costs nothing and never touches Azure.
#
# A press counts for this long. Long enough that pressing Wake *while* he is
# still saying goodbye is remembered until he's actually asleep and looking;
# short enough that a press from this morning can't wake him this afternoon.
WAKE_PRESS_VALID_FOR = 60.0     # seconds

_wake_pressed_at = 0.0


@app.route('/wake', methods=['POST'])
def request_wake():
    """Record a Wake press. Called by the Launcher's Wake button."""
    global _wake_pressed_at
    _wake_pressed_at = time.time()
    print("⏰ Wake requested")
    return jsonify({'success': True})


@app.route('/wake/pending', methods=['GET'])
def wake_pending():
    """Report whether there's a recent, unused Wake press — and use it up.

    Storing WHEN the button was pressed rather than just THAT it was pressed
    is what makes a press during the goodbye speech still work. The old
    version threw away any press made before he finished falling asleep,
    which made the button look broken.
    """
    global _wake_pressed_at
    fresh = (time.time() - _wake_pressed_at) < WAKE_PRESS_VALID_FOR
    if fresh:
        _wake_pressed_at = 0.0      # used up — one press, one wake
    return jsonify({'wake': fresh})


@app.route('/health', methods=['GET'])
def health():
    """Health check — called by ohbot_chat.py on startup."""
    return jsonify({
        'status': 'healthy',
        'conversation_length': len(conversation_history) // 2,
        'openai_key_set': bool(api_key)
    })


@app.route('/', methods=['GET'])
def home():
    return """
    <html><head><title>Yobot Server</title></head>
    <body>
        <h1>🤖 Yobot Server — Running</h1>
        <p>OpenAI API Key: <strong>{key}</strong></p>
        <p>Conversation History: <strong>{hist} exchanges</strong></p>
        <hr>
        <h2>Endpoints:</h2>
        <ul>
            <li><code>POST /intent</code> — Classify visitor input</li>
            <li><code>POST /chat</code> — General conversation with GPT</li>
            <li><code>POST /reset</code> — Clear conversation history</li>
            <li><code>GET /health</code> — Health check</li>
        </ul>
    </body></html>
    """.format(
        key="✅ Set" if api_key else "❌ Not Set",
        hist=len(conversation_history) // 2
    )


if __name__ == '__main__':
    print("=" * 60)
    print("🤖  Yobot Server starting...")
    print("=" * 60)
    print(f"  OpenAI key: {'✅ Set' if api_key else '❌ NOT SET'}")
    print(f"  Model: gpt-4o-mini")
    print(f"  Port: 5002")
    if _kb_ok:
        print(f"  Knowledge: ✅ {len(kb.KNOWLEDGE)} topics "
              f"({', '.join(kb.ALL_FILES)})")
    else:
        print("  Knowledge: ❌ not loaded — every question will go to the AI")
    print("=" * 60)
    print()
    app.run(host='0.0.0.0', port=5002, debug=False)
