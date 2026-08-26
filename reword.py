"""
Making Yobot sound less like a recording.
================================================================================

PLAIN ENGLISH VERSION
---------------------

THE PROBLEM THIS SOLVES

Right now, when a visitor says something that matches a keyword, Yobot speaks
the sentence out of the JSON file word for word. Every time. Forever.

    Visitor: "Tell me about the Clubhouse."
    Yobot:   "A Rincon Clubhouse is a free after-school space where young
              people get to build things with technology..."

    Visitor: "Tell me MORE about the Clubhouse."
    Yobot:   "A Rincon Clubhouse is a free after-school space where young
              people get to build things with technology..."

Identical. That is why he sounds rote. The AI is never involved — it only gets
a look at questions that match no keyword at all.

WHAT THIS FILE DOES

It takes the fact out of the JSON file and asks the AI to *say that fact in
Yobot's own words* instead of reading it out. Same fact, fresh wording, every
single time. And because the AI can see what the visitor actually asked and
what Yobot already said, "tell me more" gets a genuinely different, fuller
answer rather than the same recording again.

    Ask once:   "The Clubhouse is a free after-school space upstairs where
                 kids build things with technology. It opens August tenth."
    Ask again:  "Upstairs, top floor! It's free, it's for young people, and
                 it's all hands-on — robots, 3D printing, that sort of thing."

WHAT IT WILL NOT DO

It will not change a fact. Three separate safety nets:

  1. VERBATIM_TOPICS below — a list of topics that are NEVER reworded and are
     always read out exactly as written. Wifi passwords and phone numbers are
     in there. Add any topic you don't want touched.

  2. The number guard — after the AI rewords something, this file checks that
     every number, time, price, web address and email that was in the original
     is still in the new version. If the AI dropped or changed one, the
     reworded version is thrown away and the original is used instead.

  3. Any failure at all — no internet, no API key, AI too slow, weird answer —
     returns the original text unchanged. This file can never stop Yobot
     talking. Worst case he goes back to sounding like a recording.

THE MASTER SWITCH

ENABLED is False. Nothing in the live robot calls this file yet. It exists so
you can try rewording in chat_test.py and decide whether you like it before
anything on the Pi changes.

    python3 chat_test.py            (then type  /reword  to turn it on)

WHAT IT COSTS

One small AI call per canned answer, on the gpt-4o-mini model — a fraction of
a US cent each. It adds roughly half a second to a second before Yobot speaks.
Answers that already go to the AI cost the same as they do now.
"""

import os
import re
import sys
from collections import defaultdict, deque

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ============================================================================
# SETTINGS — the bits you might want to change
# ============================================================================

# The master switch. False means reword() hands back whatever you gave it,
# untouched. Turn it on in chat_test.py with /reword to experiment.
ENABLED = False

# Topics that must ALWAYS be read out exactly as written, never reworded.
# These are the ones where an AI getting creative would do real damage.
# Add a topic name here (the key from the JSON file) to lock it down.
VERBATIM_TOPICS = {
    "wifi",       # contains the guest wifi password
    "contact",    # phone and WhatsApp numbers
}

# How loose the rewording is allowed to be. temperature 0.8 is deliberately
# high — that variety is the whole point.
#
# There is no model setting here on purpose: rewording uses whichever AI the
# robot is set to use, chosen on the Launcher's Settings page. Set MODEL to a
# name here only if you want the rewording done by a different (say cheaper)
# model than the one doing the talking.
MODEL = None
TEMPERATURE = 0.8
MAX_TOKENS = 140

# How long to wait for the AI before giving up and using the original.
# Kept short: a visitor standing in front of a silent robot gets bored fast.
TIMEOUT_SECONDS = 4.0

# How many recent phrasings of a topic to remember, so the AI can be told
# "you already said it that way — try another angle."
REMEMBER_PER_TOPIC = 3


# ── Yobot's speaking style ─────────────────────────────────────────────────
# This is a fallback. If ohbotchat_server.py can be read, its real
# SYSTEM_PROMPT is used instead so there is only one personality to maintain.
_FALLBACK_VOICE = """You are Yobot, a friendly and curious robot assistant.
Keep your responses brief — 1 to 3 sentences — since they are spoken aloud.
Be warm, conversational, and a little playful.
You are talking face-to-face with someone standing right in front of you."""


