"""
What Yobot knows, and how it looks things up.
================================================================================

PLAIN ENGLISH VERSION
---------------------

Yobot's facts live in three plain-text JSON files that sit next to this one:

    knowledge.json             Who Yobot is. Travels with the robot.
    library_knowledge.json     The Biblioteca de Boquete and the Library Park.
    clubhouse_knowledge.json   The Rincón Clubhouse — here, and worldwide.

This file is the part that reads them. You should almost never need to edit it.
To change what Yobot says, edit the JSON files. To teach Yobot a brand new
topic, copy a block in a JSON file and list the words a visitor might say. That
is all — there is no Python to touch any more. (It used to be that adding a
topic meant editing a list of keywords inside ohbotchat_server.py by hand. That
list is gone; the keywords now live with their answers, where you can see them.)

WHICH FILE WINS
    The files are read in the order above and later ones win. So knowledge.json
    has a plain "Hi there!" greeting, and library_knowledge.json replaces it
    with "Welcome to the Biblioteca de Boquete." Move the robot to a new
    building, swap the venue file, and the greeting follows it.

HOW A QUESTION FINDS AN ANSWER
    Yobot looks at what the visitor said and hunts for the longest keyword that
    appears in it. "Where is the park?" matches the keyword "park". "What time
    does the park open?" matches "what time does the park open" — longer, so it
    wins, and Yobot gives the park hours rather than the library hours. If
    nothing matches, the question goes to the AI instead.

THE OTHER HALF: THE FACT SHEET
    Keywords only catch questions phrased in ways we thought of. So this file
    also builds a "fact sheet" — a compact summary of every library and
    Clubhouse fact — which gets handed to the AI along with Yobot's
    personality. That way, when a visitor asks something unexpected like
    "is there anywhere quiet to read near the river?", the AI answers from real
    facts instead of making something up.

Both the Greeter (ohbot_chat.py + ohbotchat_server.py) and the web GUI chat
panel (gui_server.py) use this same file, so there is one set of facts and one
place to edit them.
"""

import json
import os
import re
import unicodedata
from datetime import date

# ── Where the files are ────────────────────────────────────────────────────
# Read in this order. If the same topic name appears twice, the LAST file wins.
_HERE = os.path.dirname(os.path.abspath(__file__))

IDENTITY_FILE = "knowledge.json"
VENUE_FILES = ["library_knowledge.json", "clubhouse_knowledge.json"]
ALL_FILES = [IDENTITY_FILE] + VENUE_FILES

# ── The Clubhouse opening date ─────────────────────────────────────────────
# The Clubhouse answers are written with {opens} and {abre} in them instead of
# the words "opens" / "opened". Before this date Yobot says "opens"; on or
# after it he says "opened". Saves rewriting the file the morning it opens.
CLUBHOUSE_OPENING = date(2026, 8, 10)

_TENSE_WORDS = {
    "opens": ("opens", "opened"),          # English: future, past
    "abre":  ("abre", "abrió"),            # Spanish: future, past
}


def _apply_tense(text: str) -> str:
    """Swap {opens} / {abre} for the right word based on today's date."""
    past = date.today() >= CLUBHOUSE_OPENING
    for token, (future_word, past_word) in _TENSE_WORDS.items():
        word = past_word if past else future_word
        # Capitalise if the token starts the sentence.
        text = text.replace("{" + token.capitalize() + "}", word.capitalize())
        text = text.replace("{" + token + "}", word)
    return text


# ── Loading ────────────────────────────────────────────────────────────────

def _read_one(filename: str) -> dict:
    path = os.path.join(_HERE, filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"⚠️  {filename} not found — those answers are unavailable.")
        return {}
    except json.JSONDecodeError as e:
        print(f"⚠️  {filename} has a typo in it and could not be read: {e}")
        return {}
    # Keys starting with an underscore are notes to you, not topics.
    return {k: v for k, v in data.items()
            if not k.startswith("_") and isinstance(v, dict)}


def load_knowledge(files=None) -> dict:
    """Read the JSON files and merge them into one dictionary of topics."""
    merged = {}
    for filename in (files or ALL_FILES):
        merged.update(_read_one(filename))
    return merged


# The knowledge, loaded once when a program starts. Restart the program after
# editing a JSON file.
KNOWLEDGE = load_knowledge()
VENUE_KNOWLEDGE = load_knowledge(VENUE_FILES)


def topic_names() -> list:
    """Every topic Yobot has an instant answer for."""
    return sorted(KNOWLEDGE.keys())


def answer(topic: str, language: str = "en") -> str:
    """The words Yobot should say for a topic, in English or Spanish."""
    entry = KNOWLEDGE.get(topic)
    if not entry:
        return ""
    text = entry.get(f"answer_{language}") or entry.get("answer_en", "")
    return _apply_tense(text)


# ── Matching what the visitor said to a topic ──────────────────────────────

def _normalise(text: str) -> str:
    """Lower-case, and strip accents so 'dónde' and 'donde' both match."""
    text = text.lower().strip()
    text = unicodedata.normalize("NFD", text)
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def _build_index(knowledge: dict) -> list:
    """Turn every keyword into a ready-to-use search pattern.

    Sorted longest first so the most specific keyword gets first refusal —
    "park hours" beats plain "park".
    """
    index = []
    for topic, entry in knowledge.items():
        for keyword in entry.get("keywords", []):
            clean = _normalise(keyword)
            if not clean:
                continue
            pattern = re.compile(r"\b" + re.escape(clean) + r"\b")
            index.append((len(clean), topic, pattern))
    index.sort(key=lambda row: row[0], reverse=True)
    return index


