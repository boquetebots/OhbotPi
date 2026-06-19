#!/usr/bin/env python3
"""
Ohbot Flask Server — OpenAI Integration
Receives visitor input, classifies intent, and returns a response.

Two intents:
  local_knowledge  → answer from knowledge.json (instant, no API cost)
  general_chat     → send to OpenAI GPT for a conversational response

Runs on port 5002. ohbot_chat.py connects to this server.
"""

from flask import Flask, request, jsonify
from openai import OpenAI
import json
import os
from collections import deque

app = Flask(__name__)

# ── OpenAI setup ───────────────────────────────────────────────────────────────
api_key = os.environ.get("OPENAI_API_KEY")

if not api_key:
    print("❌ ERROR: OPENAI_API_KEY not set!")
    print("Add it to your .env file — see .env.example for instructions.")
    exit(1)

client = OpenAI(api_key=api_key)

# Conversation memory — stores last 10 exchanges (20 messages)
conversation_history = deque(maxlen=20)


# ============================================================================
# CUSTOMIZE THIS SECTION
# ============================================================================
#
# SYSTEM_PROMPT tells Ohbot who it is and how to behave.
# Rewrite this completely for your own use case.
#
# Tips:
#   - Give Ohbot a name, a location, and a purpose
#   - Keep responses brief — they are spoken aloud
#   - Mention any specific topics Ohbot should know about
#   - Describe the personality you want (friendly, funny, formal, etc.)
#
# Example for a museum:
#   "You are Robo, a friendly robot guide at the City Science Museum.
#    Help visitors find exhibits, answer questions about science, and
#    make learning fun. Keep responses to 1-3 sentences."
#
# Example for a reception desk:
#   "You are Ohbot, a cheerful robot receptionist at Acme HQ.
#    Help visitors check in, find meeting rooms, and contact staff.
#    Be professional but warm. Keep responses brief."
#
SYSTEM_PROMPT = """You are Ohbot, a friendly and curious robot assistant.

Keep your responses brief — 1 to 3 sentences — since they are spoken aloud.
Be warm, conversational, and a little playful.
You are talking face-to-face with someone standing right in front of you.

Customize this prompt to give Ohbot a specific name, location, personality,
and area of knowledge that suits your project.
"""

# ── Language detection ─────────────────────────────────────────────────────────

def _detect_language(text: str) -> str:
    """Quick heuristic: if common Spanish words appear, call it Spanish."""
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

    Handles greetings, goodbyes, and robot identity questions instantly.
    Everything else returns None and falls through to GPT.

    To add your own instant-answer topics:
      1. Add a keyword block below that returns a topic key
      2. Add a matching entry in knowledge.json with your answer text
    """
    t = text.lower().strip()
    lang = _detect_language(t)

    # ── GREETINGS ─────────────────────────────────────────────────────────────
    greeting_words = [
        "hello", "hi there", "good morning", "good afternoon",
        "good evening", "hey there", "hola", "buenos días", "buenos dias",
        "buenas tardes", "buenas noches", "buenas",
    ]
    if len(t.split()) <= 4 and any(g in t for g in greeting_words):
        return {"intent": "local_knowledge", "topic": "greeting", "language": lang}

    # ── GOODBYES ──────────────────────────────────────────────────────────────
    goodbye_phrases = [
        "bye", "goodbye", "good bye", "adios", "adiós",
        "hasta luego", "chao", "chau", "see you", "see you later",
        "bye bye", "thanks bye", "thank you bye",
    ]
    simple_thanks = ["thanks", "thank you", "gracias", "muchas gracias"]
    if len(t.split()) <= 6:
        if any(g in t for g in goodbye_phrases):
            return {"intent": "local_knowledge", "topic": "goodbye", "language": lang}
        if t.rstrip("!.,") in simple_thanks:
            return {"intent": "local_knowledge", "topic": "goodbye", "language": lang}

    # ── ROBOT IDENTITY ────────────────────────────────────────────────────────
    if any(p in t for p in ["who are you", "what are you", "quién eres", "quien eres",
                             "qué eres", "que eres"]):
        return {"intent": "local_knowledge", "topic": "who_are_you", "language": lang}

    if any(p in t for p in ["what can you do", "how can you help", "what do you do",
                             "qué puedes hacer", "que puedes hacer"]):
        return {"intent": "local_knowledge", "topic": "what_can_you_do", "language": lang}

    if any(p in t for p in ["what is your name", "what's your name",
                             "cómo te llamas", "como te llamas", "tu nombre"]):
        return {"intent": "local_knowledge", "topic": "your_name", "language": lang}

    if any(p in t for p in ["who made you", "who built you", "who created you",
                             "quién te hizo", "quien te hizo"]):
        return {"intent": "local_knowledge", "topic": "who_made_you", "language": lang}

    if any(p in t for p in ["are you alive", "do you have feelings", "are you real",
                             "eres vivo", "tienes sentimientos", "eres real", "are you conscious"]):
        return {"intent": "local_knowledge", "topic": "are_you_alive", "language": lang}

    if any(p in t for p in ["how do you work", "are you ai", "are you a robot",
                             "cómo funcionas", "como funcionas", "artificial intelligence"]):
        return {"intent": "local_knowledge", "topic": "how_do_you_work", "language": lang}

    if any(p in t for p in ["how old are you", "cuántos años tienes", "cuantos años tienes"]):
        return {"intent": "local_knowledge", "topic": "how_old_are_you", "language": lang}

    if any(p in t for p in ["can you dance", "puedes bailar", "dance for me"]):
        return {"intent": "local_knowledge", "topic": "can_you_dance", "language": lang}

    if any(p in t for p in ["take you home", "can i buy you", "are you for sale",
                             "puedo comprarte", "cuánto cuestas"]):
        return {"intent": "local_knowledge", "topic": "take_me_home", "language": lang}

    # ── ADD YOUR OWN TOPICS HERE ──────────────────────────────────────────────
    # Example:
    # if any(w in t for w in ["hours", "open", "close", "horario"]):
    #     return {"intent": "local_knowledge", "topic": "hours", "language": lang}
    #
    # Then add "hours": { "answer_en": "...", "answer_es": "..." } to knowledge.json

    # ── FALL THROUGH TO GPT ───────────────────────────────────────────────────
    return None


# ============================================================================
# INTENT CLASSIFICATION PROMPT (LLM fallback for ambiguous input)
# ============================================================================

INTENT_PROMPT = """You are a classifier for a robot assistant. Given a visitor's statement,
determine what they want. Respond with ONLY a JSON object, nothing else.