def _load_personality() -> str:
    """Borrow the real personality from ohbotchat_server.py if we can.

    That file quits on the spot if there is no API key, so this is wrapped up
    tightly. If anything at all goes wrong we use the fallback above.
    """
    import llm
    if not llm.is_ready()[0]:
        return _FALLBACK_VOICE
    try:
        from ohbotchat_server import SYSTEM_PROMPT
        return SYSTEM_PROMPT
    except BaseException:                                  # noqa: BLE001
        return _FALLBACK_VOICE


# ── Optional extras: where the robot lives, and the safety rules ───────────
try:
    from venue import VENUE_INFO
except Exception:                                          # noqa: BLE001
    VENUE_INFO = ""

try:
    from guardrails import SAFETY_RULES
except Exception:                                          # noqa: BLE001
    SAFETY_RULES = ""


# ============================================================================
# THE NUMBER GUARD
# ============================================================================
#
# Pulls every number, time, price, web address, email and phone number out of
# a piece of text. We run this on the original and on the AI's version, and if
# anything went missing we refuse the AI's version.
#
# Spelled-out numbers ("August tenth", "eleven to eighteen") are deliberately
# included, because the JSON answers are written to be spoken aloud and use
# words rather than digits in a lot of places.

_SPELLED_NUMBERS = (
    r"zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
    r"thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|"
    r"thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|"
    r"first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|"
    r"eleventh|twelfth|thirteenth|twentieth|thirtieth|"
    r"uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|trece|"
    r"catorce|quince|dieciseis|diecisiete|dieciocho|diecinueve|veinte|"
    r"treinta|cuarenta|cincuenta|sesenta|setenta|ochenta|noventa|cien|mil|"
    r"primero|segundo|tercero"
)

_FACT_PATTERNS = [
    re.compile(r"https?://\S+", re.I),                     # web addresses
    re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b"),            # emails
    re.compile(r"\d[\d.,:/\-]*"),                          # any digits
    re.compile(r"\b(" + _SPELLED_NUMBERS + r")\b", re.I),  # spelled numbers
]


def _facts_in(text: str) -> set:
    """Every number-ish thing in a piece of text, lower-cased."""
    found = set()
    for pattern in _FACT_PATTERNS:
        for hit in pattern.findall(text):
            hit = hit if isinstance(hit, str) else hit[0]
            cleaned = hit.strip(" .,;:").lower()
            if cleaned:
                found.add(cleaned)
    return found


def keeps_the_facts(original: str, rewritten: str) -> bool:
    """True if the rewritten version still contains every fact of the original."""
    return _facts_in(original) <= _facts_in(rewritten)


# ============================================================================
# REMEMBERING WHAT WAS ALREADY SAID
# ============================================================================

_recent = defaultdict(lambda: deque(maxlen=REMEMBER_PER_TOPIC))


def forget_everything():
    """Wipe the memory of recent phrasings. Call between visitors."""
    _recent.clear()


def times_said(topic: str) -> int:
    """How many times this topic has come up since the last reset."""
    return len(_recent[topic])


# ============================================================================
# THE MAIN JOB
# ============================================================================

# Rewording talks to the AI through llm.py, the same as everything else, so
# it follows whichever provider is chosen on the Settings page.
import llm


_INSTRUCTION = {
    "en": """You are rewording one fact for Yobot to say out loud.

THE FACT YOU MUST CONVEY:
{fact}

THE VISITOR ASKED:
"{question}"

{already}
YOUR JOB
Say that fact in Yobot's voice, as a natural reply to what the visitor
actually asked. One to three short sentences — it is spoken aloud.

RULES
- Every number, time, date, price, name and place in the fact must survive
  exactly as given. Do not round, guess, adjust or drop any of them.
- Do not add any fact that is not above. If the visitor asked for something
  the fact does not cover, say plainly that you do not know and suggest the
  front desk.
- If the visitor is asking for more detail, or has heard this before, come at
  it from a different angle and lead with the part they seem interested in.
  Do not simply repeat yourself.
- Reply with only the words Yobot should say. No quotation marks, no notes.""",

    "es": """Estás reformulando un dato para que Yobot lo diga en voz alta.

EL DATO QUE DEBES TRANSMITIR:
{fact}

EL VISITANTE PREGUNTÓ:
"{question}"

{already}
TU TAREA
Di ese dato con la voz de Yobot, como respuesta natural a lo que preguntó el
visitante. De una a tres frases cortas — se dice en voz alta.

REGLAS
- Cada número, hora, fecha, precio, nombre y lugar del dato debe conservarse
  exactamente igual. No redondees, no adivines, no ajustes ni omitas ninguno.
- No agregues ningún dato que no esté arriba. Si el visitante pregunta algo
  que el dato no cubre, di con franqueza que no lo sabes y sugiere preguntar
  en la recepción.
- Si el visitante pide más detalle, o ya escuchó esto antes, abórdalo desde
  otro ángulo y empieza por la parte que parece interesarle. No te repitas.
- Responde solo con las palabras que Yobot debe decir. Sin comillas ni notas.""",
}

