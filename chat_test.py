#!/usr/bin/env python3
"""
Yobot's typing test bench — talk to the robot's brain without the robot.
================================================================================

PLAIN ENGLISH VERSION
---------------------

WHAT THIS IS FOR

Testing what Yobot says normally means standing in front of him, talking, and
waiting. Slow, and you can't do it quietly at the kitchen table.

This is the same brain with the body unplugged. You type a question, you
instantly see what Yobot would say — and, more usefully, WHY he says it: which
keyword caught the question, which JSON file the answer came out of, and
whether the AI was involved at all.

It touches nothing. No motors, no microphone, no serial cable, no servers.
You can run it while the Greeter is running on the Pi and they will not
interfere with each other.

HOW TO RUN IT

On the Mac, in Terminal:

    cd ~/Projects/OhbotPi2
    python3 chat_test.py

Or on the Pi over SSH:

    ssh michael@192.168.50.155
    cd ~/Projects/Ohbot
    python3 chat_test.py

WHAT YOU'LL SEE

    you › what time do you close?

      language  en
      matched   hours          from library_knowledge.json
      keyword   "what time do you close"
      canned    We're open Monday to Friday, nine in the morning to five...

"matched" means a keyword caught it and Yobot reads that sentence out word for
word — the same words every single time, which is the thing you wanted to fix.
If it says "matched  — nothing" then no keyword caught it and the question
goes to the AI, which gives a different answer each time.

THE REWORDING EXPERIMENT

Type  /reword  to switch on the AI rewording from reword.py. After that, every
canned answer is shown twice: what Yobot says today, and what he would say if
the AI were allowed to put it in his own words. Ask the same question three
times in a row and watch the canned line stay identical while the reworded one
keeps finding new ways to say it.

Nothing you do in here changes the live robot. Rewording is off in the real
robot until we deliberately wire it in.

COMMANDS  (type these instead of a question)

    /help              this list
    /reword            turn the AI rewording on or off
    /ai                turn on answering the no-keyword questions with the AI
    /vs                ALSO show what the AI would say to every question, even
                       when a keyword matched — the side-by-side comparison
    /again             ask the last question again — shows the repetition
    /all               sweep every topic and print its canned answer
    /topics            list all the topic names
    /facts             show the fact sheet that gets handed to the AI
    /en  /es  /auto    force English, force Spanish, or auto-detect
    /reset             forget the conversation so far
    /quit              done
"""

import os
import sys
import textwrap

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Nicer typing — arrow keys and history at the prompt, if available.
try:
    import readline                                        # noqa: F401
except ImportError:
    pass

# ── Reading the .env file ──────────────────────────────────────────────────
# The robot normally gets its keys via yobot_core.load_env(). That route needs
# other libraries installed (pyserial, python-dotenv), which is fine on the Pi
# but often not true on a Mac — and then the key silently fails to load and
# nothing works for a reason that has nothing to do with the key.
#
# So this reads the .env file itself, in about ten lines, needing nothing.

def _load_env_file():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            name = name.strip()
            value = value.strip().strip('"').strip("'")
            # Anything already set in the real environment wins.
            os.environ.setdefault(name, value)


_load_env_file()

try:
    from yobot_core import load_env
    load_env()
except Exception:                                          # noqa: BLE001
    pass

try:
    import knowledge_base as kb
except Exception as e:                                     # noqa: BLE001
    print(f"❌ Could not load knowledge_base.py: {e}")
    print("   Run this from the folder that has the JSON files in it.")
    sys.exit(1)

import reword as rw


# ── A little colour, turned off if the terminal doesn't want it ────────────
_COLOUR = sys.stdout.isatty() and os.environ.get("TERM") != "dumb"


def _c(code, text):
    return f"\033[{code}m{text}\033[0m" if _COLOUR else text


BOLD = lambda t: _c("1", t)       # noqa: E731
DIM = lambda t: _c("2", t)        # noqa: E731
GREEN = lambda t: _c("32", t)     # noqa: E731
YELLOW = lambda t: _c("33", t)    # noqa: E731
BLUE = lambda t: _c("36", t)      # noqa: E731
RED = lambda t: _c("31", t)       # noqa: E731


def wrapped(label, text, colour=str):
    """Print a labelled line, wrapped neatly under its own label."""
    body = textwrap.wrap(text, width=76) or [""]
    print(f"  {DIM(label.ljust(9))} {colour(body[0])}")
    for line in body[1:]:
        print(f"  {' ' * 9} {colour(line)}")


