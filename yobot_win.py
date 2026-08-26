#!/usr/bin/env python3
"""
Yobot on Windows — Launcher
Version: 1.0.0

The Windows front door for the Yobot project. Uses the same shared
yobot_core library as the Raspberry Pi and the Mac — nothing here is
Windows-only except this launcher's help text and the install advice.

EASIEST: don't run this file directly — use the batch file next to it, which
finds Yobot's venv python for you and works the same in PowerShell and in
Command Prompt:

    cd D:\Projects\OhbotPi2
    .\yobot.bat ports
    .\yobot.bat test
    .\yobot.bat say "Hello there!"
    .\yobot.bat

The modes below are what those commands run.

Four ways to run it:

  python yobot_win.py test
      Hardware smoke test — no internet or API keys needed.
      Moves the head, blinks, cycles the eye LEDs, resets.
      Run this FIRST after plugging Yobot into the PC.

  python yobot_win.py say "Hello there!"
      Speaks through Azure with full lip sync — tests audio output,
      the API keys, and lip sync. Needs internet + .env keys.

  python yobot_win.py
      The full conversation bot. Starts the brain server
      (ohbotchat_server.py) automatically, then listens and chats.
      Wake a sleeping Yobot by pressing Enter.

  python yobot_win.py ports
      Lists every serial port Windows can see, with its description.
      Use this if "Robot not found" appears — it tells you whether
      Windows sees the robot at all.

Audio: uses Windows' current default microphone and speaker (whatever is
selected in Settings → System → Sound). Playback uses winsound, which is
built into Python — nothing extra to install.

Remember: only one computer can run Yobot at a time. Stop the Pi's
services and plug the USB cable into the PC first — see the "Windows" folder.
"""

import os
import sys
import time
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)


# ─────────────────────────────────────────────────────────────────────────────
# DEPENDENCY CHECK — fail with friendly instructions, not a crash
# ─────────────────────────────────────────────────────────────────────────────

def check_dependencies(need_azure=False, need_chat=False):
    missing = []

    def probe(module, pip_name):
        try:
            __import__(module)
        except ImportError:
            missing.append(pip_name)

    probe("serial", "pyserial")
    probe("lxml", "lxml")
    if need_azure or need_chat:
        probe("azure.cognitiveservices.speech", "azure-cognitiveservices-speech")
    if need_chat:
        probe("httpx", "httpx")
        probe("flask", "flask")
        probe("openai", "openai")

    if missing:
        print("[X] Some Python packages are missing:")
        print(f"    {', '.join(missing)}\n")
        print("    If you haven't made Yobot's venv yet, paste these two lines into")
        print("    PowerShell, one at a time:\n")
        print("        python -m venv $HOME\\yobot-venv")
        print('        & "$HOME\\yobot-venv\\Scripts\\pip.exe" install '
              + ' '.join(missing) + "\n")
        print("    (In Command Prompt instead: drop the & and use %USERPROFILE%")
        print("     where PowerShell uses $HOME.)\n")
        print("    Then run Yobot with:   .\\yobot.bat test")
        print("    Full guide: Windows\\START HERE.md in the project folder")
        sys.exit(1)


def warn_if_not_windows():
    """This file is the Windows front door. Point strays at the right one."""
    import platform
    if platform.system() != 'Windows':
        print(f"Note: this is the Windows launcher, but you're on "
              f"{platform.system()}.")
        print("  Mac      -> use  yobot_mac.py")
        print("  Pi/Linux -> use the Launcher web page, or run the scripts directly")
        print("Carrying on anyway.\n")


# ─────────────────────────────────────────────────────────────────────────────
# MODE 0: LIST SERIAL PORTS (the "Robot not found" helper)
# ─────────────────────────────────────────────────────────────────────────────

def list_ports():
    check_dependencies()
    import serial.tools.list_ports

    ports = list(serial.tools.list_ports.comports())

    print("=" * 60)
    print("  Serial ports Windows can see right now")
    print("=" * 60)

    if not ports:
        print("\n  (none at all)\n")
        print("  Windows isn't seeing ANY serial device. That usually means:")
        print("    1. The USB cable isn't plugged in, or is a charge-only cable")
        print("    2. Yobot's power supply is off")
        print("    3. The USB-to-serial driver isn't installed — open Device")
        print("       Manager and look for a yellow warning triangle under")
        print("       'Other devices'. See Windows\\START HERE.md for the fix.")
        return

    for p in ports:
        print(f"\n  {p.device}")
        print(f"      {p.description}")
        print(f"      {p.hwid}")

    print("\n  Yobot is whichever one mentions a USB serial chip — commonly")
    print("  CH340, CP210x, FTDI, or 'USB Serial Device'. If auto-detection")
    print("  keeps failing, add this line to your .env file:")
    print("\n      YOBOT_SERIAL_PORT=COM4        (use the right number)\n")


# ─────────────────────────────────────────────────────────────────────────────
# MODE 1: HARDWARE TEST (no internet needed)
# ─────────────────────────────────────────────────────────────────────────────

