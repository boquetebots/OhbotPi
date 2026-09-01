#!/usr/bin/env python3
"""
announce_ip.py — "Where is the Pi?" insurance.
================================================================================

THE PROBLEM THIS SOLVES

You plug the robot in at the Clubhouse. It boots. It joins their WiFi. And now
you have no idea what its address is, so you cannot open the Launcher page and
you cannot SSH in. Asking the network to tell you (yobot1.local, scanning, etc.)
often fails on venue networks, which block exactly that kind of lookup.

So instead of asking the network, we make the Pi TELL YOU. Three ways at once,
because any one of them can fail:

  1. IT SAYS IT OUT LOUD.  About a minute after power-on the robot speaks its
     own address through its speaker. You write it down. Done. This works even
     if the WiFi blocks everything else, because it uses no network at all.

  2. IT WRITES IT ON THE SD CARD.  A file called YOBOT_IP.txt is saved to the
     card's boot partition. If the robot is unplugged, pull the SD card, put it
     in your Mac, and open the file. That partition is readable by Macs and PCs.

  3. IT WRITES IT IN THE PROJECT FOLDER.  A copy lands in the Ohbot folder as
     last_known_ip.txt, so you can see it over SAMBA once you're connected.

This runs by itself at every boot. You never have to remember it.

--------------------------------------------------------------------------------
TO RUN IT BY HAND (to test it):

    cd ~/Projects/Ohbot
    python3 announce_ip.py

TO JUST TEST THE SOUND (no network needed):

    python3 announce_ip.py --test

TO MAKE IT RUN AT EVERY BOOT:

    bash install_ip_announcer.sh

--------------------------------------------------------------------------------
IT NEEDS espeak-ng. Install it once with:

    sudo apt install espeak-ng -y

We deliberately use espeak-ng and not the robot's normal Azure voice. Azure
needs working internet and valid API keys. If either of those is broken, that
is EXACTLY when you most need to hear the address. espeak-ng is installed on
the Pi itself and always works. It sounds robotic. That is fine — it only has
to read you eleven digits.

IMPORTANT — HOW THE SOUND ACTUALLY GETS OUT:

We do NOT let espeak-ng play the audio itself. On this Pi that fails silently:
no sound, no error message, exit code zero, and you conclude the speaker is
broken when it is fine. Instead espeak-ng writes a WAV file and we play that
file with pw-play, the same way the robot plays its Azure voice and its
thinking chime. See find_audio_player() below for the full story.
"""

import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# ── Settings you might want to change ────────────────────────────────────────

# How long to wait for the WiFi to connect before giving up (seconds).
# The Pi's network usually comes up 20-40 seconds after power-on.
WAIT_FOR_NETWORK_SECONDS = 90

# Say the address this many times, with a pause between. Twice is usually
# right — the first time you're still fumbling for a pen.
REPEAT_COUNT = 2

# Pause between repeats, in seconds.
PAUSE_BETWEEN_REPEATS = 3

# espeak-ng speaking speed. Lower is slower. 130 is slower than normal speech,
# which is what you want for reading numbers aloud. Confirmed clear on the
# robot's speaker 2026-08-07 — dots and digits both came through distinctly.
SPEECH_SPEED = 130

# Where to write the copies of the address.
PROJECT_DIR = Path.home() / "Projects" / "Ohbot"

# The SD card's boot partition. Newer Raspberry Pi OS uses the first path,
# older versions use the second. We try both and use whichever exists.
BOOT_PARTITIONS = [Path("/boot/firmware"), Path("/boot")]


# ── Finding our own address ──────────────────────────────────────────────────