# ============================================================================
# WORKING OUT WHERE AN ANSWER CAME FROM
# ============================================================================
#
# knowledge_base.find_topic() tells us WHICH topic matched but not which
# keyword did it, and not which file the topic came out of. For testing, both
# of those are the interesting part. So we work them out here, by reading —
# knowledge_base.py itself is not modified.

def _topic_sources() -> dict:
    """Which JSON file did each topic finally come from? (Last file wins.)"""
    sources = {}
    for filename in kb.ALL_FILES:
        for topic in kb._read_one(filename):
            sources[topic] = filename
    return sources


SOURCES = _topic_sources()


def explain_match(text: str):
    """Same matching rules as the real robot, but it also tells you why.

    Returns (topic, keyword) — or (None, None) if nothing caught it.
    """
    try:
        clean = kb._normalise(text)
        if not clean:
            return None, None
        word_count = len(clean.split())
        for _, topic, pattern in kb._INDEX:
            if topic in kb._SHORT_ONLY and word_count > kb._SHORT_ONLY_MAX_WORDS:
                continue
            found = pattern.search(clean)
            if found:
                return topic, found.group(0)
        return None, None
    except AttributeError:
        # knowledge_base.py changed shape — fall back to the plain answer.
        return kb.find_topic(text), None


# ============================================================================
# STAGE TWO: THE CLASSIFIER
# ============================================================================
#
# IMPORTANT — the real robot does NOT go straight to the AI when no keyword
# matches. ohbotchat_server.py has a second stage first:
#
#     1. keyword match        (free, instant)
#     2. if nothing matched → ask gpt-4o-mini "which topic is this?"
#     3. if the classifier picks a topic → speak that canned answer, verbatim
#     4. only if it says "general_chat" does the question reach the real AI
#
# So a question that no keyword catches can STILL come back as a stock answer.
# This bench models all three stages so you see what the robot really does.

history = []


def classify(question: str) -> tuple:
    """Stage two. Returns (intent, topic) — mirrors ohbotchat_server.py."""
    topic_list = ", ".join(kb.topic_names())
    prompt = f"""You are a classifier for a robot assistant. Given a visitor's statement,
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
   {topic_list}

2. "general_chat" = anything else — set topic to null. If you are not
   confident the visitor is asking about one of the topics above, choose
   general_chat.

Set language to "en" or "es" based on the visitor's language.
"""
    try:
        import json as _json
        response = rw._get_client().chat.completions.create(
            model=rw.MODEL,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user",   "content": question},
            ],
            max_tokens=100,
            temperature=0.1,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        result = _json.loads(raw)
        return result.get("intent", "general_chat"), result.get("topic")
    except Exception as e:                                 # noqa: BLE001
        return "general_chat", None


def ask_the_ai(question: str, language: str) -> str:
    system = "\n".join(p for p in (
        rw._load_personality(),
        rw.VENUE_INFO,
        kb.fact_sheet(language),
        rw.SAFETY_RULES,
    ) if p)
    try:
        client = rw._get_client()
        messages = [{"role": "system", "content": system}]
        messages.extend(history[-10:])
        messages.append({"role": "user", "content": question})
        response = client.chat.completions.create(
            model=rw.MODEL,
            messages=messages,
            max_tokens=150,
            temperature=0.7,
        )
        reply = response.choices[0].message.content.strip()
        history.append({"role": "user", "content": question})
        history.append({"role": "assistant", "content": reply})
        return reply
    except ImportError:
        return ("❌ the 'openai' library isn't installed on this machine — "
                "run:  pip3 install openai")
    except Exception as e:                                 # noqa: BLE001
        return f"❌ AI call failed: {e}"


# ============================================================================
# ANSWERING ONE TYPED QUESTION
# ============================================================================

class Settings:
    reword = False        # show the AI-reworded version too
    use_ai = False        # actually answer no-keyword questions with the AI
    compare = False       # ALSO ask the AI even when a keyword matched
    language = "auto"     # "auto", "en" or "es"


def language_for(text: str) -> tuple:
    if Settings.language != "auto":
        return Settings.language, "forced"
    return kb.detect_language(text), "auto-detected"