def run_hardware_test():
    check_dependencies()
    import yobot_core as yobot

    print("=" * 60)
    print(f"  Yobot Hardware Test  —  {yobot.PLATFORM}")
    print("=" * 60)

    if not yobot.init():
        print("\nTroubleshooting:")
        print("  1. Is the USB cable plugged into THIS PC (not the Pi or Mac)?")
        print("  2. Is Yobot's power supply on?")
        print("  3. Unplug the USB cable, wait 5 seconds, plug it back in.")
        print("  4. Run:  python yobot_win.py ports")
        print("     — that shows whether Windows sees the robot at all.")
        sys.exit(1)

    print("\n[OK] Connected! Running movement test...\n")

    print("  Eyes green...")
    yobot.baseColour(0, 10, 0)
    yobot.wait(1)

    print("  Head turn left / right...")
    yobot.move(yobot.HEADTURN, 7, 4)
    yobot.wait(1)
    yobot.move(yobot.HEADTURN, 3, 4)
    yobot.wait(1)
    yobot.move(yobot.HEADTURN, 5, 4)
    yobot.wait(1)

    print("  Head nod...")
    yobot.move(yobot.HEADNOD, 7, 4)
    yobot.wait(0.8)
    yobot.move(yobot.HEADNOD, 3, 4)
    yobot.wait(0.8)
    yobot.move(yobot.HEADNOD, 5, 4)
    yobot.wait(1)

    print("  Blink...")
    yobot.move(yobot.LIDBLINK, 0, 10)
    yobot.wait(0.3)
    yobot.move(yobot.LIDBLINK, 10, 10)
    yobot.wait(1)

    print("  Mouth open / close...")
    yobot.move(yobot.TOPLIP, 7, 5)
    yobot.move(yobot.BOTTOMLIP, 7, 5)
    yobot.wait(1)
    yobot.move(yobot.TOPLIP, 5, 5, avoid=False)
    yobot.move(yobot.BOTTOMLIP, 5, 5, avoid=False)
    yobot.wait(1)

    print("  Eye colors: red... blue... off")
    yobot.baseColour(10, 0, 0)
    yobot.wait(0.7)
    yobot.baseColour(0, 0, 10)
    yobot.wait(0.7)

    print("  Reset to rest position...")
    yobot.reset()
    yobot.close()

    print("\n[OK] Hardware test complete! If the head moved and the eyes")
    print("     changed color, Yobot is working on this PC.")
    print('     Next step:  python yobot_win.py say "Hello from my PC!"')


# ─────────────────────────────────────────────────────────────────────────────
# MODE 2: SPEECH TEST (needs internet + .env keys)
# ─────────────────────────────────────────────────────────────────────────────

def run_say(text):
    check_dependencies(need_azure=True)
    import asyncio
    import yobot_core as yobot

    if not os.environ.get("AZURE_SPEECH_KEY"):
        print("[X] AZURE_SPEECH_KEY not found.")
        print("    Make sure the .env file is in the same folder as this script.")
        print("    Windows tip: File Explorer hides file extensions by default,")
        print("    so a file that looks like '.env' can really be '.env.txt'.")
        print("    Turn on View -> Show -> File name extensions to check.")
        sys.exit(1)

    from ohbot_azure import AzureSpeechManager, AsyncOhbotController

    async def _say():
        print("Connecting to Yobot...")
        if not yobot.init():
            print("(no robot found — will speak without moving)")

        azure = AzureSpeechManager()
        controller = AsyncOhbotController(azure)
        await controller.start()
        try:
            await controller.set_eye_color(0, 10, 5)
            await controller.say(text)
            await controller.set_eye_color(0, 0, 0)
        finally:
            await controller.stop()

    asyncio.run(_say())
    print("\n[OK] If you heard the voice from the PC's speaker and saw the")
    print("     mouth move, speech is fully working.")
    print("     Next step:  python yobot_win.py   (the full conversation bot)")


# ─────────────────────────────────────────────────────────────────────────────
# MODE 3: FULL CONVERSATION BOT
# ─────────────────────────────────────────────────────────────────────────────

def run_full_bot():
    check_dependencies(need_azure=True, need_chat=True)
    import asyncio
    import yobot_core  # noqa: F401 — loads the .env keys

    import httpx

    # Start the brain server (handles OpenAI) as a background process,
    # unless one is already running (e.g. started by hand).
    server_url = os.environ.get("OHBOT_SERVER_URL", "http://localhost:5002")
    server_proc = None

    def server_alive():
        try:
            r = httpx.get(f"{server_url}/health", timeout=2.0)
            return r.status_code == 200
        except Exception:
            return False

    if server_alive():
        print("[OK] Brain server already running")
    else:
        print("Starting brain server (ohbotchat_server.py)...")
        server_proc = subprocess.Popen(
            [sys.executable, os.path.join(SCRIPT_DIR, "ohbotchat_server.py")],
            cwd=SCRIPT_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(30):          # wait up to ~15 seconds
            if server_alive():
                print("[OK] Brain server is up")
                break
            time.sleep(0.5)
        else:
            print("[X] Brain server didn't start. Try running it by hand to")
            print("    see the error:  python ohbotchat_server.py")
            print("    (Windows Firewall may also ask for permission the first")
            print("     time — click Allow.)")
            if server_proc:
                server_proc.terminate()
            sys.exit(1)

    # Run the conversation bot (same code as the Pi and the Mac)
    import ohbot_chat
    try:
        asyncio.run(ohbot_chat.main())
    except KeyboardInterrupt:
        pass
    finally:
        if server_proc:
            print("Stopping brain server...")
            server_proc.terminate()


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    warn_if_not_windows()

    arg = sys.argv[1].lower() if len(sys.argv) > 1 else None

    if arg == "test":
        run_hardware_test()
    elif arg in ("ports", "port"):
        list_ports()
    elif arg == "say":
        if len(sys.argv) < 3:
            print('Usage:  python yobot_win.py say "Something to say"')
            sys.exit(1)
        run_say(sys.argv[2])
    elif arg in ("help", "-h", "--help", "/?"):
        print(__doc__)
    elif arg:
        print(f"Unknown option: {sys.argv[1]}")
        print(__doc__)
        sys.exit(1)
    else:
        run_full_bot()