The JSON must have these fields:
{
    "intent": "local_knowledge" or "general_chat",
    "topic": "knowledge topic key" or null,
    "language": "en" or "es"
}

RULES:

1. "local_knowledge" = a common question that likely has a pre-written answer.
   Use these topic keys:
   greeting, goodbye, who_are_you, what_can_you_do, your_name, who_made_you,
   are_you_alive, how_do_you_work, how_old_are_you, can_you_dance, take_me_home

2. "general_chat" = anything else — set topic to null.

Set language to "en" or "es" based on the visitor's language.
"""


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

        # ── LLM FALLBACK (for ambiguous questions) ────────────────────────────
        print("🤖 Ambiguous — asking LLM to classify")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": INTENT_PROMPT},
                {"role": "user",   "content": user_message}
            ],
            max_tokens=100,
            temperature=0.1
        )

        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        result = json.loads(raw)
        print(f"✅ Intent: {result['intent']}, topic={result.get('topic')}, lang={result.get('language', 'en')}")

        return jsonify({
            'success':      True,
            'intent':       result.get('intent', 'general_chat'),
            'search_terms': None,
            'topic':        result.get('topic'),
            'language':     result.get('language', 'en'),
        })

    except json.JSONDecodeError:
        print("⚠️  Could not parse intent JSON — defaulting to general_chat")
        return jsonify({'success': True, 'intent': 'general_chat',
                        'search_terms': None, 'topic': None, 'language': 'en'})
    except Exception as e:
        print(f"❌ Intent detection error: {e}")
        return jsonify({'success': True, 'intent': 'general_chat',
                        'search_terms': None, 'topic': None, 'language': 'en'})


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

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_message})

        print("🤖 Calling OpenAI...")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=150,
            temperature=0.7
        )

        assistant_message = response.choices[0].message.content.strip()
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
    <html><head><title>Ohbot Server</title></head>
    <body>
        <h1>🤖 Ohbot Server — Running</h1>
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
    print("🤖  Ohbot Server starting...")
    print("=" * 60)
    print(f"  OpenAI key: {'✅ Set' if api_key else '❌ NOT SET'}")
    print(f"  Model: gpt-4o-mini")
    print(f"  Port: 5002")
    print("=" * 60)
    print()
    app.run(host='0.0.0.0', port=5002, debug=False)