def handle(question: str):
    lang, how = language_for(question)
    topic, keyword = explain_match(question)

    print()
    wrapped("language", f"{lang}  ({how})")

    if not topic:
        wrapped("keyword", "— nothing caught it. The robot now asks the "
                           "classifier which topic this is.", YELLOW)
        if not Settings.use_ai:
            wrapped("", "type /ai to run the classifier and the AI for real", DIM)
            print()
            return

        intent, guessed = classify(question)
        if intent == "local_knowledge" and guessed and guessed in kb.KNOWLEDGE:
            wrapped("classifier", f"picked {guessed} — the robot speaks this "
                                  f"canned answer, word for word", BLUE)
            canned = kb.answer(guessed, lang)
            wrapped("canned", canned, GREEN)
            if Settings.reword:
                new = rw.reword(canned, topic=guessed, language=lang,
                                question=question)
                wrapped("reworded", new if new != canned else "(unchanged)",
                        BOLD if new != canned else DIM)
        else:
            wrapped("classifier", "said general_chat — this reaches the real "
                                  "AI, which has the fact sheet and the "
                                  "conversation so far", BLUE)
            wrapped("ai", ask_the_ai(question, lang), GREEN)
        print()
        return

    source = SOURCES.get(topic, "?")
    canned = kb.answer(topic, lang)

    wrapped("matched", f"{topic}   from {source}", BLUE)
    if keyword:
        wrapped("keyword", f'"{keyword}"', DIM)
    if topic in rw.VERBATIM_TOPICS:
        wrapped("locked", "on the verbatim list — never reworded, by design",
                YELLOW)
    wrapped("canned", canned or "(this topic has no answer in that language!)",
            GREEN if canned else RED)

    if Settings.reword:
        new = rw.reword(canned, topic=topic, language=lang, question=question)
        if new == canned:
            wrapped("reworded", "(unchanged — see the warning above)", DIM)
        else:
            wrapped("reworded", new, BOLD)

    # /vs — ask the AI the same question, so you can see whether it would have
    # done better. This is NOT what the robot says; the canned line above is.
    if Settings.compare:
        label = f"- {topic.replace('_', ' ')}:"
        if label not in kb.fact_sheet(lang):
            wrapped("warning", "this topic is NOT in the AI's fact sheet — so "
                               "the AI is guessing below, not quoting", YELLOW)
        wrapped("ai would", ask_the_ai(question, lang), BLUE)
    print()


# ============================================================================
# COMMANDS
# ============================================================================

def show_all():
    """Every topic and the exact words Yobot reads out for it."""
    lang = "es" if Settings.language == "es" else "en"
    print()
    print(BOLD(f"  All {len(kb.KNOWLEDGE)} topics, in {lang}:"))
    current_file = None
    for filename in kb.ALL_FILES:
        topics = [t for t in kb.topic_names() if SOURCES.get(t) == filename]
        if not topics:
            continue
        if filename != current_file:
            print(f"\n  {DIM('── ' + filename + ' ' + '─' * (60 - len(filename)))}")
            current_file = filename
        for topic in topics:
            text = kb.answer(topic, lang)
            lock = YELLOW("  [never reworded]") if topic in rw.VERBATIM_TOPICS else ""
            print(f"\n  {BOLD(topic)}{lock}")
            body = textwrap.wrap(text or "(no answer in this language)", width=74)
            for line in body:
                print(f"    {(GREEN if text else RED)(line)}")
    print()


def show_topics():
    print()
    for filename in kb.ALL_FILES:
        topics = [t for t in kb.topic_names() if SOURCES.get(t) == filename]
        print(f"  {BOLD(filename)}  ({len(topics)})")
        print(textwrap.fill(", ".join(topics), width=74,
                            initial_indent="    ", subsequent_indent="    "))
    overridden = [t for t in kb._read_one(kb.IDENTITY_FILE)
                  if SOURCES.get(t) != kb.IDENTITY_FILE]
    if overridden:
        print(f"\n  {YELLOW('Overridden by a venue file:')} {', '.join(overridden)}")
    print()


# ============================================================================
# "BUT OPENAI *IS* INSTALLED"
# ============================================================================
#
# A Mac usually has several Pythons on it — Apple's own, one from Homebrew,
# maybe one from python.org, maybe a virtual environment. Installing a library
# puts it inside ONE of them. If you type `python3` and get a different one,
# that Python honestly cannot see the library, even though it is definitely
# installed on the machine.
#
# So rather than telling you to install something you already installed, this
# goes and finds the Python that HAS it and tells you the exact command to run.