_INDEX = _build_index(KNOWLEDGE)

# Greetings and goodbyes are only greetings when they're short. "Hi, where are
# the bathrooms?" is a bathroom question, not a hello.
_SHORT_ONLY = {"greeting", "goodbye"}
_SHORT_ONLY_MAX_WORDS = 6


def find_topic(text: str):
    """Which topic is this visitor asking about? Returns a name, or None."""
    clean = _normalise(text)
    if not clean:
        return None
    word_count = len(clean.split())
    for _, topic, pattern in _INDEX:
        if topic in _SHORT_ONLY and word_count > _SHORT_ONLY_MAX_WORDS:
            continue
        if pattern.search(clean):
            return topic
    return None


# ── Which language is the visitor speaking? ────────────────────────────────

_SPANISH_MARKERS = [
    "que", "donde", "esta", "estan", "hola", "gracias", "puedo", "como",
    "cuando", "puedes", "tienen", "algo", "sobre", "eres", "tienes",
    "llamas", "cual", "quien", "buenas", "buenos", "dias", "tardes",
    "noches", "biblioteca", "cuanto", "cuantos", "cuanta", "para", "hay",
    "libro", "libros", "nino", "ninos", "adios", "chao", "hasta", "luego",
    "usted", "tienes", "quiero", "necesito", "ayuda", "gratis", "abre",
    "cierra", "horario", "parque", "bano", "banos", "senor", "senora",
    "por", "con", "una", "unos", "unas", "del", "los", "las", "muy", "mas",
    "si", "no", "es", "el", "la", "en", "de", "y", "un",
]

# Words that are too short or too English-looking to trust on their own —
# they only count when a longer Spanish word turns up alongside them.
_WEAK_MARKERS = {"no", "es", "el", "la", "en", "de", "y", "un", "si", "por",
                 "con", "una", "las", "los", "del", "mas", "muy"}


def detect_language(text: str) -> str:
    """A quick guess: Spanish if common Spanish words show up, else English."""
    clean = _normalise(text)
    words = set(re.findall(r"[a-z]+", clean))
    strong = [m for m in _SPANISH_MARKERS
              if m not in _WEAK_MARKERS and m in words]
    weak = [m for m in _WEAK_MARKERS if m in words]
    if strong:
        return "es"
    # Two or more little Spanish words together ("por favor", "en la") is
    # still a decent sign, and one on its own is not.
    return "es" if len(weak) >= 2 else "en"


# ── The fact sheet handed to the AI ────────────────────────────────────────

_FACT_SHEET_HEADER = {
    "en": (
        "FACTS ABOUT THIS PLACE. Use these when answering questions about the "
        "library, the park or the Clubhouse. Put them in your own words and "
        "keep your own personality. If a visitor asks something these facts do "
        "not cover, say plainly that you do not know and suggest asking at the "
        "front desk — never guess at hours, prices, names or directions."
    ),
    "es": (
        "DATOS SOBRE ESTE LUGAR. Úsalos al responder preguntas sobre la "
        "biblioteca, el parque o el Clubhouse. Dilos con tus propias palabras y "
        "mantén tu personalidad. Si te preguntan algo que estos datos no "
        "cubren, di con franqueza que no lo sabes y sugiere preguntar en la "
        "recepción — nunca inventes horarios, precios, nombres ni direcciones."
    ),
}

# Not worth spending prompt space on — the personality already handles these.
_SKIP_IN_FACT_SHEET = {"greeting", "goodbye"}


def fact_sheet(language: str = "en") -> str:
    """A compact list of venue facts, for pasting into the AI system prompt."""
    lines = [_FACT_SHEET_HEADER.get(language, _FACT_SHEET_HEADER["en"]), ""]
    for topic, entry in VENUE_KNOWLEDGE.items():
        if topic in _SKIP_IN_FACT_SHEET:
            continue
        text = entry.get(f"answer_{language}") or entry.get("answer_en", "")
        if not text:
            continue
        label = topic.replace("_", " ")
        lines.append(f"- {label}: {_apply_tense(text)}")
    return "\n".join(lines)


# ── A quick self-check ─────────────────────────────────────────────────────
# Run this file on its own to see what loaded and try a few questions:
#     python3 knowledge_base.py
if __name__ == "__main__":
    print(f"Loaded {len(KNOWLEDGE)} topics from {len(ALL_FILES)} files.\n")
    print("Topics:", ", ".join(topic_names()), "\n")

    tests = [
        "Hello!",
        "Where is the bathroom?",
        "What time do you close?",
        "What time does the park open?",
        "Is there wifi?",
        "What is the Rincon Clubhouse?",
        "When does the clubhouse open?",
        "Who made you?",
        "Hola, donde esta el baño?",
        "¿A qué hora abre el parque?",
        "¿Qué es el Rincón Clubhouse?",
        "Cuanto cuesta el clubhouse?",
        "What is the capital of France?",
    ]
    for question in tests:
        lang = detect_language(question)
        topic = find_topic(question)
        reply = answer(topic, lang) if topic else "→ (goes to the AI)"
        print(f"[{lang}] {question}\n    {topic or '—'}: {reply[:100]}\n")