def find_my_ip():
    """Return this Pi's address on the network, or None if it isn't connected.

    The trick here looks odd: we open a connection toward a public address
    (Google's DNS server) but never actually send anything. We only do it so
    the operating system has to decide which network card it WOULD use, and
    then we ask it which address that card has. This is far more reliable than
    looking up the hostname, which often just answers "127.0.0.1" (itself).
    """
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("8.8.8.8", 80))
        ip = probe.getsockname()[0]
    except OSError:
        # No route to anywhere — we are not on a network yet.
        return None
    finally:
        probe.close()

    # 127.x.x.x means "myself", which is not useful to anyone else.
    if ip.startswith("127."):
        return None
    return ip


def wait_for_ip(timeout_seconds):
    """Keep checking for an address until we get one or we run out of time."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        ip = find_my_ip()
        if ip:
            return ip
        time.sleep(2)
    return None


def find_my_wifi_name():
    """Return the name of the WiFi network we joined, or None.

    Useful because it tells you WHICH network it picked — home lab or
    Clubhouse — which is often the actual thing that went wrong.
    """
    try:
        output = subprocess.run(
            ["iwgetid", "-r"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()
        return output or None
    except (OSError, subprocess.SubprocessError):
        return None


# ── Saying it out loud ───────────────────────────────────────────────────────

def spoken_form(ip):
    """Turn "192.168.50.155" into words that survive a cheap speaker.

    Said normally, "192" comes out as "one hundred ninety two" and the dots
    disappear entirely, so you cannot tell where one number ends and the next
    begins. Reading it digit by digit with the word "dot" between removes all
    of that ambiguity.
    """
    parts = []
    for chunk in ip.split("."):
        parts.append(" ".join(chunk))   # "192" -> "1 9 2"
        parts.append("dot")
    parts.pop()                          # drop the trailing "dot"
    return " ".join(parts)


def find_audio_player():
    """Pick the command that can actually play a WAV file on this Pi.

    THIS IS THE BIT THAT CAUGHT US OUT, so it's worth explaining.

    If you just run `espeak-ng "hello"`, espeak tries to open the sound card
    directly through ALSA. On this Pi that fails — yobot_core.py has the same
    note: "aplay's direct ALSA open fails oddly (error 524) while pw-play
    works." The nasty part is that espeak-ng fails SILENTLY. No error, no
    sound, exit code zero. It looks like the speaker is broken when it isn't.

    So we never let espeak-ng play anything. We have it write a WAV file
    instead, and then play that file with pw-play — the exact same route the
    robot already uses for its Azure voice and its thinking chime. If that
    path works for the robot, it works for us.
    """
    if shutil.which("pw-play"):
        return ["pw-play"]
    if shutil.which("paplay"):
        return ["paplay"]
    return ["aplay", "-D", "plug:default"]


def say(text):
    """Speak text out loud. Returns True if it probably worked."""
    wav_path = Path(tempfile.gettempdir()) / "yobot_announce.wav"

    # Step 1 — turn the words into a WAV file. The -w flag means "write to a
    # file instead of playing", which sidesteps espeak's broken audio output.
    try:
        subprocess.run(
            ["espeak-ng", "-v", "en", "-s", str(SPEECH_SPEED),
             "-w", str(wav_path), text],
            timeout=60, check=True,
        )
    except FileNotFoundError:
        print("espeak-ng is not installed. Install it with:")
        print("    sudo apt install espeak-ng -y")
        return False
    except (OSError, subprocess.SubprocessError) as e:
        print(f"Could not turn the text into speech: {e}")
        return False

    if not wav_path.exists() or wav_path.stat().st_size == 0:
        print("espeak-ng ran but produced an empty sound file.")
        return False

    # Step 2 — play the WAV the way everything else on this robot plays sound.
    player = find_audio_player()
    try:
        result = subprocess.run(player + [str(wav_path)], timeout=60)
        if result.returncode != 0:
            print(f"'{player[0]}' couldn't play the sound "
                  f"(exit code {result.returncode}).")
            print("Try each of these by hand to see which one works:")
            print(f"    pw-play {wav_path}")
            print(f"    aplay -D plug:default {wav_path}")
            print(f"    paplay {wav_path}")
            return False
        return True
    except FileNotFoundError:
        print(f"'{player[0]}' is not installed.")
        print("Install PipeWire's player with:")
        print("    sudo apt install pipewire-audio-client-libraries -y")
        return False
    except (OSError, subprocess.SubprocessError) as e:
        print(f"Could not play the sound: {e}")
        return False


# ── Writing it down ──────────────────────────────────────────────────────────

def write_everywhere(ip, wifi_name):
    """Save the address to every place we can, and report where it landed."""
    hostname = socket.gethostname()
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")

    contents = (
        f"Yobot network address\n"
        f"=====================\n\n"
        f"IP address : {ip}\n"
        f"Hostname   : {hostname}\n"
        f"WiFi       : {wifi_name or 'unknown'}\n"
        f"Written    : {stamp}\n\n"
        f"Open the Launcher in a browser:\n"
        f"    http://{ip}:5000\n\n"
        f"SSH in from the Mac:\n"
        f"    ssh yobot@{ip}\n\n"
        f"This file is rewritten every time the Pi boots.\n"
    )

    written_to = []

    # The SD card boot partition — readable on a Mac or PC if you pull the card.
    for boot in BOOT_PARTITIONS:
        if boot.is_dir():
            try:
                (boot / "YOBOT_IP.txt").write_text(contents)
                written_to.append(str(boot / "YOBOT_IP.txt"))
            except OSError:
                # Usually means the partition is read-only or we lack
                # permission. Not fatal — we still have the other copies.
                pass
            break

    # The project folder — visible over SAMBA.
    try:
        PROJECT_DIR.mkdir(parents=True, exist_ok=True)
        (PROJECT_DIR / "last_known_ip.txt").write_text(contents)
        written_to.append(str(PROJECT_DIR / "last_known_ip.txt"))
    except OSError:
        pass

    # The home folder — always writable, last resort.
    try:
        (Path.home() / "YOBOT_IP.txt").write_text(contents)
        written_to.append(str(Path.home() / "YOBOT_IP.txt"))
    except OSError:
        pass

    return written_to


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    quiet = "--quiet" in sys.argv        # write the files but don't speak

    # ── Sound test mode ─────────────────────────────────────────────────────
    # Checks only the speaking part, with no network involved, so you can tell
    # a sound problem apart from a WiFi problem.
    if "--test" in sys.argv:
        player = find_audio_player()
        print(f"espeak-ng found : {bool(shutil.which('espeak-ng'))}")
        print(f"Audio player    : {' '.join(player)}")
        print("")
        print("You should now hear a test phrase...")
        if say("Hello. This is a test. My network address is 1 2 3 dot 4 5 6"):
            print("")
            print("Sound worked.")
            return 0
        print("")
        print("Sound did NOT work. The messages above say why.")
        print("If the Greeter is running it may be holding the speaker —")
        print("stop it and try again:")
        print("    systemctl --user stop ohbot-conversation ohbot-server")
        return 1

    print("Looking for this Pi's network address...")
    ip = wait_for_ip(WAIT_FOR_NETWORK_SECONDS)

    if not ip:
        print("No network address found.")
        if not quiet:
            say(
                "I could not join a wireless network. "
                "Please check the WiFi name and password."
            )
        # Exit code 1 so systemd logs this as a failure you can find later.
        return 1

    wifi_name = find_my_wifi_name()
    print(f"Address : {ip}")
    print(f"WiFi    : {wifi_name or 'unknown'}")

    written_to = write_everywhere(ip, wifi_name)
    for path in written_to:
        print(f"Saved   : {path}")

    if not quiet:
        # Small pause so the speaker has finished waking up. USB audio devices
        # often swallow the first half second of sound right after boot.
        time.sleep(2)
        for i in range(REPEAT_COUNT):
            say(f"My network address is {spoken_form(ip)}")
            if i < REPEAT_COUNT - 1:
                time.sleep(PAUSE_BETWEEN_REPEATS)

    return 0


if __name__ == "__main__":
    sys.exit(main())