_HERE = os.path.dirname(os.path.abspath(__file__))


def find_python_with_openai():
    """Hunt for a Python on this machine that can see the openai library."""
    import glob
    import subprocess

    places = [
        "/opt/homebrew/bin",                     # Homebrew, Apple Silicon
        "/usr/local/bin",                        # Homebrew, Intel
        "/usr/bin",                              # Apple's own
        os.path.expanduser("~/.pyenv/shims"),
        "/Library/Frameworks/Python.framework/Versions/*/bin",
        os.path.expanduser("~/Library/Python/*/bin"),
    ]
    candidates = []
    # Virtual environments FIRST — on the Pi this project runs out of
    # ~/Projects/Ohbot/venv, and plain `python3` genuinely cannot see anything
    # installed in there. This is the usual reason for "but it IS installed".
    home = os.path.expanduser("~")
    venv_spots = [
        os.path.join(_HERE, "venv", "bin", "python3"),
        os.path.join(_HERE, ".venv", "bin", "python3"),
        os.path.join(_HERE, "*", "bin", "python3"),
        os.path.join(os.path.dirname(_HERE), "*", "bin", "python3"),
        os.path.join(home, "venv", "bin", "python3"),
        os.path.join(home, ".venv", "bin", "python3"),
        os.path.join(home, "Projects", "*", "venv", "bin", "python3"),
        os.path.join(home, "Projects", "*", ".venv", "bin", "python3"),
    ]
    for spot in venv_spots:
        candidates += sorted(glob.glob(spot))
    for place in places:
        candidates += glob.glob(os.path.join(place, "python3*"))

    seen = {os.path.realpath(sys.executable)}
    for path in candidates:
        real = os.path.realpath(path)
        if real in seen or not os.access(path, os.X_OK):
            continue
        seen.add(real)
        try:
            done = subprocess.run([path, "-c", "import openai"],
                                  capture_output=True, timeout=15)
            if done.returncode == 0:
                return path
        except Exception:                                  # noqa: BLE001
            continue
    return None


def ai_status() -> tuple:
    """Can we actually reach the AI? Returns (ok, message telling you why not).

    Checks the two things that are separately easy to get wrong: the openai
    library being visible to THIS Python, and the API key being readable.
    """
    try:
        import openai                                      # noqa: F401
    except ImportError:
        running = f"{sys.executable}  (Python {sys.version.split()[0]})"
        other = find_python_with_openai()
        if other:
            script = os.path.join(_HERE, os.path.basename(__file__))
            return False, (
                "this Python can't see the 'openai' library — but another one "
                "on your Mac can.\n"
                f"             running now: {running}\n"
                f"             has openai:  {other}\n\n"
                "             ▸ Run it with that one instead:\n"
                f"                 {other} {script} --vs\n\n"
                "             (Or install it into the one you're using:\n"
                f"                 {sys.executable} -m pip install openai )")
        return False, (
            "the 'openai' library isn't visible to this Python.\n"
            f"             running now: {running}\n"
            "             I looked for another Python on this Mac that has it "
            "and found none.\n\n"
            "             ▸ Install it into the Python you're using:\n"
            f"                 {sys.executable} -m pip install openai")
    if not os.environ.get("OPENAI_API_KEY"):
        return False, ("no OPENAI_API_KEY found. It should be in the .env file "
                       "next to this script.")
    return True, ""


def banner():
    ok, why = ai_status()
    print()
    print(BOLD("  Yobot typing test bench"))
    print(DIM(f"  {len(kb.KNOWLEDGE)} topics loaded from "
              f"{', '.join(kb.ALL_FILES)}"))

    if ok:
        print(f"  AI: {GREEN('✅ ready')}")
    else:
        print(f"  AI: {RED('❌ not available')} — {why}")
        print(DIM("      Canned answers below still work fine without it."))

    print()
    print(BOLD("  Right now:"))
    rows = [
        ("canned answers", "always on", True),
        ("/vs", "AI answer alongside every canned one", Settings.compare),
        ("/ai", "AI for questions no keyword catches", Settings.use_ai),
        ("/reword", "reword the canned answers", Settings.reword),
    ]
    for name, what, on in rows:
        state = GREEN("ON ") if on else RED("OFF")
        print(f"    {state}  {name:<9} {DIM(what)}")
    if not (Settings.use_ai or Settings.compare):
        print()
        print(YELLOW("  ▸ You will not see any AI answers until you type /vs "
                     "(or /ai)."))
        print(DIM("    Or start it already switched on:  "
                  "python3 chat_test.py --vs"))
    print()
    print(DIM("  Type a question, or /help for the commands. /quit when done."))
    print()