_ALREADY = {
    "en": "YOU HAVE ALREADY SAID THIS, PHRASED THESE WAYS — say it differently:\n{lines}\n",
    "es": "YA LO DIJISTE ASÍ — dilo de otra manera:\n{lines}\n",
}


def reword(text: str,
           topic: str = "",
           language: str = "en",
           question: str = "",
           personality: str = None) -> str:
    """Say a canned answer in Yobot's own words instead of reading it out.

    Hands back the original text unchanged if rewording is switched off, if
    the topic is on the verbatim list, or if ANYTHING goes wrong. It is always
    safe to call.
    """
    if not ENABLED or not text:
        return text
    if topic in VERBATIM_TOPICS:
        return text

    lang = "es" if language == "es" else "en"

    already = ""
    if _recent[topic]:
        lines = "\n".join(f"- {p}" for p in _recent[topic])
        already = _ALREADY[lang].format(lines=lines)

    prompt = _INSTRUCTION[lang].format(
        fact=text,
        question=question or text,
        already=already,
    )
    voice = personality or _load_personality()
    system = "\n".join(p for p in (voice, VENUE_INFO, SAFETY_RULES) if p)

    try:
        new_text = llm.ask(
            [{"role": "system", "content": system},
             {"role": "user",   "content": prompt}],
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            timeout=TIMEOUT_SECONDS,
            model=MODEL,
        ).strip('"')
    except Exception as e:                                 # noqa: BLE001
        print(f"⚠️  Rewording failed ({e}) — using the original wording.")
        return text

    # ── The safety nets ────────────────────────────────────────────────────
    if not new_text:
        return text
    if len(new_text) > len(text) * 2.5 + 60:
        print("⚠️  Reworded answer was far too long — using the original.")
        return text
    if not keeps_the_facts(text, new_text):
        missing = sorted(_facts_in(text) - _facts_in(new_text))
        print(f"⚠️  Reworded answer lost a fact {missing} — using the original.")
        return text

    _recent[topic].append(new_text)
    return new_text


# ============================================================================
# A quick self-check — run this file on its own:  python3 reword.py
# ============================================================================

if __name__ == "__main__":
    print("Checking the number guard (this needs no API key and costs nothing)\n")

    checks = [
        ("It opens on Monday, August tenth, 2026.",
         "Doors open Monday the tenth of August, 2026!",
         True,  "kept the date"),
        ("It opens on Monday, August tenth, 2026.",
         "It opens next month sometime!",
         False, "lost the date — would be refused"),
        ("The Clubhouse is for young people aged 11 to 18.",
         "It's for anyone 11 up to 18 years old.",
         True,  "kept both ages"),
        ("The Clubhouse is for young people aged 11 to 18.",
         "It's for teenagers.",
         False, "lost the ages — would be refused"),
        ("It is completely free.",
         "Free! Not a penny.",
         True,  "no numbers to lose"),
    ]

    passed = 0
    for original, rewritten, expected, note in checks:
        got = keeps_the_facts(original, rewritten)
        ok = "✅" if got == expected else "❌"
        passed += got == expected
        print(f"{ok} {note}")
        print(f"     was: {original}")
        print(f"     new: {rewritten}\n")

    print(f"{passed} of {len(checks)} checks behaved as expected.")
    print(f"\nMaster switch ENABLED = {ENABLED}")
    print(f"Never reworded: {', '.join(sorted(VERBATIM_TOPICS))}")
    print("\nTo hear the difference, run:  python3 chat_test.py")