def main():
    # Command-line switches, so you don't have to type the commands each time:
    #     python3 chat_test.py --vs        side-by-side on from the start
    #     python3 chat_test.py --ai        AI for unmatched questions
    #     python3 chat_test.py --reword    rewording on
    #     python3 chat_test.py --es        Spanish
    flags = [a.lower() for a in sys.argv[1:]]

    if "--doctor" in flags:
        print()
        print(BOLD("  Which Python am I, and what can I see?"))
        print(f"    running        {sys.executable}")
        print(f"    version        {sys.version.split()[0]}")
        for name in ("openai", "dotenv", "httpx"):
            try:
                mod = __import__(name)
                where = getattr(mod, "__file__", "?")
                print(f"    {name:<14} {GREEN('found')}  {where}")
            except ImportError:
                print(f"    {name:<14} {RED('missing')}")
        env_path = os.path.join(_HERE, ".env")
        print(f"    .env file      {'found' if os.path.exists(env_path) else 'MISSING'}"
              f"  {env_path}")
        key = os.environ.get("OPENAI_API_KEY", "")
        print(f"    api key        {('loaded, ends ...' + key[-4:]) if key else RED('not loaded')}")
        other = find_python_with_openai()
        if other:
            print(f"\n    Another Python here that HAS openai:\n      {other}")
        print()
        return

    if "--vs" in flags:
        Settings.compare = Settings.use_ai = True
    if "--ai" in flags:
        Settings.use_ai = True
    if "--reword" in flags:
        Settings.reword = rw.ENABLED = True
    if "--es" in flags:
        Settings.language = "es"

    banner()
    last_question = ""

    while True:
        try:
            raw = input(BOLD("you › ")).strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Bye.\n")
            return

        if not raw:
            continue

        if raw.startswith("/"):
            command = raw.lower().split()[0]

            if command in ("/quit", "/q", "/exit"):
                print("  Bye.\n")
                return

            elif command in ("/help", "/h", "/?"):
                print(__doc__.split("COMMANDS")[1])

            elif command == "/reword":
                rw.ENABLED = Settings.reword = not Settings.reword
                state = GREEN("ON — canned answers get reworded by the AI") \
                    if Settings.reword else DIM("OFF")
                print(f"  rewording {state}\n")

            elif command == "/ai":
                Settings.use_ai = not Settings.use_ai
                state = GREEN("ON") if Settings.use_ai else DIM("OFF")
                print(f"  answering no-keyword questions with the AI: {state}\n")

            elif command == "/again":
                if last_question:
                    print(DIM(f"  (asking again: {last_question})"))
                    handle(last_question)
                else:
                    print("  Ask something first.\n")

            elif command == "/all":
                show_all()

            elif command == "/topics":
                show_topics()

            elif command == "/vs":
                Settings.compare = not Settings.compare
                if Settings.compare:
                    Settings.use_ai = True
                state = GREEN("ON") if Settings.compare else DIM("OFF")
                print(f"  also showing what the AI would say: {state}\n")

            elif command == "/facts":
                lang = "es" if Settings.language == "es" else "en"
                print()
                sheet = kb.fact_sheet(lang)
                print(sheet)
                print()
                # Work out what's genuinely missing rather than assuming.
                missing = [t for t in kb.topic_names()
                           if f"- {t.replace('_', ' ')}:" not in sheet]
                if missing:
                    print(YELLOW("  NOT in the fact sheet above — the AI has "
                                 "never heard of these:"))
                    print(textwrap.fill(", ".join(missing), width=74,
                                        initial_indent="    ",
                                        subsequent_indent="    "))
                    print(DIM("    (greeting and goodbye are left out on "
                              "purpose — the personality covers them)"))
                else:
                    print(GREEN("  Every topic is in the fact sheet."))
                print()

            elif command in ("/en", "/es", "/auto"):
                Settings.language = command[1:]
                print(f"  language: {BOLD(Settings.language)}\n")

            elif command == "/reset":
                history.clear()
                rw.forget_everything()
                print("  Conversation forgotten.\n")

            else:
                print(f"  Don't know {command}. Try /help\n")
            continue

        last_question = raw
        handle(raw)


if __name__ == "__main__":
    main()
